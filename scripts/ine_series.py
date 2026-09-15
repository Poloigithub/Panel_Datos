"""Motor de descarga de series del INE.

Resuelve series por el nombre con que el INE las publica. Ese nombre encadena
los valores de las variables de la serie separados por puntos, por ejemplo

    "Mujeres. Castellón/Castelló. Total. Parados. Valor absoluto."

de modo que una serie es «la del total» cuando sus segmentos son los que
identifican la magnitud más, como mucho, formas de decir «el total». Con eso
basta para localizarla sin depender de identificadores de tabla, que el INE
reorganiza.

Dos complicaciones reales que este módulo resuelve:

- El INE reparte la misma cifra entre varias series y a veces estrena una con
  dos trimestres mientras la histórica sigue publicándose aparte, así que se
  parte de la más completa y se rellenan sus huecos con las demás, pero sólo
  con las que coinciden donde se solapan.
- El periodo llega en formas distintas según el detalle pedido, y hay
  operaciones anuales, trimestrales y semestrales.
"""

from __future__ import annotations

import re
import unicodedata

import ine_api

# Segmentos que pueden sobrar en el nombre de una serie sin cambiar lo que
# mide: son formas de decir «el total» de una variable.
EXTRAS_ADMITIDOS = {
    "total", "totales", "ambos sexos", "de 16 y mas anos", "todas las edades",
    "valor absoluto", "dato base", "numero", "ambas nacionalidades", "anual",
    "porcentaje", "no considerado", "total edades",
}

PERIODO = re.compile(r"^(\d{4})(?:([TSM])(\d{1,2}))?$")
ROMANOS = {"I": "T1", "II": "T2", "III": "T3", "IV": "T4"}
# Trimestres y semestres tal y como los numera Tempus 3 en FK_Periodo.
FK_SUBPERIODOS = {19: "T1", 20: "T2", 21: "T3", 22: "T4", 23: "S1", 24: "S2"}


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def segmentos(nombre: str) -> set[str]:
    """Los valores de variable que componen el nombre de una serie."""
    partes = (nombre or "").replace(",", ".").split(".")
    return {normaliza(p) for p in partes if normaliza(p)}


def etiqueta_periodo(dato: dict) -> str | None:
    """'2026T2', '2024S1' o '2023' a partir de un punto de una serie.

    Con det=2 el INE devuelve `NombrePeriodo` ya formateado; con tip=A un
    `T3_Periodo` ("T2"); y a secas un `FK_Periodo` numérico. Las operaciones
    anuales no traen subperiodo y se quedan sólo con el año.
    """
    directo = dato.get("NombrePeriodo")
    if directo and PERIODO.match(str(directo).strip().upper()):
        return str(directo).strip().upper()

    anyo = dato.get("Anyo") or dato.get("Anio")
    if not anyo:
        return None

    periodo = dato.get("Periodo")
    nombre = periodo.get("Nombre") if isinstance(periodo, dict) else periodo
    nombre = nombre or dato.get("T3_Periodo")
    if nombre:
        nombre = str(nombre).strip().upper()
        if nombre in ROMANOS:
            return f"{anyo}{ROMANOS[nombre]}"
        if PERIODO.match(f"{anyo}{nombre}"):
            return f"{anyo}{nombre}"

    subperiodo = FK_SUBPERIODOS.get(dato.get("FK_Periodo"))
    if subperiodo:
        return f"{anyo}{subperiodo}"
    return str(anyo)


def orden_periodo(periodo: str) -> tuple[int, int]:
    coincidencia = PERIODO.match(periodo or "")
    if not coincidencia:
        return (0, 0)
    anyo, _, numero = coincidencia.groups()
    return (int(anyo), int(numero) if numero else 0)


_descargadas: dict[str, dict[str, float]] = {}


def descarga_serie(codigo: str) -> dict[str, float]:
    """Serie completa, ya indexada por periodo y sin valores ausentes."""
    if codigo in _descargadas:
        return _descargadas[codigo]
    try:
        datos = ine_api.get("DATOS_SERIE", codigo, nult=400, det=2)
    except ine_api.INEError as exc:
        print(f"      ! no se pudo descargar {codigo}: {exc}")
        _descargadas[codigo] = {}
        return {}

    valores: dict[str, float] = {}
    for punto in datos.get("Data", []):
        periodo = etiqueta_periodo(punto)
        valor = punto.get("Valor")
        if periodo and valor is not None:
            valores[periodo] = valor
    _descargadas[codigo] = valores
    return valores


def concuerdan(a: dict[str, float], b: dict[str, float]) -> bool:
    """¿Dos series miden lo mismo allí donde se solapan?

    Sin solape no se puede afirmar que lo hagan, y mezclarlas encadenaría
    metodologías distintas, así que se responde que no.
    """
    comunes = set(a) & set(b)
    if not comunes:
        return False
    for periodo in comunes:
        referencia = max(abs(a[periodo]), abs(b[periodo]), 1e-9)
        if abs(a[periodo] - b[periodo]) / referencia > 0.01:
            return False
    return True


def fusiona(candidatas: list[dict], etiqueta: str, tope: int = 12) -> tuple[dict[str, float], list[str]]:
    """Reúne en una sola serie las candidatas que miden lo mismo."""
    orden = sorted(candidatas, key=lambda c: len(segmentos(c.get("Nombre", ""))))[:tope]
    descargadas = [(c["COD"], descarga_serie(c["COD"])) for c in orden]
    descargadas = [(codigo, valores) for codigo, valores in descargadas if valores]
    if not descargadas:
        print(f"      {etiqueta}: {len(candidatas)} candidatas, ninguna con datos")
        return {}, []

    descargadas.sort(key=lambda t: (len(t[1]), max(orden_periodo(p) for p in t[1])), reverse=True)
    base_codigo, fusionada = descargadas[0]
    fusionada = dict(fusionada)
    usados = [base_codigo]

    for codigo, valores in descargadas[1:]:
        nuevos = {p: v for p, v in valores.items() if p not in fusionada}
        if not nuevos or not concuerdan(fusionada, valores):
            continue
        fusionada.update(nuevos)
        usados.append(codigo)

    if len(usados) > 1:
        print(f"      {etiqueta}: {len(fusionada)} periodos uniendo "
              f"{len(usados)} series ({', '.join(usados)})")
    else:
        print(f"      {etiqueta}: {len(fusionada)} periodos ({base_codigo})")
    return fusionada, usados


def indexa_por_segmentos(operacion: str, filtro: str) -> dict[frozenset, list[dict]]:
    """Todas las series de una operación para un ámbito, por sus segmentos."""
    series = ine_api.get("SERIE_METADATAOPERACION", operacion, g1=filtro)
    indice: dict[frozenset, list[dict]] = {}
    for serie in series:
        indice.setdefault(frozenset(segmentos(serie.get("Nombre", ""))), []).append(serie)
    return indice


def candidatas_para(indice: dict[frozenset, list[dict]], obligatorio: set[str],
                    extras: set[str] | None = None) -> list[dict]:
    """Series que contienen lo obligatorio y no añaden más que totales."""
    admitidos = EXTRAS_ADMITIDOS if extras is None else extras
    obligatorio = {normaliza(s) for s in obligatorio}
    elegidas, vistos = [], set()
    for segs, grupo in indice.items():
        if not (obligatorio <= segs and (segs - obligatorio) <= admitidos):
            continue
        for serie in grupo:
            if serie["COD"] not in vistos:
                vistos.add(serie["COD"])
                elegidas.append(serie)
    return elegidas


def resuelve(indice: dict[frozenset, list[dict]], obligatorio: set[str],
             etiqueta: str, extras: set[str] | None = None,
             avisar: bool = True) -> tuple[dict[str, float], list[str]]:
    """Localiza y descarga la serie del total que encaja con lo pedido."""
    candidatas = candidatas_para(indice, obligatorio, extras)
    if not candidatas:
        if avisar:
            print(f"      sin serie para {etiqueta} ({sorted(obligatorio)})")
        return {}, []
    if len(candidatas) == 1:
        valores = descarga_serie(candidatas[0]["COD"])
        print(f"      {etiqueta}: {len(valores)} periodos ({candidatas[0]['COD']})")
        return valores, [candidatas[0]["COD"]]
    return fusiona(candidatas, etiqueta)
