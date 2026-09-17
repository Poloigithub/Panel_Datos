"""Huelgas: cuántas hay, cuánta gente las secunda y cuántas jornadas cuestan.

Es la única medida de conflicto laboral que existe, y estuvo a punto de
quedarse fuera del panel por un error mío: un sondeo buscó la palabra
«provincia» en el índice del fichero, no la encontró y dio la estadística por
nacional. La tabla provincial está ahí, pero su título la llama **«según
repercusión territorial de las huelgas»**, sin nombrar la provincia. Está a dos
líneas de lo que se miró.

De cada avance mensual se lee esa tabla, la `HUE-3`, que reparte por comunidad
autónoma y provincia las huelgas desarrolladas, los trabajadores participantes
y las jornadas no trabajadas.

Dos cosas sobre lo que significa «repercusión territorial»: una huelga estatal
aparece en todas las provincias donde tuvo seguimiento, y una huelga de empresa
sólo donde está la empresa. Así que la suma de provincias no da el total
nacional de huelgas -una misma huelga se cuenta en varias- pero sí el de
participantes y jornadas, que es lo que de verdad mide el conflicto.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import bloques_ine as bloques  # noqa: E402
import red_ministerio as red  # noqa: E402
import xls  # noqa: E402

BASE = "https://www.mites.gob.es/estadisticas/hue"
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
         "sep", "oct", "nov", "dic")
FICHERO = "{base}/hue{aa}{mes}publicacion/hue_{mm:02d}_{aa}.xls"

FALLOS_SEGUIDOS = 4

FILAS = {
    "espana": "total",
    "comunitat-valenciana": "comunitatvalenciana",
    "castellon": "castellon",
}

# Cómo se llama en el fichero el bloque de cada magnitud. La columna del mes es
# la primera de cada bloque; la segunda es el acumulado del año, que aquí no se
# usa porque lo interesante de una huelga es cuándo pasó.
CABECERAS = {
    "huelgas": "huelgas",
    "participantes": "participantes",
    "jornadas_perdidas": "jornadas no trabajadas",
}

AVISO_REPERCUSION = (
    "Es la repercusión territorial: una huelga estatal aparece en todas las "
    "provincias donde tuvo seguimiento. Por eso la suma de provincias no da el "
    "total nacional de huelgas -una misma huelga se cuenta en varias- aunque "
    "sí el de participantes y jornadas.")

BLOQUE = {
    "titulo": "Huelgas",
    "indicadores": {
        "participantes": {
            "titulo": "Personas que secundaron una huelga",
            "unidad": "personas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "trabajadores participantes en el mes",
            "nota": AVISO_REPERCUSION,
        },
        "jornadas_perdidas": {
            "titulo": "Jornadas no trabajadas",
            "unidad": "jornadas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "jornadas de trabajo perdidas por huelga en el mes",
            "nota": "Es la medida del tamaño de un conflicto: no es lo mismo "
                    "que mil personas paren una hora que una semana.",
        },
        "huelgas": {
            "titulo": "Huelgas con repercusión en el territorio",
            "unidad": "huelgas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "huelgas desarrolladas con seguimiento en el mes",
            "nota": AVISO_REPERCUSION,
        },
    },
}


def normaliza(texto: str) -> str:
    """Sin acentos, sin espacios y en minúsculas.

    Sin espacios del todo: la fila del total viene escrita «T O T A L».
    """
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return "".join(plano.split())


def suave(texto: str) -> str:
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return " ".join(plano.split())


BUSCADOS = {normaliza(n): c for c, n in FILAS.items()}


def hoja_provincial(libro) -> str | None:
    """La tabla que reparte por territorio.

    Se busca por «repercusión territorial», que es como el ministerio la llama
    en el índice, y no por «provincia», que no aparece ahí aunque sí dentro.
    """
    indice = next((h for h in libro.hojas if suave(h).startswith("indice")), None)
    if not indice:
        return None
    for fila in libro.filas(indice):
        celdas = [str(c) for c in fila if c not in (None, "")]
        if not celdas:
            continue
        descripcion = suave(" ".join(celdas))
        if "repercusion territorial" not in descripcion:
            continue
        # En el índice hay dos con ese nombre: el cuadro resumen y la tabla
        # entera. La buena es la que no está entre los resúmenes, y se
        # distingue porque su código no lleva erre.
        codigo = suave(celdas[0]).rstrip(". ")
        if "-r" in codigo:
            continue
        for nombre in libro.hojas:
            if suave(nombre).rstrip(". ") == codigo:
                return nombre
    return None


def columnas_del_mes(filas: list[list]) -> dict[str, int]:
    """Dónde empieza cada bloque, por su cabecera. La primera columna es el mes."""
    encontradas: dict[str, int] = {}
    for fila in filas[:10]:
        for columna, celda in enumerate(fila):
            if not isinstance(celda, str):
                continue
            plano = suave(celda)
            for clave, cabecera in CABECERAS.items():
                if clave not in encontradas and plano.startswith(cabecera):
                    encontradas[clave] = columna
        if len(encontradas) == len(CABECERAS):
            break
    return encontradas


def lee_mes(datos: bytes) -> dict[str, dict[str, float]]:
    libro = xls.Libro(datos)
    hoja = hoja_provincial(libro)
    if not hoja:
        return {}
    filas = libro.filas(hoja)
    columnas = columnas_del_mes(filas)
    if len(columnas) < len(CABECERAS):
        return {}

    salida: dict[str, dict[str, float]] = {}
    for fila in filas:
        if not fila:
            continue
        clave = BUSCADOS.get(normaliza(str(fila[0] or "")))
        if not clave or clave in salida:
            continue
        valores = {}
        for magnitud, columna in columnas.items():
            valor = fila[columna] if columna < len(fila) else None
            if isinstance(valor, (int, float)):
                valores[magnitud] = float(valor)
        if valores:
            salida[clave] = valores
    return salida


def ya_bajados() -> dict[str, dict[str, dict[str, float]]]:
    guardado: dict[str, dict[str, dict[str, float]]] = {}
    for ambito in FILAS:
        fichero = RAIZ / "data" / "huelgas" / f"{ambito}.json"
        if not fichero.exists():
            continue
        contenido = json.loads(fichero.read_text(encoding="utf-8"))
        for magnitud, valores in contenido["series"]["ambos"].items():
            for periodo, valor in zip(contenido["periodos"], valores):
                if valor is not None:
                    guardado.setdefault(periodo, {}) \
                        .setdefault(ambito, {})[magnitud] = valor
    return guardado


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    hoy = dt.date.today()
    print("\n=== Huelgas ===")

    guardado = ya_bajados()
    print(f"  {len(guardado)} meses ya guardados")

    anyo, mes = hoy.year, hoy.month
    fallos, pedidos = 0, 0
    while fallos < FALLOS_SEGUIDOS:
        periodo = f"{anyo}M{mes:02d}"
        reciente = (hoy.year * 12 + hoy.month) - (anyo * 12 + mes) < 3
        if periodo in guardado and not reciente:
            fallos = 0
        else:
            url = FICHERO.format(base=BASE, aa=f"{anyo % 100:02d}",
                                 mes=MESES[mes - 1], mm=mes)
            estado, _, datos = red.abre(url)
            pedidos += 1
            if estado != 200 or datos[:8] != xls.FIRMA:
                print(f"    {periodo}: sin fichero")
                fallos += 1
            else:
                leido = lee_mes(datos)
                if leido:
                    guardado[periodo] = leido
                    fallos = 0
                    print(f"    {periodo}: Castellón "
                          f"{leido.get('castellon', {}).get('participantes')} "
                          f"participantes")
                else:
                    print(f"    {periodo}: sin tabla territorial")
                    fallos += 1
        anyo, mes = (anyo - 1, 12) if mes == 1 else (anyo, mes - 1)

    por_ambito: dict[str, dict] = {a: {"ambos": {}} for a in FILAS}
    for periodo, ambitos in guardado.items():
        for ambito, magnitudes in ambitos.items():
            for magnitud, valor in magnitudes.items():
                por_ambito[ambito]["ambos"].setdefault(magnitud, {})[periodo] = valor

    print(f"  {pedidos} peticiones · {len(guardado)} meses en total")
    periodos = bloques.escribe_bloque("huelgas", BLOQUE, por_ambito, ahora, RAIZ)
    return 0 if periodos else 1


if __name__ == "__main__":
    raise SystemExit(main())
