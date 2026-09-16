"""Qué hay exactamente en las hojas de lanzamientos del fichero del CGPJ.

El descargador encuentra las hojas pero no sus filas: no comparten formato con
las de servicios comunes, que son las que se sondearon. Esto vuelca las cuatro
tal cual, sin suponer nada de dónde está el nombre del territorio.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import cgpj_lanzamientos as cgpj  # noqa: E402
from xlsx import Libro  # noqa: E402

SALIDA = RAIZ / "sondeos"


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    url, nombre = cgpj.localiza_fichero()
    libro = Libro(cgpj.descarga(url))
    lineas = ["# Las hojas de lanzamientos por dentro", "", f"Fichero: `{nombre}`", ""]

    for hoja in libro.hojas:
        if "lanz" not in cgpj.normaliza(hoja):
            continue
        filas = libro.filas(hoja)
        lineas += [f"## «{hoja}»", f"- {len(filas)} filas", "", "```"]
        for i, fila in enumerate(filas[:12]):
            lineas.append(f"{i:>3} | " + " | ".join(
                f"{j}:{str(c)[:22]}" for j, c in enumerate(fila[:10]) if c is not None))
        lineas.append("...")
        for i, fila in enumerate(filas):
            texto = cgpj.normaliza(" ".join(str(c) for c in fila[:4] if c))
            if "castellon" in texto or texto.startswith("total"):
                lineas.append(f"{i:>3} | " + " | ".join(
                    f"{j}:{str(c)[:22]}" for j, c in enumerate(fila[:10]) if c is not None))
        lineas += ["```", ""]

    (SALIDA / "lanzamientos-hojas.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas[:60]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
