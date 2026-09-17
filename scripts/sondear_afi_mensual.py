"""¿Publica el ministerio la afiliación cada mes, y con provincia?

La sección de afiliación es anual, del Anuario de Estadísticas, y su último
dato es de 2025. Pero el ministerio publica también un avance mensual, y si
trae provincia convertiría una de las secciones más quietas del panel en una
de las que más se mueven: el empleo de Castellón con dos meses de retraso en
vez de un año.

El mapa de carpetas del sondeo anterior dejó dos candidatas con cadencia
mensual y formato XLSX: `Emp` -que el índice llama «Empresas inscritas en la
Seguridad Social»- y `reg`, que es regulación de empleo. Ninguna suena a
afiliación, así que primero hay que mirar la página de la estadística y ver
a dónde enlaza de verdad.
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
from xlsx import Libro  # noqa: E402

SALIDA = RAIZ / "sondeos"
BASE = "https://www.mites.gob.es"

PAGINAS = [
    ("afiliación", f"{BASE}/es/estadisticas/mercado_trabajo/AFI/welcome.htm"),
    ("autónomos", f"{BASE}/es/estadisticas/mercado_trabajo/TAASS/welcome.htm"),
    ("empresas", f"{BASE}/es/estadisticas/mercado_trabajo/EMP/welcome.htm"),
    ("mercado de trabajo", f"{BASE}/es/estadisticas/mercado_trabajo/index.htm"),
]

ANCLA = re.compile(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
ETIQUETAS = re.compile(r"<[^>]+>")
DATOS = re.compile(r"\.(xlsx?|csv)(\?|$)", re.I)


def limpia(bruto: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(ETIQUETAS.sub(" ", bruto))).strip()


def texto(datos: bytes) -> str:
    for codigo in ("utf-8", "iso-8859-15", "cp1252"):
        try:
            return datos.decode(codigo)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", "replace")


def anclas(url: str) -> list[tuple[str, str]]:
    estado, tipo, datos = red.abre(url, limite=4_000_000)
    if estado != 200 or "html" not in tipo.lower():
        return []
    salida = []
    for destino, bruto in ANCLA.findall(texto(datos)):
        nombre = limpia(bruto)
        if nombre and len(nombre) > 2:
            salida.append((nombre, urllib.parse.urljoin(url, html.unescape(destino))))
    return salida


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# ¿Hay afiliación mensual, y con provincia?", "",
              "Si la hay, la sección pasa de tener el último dato en 2025 a",
              "tenerlo con dos meses de retraso.", ""]

    vistos: set[str] = set()
    ficheros: list[tuple[str, str]] = []

    for etiqueta, url in PAGINAS:
        encontradas = anclas(url)
        print(f"· {etiqueta}: {len(encontradas)} enlaces")
        lineas += [f"## {etiqueta}", "", f"`{url}` · {len(encontradas)} enlaces", ""]
        for nombre, destino in encontradas:
            if "/estadisticas/" not in destino.lower():
                continue
            if destino in vistos:
                continue
            vistos.add(destino)
            lineas.append(f"- {nombre} → `{destino}`")
            if DATOS.search(destino):
                ficheros.append((nombre, destino))
        lineas.append("")

    # Y un nivel más adentro: la página de la estadística suele enlazar a la
    # del mes publicado, y es ahí donde cuelgan los ficheros.
    lineas += ["## Un nivel más adentro", ""]
    dentro_de = [(n, d) for n, d in anclas(PAGINAS[0][1])
                 if "/estadisticas/" in d.lower() and not DATOS.search(d)]
    for nombre, destino in dentro_de[:12]:
        sueltos = [(n, d) for n, d in anclas(destino) if DATOS.search(d)]
        if not sueltos:
            continue
        lineas.append(f"### {nombre} · `{destino}` · {len(sueltos)} ficheros")
        for n, d in sueltos[:15]:
            lineas.append(f"- {n} → `{d}`")
            ficheros.append((n, d))
        lineas.append("")

    # Abrir el primer XLSX que aparezca, a ver si trae provincias.
    lineas += ["## Por dentro", ""]
    abiertos = 0
    for nombre, url in ficheros:
        if abiertos >= 2 or not re.search(r"\.xlsx($|\?)", url, re.I):
            continue
        estado, _, datos = red.abre(url)
        lineas.append(f"### `{url.split('/')[-1]}` ({estado}, {len(datos)} bytes)")
        print(f"    abriendo {url.split('/')[-1]}: {estado}")
        if estado == 200 and datos[:2] == b"PK":
            try:
                libro = Libro(datos)
                hojas = list(libro.hojas)
                lineas.append(f"    - {len(hojas)} hojas: "
                              + ", ".join(f"«{h}»" for h in hojas[:30]))
                provinciales = [h for h in hojas if "prov" in h.lower()]
                for hoja in (provinciales or hojas)[:2]:
                    filas = libro.filas(hoja)
                    lineas.append(f"    - hoja «{hoja}», {len(filas)} filas:")
                    for fila in filas[:20]:
                        celdas = [("" if c is None else str(c)) for c in fila[:8]]
                        while celdas and celdas[-1] == "":
                            celdas.pop()
                        if celdas:
                            lineas.append(f"        · {' | '.join(celdas)}")
            except Exception as exc:  # noqa: BLE001
                lineas.append(f"    - no se ha podido abrir: "
                              f"{type(exc).__name__}: {exc}")
        lineas.append("")
        abiertos += 1
    if abiertos == 0:
        lineas.append("*No ha aparecido ningún XLSX que abrir.*")

    (SALIDA / "afi-mensual.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/afi-mensual.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
