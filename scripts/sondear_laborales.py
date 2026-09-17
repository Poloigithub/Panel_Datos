"""Huelgas, despidos y regulación de empleo: las tres que quedaban.

El lector de `.xls` dejó a tiro tres estadísticas del Ministerio de Trabajo que
el panel no podía tocar, y las tres cuentan cosas que no cuenta ninguna otra:

- **Huelgas y cierres patronales** (`hue`): cuántas huelgas hay, cuánta gente
  las secunda y cuántas jornadas se pierden. Es la única medida de conflicto
  laboral que existe.
- **Despidos y su coste** (`dec`): cuántos despidos se declaran improcedentes y
  cuánto se paga por ellos.
- **Regulación de empleo** (`reg`): los ERE y ERTE, con los trabajadores
  afectados por tipo de medida.

De las tres hay que averiguar lo de siempre -cómo se llaman sus ficheros, qué
hoja baja a provincia y cómo está montada- y una cosa más: `reg` ya publica en
XLSX desde 2023, así que ésa ni siquiera necesita el lector nuevo.
"""

from __future__ import annotations

import html
import re
import sys
import urllib.parse
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import red_ministerio as red  # noqa: E402
import xls  # noqa: E402
import xlsx  # noqa: E402

SALIDA = RAIZ / "sondeos"
BASE = "https://www.mites.gob.es/es/estadisticas/condiciones_trabajo_relac_laborales"

# Las direcciones buenas, que las trajo el propio índice del ministerio. Las
# primeras eran inventadas a partir del nombre de la estadística, y como el
# sitio devuelve su portada con un 200 para lo que no existe, en vez de un 404
# se recibía el organigrama entero.
PAGINAS = [
    ("huelgas", f"{BASE}/HUE/welcome.htm"),
    ("despidos", f"{BASE}/dec/welcome.htm"),
    ("regulación de empleo", f"{BASE}/REG/welcome.htm"),
    ("enfermedades profesionales", f"{BASE}/EPR/welcome.htm"),
]

ANCLA = re.compile(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
ETIQUETAS = re.compile(r"<[^>]+>")
DATOS = re.compile(r"\.(xlsx?|csv)(\?|$)", re.I)

# Lo que se busca dentro de cada libro.
PROVINCIAL = ("provincia",)


def limpia(bruto: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(ETIQUETAS.sub(" ", bruto))).strip()


def texto(datos: bytes) -> str:
    for codigo in ("utf-8", "iso-8859-15", "cp1252"):
        try:
            return datos.decode(codigo)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", "replace")


def normaliza(t: str) -> str:
    plano = (t or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return " ".join(plano.split())


def anclas(url: str) -> list[tuple[str, str]]:
    estado, tipo, datos = red.abre(url, limite=4_000_000)
    if estado != 200 or "html" not in tipo.lower():
        return []
    return [(limpia(b), urllib.parse.urljoin(url, html.unescape(d)))
            for d, b in ANCLA.findall(texto(datos)) if limpia(b)]


def abre(datos: bytes):
    """El libro, sea del formato que sea. Ésa es la gracia de tener los dos."""
    if datos[:2] == b"PK":
        return xlsx.Libro(datos), "XLSX"
    if datos[:8] == xls.FIRMA:
        return xls.Libro(datos), "xls binario"
    raise ValueError("no es una hoja de cálculo")


def mira_dentro(lineas: list[str], url: str) -> None:
    estado, _, datos = red.abre(url)
    nombre = urllib.parse.unquote(url.split("/")[-1])
    lineas.append(f"### `{nombre}` ({estado}, {len(datos)} bytes)")
    if estado != 200 or len(datos) < 1000:
        lineas += ["    - no se ha podido bajar", ""]
        return
    try:
        libro, formato = abre(datos)
    except Exception as exc:  # noqa: BLE001
        lineas += [f"    - no se ha podido abrir: {type(exc).__name__}: {exc}", ""]
        return

    hojas = list(libro.hojas)
    lineas.append(f"    - {formato}, {len(hojas)} hojas")
    indice = next((h for h in hojas if normaliza(h).startswith("indice")), None)
    elegida = None
    if indice:
        lineas += ["    - su índice:", "```"]
        for fila in libro.filas(indice):
            celdas = [str(c) for c in fila if c not in (None, "")]
            if not celdas:
                continue
            lineas.append(" | ".join(celdas))
            plano = normaliza(" ".join(celdas))
            if not elegida and all(p in plano for p in PROVINCIAL):
                codigo = normaliza(celdas[0]).rstrip(". ")
                for h in hojas:
                    if normaliza(h).rstrip(". ") == codigo:
                        elegida = h
        lineas += ["```", ""]

    if elegida:
        lineas += [f"    - hoja provincial: «{elegida}»", "```"]
        for i, fila in enumerate(libro.filas(elegida)[:30]):
            celdas = [("" if c is None else str(c)) for c in fila[:10]]
            while celdas and celdas[-1] == "":
                celdas.pop()
            if celdas:
                lineas.append(f"{i:>3} | " + " | ".join(celdas))
        lineas += ["```", ""]
    else:
        lineas += ["    - **ninguna hoja baja a provincia**", ""]


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Huelgas, despidos y regulación de empleo", "",
              "Las tres que el lector de .xls dejó a tiro. De cada una: cómo se",
              "llaman sus ficheros, qué hoja baja a provincia y en qué formato.",
              ""]

    for etiqueta, url in PAGINAS:
        encontradas = anclas(url)
        ficheros = [(n, d) for n, d in encontradas if DATOS.search(d)]
        print(f"· {etiqueta}: {len(encontradas)} enlaces, {len(ficheros)} ficheros")
        lineas += [f"## {etiqueta}", "", f"`{url}` · {len(encontradas)} enlaces", ""]
        for n, d in ficheros[:12]:
            lineas.append(f"- {n} → `{d}`")
        if not ficheros:
            for n, d in encontradas:
                if "/estadisticas/" in d.lower() and len(n) > 4:
                    lineas.append(f"- {n} → `{d}`")
        lineas.append("")

        for _, destino in ficheros[:1]:
            mira_dentro(lineas, destino)

    (SALIDA / "laborales.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/laborales.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
