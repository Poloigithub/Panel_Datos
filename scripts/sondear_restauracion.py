"""Los tres huecos que dejó la cesta: comer fuera, el azúcar y los preparados.

Al ampliar la cesta quedaron cinco combinaciones sin serie: «restaurantes y
bares» en los tres ámbitos, y el azúcar y los alimentos preparados en la
Comunitat. El sondeo general (`sondeos/cesta.md`) no sirve para resolverlo
porque filtra por palabras de comida y además corta la lista en 60 productos.

Esto no filtra ni corta: imprime las combinaciones completas, tal y como el INE
nombra las series, de todo lo que suene a restauración, azúcar o preparados. Con
el nombre exacto delante se puede escribir la búsqueda que falta.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import ine_series as motor  # noqa: E402

SALIDA = RAIZ / "sondeos"

AMBITOS = [("España", "349:16473"), ("Comunitat Valenciana", "70:9006"),
           ("Castellón", "115:13")]

TEMAS = {
    "comer fuera": ("restaurant", "bar", "cafeteria", "cafes", "hotel",
                    "comida rapida", "cantina", "comedor", "restauracion",
                    "servicio de alimentacion"),
    "azúcar": ("azucar", "chocolate", "confiteria", "confitura", "helado",
               "dulce"),
    "preparados": ("preparado", "precocinado", "elaborad"),
}

# Las series de bases anteriores conviven con las vigentes y no interesan.
VIEJAS = ("base 1992", "base 2001", "base 2006", "base 2011", "base 2016",
          "base 2021")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Comer fuera, azúcar y preparados: cómo los nombra el INE", "",
              "Combinaciones completas, sin filtrar por palabras de comida y sin",
              "cortar la lista. Las de bases anteriores van aparte.", ""]

    for nombre, filtro in AMBITOS:
        print(f"· {nombre}")
        indice = motor.indexa_por_segmentos("IPC", filtro)
        lineas += [f"## {nombre}", f"- {len(indice)} combinaciones", ""]

        for tema, palabras in TEMAS.items():
            tocan = [segs for segs in indice
                     if any(p in s for s in segs for p in palabras)]
            vigentes = [s for s in tocan if not any(v in s for v in VIEJAS)]
            print(f"    {tema}: {len(tocan)} combinaciones, "
                  f"{len(vigentes)} en la base vigente")
            lineas.append(f"### {tema} · {len(vigentes)} en la base vigente "
                          f"de {len(tocan)}")
            for segs in sorted(vigentes, key=sorted):
                serie = indice[segs][0]
                lineas.append(f"    - `{sorted(segs)}` → {serie.get('COD')}")
            lineas.append("")

    (SALIDA / "restauracion.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/restauracion.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
