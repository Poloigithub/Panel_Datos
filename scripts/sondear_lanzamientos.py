"""Sondeo de los lanzamientos: desahucios por hipoteca y por alquiler.

La estadística de Ejecuciones Hipotecarias del INE, que ya está en el panel,
sólo cuenta hipotecas: no existe en ella la variante de alquiler. Lo que sí se
reparte entre una cosa y otra son los **lanzamientos practicados**, que publica
el Consejo General del Poder Judicial separando los derivados de la Ley
Hipotecaria de los derivados de la Ley de Arrendamientos Urbanos.

La primera versión de este sondeo miró el catálogo de datos.gob.es, que no
tiene nada con ese nombre, y las portadas del CGPJ, de las que sólo leyó los
primeros kilobytes. Esta rastrea el portal de estadística judicial dos niveles
en busca de hojas de cálculo, que es como el CGPJ publica sus datos.
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

SALIDA = RAIZ / "sondeos"
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

SEMILLAS = [
    "https://www.poderjudicial.es/cgpj/es/Temas/Estadistica-Judicial/",
    "https://www.poderjudicial.es/cgpj/es/Temas/Estadistica-Judicial/Estadistica-por-temas/",
    "https://www.poderjudicial.es/cgpj/es/Temas/Estadistica-Judicial/Datos-abiertos/",
]

# Qué se busca en el texto de un enlace para decidir si merece la pena seguirlo.
INTERESANTES = ("lanzamiento", "crisis", "desahucio", "hipotecari", "arrendamiento",
                "civil", "dato", "abierto", "efecto")
FICHEROS = (".xlsx", ".xls", ".csv", ".zip", ".px")
TOPE_PETICIONES = 30

ENLACE = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
ETIQUETAS = re.compile(r"<[^>]+>")


def descarga(url: str, limite: int = 600_000):
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=90) as respuesta:
            bruto = respuesta.read(limite)
            tipo = respuesta.headers.get("Content-Type", "?")
            for codificacion in ("utf-8", "latin-1"):
                try:
                    return respuesta.status, tipo, bruto.decode(codificacion)
                except UnicodeDecodeError:
                    continue
            return respuesta.status, tipo, ""
    except urllib.error.HTTPError as exc:
        return exc.code, "-", str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}"


def enlaces_de(base: str, cuerpo: str) -> list[tuple[str, str]]:
    encontrados = []
    for href, texto in ENLACE.findall(cuerpo):
        limpio = html.unescape(ETIQUETAS.sub(" ", texto))
        limpio = " ".join(limpio.split())
        encontrados.append((urllib.parse.urljoin(base, html.unescape(href)), limpio))
    return encontrados


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Sondeo de lanzamientos (hipoteca y alquiler)", "",
              "Rastreo del portal de estadística judicial del CGPJ en busca de los",
              "ficheros de lanzamientos practicados, que separan los derivados de la Ley",
              "Hipotecaria de los de la Ley de Arrendamientos Urbanos.", ""]

    por_visitar = [(u, "semilla", 0) for u in SEMILLAS]
    vistos: set[str] = set()
    ficheros: list[tuple[str, str, str]] = []
    peticiones = 0

    while por_visitar and peticiones < TOPE_PETICIONES:
        url, etiqueta, nivel = por_visitar.pop(0)
        if url in vistos:
            continue
        vistos.add(url)
        peticiones += 1
        codigo, tipo, cuerpo = descarga(url)
        print(f"  [{peticiones}] {codigo} {url}")
        lineas.append(f"- `{codigo}` nivel {nivel} · **{etiqueta}** · {url}")
        if codigo != 200 or "html" not in tipo:
            continue

        for destino, texto in enlaces_de(url, cuerpo):
            bajo = (destino + " " + texto).lower()
            if destino.lower().endswith(FICHEROS):
                if destino not in [f[0] for f in ficheros]:
                    ficheros.append((destino, texto, url))
                continue
            if nivel >= 1 or "poderjudicial.es" not in destino:
                continue
            if any(p in bajo for p in INTERESANTES):
                por_visitar.append((destino, texto[:60], nivel + 1))

    lineas += ["", f"## {len(ficheros)} ficheros descargables encontrados", ""]
    for destino, texto, desde in ficheros:
        lineas.append(f"- **{texto or '(sin texto)'}**")
        lineas.append(f"    - {destino}")
        lineas.append(f"    - enlazado desde {desde}")

    interesantes = [f for f in ficheros
                    if any(p in (f[0] + " " + f[1]).lower()
                           for p in ("lanzamiento", "crisis", "hipotecari", "arrendamiento"))]
    lineas += ["", f"## De ésos, {len(interesantes)} suenan a lanzamientos", ""]
    for destino, texto, _ in interesantes:
        codigo, tipo, _ = descarga(destino, 2000)
        lineas.append(f"- `{codigo}` {tipo} · {texto} · {destino}")

    (SALIDA / "lanzamientos.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/lanzamientos.md ({len(lineas)} líneas, "
          f"{peticiones} peticiones, {len(ficheros)} ficheros)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
