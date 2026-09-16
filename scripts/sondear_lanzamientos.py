"""Sondeo de los lanzamientos: desahucios por hipoteca y por alquiler.

La estadística de Ejecuciones Hipotecarias del INE, que ya está en el panel,
sólo cuenta hipotecas. Quien separa los desahucios por impago de hipoteca de
los de impago de alquiler es el CGPJ, en los ficheros de «Efecto de la crisis
en los órganos judiciales»: lanzamientos derivados de la Ley Hipotecaria,
lanzamientos derivados de la Ley de Arrendamientos Urbanos y el resto.

Los sondeos anteriores localizaron dónde cuelgan esos ficheros. Éste los lista
todos, se baja el más reciente y enseña por dentro qué hojas tiene, cómo se
titulan sus columnas y si el dato llega a provincia, que es lo único que
decide si esto puede entrar en el panel.
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
from xlsx import Libro  # noqa: E402

SALIDA = RAIZ / "sondeos"
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

CRISIS = ("https://www.poderjudicial.es/cgpj/es/Temas/Estadistica-Judicial/"
          "Estadistica-por-temas/Datos-penales--civiles-y-laborales/Civil-y-laboral/"
          "Efecto-de-la-Crisis-en-los-organos-judiciales/")

HOJA_CALCULO = re.compile(r'href="([^"]*\.xlsx?(?:\?[^"]*)?)"', re.I)


def codifica(url: str) -> str:
    """Los nombres de fichero del CGPJ llevan espacios y acentos.

    Tal cual, urllib los rechaza por «control characters», así que hay que
    escapar la ruta antes de pedirla.
    """
    partes = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        partes.scheme, partes.netloc,
        urllib.parse.quote(partes.path, safe="/%"),
        urllib.parse.quote(partes.query, safe="=&%"),
        partes.fragment,
    ))


def descarga(url: str, limite: int = 8_000_000) -> tuple[int, str, bytes]:
    try:
        peticion = urllib.request.Request(codifica(url), headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=180) as respuesta:
            return (respuesta.status, respuesta.headers.get("Content-Type", "?"),
                    respuesta.read(limite))
    except urllib.error.HTTPError as exc:
        return exc.code, "-", str(exc.reason).encode()
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}".encode()


def nombre_de(url: str) -> str:
    return urllib.parse.unquote(url.split("/")[-1].split("?")[0])


def resume(lineas: list[str], datos: bytes, etiqueta: str) -> None:
    """Enseña la estructura de un libro: hojas, cabeceras y primeras filas."""
    try:
        libro = Libro(datos)
    except Exception as exc:  # noqa: BLE001
        lineas.append(f"- no se ha podido abrir: {type(exc).__name__}: {exc}")
        return
    lineas.append(f"- {len(libro.hojas)} hojas: {', '.join(list(libro.hojas)[:12])}")

    for nombre in libro.hojas:
        filas = libro.filas(nombre)
        texto = " ".join(str(c) for fila in filas[:40] for c in fila if c)
        if "lanzamiento" not in texto.lower():
            continue
        lineas += ["", f"#### Hoja «{nombre}» de {etiqueta}",
                   f"- {len(filas)} filas"]
        for i, fila in enumerate(filas[:28]):
            celdas = [str(c) for c in fila[:9] if c is not None]
            if celdas:
                lineas.append(f"    {i:>3} | " + " | ".join(celdas))
        # ¿Aparece Castellón por algún lado? Eso decide si sirve para el panel.
        donde = [i for i, fila in enumerate(filas)
                 if any("castell" in str(c).lower() for c in fila if c)]
        lineas.append(f"- «Castellón» aparece en {len(donde)} filas: {donde[:8]}")
        for i in donde[:3]:
            lineas.append(f"    {i:>3} | " + " | ".join(
                str(c) for c in filas[i][:9] if c is not None))


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Sondeo de lanzamientos (hipoteca y alquiler)", "",
              "Los lanzamientos por impago de hipoteca y por impago de alquiler los",
              "publica el CGPJ en los ficheros de «Efecto de la crisis en los órganos",
              "judiciales». Aquí se mira cuántos hay, cómo se llaman y qué tienen dentro.", ""]

    codigo, tipo, bruto = descarga(CRISIS, 2_000_000)
    cuerpo = bruto.decode("utf-8", errors="replace")
    lineas += [f"## Página de «Efecto de la crisis»", f"- `{codigo}` · {tipo}"]

    ficheros = []
    for href in HOJA_CALCULO.findall(cuerpo):
        url = urllib.parse.urljoin(CRISIS, html.unescape(href))
        if url not in ficheros:
            ficheros.append(url)
    lineas.append(f"- {len(ficheros)} hojas de cálculo enlazadas")
    for url in ficheros:
        lineas.append(f"    - {nombre_de(url)}")

    # Primero los que traen series por provincia, que es el detalle que el
    # panel necesita; después el más reciente de los trimestrales. Los de
    # juzgados de lo mercantil cuentan concursos, no desahucios.
    def prioridad(url: str) -> int:
        nombre = nombre_de(url).lower()
        if "mercantil" in nombre or "microempresa" in nombre:
            return 9
        if "provincia" in nombre:
            return 0
        if "lanzamientos por pj" in nombre:
            return 1
        if nombre.startswith("series"):
            return 2
        return 3

    interesantes = sorted(ficheros, key=prioridad)
    interesantes = [u for u in interesantes if prioridad(u) < 9]
    lineas += ["", f"## Dentro de los ficheros ({len(interesantes)} sin contar los mercantiles)", ""]
    for url in interesantes[:3]:
        etiqueta = nombre_de(url)
        codigo, tipo, datos = descarga(url)
        lineas += [f"### {etiqueta}", f"- `{codigo}` · {tipo} · {len(datos)} bytes", f"- {url}"]
        if codigo == 200 and len(datos) > 1000:
            resume(lineas, datos, etiqueta)
        else:
            lineas.append(f"- {datos[:200]!r}")
        lineas.append("")

    (SALIDA / "lanzamientos.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/lanzamientos.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
