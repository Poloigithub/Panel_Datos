"""Despidos y expedientes de regulación: cuando la empresa te echa.

Dos estadísticas del Ministerio de Trabajo que cuentan las dos caras de lo
mismo y que el panel no tenía:

- **Regulación de empleo** (`REG-4`): trabajadores afectados cada mes por un
  despido colectivo, una suspensión de contrato o una reducción de jornada, con
  dato de provincia. Es lo que se conoce por ERE y ERTE.
- **Despidos y su coste** (`DESP-6`): cuántos despidos hubo en el año, por
  provincia y por sexo.

Van juntos porque responden a la misma pregunta -cuánta gente pierde el empleo
sin quererlo- y separados dentro, porque no son lo mismo: un ERTE suspende el
contrato y un despido lo termina.

Los ficheros son de dos formatos distintos y da igual: la regulación de empleo
viene en XLSX y los despidos en el `.xls` binario, y el panel abre los dos
desde que tiene lector para cada uno.
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
import xlsx  # noqa: E402

BASE = "https://www.mites.gob.es/estadisticas"
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
         "sep", "oct", "nov", "dic")
REGULACION = "{base}/reg/reg{aa}{mes}/reg_{mm:02d}_{anyo}.xlsx"
DESPIDOS = "{base}/dec/dec{aa}/DEC_{anyo}.xls"

PRIMER_ANYO_DESPIDOS = 2019   # antes, el ministerio los publica en un fichero conjunto
FALLOS_SEGUIDOS = 4

FILAS = {
    "espana": "total",
    "comunitat-valenciana": "comunitatvalenciana",
    "castellon": "castellon",
}

BLOQUE = {
    "titulo": "Despidos y regulación de empleo",
    "indicadores": {
        "ere_afectados": {
            "titulo": "Personas afectadas por un expediente de regulación",
            "unidad": "personas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "trabajadores afectados en el mes",
            "nota": "Suma de los tres tipos de medida: despido colectivo, "
                    "suspensión de contrato y reducción de jornada. Es lo que "
                    "se conoce por ERE y ERTE.",
        },
        "ere_despido": {
            "titulo": "De ellas, por despido colectivo",
            "unidad": "personas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "trabajadores que pierden el empleo",
            "sobre_total": "ere_afectados",
        },
        "ere_suspension": {
            "titulo": "De ellas, por suspensión de contrato",
            "unidad": "personas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "trabajadores con el contrato suspendido",
            "sobre_total": "ere_afectados",
            "nota": "La suspensión no termina el contrato, lo para. Es la "
                    "figura de los ERTE.",
        },
        "despidos": {
            "titulo": "Despidos en el año",
            "unidad": "despidos", "decimales": 0, "por_sexo": True,
            "unidad_texto": "despidos registrados en el año",
            "nota": "De la Estadística de Despidos y su Coste, que es anual. "
                    "Cuenta los despidos, no las personas: quien es despedido "
                    "dos veces en un año cuenta dos veces.",
        },
    },
}


def normaliza(texto: str) -> str:
    """Sin acentos, sin espacios y en minúsculas.

    Sin espacios del todo, no sólo los repetidos: la fila del total de la
    regulación de empleo viene escrita «T O T A L», con las letras sueltas.
    """
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return "".join(plano.split())


BUSCADOS = {normaliza(n): c for c, n in FILAS.items()}


def suave(texto: str) -> str:
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return " ".join(plano.split())


def abre(datos: bytes):
    """El libro, sea del formato que sea."""
    if datos[:2] == b"PK":
        return xlsx.Libro(datos)
    if datos[:8] == xls.FIRMA:
        return xls.Libro(datos)
    raise ValueError("no es una hoja de cálculo")


def hoja_por_descripcion(libro, palabras: tuple[str, ...]) -> str | None:
    indice = next((h for h in libro.hojas if suave(h).startswith("indice")), None)
    if not indice:
        return None
    for fila in libro.filas(indice):
        celdas = [str(c) for c in fila if c not in (None, "")]
        if not celdas or not all(p in suave(" ".join(celdas)) for p in palabras):
            continue
        codigo = suave(celdas[0]).rstrip(". ")
        for nombre in libro.hojas:
            if suave(nombre).rstrip(". ") == codigo:
                return nombre
    return None


def columnas_de(filas: list[list], cabeceras: tuple[str, ...]) -> dict[str, int]:
    """Dónde está cada bloque de la tabla, por lo que dice su cabecera.

    Contar columnas a mano es lo que rompe estos lectores cuando el ministerio
    añade una. Se buscan por su nombre y se coge la primera columna de cada uno.
    """
    encontradas: dict[str, int] = {}
    for fila in filas[:12]:
        for columna, celda in enumerate(fila):
            if not isinstance(celda, str):
                continue
            plano = suave(celda)
            for clave in cabeceras:
                if clave not in encontradas and plano.startswith(clave):
                    encontradas[clave] = columna
        if len(encontradas) == len(cabeceras):
            break
    return encontradas


def lee_regulacion(datos: bytes) -> dict[str, dict[str, float]]:
    libro = abre(datos)
    # Las dos palabras por separado y no la frase entera: el índice dice «por
    # comunidad autónoma, provincia y sexo», sin la «y» en medio que llevan
    # los demás ficheros del ministerio. Pedirlas sueltas encaja igual y
    # descarta la tabla que sólo llega a comunidad autónoma.
    hoja = hoja_por_descripcion(libro, ("comunidad autonoma", "provincia"))
    if not hoja:
        return {}
    filas = libro.filas(hoja)
    columnas = columnas_de(filas, ("total", "despidos colectivos",
                                   "suspension de contrato"))
    if "total" not in columnas:
        return {}

    magnitudes = {"ere_afectados": columnas["total"],
                  "ere_despido": columnas.get("despidos colectivos"),
                  "ere_suspension": columnas.get("suspension de contrato")}
    salida: dict[str, dict[str, float]] = {}
    for fila in filas:
        if not fila:
            continue
        clave = BUSCADOS.get(normaliza(str(fila[0] or "")))
        if not clave or clave in salida:
            continue
        valores = {}
        for magnitud, columna in magnitudes.items():
            if columna is None or columna >= len(fila):
                continue
            valor = fila[columna]
            if isinstance(valor, (int, float)):
                valores[magnitud] = float(valor)
        if valores:
            salida[clave] = valores
    return salida


def lee_despidos(datos: bytes) -> dict[str, dict[str, float]]:
    """Los despidos del año, por provincia y sexo."""
    libro = abre(datos)
    hoja = hoja_por_descripcion(libro, ("despidos", "provincia"))
    if not hoja:
        return {}
    filas = libro.filas(hoja)
    columnas = columnas_de(filas, ("total", "hombres", "mujeres"))
    if "total" not in columnas:
        return {}

    salida: dict[str, dict[str, float]] = {}
    for fila in filas:
        if not fila:
            continue
        clave = BUSCADOS.get(normaliza(str(fila[0] or "")))
        if not clave or clave in salida:
            continue
        valores = {}
        for sexo, cabecera in (("ambos", "total"), ("hombres", "hombres"),
                               ("mujeres", "mujeres")):
            columna = columnas.get(cabecera)
            if columna is None or columna >= len(fila):
                continue
            valor = fila[columna]
            if isinstance(valor, (int, float)):
                valores[sexo] = float(valor)
        if valores:
            salida[clave] = valores
    return salida


def ya_bajados(magnitud: str) -> dict[str, dict[str, float]]:
    """Lo que ya está en el repositorio, para no volver a pedirlo."""
    guardado: dict[str, dict[str, float]] = {}
    for ambito in FILAS:
        fichero = RAIZ / "data" / "despidos" / f"{ambito}.json"
        if not fichero.exists():
            continue
        contenido = json.loads(fichero.read_text(encoding="utf-8"))
        valores = (contenido["series"].get("ambos") or {}).get(magnitud) or []
        for periodo, valor in zip(contenido["periodos"], valores):
            if valor is not None:
                guardado.setdefault(periodo, {})[ambito] = valor
    return guardado


def descarga_regulacion(hoy: dt.date, por_ambito: dict) -> None:
    guardado = ya_bajados("ere_afectados")
    completos: dict[str, dict[str, dict[str, float]]] = {}
    print(f"  regulación de empleo: {len(guardado)} meses ya guardados")

    anyo, mes = hoy.year, hoy.month
    fallos, pedidos = 0, 0
    while fallos < FALLOS_SEGUIDOS:
        periodo = f"{anyo}M{mes:02d}"
        reciente = (hoy.year * 12 + hoy.month) - (anyo * 12 + mes) < 2
        if periodo in guardado and not reciente:
            fallos = 0
        else:
            url = REGULACION.format(base=BASE, aa=f"{anyo % 100:02d}",
                                    mes=MESES[mes - 1], mm=mes, anyo=anyo)
            estado, _, datos = red.abre(url)
            pedidos += 1
            if estado != 200 or datos[:2] != b"PK":
                print(f"    {periodo}: sin fichero")
                fallos += 1
            else:
                leido = lee_regulacion(datos)
                if leido:
                    completos[periodo] = leido
                    fallos = 0
                    print(f"    {periodo}: Castellón "
                          f"{leido.get('castellon', {}).get('ere_afectados')}")
                else:
                    print(f"    {periodo}: sin tabla provincial")
                    fallos += 1
        anyo, mes = (anyo - 1, 12) if mes == 1 else (anyo, mes - 1)

    # Lo ya guardado se conserva tal cual; lo nuevo se añade encima.
    for periodo, ambitos in guardado.items():
        completos.setdefault(periodo, {})
        for ambito, valor in ambitos.items():
            completos[periodo].setdefault(ambito, {}).setdefault("ere_afectados", valor)
    for periodo, ambitos in completos.items():
        for ambito, valores in ambitos.items():
            for magnitud, valor in valores.items():
                por_ambito[ambito]["ambos"].setdefault(magnitud, {})[periodo] = valor
    print(f"  regulación de empleo: {pedidos} peticiones, "
          f"{len(completos)} meses en total")


def descarga_despidos(hoy: dt.date, por_ambito: dict) -> None:
    print("  despidos y su coste:")
    for anyo in range(PRIMER_ANYO_DESPIDOS, hoy.year + 1):
        url = DESPIDOS.format(base=BASE, aa=f"{anyo % 100:02d}", anyo=anyo)
        estado, _, datos = red.abre(url)
        if estado != 200 or datos[:8] != xls.FIRMA:
            print(f"    {anyo}: todavía no publicado")
            continue
        try:
            leido = lee_despidos(datos)
        except Exception as exc:  # noqa: BLE001
            print(f"    {anyo}: no se ha podido leer: {type(exc).__name__}: {exc}")
            continue
        if not leido:
            print(f"    {anyo}: sin tabla provincial")
            continue
        for ambito, sexos in leido.items():
            for sexo, valor in sexos.items():
                por_ambito[ambito].setdefault(sexo, {}) \
                    .setdefault("despidos", {})[str(anyo)] = valor
        print(f"    {anyo}: Castellón {leido.get('castellon', {}).get('ambos')}")


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    hoy = dt.date.today()
    print("\n=== Despidos y regulación de empleo ===")

    por_ambito: dict[str, dict] = {a: {"ambos": {}} for a in FILAS}
    descarga_regulacion(hoy, por_ambito)
    descarga_despidos(hoy, por_ambito)

    periodos = bloques.escribe_bloque("despidos", BLOQUE, por_ambito, ahora, RAIZ)
    return 0 if periodos else 1


if __name__ == "__main__":
    raise SystemExit(main())
