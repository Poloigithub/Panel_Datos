"""Las hojas de la afiliación, por dentro.

El sondeo anterior localizó la fuente: el Anuario de Estadísticas del
Ministerio de Trabajo publica un `AFI.xlsx` por año, de 2015 en adelante, y
dentro hay dos hojas que bajan a provincia:

- `Afi-07`: trabajadores afiliados en alta laboral, según régimen, por
  comunidad autónoma y provincia.
- `Afi-13`: trabajadores autónomos, por comunidad autónoma y provincia.

Con eso la afiliación entra en el panel con los tres ámbitos y, de paso, los
accidentes de trabajo dejan de ser una cifra absoluta: se pueden convertir en
accidentes por cada cien mil afiliados, que es lo que la página de
siniestralidad reconoce ahora mismo que le falta.

Falta lo de siempre: dónde empieza la tabla, en qué fila está Castellón, qué
son las columnas y si el número es la media del año o la foto de diciembre.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import red_ministerio as red  # noqa: E402
from xlsx import Libro  # noqa: E402

SALIDA = RAIZ / "sondeos"
ANUARIO = "https://www.mites.gob.es/ficheros/ministerio/estadisticas/anuarios"

FICHEROS = [("el más reciente", 2025), ("uno de en medio", 2020),
            ("el más antiguo en XLSX", 2015)]

# El nombre de la hoja no sirve de ancla: en 2015 la provincial es «Afi-07» y
# en 2025 es «AFI-7», y por el camino el fichero pasa de 22 hojas a 40. Lo que
# no cambia es lo que dice el índice de cada hoja, así que la hoja se busca por
# su descripción. Esto es también lo que tendrá que hacer el descargador.
BUSCADAS = {
    "afiliados por provincia":
        ("afiliados", "comunidad autonoma y provincia"),
    "autónomos por provincia":
        ("autonomos", "comunidad autonoma y provincia"),
}


def normaliza(texto: str) -> str:
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return " ".join(plano.split())


def hoja_por_descripcion(libro: Libro, palabras: tuple[str, ...]) -> str | None:
    """La hoja que el índice describe con todas esas palabras."""
    indice = next((h for h in libro.hojas if normaliza(h).startswith("indice")), None)
    if not indice:
        return None
    for fila in libro.filas(indice):
        celdas = [normaliza(str(c)) for c in fila if c not in (None, "")]
        if not celdas:
            continue
        descripcion = " ".join(celdas)
        if all(p in descripcion for p in palabras):
            # El código de la hoja va en la primera celda, como «AFI-07.»
            codigo = celdas[0].rstrip(". ").replace(" ", "")
            for nombre in libro.hojas:
                if normaliza(nombre).replace("-0", "-").replace(" ", "") == \
                        codigo.replace("-0", "-"):
                    return nombre
    return None


def vuelca(lineas: list[str], libro: Libro, hoja: str, filas_max: int = 75) -> None:
    filas = libro.filas(hoja)
    lineas.append(f"### Hoja «{hoja}» · {len(filas)} filas")
    lineas.append("```")
    for i, fila in enumerate(filas[:filas_max]):
        celdas = [("" if c is None else str(c)) for c in fila[:11]]
        while celdas and celdas[-1] == "":
            celdas.pop()
        if celdas:
            lineas.append(f"{i:>3} | " + " | ".join(celdas))
    lineas.append("```")
    lineas.append("")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# La afiliación por dentro", "",
              "Dónde empieza la tabla, en qué fila está Castellón, qué son las",
              "columnas y si el número es la media del año o la foto de diciembre.",
              ""]

    for etiqueta, anyo in FICHEROS:
        url = f"{ANUARIO}/{anyo}/AFI/AFI.xlsx"
        print(f"· {etiqueta} ({anyo}): {url}")
        estado, _, datos = red.abre(url)
        lineas += [f"## {etiqueta} · {anyo}", "",
                   f"`{url}` → {estado}, {len(datos)} bytes", ""]
        if estado != 200 or datos[:2] != b"PK":
            lineas.append("No es un XLSX que se pueda abrir.")
            continue
        libro = Libro(datos)
        nombres = list(libro.hojas)
        lineas.append(f"{len(nombres)} hojas: {', '.join(nombres)}")
        lineas.append("")
        for que, palabras in BUSCADAS.items():
            real = hoja_por_descripcion(libro, palabras)
            if real:
                lineas.append(f"**{que}** → hoja «{real}»")
                lineas.append("")
                vuelca(lineas, libro, real, filas_max=40)
                print(f"    {que}: «{real}»")
            else:
                lineas += [f"**{que}**: no se ha encontrado en el índice", ""]
                print(f"    {que}: no encontrada")

    (SALIDA / "afi-hojas.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/afi-hojas.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
