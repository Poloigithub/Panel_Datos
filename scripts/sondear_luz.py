"""El precio de la luz: ¿qué se puede bajar, y con qué detalle?

Red Eléctrica publica los precios del mercado eléctrico en dos sitios que no
son el mismo:

- `apidatos.ree.es`, que es la API pública de los datos del sistema y no pide
  credenciales.
- `api.esios.ree.es`, la del operador del sistema, que para casi todo pide un
  token pero sirve algunos ficheros sueltos sin él.

Lo que hay que averiguar antes de escribir nada es qué indicador da el PVPC
-el precio regulado, que es el que paga quien no ha contratado nada raro-, con
qué antigüedad llega y en qué granularidad. Y una cosa más, que en este caso
es la importante: **el precio de la luz no tiene provincia**. El PVPC es el
mismo en toda la península, así que esta sección no podrá tener los tres
ámbitos del panel y la página tendrá que decirlo en vez de disimularlo.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "sondeos"
CABECERAS = {
    "User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)",
    "Accept": "application/json",
}

HOY = dt.date.today()
AYER = HOY - dt.timedelta(days=1)
HACE_UN_MES = HOY - dt.timedelta(days=31)
HACE_UN_ANYO = HOY - dt.timedelta(days=370)

APIDATOS = "https://apidatos.ree.es/es/datos"

# Segunda vuelta. La primera dejó claro que el PVPC por horas se baja sin
# problema, que el spot viene cada quince minutos y que no hay desglose por
# comunidad. Lo que falta: hasta dónde se puede pedir de una vez -un año por
# días dio error- y hasta cuándo llega el histórico, que es lo que decide si
# esto es una sección o una curiosidad del día.
PRUEBAS = [
    ("medias diarias de un mes",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date={HACE_UN_MES}T00:00&end_date={AYER}T23:59&time_trunc=day"),
    ("medias diarias de un año, acotado a la península",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date={HACE_UN_ANYO}T00:00&end_date={AYER}T23:59&time_trunc=day"
     f"&geo_limit=peninsular&geo_ids=8741"),
    ("medias mensuales de cinco años",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date={HOY.year - 5}-01-01T00:00&end_date={AYER}T23:59"
     f"&time_trunc=month&geo_limit=peninsular&geo_ids=8741"),
    ("¿hasta dónde llega el histórico? un día de 2015",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date=2015-06-15T00:00&end_date=2015-06-15T23:59&time_trunc=hour"),
    ("¿y de 2019?",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date=2019-06-15T00:00&end_date=2019-06-15T23:59&time_trunc=hour"),
    ("hoy, que es lo que se enseñaría arriba de la página",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date={HOY}T00:00&end_date={HOY}T23:59&time_trunc=hour"),
    ("precios en tiempo real, por horas de ayer",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date={AYER}T00:00&end_date={AYER}T23:59&time_trunc=hour"),
    ("PVPC por horas de ayer",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date={AYER}T00:00&end_date={AYER}T23:59&time_trunc=hour"
     f"&geo_limit=peninsular&geo_ids=8741"),
    ("media diaria de un año",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date={HACE_UN_ANYO}T00:00&end_date={AYER}T23:59&time_trunc=day"),
    ("media mensual de un año",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date={HACE_UN_ANYO}T00:00&end_date={AYER}T23:59&time_trunc=month"),
    ("¿hay desglose por comunidad?",
     f"{APIDATOS}/mercados/precios-mercados-tiempo-real"
     f"?start_date={AYER}T00:00&end_date={AYER}T23:59&time_trunc=day"
     f"&geo_trunc=electric_system&geo_limit=ccaa&geo_ids=10"),
    ("PVPC en bruto de esios, sin credencial",
     f"https://api.esios.ree.es/archives/70/download_json?date={AYER}"),
]


def pide(url: str) -> tuple[int, str, bytes]:
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=90) as respuesta:
            return (respuesta.status, respuesta.headers.get("Content-Type", "?"),
                    respuesta.read(4_000_000))
    except urllib.error.HTTPError as exc:
        return exc.code, "-", exc.read(2000) if hasattr(exc, "read") else b""
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}".encode()


def describe(lineas: list[str], datos: bytes) -> None:
    """Qué series trae la respuesta, cuántos puntos y de cuándo a cuándo."""
    try:
        ficha = json.loads(datos)
    except json.JSONDecodeError:
        lineas.append(f"    - no es JSON: {datos[:200].decode('utf-8', 'replace')}")
        return

    if isinstance(ficha, list):
        lineas.append(f"    - lista de {len(ficha)} elementos; el primero: "
                      f"`{json.dumps(ficha[0], ensure_ascii=False)[:300]}`")
        return

    incluidos = ficha.get("included") or []
    if not incluidos:
        # El fichero suelto de esios no tiene la forma de la API pública, así
        # que hay que enseñar lo que sea que traiga.
        lineas.append(f"    - claves: {list(ficha)[:10]}")
        for clave in list(ficha)[:3]:
            valor = ficha[clave]
            if isinstance(valor, list) and valor:
                lineas.append(f"        · `{clave}`: {len(valor)} elementos, "
                              f"el primero `{json.dumps(valor[0], ensure_ascii=False)[:250]}`")
            else:
                lineas.append(f"        · `{clave}`: "
                              f"`{json.dumps(valor, ensure_ascii=False)[:250]}`")
        return
    lineas.append(f"    - {len(incluidos)} series")
    for serie in incluidos[:6]:
        atributos = serie.get("attributes", {})
        valores = atributos.get("values") or []
        titulo = atributos.get("title", "?")
        unidad = atributos.get("magnitude") or atributos.get("type") or "?"
        if valores:
            lineas.append(f"        · **{titulo}** ({unidad}): {len(valores)} puntos, "
                          f"de {valores[0].get('datetime')} a {valores[-1].get('datetime')}")
            lineas.append(f"          primero: {valores[0].get('value')} · "
                          f"último: {valores[-1].get('value')}")
        else:
            lineas.append(f"        · **{titulo}** ({unidad}): sin valores")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# El precio de la luz: qué se puede bajar", "",
              "Y sobre todo: con qué detalle territorial, que en este caso es",
              "la pregunta que decide cómo se presenta la sección.", ""]

    print("=== Precio de la luz ===")
    for etiqueta, url in PRUEBAS:
        estado, tipo, datos = pide(url)
        print(f"  {estado} · {etiqueta}")
        lineas += [f"## {etiqueta}", "", f"`{url}`", "",
                   f"- {estado} ({tipo.split(';')[0]}), {len(datos)} bytes"]
        if estado == 200:
            describe(lineas, datos)
        else:
            lineas.append(f"    - {datos[:300].decode('utf-8', 'replace')}")
        lineas.append("")

    (SALIDA / "luz.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/luz.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
