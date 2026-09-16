"""Qué publican SEPE y Seguridad Social, y en qué formato.

Diagnóstico previo al parser. La lección de la fase 1 es que adivinar sale
caro: aquí se comprueba qué responde cada fuente antes de escribir nada.

Se usa datos.gob.es como directorio -su API es estable y apunta a las URLs
reales de descarga- y además se prueban las direcciones directas conocidas.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SALIDA = Path(__file__).resolve().parents[1] / "data" / "_catalogo"
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

BUSQUEDAS = ["paro registrado municipios", "afiliacion seguridad social municipios",
             "contratos registrados municipios"]

# Direcciones que el SEPE y la Seguridad Social han usado para sus ficheros.
DIRECTAS = [
    "https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Paro_por_municipios_2026_csv.csv",
    "https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Paro_por_municipios_2025_csv.csv",
    "https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Paro_por_municipios_2024_csv.csv",
    "https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Paro_registrado_por_municipios_2025_csv.csv",
]


def descarga(url: str, limite: int = 4000) -> tuple[int, str, str]:
    """(código, tipo de contenido, primeros bytes) sin descargar el fichero entero."""
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=90) as respuesta:
            tipo = respuesta.headers.get("Content-Type", "?")
            trozo = respuesta.read(limite)
            for codificacion in ("utf-8", "latin-1"):
                try:
                    return respuesta.status, tipo, trozo.decode(codificacion)
                except UnicodeDecodeError:
                    continue
            return respuesta.status, tipo, repr(trozo[:200])
    except urllib.error.HTTPError as exc:
        return exc.code, "-", f"HTTPError: {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}"


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Fuentes de paro registrado y afiliación", ""]

    lineas += ["## Catálogo de datos.gob.es", ""]
    for consulta in BUSQUEDAS:
        url = ("https://datos.gob.es/apidata/catalog/dataset/title/"
               + urllib.parse.quote(consulta)
               + "?_pageSize=10&_page=0&_sort=title")
        codigo, tipo, cuerpo = descarga(url, 60000)
        lineas.append(f"### «{consulta}» → {codigo} ({tipo})")
        if codigo != 200:
            lineas += [f"```\n{cuerpo[:500]}\n```", ""]
            continue
        try:
            datos = json.loads(cuerpo)
        except json.JSONDecodeError:
            lineas += ["respuesta no es JSON", f"```\n{cuerpo[:500]}\n```", ""]
            continue

        items = (datos.get("result") or {}).get("items") or []
        lineas.append(f"{len(items)} conjuntos de datos")
        for item in items[:6]:
            titulos = item.get("title")
            if isinstance(titulos, list):
                titulo = next((t.get("_value") for t in titulos
                               if t.get("_lang") in (None, "es")), titulos[0].get("_value"))
            else:
                titulo = titulos
            lineas.append(f"- **{titulo}**")
            lineas.append(f"  - publicador: {item.get('publisher')}")
            for dist in (item.get("distribution") or [])[:6]:
                if isinstance(dist, dict):
                    lineas.append(f"  - {dist.get('format', {}).get('value', '?')} "
                                  f"→ {dist.get('accessURL')}")
        lineas.append("")

    lineas += ["## Direcciones directas", ""]
    for url in DIRECTAS:
        codigo, tipo, cuerpo = descarga(url)
        lineas.append(f"### {url}")
        lineas.append(f"- {codigo} · {tipo}")
        if codigo == 200:
            primeras = cuerpo.splitlines()[:6]
            lineas.append("```")
            lineas += primeras
            lineas.append("```")
        else:
            lineas.append(f"  {cuerpo[:200]}")
        lineas.append("")

    (SALIDA / "paro.md").write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas[:120]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
