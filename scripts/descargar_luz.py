"""El precio de la luz, hora a hora y mes a mes.

Del PVPC -el precio regulado, el que paga quien no ha contratado nada raro-,
que publica Red Eléctrica en una API abierta y sin credenciales.

Tres cosas que este dato obliga a decir en voz alta:

- **No tiene provincia.** El PVPC es el mismo en toda la península. Es la única
  sección del panel sin los tres ámbitos, y la página lo dice en vez de
  disimularlo repitiendo la misma cifra tres veces.
- **La API no agrega.** Pedir medias diarias o mensuales devuelve error: sólo
  sirve hora a hora. Las medias las calcula el panel. Lo que sí acepta son
  rangos de hasta un mes, así que se baja un mes por petición.
- **El histórico vive en el repositorio.** Una vez bajado un mes, no se vuelve
  a pedir: se guarda el detalle diario en `diario.json` y cada actualización
  sólo pide el mes en curso y los que falten. El primer día son sesenta y
  pico peticiones; a partir de ahí, una.

Se guarda en **céntimos por kWh**, que es la unidad de una factura, y no en
euros por megavatio hora, que es como lo publica Red Eléctrica. Es una simple
división entre diez y evita que el lector tenga que hacerla de cabeza.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import bloques_ine as bloques  # noqa: E402

DESTINO = RAIZ / "data" / "luz"
DIARIO = DESTINO / "diario.json"

API = ("https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"
       "?start_date={desde}T00:00&end_date={hasta}T23:59&time_trunc=hour")
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)",
             "Accept": "application/json"}

# Junio de 2021, y no es una fecha arbitraria: es cuando entró la tarifa 2.0TD
# con tramos horarios y la API deja de servir PVPC hacia atrás. Pedir los meses
# anteriores era gastar cinco peticiones para que contestaran vacío.
PRIMER_MES = (2021, 6)
DE_MWH_A_KWH = 10        # 100 €/MWh son 10 céntimos por kWh

# Un mes cuenta para la serie mensual cuando están casi todos sus días. Con
# menos, la media diría más del hueco que del precio.
DIAS_MINIMOS = 26

AVISO_PENINSULAR = ("El PVPC es el mismo en toda la península, así que esta "
                    "serie no tiene desglose territorial: repetir la misma "
                    "cifra para la Comunitat y para Castellón sería fingir un "
                    "detalle que no existe.")

BLOQUE = {
    "titulo": "El precio de la luz",
    "indicadores": {
        "pvpc_medio": {
            "titulo": "Precio medio de la luz",
            "unidad": "c€/kWh", "decimales": 2, "por_sexo": False,
            "unidad_texto": "céntimos de euro por kilovatio hora, media del mes",
            "sin_ambitos": ("castellon", "comunitat-valenciana"),
            "nota": AVISO_PENINSULAR,
        },
        "pvpc_barata": {
            "titulo": "La hora más barata del día",
            "unidad": "c€/kWh", "decimales": 2, "por_sexo": False,
            "unidad_texto": "media de la hora más barata de cada día del mes",
            "sin_ambitos": ("castellon", "comunitat-valenciana"),
        },
        "pvpc_cara": {
            "titulo": "La hora más cara del día",
            "unidad": "c€/kWh", "decimales": 2, "por_sexo": False,
            "unidad_texto": "media de la hora más cara de cada día del mes",
            "sin_ambitos": ("castellon", "comunitat-valenciana"),
        },
        "pvpc_brecha": {
            "titulo": "Diferencia entre la hora cara y la barata",
            "unidad": "c€/kWh", "decimales": 2, "por_sexo": False,
            "unidad_texto": "cuánto se ahorra al día quien puede elegir la hora",
            "sin_ambitos": ("castellon", "comunitat-valenciana"),
            # Sin nota: «cuánto se ahorra al día quien puede elegir la hora»
            # ya está en la unidad, justo encima. Repetirlo debajo, más largo,
            # no añadía nada.
        },
    },
}


def pide(url: str, intentos: int = 4) -> dict | None:
    espera = 2
    for intento in range(intentos):
        try:
            peticion = urllib.request.Request(url, headers=CABECERAS)
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                return json.loads(respuesta.read(8_000_000))
        except urllib.error.HTTPError as exc:
            # Un 400 aquí no es un fallo pasajero: es que ese rango no existe.
            if exc.code == 400:
                return None
            if intento == intentos - 1:
                print(f"      {exc.code} en {url[:90]}")
                return None
        except Exception as exc:  # noqa: BLE001
            if intento == intentos - 1:
                print(f"      {type(exc).__name__} en {url[:90]}")
                return None
        time.sleep(espera)
        espera *= 2
    return None


def horas_pvpc(ficha: dict) -> list[tuple[str, float]]:
    """Las horas del PVPC, en céntimos por kWh y con su fecha y hora."""
    for serie in ficha.get("included") or []:
        atributos = serie.get("attributes", {})
        if "pvpc" not in (atributos.get("title") or "").lower():
            continue
        salida = []
        for punto in atributos.get("values") or []:
            momento = punto.get("datetime") or ""
            valor = punto.get("value")
            if len(momento) >= 13 and isinstance(valor, (int, float)):
                salida.append((momento[:13], valor / DE_MWH_A_KWH))
        return salida
    return []


def resume_dias(horas: list[tuple[str, float]]) -> dict[str, dict]:
    """De horas sueltas a un resumen por día: media, la más barata y la más cara."""
    por_dia: dict[str, list[tuple[int, float]]] = {}
    for momento, valor in horas:
        dia, hora = momento[:10], int(momento[11:13])
        por_dia.setdefault(dia, []).append((hora, valor))

    resumen = {}
    for dia, valores in por_dia.items():
        # Un día con menos de veinte horas está a medio publicar; el de cambio
        # de hora tiene 23 o 25 y ésos sí valen.
        if len(valores) < 20:
            continue
        barata = min(valores, key=lambda v: v[1])
        cara = max(valores, key=lambda v: v[1])
        resumen[dia] = {
            "media": round(sum(v for _, v in valores) / len(valores), 4),
            "minimo": round(barata[1], 4), "hora_minima": barata[0],
            "maximo": round(cara[1], 4), "hora_maxima": cara[0],
            "horas": len(valores),
        }
    return resumen


def meses_hasta(hoy: dt.date) -> list[tuple[int, int]]:
    meses = []
    anyo, mes = PRIMER_MES
    while (anyo, mes) <= (hoy.year, hoy.month):
        meses.append((anyo, mes))
        anyo, mes = (anyo + 1, 1) if mes == 12 else (anyo, mes + 1)
    return meses


def fin_de_mes(anyo: int, mes: int) -> dt.date:
    return (dt.date(anyo + 1, 1, 1) if mes == 12 else dt.date(anyo, mes + 1, 1)) \
        - dt.timedelta(days=1)


def dias_del_mes(anyo: int, mes: int, diario: dict) -> int:
    prefijo = f"{anyo}-{mes:02d}-"
    return sum(1 for dia in diario if dia.startswith(prefijo))


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    hoy = dt.date.today()
    DESTINO.mkdir(parents=True, exist_ok=True)
    print("\n=== El precio de la luz ===")

    diario: dict[str, dict] = {}
    if DIARIO.exists():
        diario = json.loads(DIARIO.read_text(encoding="utf-8")).get("dias", {})
        print(f"  {len(diario)} días ya guardados")

    pedidos = 0
    ultimas_horas: list[tuple[str, float]] = []
    for anyo, mes in meses_hasta(hoy):
        completo = fin_de_mes(anyo, mes)
        esperados = completo.day if completo < hoy else hoy.day
        # Un mes cerrado y entero no se vuelve a pedir nunca: ya está en git.
        if dias_del_mes(anyo, mes, diario) >= esperados - 1 and completo < hoy:
            continue
        desde = dt.date(anyo, mes, 1)
        hasta = min(completo, hoy)
        ficha = pide(API.format(desde=desde, hasta=hasta))
        pedidos += 1
        if not ficha:
            print(f"    {anyo}-{mes:02d}: sin datos")
            continue
        horas = horas_pvpc(ficha)
        nuevos = resume_dias(horas)
        diario.update(nuevos)
        # El mes en curso es siempre el último que se pide, así que sus horas
        # sirven para el detalle del último día sin gastar otra petición.
        ultimas_horas = horas
        print(f"    {anyo}-{mes:02d}: {len(nuevos)} días")

    if not diario:
        print("  no se ha podido bajar nada")
        return 1

    DIARIO.write_text(json.dumps(
        {"actualizado": ahora, "unidad": "c€/kWh", "dias": dict(sorted(diario.items()))},
        ensure_ascii=False), encoding="utf-8")
    print(f"  {pedidos} peticiones · {len(diario)} días en total")

    # ------------------------------------------------- la serie mensual
    por_mes: dict[str, list[dict]] = {}
    for dia, ficha in diario.items():
        por_mes.setdefault(f"{dia[:4]}M{dia[5:7]}", []).append(ficha)

    series: dict[str, dict[str, float]] = {}
    for periodo, fichas in por_mes.items():
        if len(fichas) < DIAS_MINIMOS:
            continue
        cuantos = len(fichas)
        series.setdefault("pvpc_medio", {})[periodo] = \
            sum(f["media"] for f in fichas) / cuantos
        series.setdefault("pvpc_barata", {})[periodo] = \
            sum(f["minimo"] for f in fichas) / cuantos
        series.setdefault("pvpc_cara", {})[periodo] = \
            sum(f["maximo"] for f in fichas) / cuantos
        series.setdefault("pvpc_brecha", {})[periodo] = \
            sum(f["maximo"] - f["minimo"] for f in fichas) / cuantos

    por_ambito = {"espana": {"ambos": series},
                  "comunitat-valenciana": {"ambos": {}},
                  "castellon": {"ambos": {}}}
    periodos = bloques.escribe_bloque("luz", BLOQUE, por_ambito, ahora, RAIZ)

    # ------------------------------------------------- el día más reciente
    # Lo que se enseña arriba de la página: las veinticuatro horas del último
    # día publicado. Salen de la última petición, que es la del mes en curso.
    ultimo = max(diario)
    detalle = [{"hora": int(momento[11:13]), "valor": round(valor, 4)}
               for momento, valor in sorted(ultimas_horas)
               if momento[:10] == ultimo]
    (DESTINO / "hoy.json").write_text(json.dumps({
        "actualizado": ahora, "dia": ultimo, "unidad": "c€/kWh",
        "resumen": diario[ultimo], "horas": detalle,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  escrito data/luz/hoy.json ({ultimo}, {len(detalle)} horas)")

    if periodos:
        ultimo_mes = periodos[-1]
        print(f"  media de {ultimo_mes}: "
              f"{series['pvpc_medio'][ultimo_mes]:.2f} c€/kWh")
    return 0 if periodos else 1


if __name__ == "__main__":
    raise SystemExit(main())
