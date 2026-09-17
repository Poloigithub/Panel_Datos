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

FICHEROS = [("el más reciente", f"{ANUARIO}/2025/AFI/AFI.xlsx"),
            ("el más antiguo en XLSX", f"{ANUARIO}/2015/AFI/AFI.xlsx")]

HOJAS = ("Afi-07", "Afi-13", "Afi-08a")


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

    for etiqueta, url in FICHEROS:
        print(f"· {etiqueta}: {url}")
        estado, _, datos = red.abre(url)
        lineas += [f"## {etiqueta}", "", f"`{url}` → {estado}, {len(datos)} bytes", ""]
        if estado != 200 or datos[:2] != b"PK":
            lineas.append("No es un XLSX que se pueda abrir.")
            continue
        libro = Libro(datos)
        nombres = list(libro.hojas)
        lineas.append(f"Hojas: {', '.join(nombres)}")
        lineas.append("")
        for hoja in HOJAS:
            # Los nombres de hoja bailan de mayúsculas entre años.
            real = next((h for h in nombres if h.lower() == hoja.lower()), None)
            if real:
                vuelca(lineas, libro, real)
                print(f"    volcada «{real}»")
            else:
                lineas += [f"### Hoja «{hoja}»: no está en este fichero", ""]

    (SALIDA / "afi-hojas.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/afi-hojas.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
