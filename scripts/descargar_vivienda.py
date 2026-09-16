"""Descarga del INE el bloque de vivienda del panel.

Cinco operaciones distintas, cada una con su nivel territorial y su
frecuencia, que es justo lo que hay que contar bien:

- **ETDP** (Transmisión de Derechos de la Propiedad): compraventas de vivienda,
  mensuales y con dato propio de provincia.
- **HPT** (Hipotecas): número e importe de las hipotecas sobre viviendas,
  mensuales y provinciales. De ahí sale la hipoteca media.
- **EH** (Ejecuciones Hipotecarias): trimestral y provincial.
- **IPV** (Índice de Precios de la Vivienda): trimestral, pero **el INE no lo
  publica por provincia**, sólo por comunidad autónoma y para el conjunto de
  España. Castellón no tiene índice de precios de compraventa y la página lo
  dice; inventarlo a partir de la media autonómica sería peor que no darlo.
- **IPVA** (Índice de Precios de Vivienda en Alquiler): anual, y este sí llega
  a provincia.

El precio del alquiler en euros por metro cuadrado del sistema estatal de
referencia (MIVAU) se sondeó y responde 403 a cualquier descarga automática,
así que no entra: el alquiler se sigue por el índice del INE, que es una
variación, no un nivel.

Se añaden dos indicadores derivados: la hipoteca media -importe entre número- y
los años de renta del hogar que cuesta, que es el cruce con la renta del Atlas
que ya publica el panel.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bloques_ine as bloques  # noqa: E402
import ine_series as motor  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "config"

# El INE publica la misma magnitud en versión mensual y acumulada del año. La
# palabra «anual» distingue la segunda, y mezclarlas daría una serie que salta
# de un mes a un año entero, así que aquí deja de ser un extra admisible.
EXTRAS = motor.EXTRAS_ADMITIDOS - {"anual"}

BLOQUE = {
    "titulo": "Vivienda",
    "operaciones": ["ETDP", "HPT", "EH", "IPV", "IPVA"],
    "indicadores": {
        "compraventas": {
            "titulo": "Compraventas de vivienda", "unidad": "operaciones", "decimales": 0,
            "unidad_texto": "compraventas inscritas en el mes",
            "rango": (0, 300_000),
            "operacion": "ETDP",
            "busquedas": [{"compraventa", "total viviendas"}],
            "por_sexo": False,
        },
        "compraventas_nueva": {
            "titulo": "Compraventas de vivienda nueva", "unidad": "operaciones", "decimales": 0,
            "rango": (0, 300_000),
            "operacion": "ETDP",
            "busquedas": [{"compraventa", "vivienda nueva"}],
            "sobre_total": "compraventas",
            "por_sexo": False,
        },
        "compraventas_usada": {
            "titulo": "Compraventas de vivienda de segunda mano",
            "unidad": "operaciones", "decimales": 0,
            "rango": (0, 300_000),
            "operacion": "ETDP",
            "busquedas": [{"compraventa", "vivienda segunda mano"}],
            "sobre_total": "compraventas",
            "por_sexo": False,
        },
        "compraventas_protegida": {
            "titulo": "Compraventas de vivienda protegida",
            "unidad": "operaciones", "decimales": 0,
            "rango": (0, 300_000),
            "operacion": "ETDP",
            "busquedas": [{"compraventa", "vivienda protegida"}],
            "sobre_total": "compraventas",
            "por_sexo": False,
        },
        "hipotecas": {
            "titulo": "Hipotecas sobre viviendas", "unidad": "hipotecas", "decimales": 0,
            "unidad_texto": "hipotecas constituidas en el mes",
            "rango": (0, 300_000),
            "operacion": "HPT",
            # «mensual» y «base nueva» van en el nombre: sin el primero se
            # cuela el acumulado del año, y sin el segundo, la serie con la
            # metodología anterior, que no se puede encadenar con esta.
            "busquedas": [{"base nueva", "mensual", "numero de hipotecas", "viviendas"}],
            "por_sexo": False,
        },
        "importe_hipotecas": {
            "titulo": "Importe de las hipotecas sobre viviendas",
            "unidad": "miles de euros", "decimales": 0,
            "unidad_texto": "miles de euros prestados en el mes",
            "operacion": "HPT",
            "busquedas": [{"base nueva", "importe de hipotecas", "mensual", "viviendas"}],
            "por_sexo": False,
        },
        "ejecuciones": {
            "titulo": "Ejecuciones hipotecarias sobre viviendas",
            "unidad": "ejecuciones", "decimales": 0,
            "unidad_texto": "ejecuciones iniciadas en el año",
            "rango": (0, 100_000),
            "operacion": "EH",
            "busquedas": [{"fincas urbanas: viviendas"}],
            "por_sexo": False,
        },
        "ipv": {
            "titulo": "Índice de precios de la vivienda", "unidad": "índice", "decimales": 3,
            "unidad_texto": "índice, base 2015 = 100",
            "rango": (30, 400),
            "operacion": "IPV",
            "busquedas": [{"general", "indice"}],
            # El INE no publica el IPV por provincia: no hay serie de Castellón
            # que buscar, y pedirla sólo llenaría el registro de avisos.
            "sin_ambitos": ("castellon",),
            "nota": "El INE no publica este índice por provincia: sólo por "
                    "comunidad autónoma y para el conjunto de España.",
            "por_sexo": False,
        },
        "ipv_variacion": {
            "titulo": "Variación anual del precio de la vivienda",
            "unidad": "%", "decimales": 2,
            "unidad_texto": "variación respecto al mismo trimestre del año anterior",
            "rango": (-40, 40),
            "operacion": "IPV",
            "busquedas": [{"general", "variacion anual"}],
            "sin_ambitos": ("castellon",),
            "nota": "El INE no publica este índice por provincia: sólo por "
                    "comunidad autónoma y para el conjunto de España.",
            "por_sexo": False,
        },
        "ipva": {
            "titulo": "Índice de precios de la vivienda en alquiler",
            "unidad": "índice", "decimales": 3,
            "unidad_texto": "índice anual, base 2015 = 100",
            "rango": (30, 400),
            "operacion": "IPVA",
            "busquedas": [{"indice"}],
            "por_sexo": False,
        },
        "ipva_variacion": {
            "titulo": "Variación anual del precio del alquiler",
            "unidad": "%", "decimales": 2,
            "unidad_texto": "variación respecto al año anterior",
            "rango": (-40, 40),
            "operacion": "IPVA",
            "busquedas": [{"variacion anual"}],
            "por_sexo": False,
        },
    },
}

for _indicador in BLOQUE["indicadores"].values():
    _indicador.setdefault("extras", EXTRAS)


# Una hipoteca media por debajo de 20.000 € o por encima de 600.000 € no
# existe: el rango sirve para saber en qué unidad viene el importe, que el INE
# publica en miles de euros pero no siempre etiqueta igual.
MEDIA_PLAUSIBLE = (20_000, 600_000)


def hipoteca_media(importes: dict, numeros: dict) -> tuple[dict, str] | tuple[None, str]:
    """Importe medio por hipoteca, en euros, eligiendo la escala por sensatez.

    Los dos candidatos -importe en miles o en euros- se diferencian en un
    factor 1.000, así que no hay ambigüedad posible: o uno cae dentro de lo
    que puede costar una hipoteca o cae el otro.
    """
    comunes = sorted(set(importes) & set(numeros))
    if not comunes:
        return None, "sin periodos comunes entre importe y número"
    for factor, unidad in ((1000, "miles de euros"), (1, "euros")):
        media = {p: importes[p] * factor / numeros[p] for p in comunes if numeros[p]}
        if not media:
            continue
        centro = sorted(media.values())[len(media) // 2]
        if MEDIA_PLAUSIBLE[0] <= centro <= MEDIA_PLAUSIBLE[1]:
            return {p: round(v, 2) for p, v in media.items()}, unidad
    return None, "el importe medio no cae en ningún rango plausible"


def suma_anual(valores: dict, por_anyo: int) -> dict[str, float]:
    """Suma los subperiodos de cada año, sólo para los años completos."""
    agrupados: dict[str, list[float]] = {}
    for periodo, valor in valores.items():
        agrupados.setdefault(periodo[:4], []).append(valor)
    return {anyo: sum(v) for anyo, v in agrupados.items() if len(v) == por_anyo}


def a_anual(valores: dict) -> dict[str, float]:
    """Deja una serie en años, venga en trimestres o ya en años.

    El INE publica las ejecuciones hipotecarias por trimestres para España y
    las comunidades, pero por provincia sólo el total del año. Comparar un
    trimestre de España con un año de Castellón no significa nada, así que se
    baja todo al denominador común, que es el año.
    """
    if all(len(p) == 4 for p in valores):
        return dict(valores)
    return suma_anual({p: v for p, v in valores.items() if "T" in p}, 4)


def media_anual(valores: dict, minimo: int = 10) -> dict[str, float]:
    """Media de los meses de cada año, sólo para los años casi completos.

    Sin el mínimo, el año en curso aparecería con dos meses y se compararía
    con años enteros.
    """
    por_anyo: dict[str, list[float]] = {}
    for periodo, valor in valores.items():
        anyo = periodo[:4]
        por_anyo.setdefault(anyo, []).append(valor)
    return {anyo: sum(v) / len(v) for anyo, v in por_anyo.items() if len(v) >= minimo}


def renta_por_hogar(ambito_id: str) -> dict[str, float]:
    """Renta neta media por hogar que ya publica el bloque de renta."""
    ruta = RAIZ / "data" / "renta" / f"{ambito_id}.json"
    if not ruta.exists():
        return {}
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    valores = (contenido.get("series", {}).get("ambos", {}) or {}).get("renta_hogar")
    if not valores:
        return {}
    return {periodo: valor
            for periodo, valor in zip(contenido["periodos"], valores)
            if valor is not None}


def posproceso(ambito, series, origen):
    """Añade la hipoteca media y los años de renta que cuesta."""
    magnitudes = series.setdefault("ambos", {})

    ejecuciones = magnitudes.get("ejecuciones")
    if ejecuciones:
        anuales = a_anual(ejecuciones)
        if len(anuales) != len(ejecuciones):
            print(f"      ejecuciones: {len(ejecuciones)} trimestres → "
                  f"{len(anuales)} años completos")
            magnitudes["ejecuciones"] = anuales
            origen.setdefault("ambos", {}).setdefault("ejecuciones", []).append(
                "sumado por años")

    importes = magnitudes.get("importe_hipotecas")
    numeros = magnitudes.get("hipotecas")
    if not importes or not numeros:
        print("      sin hipoteca media: falta el importe o el número")
        return

    media, detalle = hipoteca_media(importes, numeros)
    if not media:
        print(f"      sin hipoteca media: {detalle}")
        return
    magnitudes["hipoteca_media"] = media
    origen.setdefault("ambos", {})["hipoteca_media"] = [
        f"derivado:importe_hipotecas/hipotecas ({detalle})"]
    ultimo = max(media, key=motor.orden_periodo)
    print(f"      hipoteca_media: {len(media)} periodos, {ultimo} = "
          f"{media[ultimo]:,.0f} € (importe en {detalle})")

    renta = renta_por_hogar(ambito["id"])
    if not renta:
        print("      sin esfuerzo: no hay renta por hogar publicada")
        return
    anual = media_anual(media)
    esfuerzo = {anyo: round(valor / renta[anyo], 2)
                for anyo, valor in anual.items() if renta.get(anyo)}
    if not esfuerzo:
        print("      sin esfuerzo: la renta y la hipoteca no comparten años")
        return
    magnitudes["esfuerzo"] = esfuerzo
    origen.setdefault("ambos", {})["esfuerzo"] = [
        "derivado:hipoteca_media anual / renta_hogar"]
    ultimo = max(esfuerzo)
    print(f"      esfuerzo: {len(esfuerzo)} periodos, {ultimo} = {esfuerzo[ultimo]} "
          f"años de renta del hogar")


DERIVADOS = {
    "hipoteca_media": {
        "titulo": "Hipoteca media sobre vivienda", "unidad": "euros", "decimales": 0,
        "unidad_texto": "euros prestados por hipoteca",
        "por_sexo": False,
        "nota": "Importe total entre número de hipotecas del mes. No es el "
                "precio de la vivienda: es lo que se pide prestado.",
    },
    "esfuerzo": {
        "titulo": "Hipoteca media en años de renta del hogar",
        "unidad": "años", "decimales": 2,
        "unidad_texto": "años de renta neta del hogar que suma la hipoteca media",
        "por_sexo": False,
        "nota": "Media anual de la hipoteca media dividida entre la renta neta "
                "media por hogar del Atlas del INE. Mide el endeudamiento de "
                "quien compra, no el precio de la vivienda.",
    },
}


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    CONFIG.mkdir(parents=True, exist_ok=True)
    print("\n=== Vivienda ===")
    por_ambito, procedencias, faltantes = bloques.descarga_bloque(
        "vivienda", BLOQUE, posproceso)
    bloques.escribe_bloque("vivienda", BLOQUE, por_ambito, ahora, RAIZ, DERIVADOS)

    (CONFIG / "series-vivienda.json").write_text(
        json.dumps(procedencias, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if faltantes:
        print(f"\nNo se ha encontrado serie para {len(faltantes)} combinaciones:")
        for f in faltantes:
            print(f"  - {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
