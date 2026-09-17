"""Qué es cada carpeta del ministerio, y qué hay dentro de las que importan.

El sondeo anterior dejó el mapa del terreno: `eat`, `cct`, `hue`, `reg`, `Emp`,
`Mac`, `EAL`, `ajs`, `dec`. Lo que no dejó es qué significa cada una, y sin eso
no se puede decidir nada: **no hay ninguna carpeta que se llame `afi` ni `ele`**,
así que o la afiliación y las elecciones sindicales están escondidas detrás de
uno de esos códigos, o el ministerio no las publica aquí.

La traducción está en el texto de los enlaces, que es lo que lee una persona
cuando entra. Esto los recoge -texto y destino, juntos- y de paso abre por
dentro lo más reciente de las carpetas que publican en XLSX y con la cadencia
que tendría la afiliación.
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

PORTALES = [
    f"{BASE}/estadisticas/bel/welcome.htm",
    f"{BASE}/es/estadisticas/index.htm",
    f"{BASE}/es/estadisticas/condiciones_trabajo_relac_laborales/index.htm",
    f"{BASE}/es/estadisticas/mercado_trabajo/index.htm",
    f"{BASE}/es/estadisticas/tendencias_empleo/index.htm",
]

# Las carpetas sin descifrar que publican en XLSX y podrían ser lo que se busca.
CARPETAS = [
    ("Emp", f"{BASE}/estadisticas/Emp/Emp26-Ago/index.htm"),
    ("EAL", f"{BASE}/estadisticas/EAL/EAL2024/index.htm"),
    ("reg", f"{BASE}/estadisticas/reg/reg26jun/index.htm"),
    ("Mac", f"{BASE}/estadisticas/Mac/mac26junpublicacion/index.htm"),
]

# Texto del enlace y destino, en el mismo trozo.
ANCLA = re.compile(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
ETIQUETAS = re.compile(r"<[^>]+>")
DATOS = re.compile(r"\.(xlsx?|csv|ods)(\?|$)", re.I)

INTERESA = ("afilia", "seguridad social", "eleccion", "sindical", "delegad",
            "cotizant", "empresas inscritas", "trabajadores")


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
    pagina = texto(datos)
    salida = []
    for destino, bruto in ANCLA.findall(pagina):
        nombre = limpia(bruto)
        if nombre:
            salida.append((nombre, urllib.parse.urljoin(url, html.unescape(destino))))
    return salida


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Qué es cada carpeta del ministerio", "",
              "No hay ninguna carpeta llamada `afi` ni `ele`, así que la",
              "afiliación y las elecciones sindicales, si están, se llaman de",
              "otra manera. La traducción está en el texto de los enlaces.", ""]

    print("=== Portales ===")
    for url in PORTALES:
        encontradas = anclas(url)
        print(f"  {url}: {len(encontradas)} enlaces")
        lineas += [f"## `{url}` · {len(encontradas)} enlaces", ""]
        relevantes = [(n, d) for n, d in encontradas
                      if any(p in n.lower() for p in INTERESA)]
        if relevantes:
            lineas.append("**Lo que suena a lo que se busca:**")
            for nombre, destino in relevantes[:25]:
                lineas.append(f"- **{nombre}** → `{destino}`")
            lineas.append("")
        lineas.append("Todos los enlaces a estadísticas:")
        for nombre, destino in encontradas:
            if "/estadisticas/" in destino.lower() and len(nombre) > 3:
                lineas.append(f"- {nombre} → `{destino}`")
        lineas.append("")

    print("=== Carpetas sin descifrar ===")
    for codigo, url in CARPETAS:
        encontradas = anclas(url)
        ficheros = [(n, d) for n, d in encontradas if DATOS.search(d)]
        print(f"  {codigo}: {len(encontradas)} enlaces, {len(ficheros)} ficheros")
        lineas += [f"## Carpeta `{codigo}`", "", f"`{url}`", ""]
        for nombre, destino in encontradas[:40]:
            lineas.append(f"- {nombre} → `{destino}`")
        lineas.append("")

        for nombre, destino in ficheros[:1]:
            estado, _, datos = red.abre(destino)
            lineas.append(f"### Por dentro: `{destino.split('/')[-1]}` ({estado})")
            if estado == 200 and datos[:2] == b"PK":
                try:
                    libro = Libro(datos)
                    hojas = list(libro.hojas)
                    lineas.append(f"    - {len(hojas)} hojas: "
                                  + ", ".join(f"«{h}»" for h in hojas[:25]))
                    for hoja in hojas[:2]:
                        filas = libro.filas(hoja)
                        lineas.append(f"    - hoja «{hoja}», {len(filas)} filas:")
                        for fila in filas[:15]:
                            celdas = [("" if c is None else str(c)) for c in fila[:8]]
                            while celdas and celdas[-1] == "":
                                celdas.pop()
                            if celdas:
                                lineas.append(f"        · {' | '.join(celdas)}")
                except Exception as exc:  # noqa: BLE001
                    lineas.append(f"    - no se ha podido abrir: "
                                  f"{type(exc).__name__}: {exc}")
            else:
                lineas.append("    - no es un XLSX")
            lineas.append("")

    (SALIDA / "bel.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/bel.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
