"""Cómo se llama la serie del salario bruto del conjunto de España.

Por comunidad autónoma se encuentra sin problema -['ambos sexos', 'componente
del salario bruto anual', 'comunitat valenciana', 'salario bruto']- pero la
equivalente nacional no aparece. Puede ser que se llame de otra forma o que
caiga fuera del tope de diez mil series del INE. Esto enseña todos los
conjuntos cortos que mencionan salario o ganancia, que es lo que hace falta
para declararla bien.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import ine_series as motor  # noqa: E402

SALIDA = RAIZ / "sondeos"
CLAVES = ("salario bruto", "ganancia", "salario medio")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# La serie del salario en la encuesta de estructura salarial", ""]

    for nombre, filtro in (("España", "349:16473"), ("Comunitat Valenciana", "70:9006")):
        indice = motor.indexa_por_segmentos("EAES", filtro)
        lineas += [f"## {nombre}", f"- {len(indice)} combinaciones de segmentos", ""]
        cortos = [segs for segs in indice
                  if len(segs) <= 5 and any(c in s for s in segs for c in CLAVES)]
        lineas.append(f"- {len(cortos)} con salario o ganancia y hasta cinco segmentos:")
        for segs in sorted(cortos, key=lambda s: (len(s), sorted(s)))[:40]:
            lineas.append(f"    - {sorted(segs)} → `{indice[segs][0]['COD']}`")
        lineas.append("")

    (SALIDA / "eaes.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas[:60]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
