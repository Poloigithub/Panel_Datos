"""Sondeo de los lanzamientos: desahucios por hipoteca y por alquiler.

La estadística de Ejecuciones Hipotecarias del INE, que ya está en el panel,
sólo cuenta hipotecas: no existe en ella la variante de alquiler. Lo que sí se
reparte entre una cosa y otra son los **lanzamientos practicados**, que publica
el Consejo General del Poder Judicial separando los derivados de la Ley
Hipotecaria de los derivados de la Ley de Arrendamientos Urbanos.

Dos sondeos anteriores descartaron el catálogo de datos.gob.es -no tiene nada
con ese nombre- y un rastreo a ciegas del portal del CGPJ, que se fue por
secciones que no eran. Pero enseñó la puerta buena: el CGPJ mantiene una base
de datos de estadística judicial en PC-Axis, que es formato máquina. Esta
versión mira esa página y las de datos civiles enteras, y apunta todo enlace
que huela a fichero, venga con la extensión que venga.
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

PAGINAS = [
    ("PC-Axis", "https://www.poderjudicial.es/cgpj/es/Temas/Estadistica-Judicial/"
                "Base-de-datos-de-la-estadistica-judicial--PC-AXIS-/"),
    ("Datos civiles", "https://www.poderjudicial.es/cgpj/es/Temas/Estadistica-Judicial/"
                      "Estadistica-por-temas/Datos-penales--civiles-y-laborales/"),
    ("Justicia dato a dato", "https://www.poderjudicial.es/cgpj/es/Temas/Estadistica-Judicial/"
                             "Estudios-e-Informes/Justicia-Dato-a-Dato/Justicia-Dato-a-Dato"),
    ("Buscador del sitio", "https://www.poderjudicial.es/search/indexAN.jsp?"
                           "org=cgpj&tem=&loc=&query=lanzamientos"),
    # El portal estadístico de la Generalitat republica datos del CGPJ para la
    # Comunitat y sus provincias, y su pxweb sí es formato máquina.
    ("PEGV", "https://pegv.gva.es/es/temas/sociedad/justicia"),
]

# Un fichero de datos puede colgar de cualquier ruta; lo que lo delata es la
# extensión o el almacén de ficheros del CGPJ, que es /stfls/.
FICHERO = re.compile(r'(?:href|src)="([^"]*(?:\.xlsx|\.xls|\.csv|\.zip|\.px|/stfls/)[^"]*)"', re.I)
ENLACE = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
ETIQUETAS = re.compile(r"<[^>]+>")
CLAVES = ("lanzamiento", "crisis", "hipotecari", "arrendamiento", "desahucio", "efecto")


def descarga(url: str, limite: int = 1_500_000):
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=120) as respuesta:
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


def texto_de(fragmento: str) -> str:
    return " ".join(html.unescape(ETIQUETAS.sub(" ", fragmento)).split())


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Sondeo de lanzamientos (hipoteca y alquiler)", "",
              "Los lanzamientos practicados los publica el CGPJ separando los de la Ley",
              "Hipotecaria de los de la Ley de Arrendamientos Urbanos. Aquí se busca en",
              "qué formato y con qué detalle territorial.", ""]

    candidatos: list[str] = []

    for nombre, url in PAGINAS:
        print(f"· {nombre}")
        codigo, tipo, cuerpo = descarga(url)
        lineas += [f"## {nombre}", f"- `{codigo}` · {tipo} · {url}",
                   f"- {len(cuerpo)} caracteres"]
        if codigo != 200 or not cuerpo:
            lineas += [f"- {cuerpo[:200]}", ""]
            continue

        ficheros = {urllib.parse.urljoin(url, html.unescape(h)) for h in FICHERO.findall(cuerpo)}
        lineas.append(f"- {len(ficheros)} enlaces a fichero de datos")
        for destino in sorted(ficheros)[:25]:
            lineas.append(f"    - {destino}")
        candidatos += list(ficheros)

        # Enlaces cuyo texto menciona lo que se busca, sea cual sea su destino.
        interesantes = [(urllib.parse.urljoin(url, html.unescape(href)), texto_de(texto))
                        for href, texto in ENLACE.findall(cuerpo)
                        if any(c in (href + texto).lower() for c in CLAVES)]
        lineas.append(f"- {len(interesantes)} enlaces que mencionan lanzamientos o afines")
        for destino, texto in interesantes[:20]:
            lineas.append(f"    - **{texto[:80] or '(sin texto)'}** → {destino}")
        candidatos += [d for d, _ in interesantes]
        lineas.append("")

    # Segundo nivel: se abre lo que ha salido, para ver si lleva a un fichero.
    lineas += ["## Qué hay detrás de los candidatos", ""]
    vistos: set[str] = set()
    for destino in candidatos:
        if destino in vistos or len(vistos) >= 12:
            continue
        vistos.add(destino)
        codigo, tipo, cuerpo = descarga(destino, 400_000)
        lineas.append(f"### `{codigo}` {tipo}")
        lineas.append(f"- {destino}")
        if codigo == 200 and "html" in tipo:
            ficheros = {urllib.parse.urljoin(destino, html.unescape(h))
                        for h in FICHERO.findall(cuerpo)}
            lineas.append(f"- {len(ficheros)} ficheros de datos dentro")
            for f in sorted(ficheros)[:15]:
                lineas.append(f"    - {f}")
        elif codigo == 200:
            lineas.append(f"- descarga directa de {len(cuerpo)} caracteres")
        lineas.append("")

    (SALIDA / "lanzamientos.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/lanzamientos.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
