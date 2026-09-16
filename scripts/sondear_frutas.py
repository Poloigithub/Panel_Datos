"""¿Cómo se llama la serie viva del índice de la fruta?

«Frutas frescas» dejó de actualizarse en diciembre de 2025 y ni «frutas frescas
o refrigeradas» ni «frutas» devuelven índice. Antes de seguir probando nombres
a ciegas, esto lista todos los conjuntos de segmentos del IPC de España que
mencionan fruta, con el detalle completo y no recortado.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import ine_series as motor  # noqa: E402

SALIDA = RAIZ / "sondeos"


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Las series de fruta del IPC", ""]
    for nombre, filtro in (("España", "349:16473"), ("Comunitat Valenciana", "70:9006")):
        indice = motor.indexa_por_segmentos("IPC", filtro)
        conjuntos = [segs for segs in indice if any("fruta" in s for s in segs)]
        lineas += [f"## {nombre}", f"- {len(conjuntos)} conjuntos con fruta", ""]
        for segs in sorted(conjuntos, key=lambda s: (len(s), sorted(s))):
            lineas.append(f"- {sorted(segs)} → `{indice[segs][0]['COD']}`")
        lineas.append("")
    (SALIDA / "frutas.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas[:50]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
