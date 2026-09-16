"""Sondeo de las fuentes de afiliación a la Seguridad Social.

El paro registrado ya está resuelto con los ficheros del SEPE. Falta saber si
la afiliación tiene algo equivalente: un fichero estable, legible sin
autenticación y con detalle municipal.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SALIDA = Path(__file__).resolve().parents[1] / "data" / "_catalogo"
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

BUSQUEDAS = ["afiliacion", "afiliados", "afiliacion municipios", "seguridad social"]

DIRECTAS = [
    # El SEPE publica contratos con el mismo patrón que el paro.
    "https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Contratos_por_municipios_2026_csv.csv",
    "https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Contratos_por_municipios_2025_csv.csv",
    # Afiliación: patrones publicados por la Seguridad Social.
    "https://www.seg-social.es/wps/wcm/connect/wss/afiliacion_municipios.csv",
    "https://datos.gob.es/es/catalogo.csv",
]


def sondea(url: str, limite: int = 3000):
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=90) as respuesta:
            trozo = respuesta.read(limite)
            for codificacion in ("utf-8", "latin-1"):
                try:
                    return respuesta.status, respuesta.headers.get("Content-Type", "?"), trozo.decode(codificacion)
                except UnicodeDecodeError:
                    continue
            return respuesta.status, "binario", repr(trozo[:120])
    except urllib.error.HTTPError as exc:
        return exc.code, "-", str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}"


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Sondeo de afiliación y contratos", ""]

    for consulta in BUSQUEDAS:
        url = ("https://datos.gob.es/apidata/catalog/dataset/title/"
               + urllib.parse.quote(consulta) + "?_pageSize=12&_page=0")
        codigo, tipo, cuerpo = sondea(url, 80000)
        lineas.append(f"## «{consulta}» → {codigo}")
        if codigo != 200:
            lineas += [f"  {cuerpo[:200]}", ""]
            continue
        try:
            items = (json.loads(cuerpo).get("result") or {}).get("items") or []
        except json.JSONDecodeError:
            lineas += ["  respuesta no JSON", ""]
            continue
        lineas.append(f"  {len(items)} conjuntos")
        for item in items[:8]:
            titulos = item.get("title")
            titulo = (next((t.get("_value") for t in titulos if t.get("_lang") in (None, "es")),
                           titulos[0].get("_value")) if isinstance(titulos, list) else titulos)
            lineas.append(f"  - **{titulo}**")
            # Con una sola distribución la API devuelve un objeto, no una lista.
            distribuciones = item.get("distribution") or []
            if isinstance(distribuciones, dict):
                distribuciones = [distribuciones]
            for dist in distribuciones[:4]:
                if isinstance(dist, dict):
                    lineas.append(f"    - {dist.get('accessURL')}")
        lineas.append("")

    lineas += ["## Direcciones directas", ""]
    for url in DIRECTAS:
        codigo, tipo, cuerpo = sondea(url)
        lineas.append(f"### {url}")
        lineas.append(f"- {codigo} · {tipo}")
        if codigo == 200:
            lineas.append("```")
            lineas += cuerpo.splitlines()[:5]
            lineas.append("```")
        lineas.append("")

    (SALIDA / "afiliacion.md").write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas[:100]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
