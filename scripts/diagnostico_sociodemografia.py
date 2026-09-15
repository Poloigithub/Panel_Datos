"""Por qué no casan las búsquedas que fallaron: enseña los segmentos reales."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_series as motor  # noqa: E402

SALIDA = Path(__file__).resolve().parents[1] / "data" / "_catalogo"

# (operación, filtro del ámbito, palabras que deben aparecer en el nombre)
CASOS = [
    ("IDB", "115:13", ("esperanza de vida",)),
    ("IDB", "115:13", ("natalidad",)),
    ("IDB", "115:13", ("mortalidad", "tasa")),
    ("IDB", "115:13", ("fecundidad", "hijos")),
    ("IDB", "115:13", ("maternidad",)),
    ("IDB", "115:13", ("saldo migratorio",)),
    ("IDB", "349:16473", ("esperanza de vida",)),
    ("IDB", "115:13", ("proporcion de poblacion extranjera",)),
    ("IDB", "115:13", ("proporcion de personas mayores",)),
    ("ADRH", "115:13", ("mediana por hogar",)),
    ("ADRH", "349:16473", ("renta neta media por persona",)),
    ("ECP", "349:16473", ("poblacion",)),
]


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Segmentos reales de las series que no casaban", ""]

    cache: dict[tuple[str, str], dict] = {}
    for operacion, filtro, claves in CASOS:
        lineas += [f"## {operacion} · {filtro} · {' + '.join(claves)}", ""]
        if (operacion, filtro) not in cache:
            try:
                cache[(operacion, filtro)] = motor.indexa_por_segmentos(operacion, filtro)
            except Exception as exc:  # noqa: BLE001
                lineas += [f"ERROR: {exc}", ""]
                continue
        indice = cache[(operacion, filtro)]

        encontradas = []
        for segs, grupo in indice.items():
            texto = " ".join(sorted(segs))
            if all(clave in texto for clave in claves):
                encontradas.append((len(segs), segs, grupo[0]))
        encontradas.sort(key=lambda t: t[0])
        lineas.append(f"Conjuntos de segmentos que encajan: {len(encontradas)}")
        for nsegs, segs, serie in encontradas[:14]:
            lineas.append(f"- ({nsegs}) `{serie.get('COD')}` {sorted(segs)}")
        lineas.append("")

    (SALIDA / "diagnostico.md").write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
