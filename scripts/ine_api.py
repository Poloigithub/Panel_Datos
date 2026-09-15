"""Cliente mínimo para la API JSON del INE (Tempus 3).

Documentación: https://www.ine.es/dyngs/DAB/index.htm?cid=1099
Base de la API: https://servicios.ine.es/wstempus/js/{idioma}/{función}/{entrada}[?parámetros]
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://servicios.ine.es/wstempus/js/ES"
USER_AGENT = "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"


class INEError(RuntimeError):
    pass


def _url(funcion: str, entrada: str = "", **params) -> str:
    ruta = f"{BASE}/{funcion}"
    if entrada:
        ruta = f"{ruta}/{entrada}"
    limpios = {k: v for k, v in params.items() if v is not None}
    if limpios:
        ruta = f"{ruta}?{urllib.parse.urlencode(limpios, safe=':,')}"
    return ruta


def get(funcion: str, entrada: str = "", *, reintentos: int = 4, **params):
    """GET a la API del INE devolviendo JSON ya parseado."""
    url = _url(funcion, entrada, **params)
    ultimo_error: Exception | None = None
    for intento in range(reintentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as resp:
                bruto = resp.read().decode("utf-8", errors="replace")
            return json.loads(bruto)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            ultimo_error = exc
            if intento < reintentos - 1:
                espera = 2 ** (intento + 1)
                print(f"  ! fallo en {url} ({exc}); reintento en {espera}s")
                time.sleep(espera)
    raise INEError(f"No se pudo obtener {url}: {ultimo_error}")
