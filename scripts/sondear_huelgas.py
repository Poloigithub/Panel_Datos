"""Huelgas a fondo, y de paso las otras dos que quedaban por mirar.

El sondeo anterior dijo que el fichero mensual de huelgas no baja a provincia
y lo dejó ahí. Es quedarse corto: entre «provincia» y «nada» hay un escalón,
la **comunidad autónoma**, y el índice del fichero habla de «ámbito
territorial» y de «repercusión territorial», que son dos cosas distintas y
ninguna se miró por dentro. También está la monografía anual, que suele traer
más detalle que el avance del mes.

Así que esto abre todas las hojas que mencionen territorio y enseña lo que hay.
Y ya puestos, llama a las puertas de las otras dos candidatas: enfermedades
profesionales y mediación, arbitraje y conciliación.
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
BASE = "https://www.mites.gob.es"
CONDICIONES = f"{BASE}/es/estadisticas/condiciones_trabajo_relac_laborales"

PAGINAS = [
    ("huelgas", f"{CONDICIONES}/HUE/welcome.htm"),
    ("enfermedades profesionales", f"{CONDICIONES}/EPR/welcome.htm"),
    ("mediación, arbitraje y conciliación", f"{CONDICIONES}/MAC/welcome.htm"),
]

ANCLA = re.compile(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
ETIQUETAS = re.compile(r"<[^>]+>")
DATOS = re.compile(r"\.(xlsx?|csv)(\?|$)", re.I)

TERRITORIO = ("territorial", "comunidad autonoma", "provincia", "ccaa")


def limpia(bruto: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(ETIQUETAS.sub(" ", bruto))).strip()


def texto(datos: bytes) -> str:
    for codigo in ("utf-8", "iso-8859-15", "cp1252"):
        try:
            return datos.decode(codigo)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", "replace")


def suave(t: str) -> str:
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
    if datos[:2] == b"PK":
        return xlsx.Libro(datos)
    if datos[:8] == xls.FIRMA:
        return xls.Libro(datos)
    raise ValueError("no es una hoja de cálculo")


def vuelca(lineas: list[str], libro, hoja: str, tope: int = 32) -> None:
    try:
        filas = libro.filas(hoja)
    except Exception as exc:  # noqa: BLE001
        lineas.append(f"    - «{hoja}»: {type(exc).__name__}: {exc}")
        return
    lineas += [f"#### Hoja «{hoja}» · {len(filas)} filas", "```"]
    for i, fila in enumerate(filas[:tope]):
        celdas = [("" if c is None else str(c)) for c in fila[:9]]
        while celdas and celdas[-1] == "":
            celdas.pop()
        if celdas:
            lineas.append(f"{i:>3} | " + " | ".join(celdas))
    lineas += ["```", ""]


def mira(lineas: list[str], url: str, todas_las_territoriales: bool) -> None:
    estado, _, datos = red.abre(url)
    nombre = urllib.parse.unquote(url.split("/")[-1])
    lineas.append(f"### `{nombre}` ({estado}, {len(datos)} bytes)")
    if estado != 200 or len(datos) < 1000:
        lineas += ["    - no se ha podido bajar", ""]
        return
    try:
        libro = abre(datos)
    except Exception as exc:  # noqa: BLE001
        lineas += [f"    - no se abre: {type(exc).__name__}: {exc}", ""]
        return

    hojas = list(libro.hojas)
    lineas.append(f"    - {len(hojas)} hojas")
    indice = next((h for h in hojas if suave(h).startswith("indice")), None)
    territoriales: list[str] = []
    if indice:
        lineas += ["    - su índice:", "```"]
        for fila in libro.filas(indice):
            celdas = [str(c) for c in fila if c not in (None, "")]
            if not celdas:
                continue
            lineas.append(" | ".join(celdas))
            if any(p in suave(" ".join(celdas)) for p in TERRITORIO):
                codigo = suave(celdas[0]).rstrip(". ")
                for h in hojas:
                    if suave(h).rstrip(". ") == codigo:
                        territoriales.append(h)
        lineas += ["```", ""]

    print(f"      {len(territoriales)} hojas territoriales")
    for hoja in territoriales[:(6 if todas_las_territoriales else 2)]:
        vuelca(lineas, libro, hoja)
    if not territoriales:
        lineas += ["    - **ninguna hoja menciona territorio**", ""]


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Huelgas a fondo, y las dos que quedaban", "",
              "Entre «provincia» y «nada» está la comunidad autónoma, que el",
              "sondeo anterior no llegó a mirar.", ""]

    for etiqueta, url in PAGINAS:
        encontradas = anclas(url)
        ficheros = [(n, d) for n, d in encontradas if DATOS.search(d)]
        print(f"· {etiqueta}: {len(ficheros)} ficheros")
        lineas += [f"## {etiqueta}", "", f"`{url}`", ""]
        for n, d in ficheros[:14]:
            lineas.append(f"- {n} → `{d}`")
        lineas.append("")

        es_huelgas = etiqueta == "huelgas"
        # De las huelgas se abren dos: el avance del mes y la monografía anual,
        # que suele traer más detalle. De las otras, con el primero basta.
        candidatos = ficheros[:1]
        if es_huelgas:
            anuales = [f for f in ficheros if "monografic" in f[1].lower()]
            candidatos = ficheros[:1] + anuales[:1]
        for _, destino in candidatos:
            mira(lineas, destino, es_huelgas)

    (SALIDA / "huelgas.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/huelgas.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
