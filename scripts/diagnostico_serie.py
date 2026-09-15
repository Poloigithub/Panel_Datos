"""Por qué no aparecen como candidatas las series nacionales de parados de
hombres y de tasa de actividad de mujeres."""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402
import descargar_epa as d  # noqa: E402


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).lower().split())


BUSQUEDAS = [
    ("parados de hombres", ("parados", "hombres")),
    ("tasa de actividad de mujeres", ("tasa de actividad", "mujeres")),
    ("tasa de empleo de mujeres", ("tasa de empleo", "mujeres")),
]


def main() -> int:
    series = ine_api.get("SERIE_METADATAOPERACION", "EPA", g1="349:16473")
    print(f"Series con variable Total Nacional: {len(series)}\n")

    for etiqueta, claves in BUSQUEDAS:
        print(f"== {etiqueta} ==")
        encontradas = []
        for s in series:
            n = normaliza(s.get("Nombre", ""))
            if all(k in n for k in claves) and "error" not in n:
                segs = d.segmentos(s.get("Nombre", ""))
                # sólo las simples, que son las candidatas plausibles
                if len(segs) <= 6:
                    encontradas.append((len(segs), s))
        encontradas.sort(key=lambda t: t[0])
        print(f"  {len(encontradas)} series simples")
        for nsegs, s in encontradas[:18]:
            cob = d.cobertura(s["COD"])
            print(f"    {s['COD']} · {nsegs} segs · {cob[0]:3d} trim · {s.get('Nombre','').strip()}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
