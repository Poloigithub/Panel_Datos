"""Descarga el paro registrado del SEPE.

El SEPE publica un CSV por año con el paro registrado de **todos los
municipios de España, mes a mes**, desglosado por sexo, tramo de edad y sector
de actividad. De ahí salen a la vez los tres ámbitos del panel y el detalle
municipal de la provincia de Castellón.

Dos particularidades de la fuente que condicionan todo lo demás:

- **El secreto estadístico**: los valores inferiores a cinco se publican como
  `<5`. No son ceros y no se pueden tratar como tales.
- **El peso**: cada fichero anual ronda las cien mil filas, así que por
  defecto sólo se rehacen el año en curso y el anterior; el resto del
  histórico ya está en el repositorio y no se vuelve a descargar. Con
  `--desde AAAA` se reconstruye todo.

Uso:
    python scripts/descargar_paro.py            # año en curso y anterior
    python scripts/descargar_paro.py --desde 2006
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "data" / "paro-registrado"

URL = ("https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/"
       "datos/Paro_por_municipios_{anyo}_csv.csv")
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

# El primer año con fichero publicado en este formato.
PRIMER_ANYO = 2006

AMBITOS = {
    "espana": {"nombre": "España", "tipo": "Nacional"},
    "comunitat-valenciana": {"nombre": "Comunitat Valenciana", "tipo": "Comunidad autónoma"},
    "castellon": {"nombre": "Castellón", "tipo": "Provincia"},
}
CODIGO_CCAA_VALENCIANA = "10"
CODIGO_PROVINCIA_CASTELLON = "12"

# columna del CSV -> (magnitud, sexo)
COLUMNAS = {
    "total Paro Registrado": ("paro_total", None),
    "Paro hombre edad < 25": ("paro_menores_25", "hombres"),
    "Paro hombre edad 25 -45": ("paro_25_44", "hombres"),
    "Paro hombre edad >=45": ("paro_45_mas", "hombres"),
    "Paro mujer edad < 25": ("paro_menores_25", "mujeres"),
    "Paro mujer edad 25 -45": ("paro_25_44", "mujeres"),
    "Paro mujer edad >=45": ("paro_45_mas", "mujeres"),
    "Paro Agricultura": ("paro_agricultura", None),
    "Paro Industria": ("paro_industria", None),
    "Paro Construcción": ("paro_construccion", None),
    "Paro Servicios": ("paro_servicios", None),
    "Paro Sin empleo Anterior": ("paro_sin_empleo_anterior", None),
}

INDICADORES = {
    "paro_total": {"titulo": "Paro registrado", "unidad": "personas", "decimales": 0,
                   "por_sexo": True},
    "paro_menores_25": {"titulo": "Menores de 25 años", "unidad": "personas",
                        "decimales": 0, "por_sexo": True, "sobre_total": "paro_total"},
    "paro_25_44": {"titulo": "De 25 a 44 años", "unidad": "personas",
                   "decimales": 0, "por_sexo": True, "sobre_total": "paro_total"},
    "paro_45_mas": {"titulo": "De 45 años o más", "unidad": "personas",
                    "decimales": 0, "por_sexo": True, "sobre_total": "paro_total"},
    "paro_agricultura": {"titulo": "Agricultura", "unidad": "personas",
                         "decimales": 0, "por_sexo": False, "sobre_total": "paro_total"},
    "paro_industria": {"titulo": "Industria", "unidad": "personas",
                       "decimales": 0, "por_sexo": False, "sobre_total": "paro_total"},
    "paro_construccion": {"titulo": "Construcción", "unidad": "personas",
                          "decimales": 0, "por_sexo": False, "sobre_total": "paro_total"},
    "paro_servicios": {"titulo": "Servicios", "unidad": "personas",
                       "decimales": 0, "por_sexo": False, "sobre_total": "paro_total"},
    "paro_sin_empleo_anterior": {"titulo": "Sin empleo anterior", "unidad": "personas",
                                 "decimales": 0, "por_sexo": False, "sobre_total": "paro_total"},
}


class Censurado(Exception):
    """El SEPE oculta los valores menores de cinco."""


def valor(texto: str) -> int:
    """Convierte una celda en número; los valores ocultos se señalan aparte."""
    limpio = (texto or "").strip().replace(".", "")
    if not limpio:
        raise Censurado
    if limpio.startswith("<"):
        raise Censurado
    return int(limpio)


def descarga_anyo(anyo: int) -> str | None:
    url = URL.format(anyo=anyo)
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=300) as respuesta:
            bruto = respuesta.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(f"  {anyo}: sin fichero publicado")
            return None
        print(f"  {anyo}: error {exc.code} {exc.reason}")
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"  {anyo}: {type(exc).__name__}: {exc}")
        return None

    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            return bruto.decode(codificacion)
        except UnicodeDecodeError:
            continue
    print(f"  {anyo}: no se ha podido decodificar")
    return None


def periodo_de(codigo_mes: str) -> str | None:
    """'202601' -> '2026M01'."""
    codigo = (codigo_mes or "").strip()
    if len(codigo) != 6 or not codigo.isdigit():
        return None
    mes = int(codigo[4:])
    if not 1 <= mes <= 12:
        return None
    return f"{codigo[:4]}M{mes:02d}"


def lee_anyo(texto: str, acumulado: dict, municipios: dict, censura: dict) -> int:
    """Suma un fichero anual a los acumuladores. Devuelve las filas leídas."""
    lineas = texto.splitlines()
    # La primera fila es un título con celdas vacías; la cabecera va debajo.
    inicio = 0
    for i, linea in enumerate(lineas[:5]):
        if "Código mes" in linea or "Codigo mes" in linea:
            inicio = i
            break

    lector = csv.DictReader(io.StringIO("\n".join(lineas[inicio:])), delimiter=";")
    campos = {(c or "").strip(): c for c in (lector.fieldnames or [])}
    filas = 0

    for fila in lector:
        periodo = periodo_de(fila.get(campos.get("Código mes", "Código mes "), ""))
        if not periodo:
            continue
        filas += 1

        codigo_ccaa = (fila.get(campos.get("Código de CA", ""), "") or "").strip()
        codigo_provincia = (fila.get(campos.get("Codigo Provincia", ""), "") or "").strip().zfill(2)
        codigo_municipio = (fila.get(campos.get("Codigo Municipio", ""), "") or "").strip()
        # Las claves de `campos` ya vienen sin espacios; el nombre original de
        # esta columna sí los lleva (« Municipio»).
        nombre_municipio = (fila.get(campos.get("Municipio", ""), "") or "").strip()

        ambitos = ["espana"]
        if codigo_ccaa.zfill(2) == CODIGO_CCAA_VALENCIANA:
            ambitos.append("comunitat-valenciana")
        if codigo_provincia == CODIGO_PROVINCIA_CASTELLON:
            ambitos.append("castellon")

        for etiqueta, columna in campos.items():
            if etiqueta not in COLUMNAS:
                continue
            magnitud, sexo = COLUMNAS[etiqueta]
            try:
                numero = valor(fila.get(columna, ""))
            except Censurado:
                censura[magnitud] += 1
                continue

            for ambito in ambitos:
                acumulado[(ambito, sexo or "ambos", magnitud, periodo)] += numero
                if sexo:
                    acumulado[(ambito, "ambos", magnitud, periodo)] += numero

            if codigo_provincia == CODIGO_PROVINCIA_CASTELLON and magnitud == "paro_total":
                municipios[(codigo_municipio, nombre_municipio, periodo)] = numero

    return filas


def compone_totales(acumulado: dict) -> None:
    """El paro por sexo es la suma de sus tramos de edad.

    El SEPE no publica el total de hombres ni el de mujeres, sólo el general,
    pero sí los tres tramos de edad de cada sexo, y su suma es ese total.
    """
    tramos = ("paro_menores_25", "paro_25_44", "paro_45_mas")
    periodos_por_sexo = defaultdict(set)
    for (ambito, sexo, magnitud, periodo) in list(acumulado):
        if sexo in ("hombres", "mujeres") and magnitud in tramos:
            periodos_por_sexo[(ambito, sexo)].add(periodo)

    for (ambito, sexo), periodos in periodos_por_sexo.items():
        for periodo in periodos:
            total = sum(acumulado.get((ambito, sexo, tramo, periodo), 0) for tramo in tramos)
            acumulado[(ambito, sexo, "paro_total", periodo)] = total


def escribe_municipios(municipios: dict, ahora: str) -> int:
    """Paro registrado de cada municipio de Castellón, mes a mes.

    Se publica aparte de los ámbitos porque tiene otra forma -una serie por
    municipio- y porque es la base del mapa provincial.
    """
    fichero = DESTINO / "municipios-castellon.json"
    previo: dict = {}
    if fichero.exists():
        anterior = json.loads(fichero.read_text(encoding="utf-8"))
        periodos_previos = anterior.get("periodos", [])
        for codigo, municipio in anterior.get("municipios", {}).items():
            for i, valor_previo in enumerate(municipio.get("paro_total", [])):
                if valor_previo is not None and i < len(periodos_previos):
                    previo[(codigo, municipio.get("nombre", ""), periodos_previos[i])] = valor_previo

    previo.update(municipios)
    if not previo:
        return 0

    periodos = sorted({clave[2] for clave in previo}, key=lambda p: (int(p[:4]), int(p[5:])))
    nombres: dict[str, str] = {}
    valores: dict[str, dict[str, int]] = defaultdict(dict)
    for (codigo, nombre, periodo), numero in previo.items():
        if nombre:
            nombres[codigo] = nombre
        valores[codigo][periodo] = numero

    contenido = {
        "ambito": {"id": "municipios-castellon", "nombre": "Municipios de Castellón",
                   "tipo": "Municipios"},
        "actualizado": ahora,
        "periodos": periodos,
        "municipios": {
            codigo: {
                "nombre": nombres.get(codigo, codigo),
                "paro_total": [valores[codigo].get(p) for p in periodos],
            }
            for codigo in sorted(valores)
        },
    }
    fichero.write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")
    return len(valores)


def carga_previo(fichero: Path) -> dict:
    if not fichero.exists():
        return {}
    contenido = json.loads(fichero.read_text(encoding="utf-8"))
    periodos = contenido.get("periodos", [])
    previo = {}
    for sexo, magnitudes in contenido.get("series", {}).items():
        for magnitud, valores in magnitudes.items():
            for i, v in enumerate(valores):
                if v is not None and i < len(periodos):
                    previo[(sexo, magnitud, periodos[i])] = v
    return previo


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--desde", type=int, default=None,
                            help="primer año a descargar (por defecto, el anterior al actual)")
    argumentos = analizador.parse_args()

    hoy = dt.date.today()
    desde = argumentos.desde or (hoy.year - 1)
    anyos = list(range(max(PRIMER_ANYO, desde), hoy.year + 1))

    DESTINO.mkdir(parents=True, exist_ok=True)
    acumulado: dict = defaultdict(int)
    municipios: dict = {}
    censura: dict = defaultdict(int)

    print(f"Descargando el paro registrado del SEPE ({anyos[0]}-{anyos[-1]})…")
    total_filas = 0
    for anyo in anyos:
        texto = descarga_anyo(anyo)
        if not texto:
            continue
        filas = lee_anyo(texto, acumulado, municipios, censura)
        total_filas += filas
        print(f"  {anyo}: {filas} filas")

    if not acumulado:
        print("No se ha leído ningún dato; no se toca nada.")
        return 1

    compone_totales(acumulado)

    if censura:
        print("\nValores ocultos por secreto estadístico (menores de 5):")
        for magnitud, cuantos in sorted(censura.items(), key=lambda t: -t[1]):
            print(f"  {magnitud}: {cuantos}")

    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    periodos_nuevos = {clave[3] for clave in acumulado}

    indice = {
        "actualizado": ahora,
        "titulo": "Paro registrado",
        "fuente": {"organismo": "Servicio Público de Empleo Estatal (SEPE)",
                   "url": URL.format(anyo=hoy.year)},
        "indicadores": INDICADORES,
        "ambitos": [],
    }

    for ambito_id, ambito in AMBITOS.items():
        fichero = DESTINO / f"{ambito_id}.json"
        previo = carga_previo(fichero)

        # Lo descargado ahora manda sobre lo que hubiera guardado.
        for (amb, sexo, magnitud, periodo), numero in acumulado.items():
            if amb == ambito_id:
                previo[(sexo, magnitud, periodo)] = numero

        periodos = sorted({clave[2] for clave in previo},
                          key=lambda p: (int(p[:4]), int(p[5:])))
        series: dict = defaultdict(dict)
        for (sexo, magnitud, periodo), numero in previo.items():
            series[sexo][magnitud] = series[sexo].get(magnitud, {})
            series[sexo][magnitud][periodo] = numero

        contenido = {
            "ambito": {"id": ambito_id, "nombre": ambito["nombre"], "tipo": ambito["tipo"]},
            "actualizado": ahora,
            "periodos": periodos,
            "series": {
                sexo: {magnitud: [valores.get(p) for p in periodos]
                       for magnitud, valores in magnitudes.items()}
                for sexo, magnitudes in series.items()
            },
        }
        fichero.write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")
        indice["ambitos"].append({"id": ambito_id, "nombre": ambito["nombre"],
                                  "fichero": f"{ambito_id}.json"})
        print(f"  escrito data/paro-registrado/{ambito_id}.json ({len(periodos)} meses)")

    cuantos = escribe_municipios(municipios, ahora)
    if cuantos:
        indice["municipios"] = {"fichero": "municipios-castellon.json", "cuantos": cuantos}
        print(f"  escrito data/paro-registrado/municipios-castellon.json ({cuantos} municipios)")

    todos = sorted(periodos_nuevos, key=lambda p: (int(p[:4]), int(p[5:])))
    indice["ultimo_periodo"] = todos[-1]
    indice["primer_periodo"] = todos[0]
    (DESTINO / "index.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\nListo: {total_filas} filas, {len(todos)} meses "
          f"({todos[0]} … {todos[-1]}), {len({m[0] for m in municipios})} municipios "
          f"de Castellón.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
