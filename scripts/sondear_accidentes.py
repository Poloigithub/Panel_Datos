"""Las hojas de accidentes de trabajo, por dentro.

El sondeo general ya dijo lo importante: el Ministerio de Trabajo publica los
accidentes cada mes en un XLSX legible -desde marzo de 2021- y una de sus
hojas, la `ATR-A1.1`, es **por comunidad autónoma y provincia**. Ahí están los
tres ámbitos del panel de golpe, que es justo lo que no tiene ninguna
estadística salarial.

Falta lo de siempre antes de escribir un descargador: cómo está montada la
hoja. Dónde empieza la tabla, en qué columna va Castellón, si las columnas son
leve/grave/mortal o algo más, si los datos son del mes o acumulados del año, y
si el fichero de diciembre sirve como total anual.

Se abren dos: el último mes publicado y el diciembre del año pasado.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import red_ministerio as red  # noqa: E402
from xlsx import Libro  # noqa: E402

SALIDA = RAIZ / "sondeos"
BASE = "https://www.mites.gob.es/estadisticas/eat"

FICHEROS = [
    ("último mes publicado", f"{BASE}/eat26_07/ATR_07_2026.xlsx"),
    ("diciembre del año pasado", f"{BASE}/eat25_12/ATR_12_2025.xlsx"),
]

# Las tres que deciden si esto entra: el resumen, los mortales y la provincial.
HOJAS = ("ATR-R1", "ATR-R2", "ATR-A1.1")


def vuelca(lineas: list[str], libro: Libro, hoja: str, filas_max: int = 70) -> None:
    filas = libro.filas(hoja)
    lineas.append(f"### Hoja «{hoja}» · {len(filas)} filas")
    lineas.append("```")
    for i, fila in enumerate(filas[:filas_max]):
        celdas = [("" if c is None else str(c)) for c in fila[:12]]
        while celdas and celdas[-1] == "":
            celdas.pop()
        if celdas:
            lineas.append(f"{i:>3} | " + " | ".join(celdas))
    lineas.append("```")
    lineas.append("")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Accidentes de trabajo: cómo están montadas las hojas", "",
              "Lo que hace falta para escribir el descargador: dónde empieza la",
              "tabla, en qué fila está Castellón, qué son las columnas y si los",
              "datos son del mes o acumulados del año.", ""]

    for etiqueta, url in FICHEROS:
        print(f"· {etiqueta}: {url}")
        estado, tipo, datos = red.abre(url)
        lineas += [f"## {etiqueta}", "",
                   f"`{url}` → {estado}, {len(datos)} bytes", ""]
        if estado != 200:
            lineas.append(f"No se ha podido bajar: {datos[:200].decode('utf-8', 'replace')}")
            continue
        try:
            libro = Libro(datos)
        except Exception as exc:  # noqa: BLE001
            lineas.append(f"No se ha podido abrir: {type(exc).__name__}: {exc}")
            continue
        for hoja in HOJAS:
            if hoja in libro.hojas:
                vuelca(lineas, libro, hoja)
                print(f"    volcada «{hoja}»")
            else:
                lineas.append(f"### Hoja «{hoja}»: no está en este fichero")
                lineas.append("")

    (SALIDA / "accidentes.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/accidentes.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
