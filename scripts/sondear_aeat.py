"""¿Se puede leer el salario medio por provincia de la Agencia Tributaria?

El sondeo anterior dejó la fase 5 a medias: ninguna operación salarial del INE
llega a provincia, pero la AEAT publica «Mercado de Trabajo y Pensiones en las
Fuentes Tributarias», que sí trae salario medio provincial. Falta saber si sus
tablas se pueden descargar sin manos.

La publicación vive en una dirección por año
(`.../sites/mercado/2023/home.html`), así que esto mira varios años, sigue los
enlaces de esas portadas y apunta qué formatos ofrece cada tabla. Lo que decide
es si hay XLSX o CSV: una tabla en HTML también se puede leer, pero atarse al
maquetado de una página es atarse a que no lo cambien.
"""

from __future__ import annotations

import html
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import ine_series as motor  # noqa: E402

SALIDA = RAIZ / "sondeos"
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

BASE = ("https://sede.agenciatributaria.gob.es/AEAT/Contenidos_Comunes/"
        "La_Agencia_Tributaria/Estadisticas/Publicaciones/sites/mercado/")
ANYOS = ("2023", "2022", "2021")

CATALOGO = ("https://sede.agenciatributaria.gob.es/Sede/datosabiertos/catalogo/hacienda/"
            "Mercado_de_Trabajo_y_Pensiones_en_las_Fuentes_Tributarias.shtml")

FICHERO = re.compile(r'href="([^"]*\.(?:xlsx?|csv|zip)(?:\?[^"]*)?)"', re.I)
ENLACE = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
ETIQUETAS = re.compile(r"<[^>]+>")
CLAVES = ("provincia", "salario", "asalariado", "remuneracion", "territorial")


def descarga(url: str, limite: int = 900_000):
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=120) as respuesta:
            trozo = respuesta.read(limite)
            tipo = respuesta.headers.get("Content-Type", "?")
            for codificacion in ("utf-8", "latin-1"):
                try:
                    return respuesta.status, tipo, trozo.decode(codificacion)
                except UnicodeDecodeError:
                    continue
            return respuesta.status, tipo, ""
    except urllib.error.HTTPError as exc:
        return exc.code, "-", str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}"


def texto(fragmento: str) -> str:
    return " ".join(html.unescape(ETIQUETAS.sub(" ", fragmento)).split())


def mira(url: str, etiqueta: str, lineas: list[str], nivel: int = 0) -> list[str]:
    codigo, tipo, cuerpo = descarga(url)
    lineas += [f"{'#' * (nivel + 3)} {etiqueta}", f"- `{codigo}` · {tipo} · {url}"]
    if codigo != 200 or not cuerpo:
        lineas += [f"- {cuerpo[:200]}", ""]
        return []

    ficheros = sorted({urllib.parse.urljoin(url, html.unescape(h))
                       for h in FICHERO.findall(cuerpo)})
    lineas.append(f"- {len(ficheros)} ficheros descargables")
    for fichero in ficheros[:20]:
        lineas.append(f"    - {fichero}")

    interesantes = []
    for href, etiqueta_enlace in ENLACE.findall(cuerpo):
        limpio = texto(etiqueta_enlace)
        if any(c in motor.normaliza(href + " " + limpio) for c in CLAVES):
            interesantes.append((urllib.parse.urljoin(url, html.unescape(href)), limpio))
    lineas.append(f"- {len(interesantes)} enlaces que mencionan provincia o salario")
    for destino, limpio in interesantes[:20]:
        lineas.append(f"    - **{limpio[:70] or '(sin texto)'}** → {destino}")
    lineas.append("")
    return [d for d, _ in interesantes]


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Sondeo de la Agencia Tributaria", "",
              "La pregunta: ¿se puede descargar sin manos el salario medio por",
              "provincia de «Mercado de Trabajo y Pensiones en las Fuentes",
              "Tributarias»?", "", "## Portadas por año", ""]

    candidatos: list[str] = []
    for anyo in ANYOS:
        print(f"· portada {anyo}")
        candidatos += mira(f"{BASE}{anyo}/home.html", f"Año {anyo}", lineas)

    lineas += ["## Catálogo de datos abiertos", ""]
    candidatos += mira(CATALOGO, "Ficha del catálogo", lineas)

    lineas += ["## Qué hay detrás de los enlaces prometedores", ""]
    vistos: set[str] = set()
    for destino in candidatos:
        if destino in vistos or len(vistos) >= 8:
            continue
        vistos.add(destino)
        print(f"· {destino[:70]}")
        mira(destino, destino.split("/")[-1][:60], lineas, nivel=1)

    (SALIDA / "aeat.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/aeat.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
