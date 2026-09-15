"""Cuarta ronda: los códigos de serie concretos que necesita el panel.

Descargar por código de serie (DATOS_SERIE) es más estable que hacerlo por
tabla: el código no cambia aunque el INE reorganice las tablas.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402

SALIDA = Path(__file__).resolve().parents[1] / "data" / "_catalogo"

# Palabras que delatan un desglose que no queremos (queremos los totales).
DESCARTES = (
    "rama de actividad", "sector economico", "nivel de formacion", "nacionalidad",
    "jornada", "ocupacion", "situacion profesional", "estado civil", "parentesco",
    "tiempo de busqueda", "error", "asalariado", "sector publico", "sector privado",
    "distribucion porcentual", "contrato", "estudios", "vivienda", "hogar",
    "menores de", "de 16 a", "de 20 a", "de 25 a", "de 45 a", "de 55 a", "y mas anos",
    "tiempo que llevan", "horas efectivas", "turno", "domicilio", "sector del nivel",
)


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def interesa(nombre: str) -> bool:
    n = normaliza(nombre)
    if not n.startswith(("ocupados", "parados", "activos", "tasa de", "tasas de", "castell")):
        return False
    return not any(d in n for d in DESCARTES)


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Códigos de serie EPA candidatos", ""]

    ambitos = [
        ("Castellón (provincia)", "115:13", True),   # pocas series: se vuelcan todas
        ("Comunitat Valenciana", "70:9006", False),
        ("Total Nacional", "349:16473", False),
    ]

    for etiqueta, filtro, volcar_todo in ambitos:
        lineas += [f"## {etiqueta} (`g1={filtro}`)", ""]
        try:
            series = ine_api.get("SERIE_METADATAOPERACION", "EPA", g1=filtro, det=2)
        except Exception as exc:  # noqa: BLE001
            lineas += [f"ERROR: {exc}", ""]
            continue

        elegidas = series if volcar_todo else [s for s in series if interesa(s.get("Nombre", ""))]
        lineas += [f"Series totales: {len(series)} · volcadas: {len(elegidas)}", ""]

        for s in elegidas[:260]:
            periodicidad = s.get("FK_Periodicidad")
            lineas.append(f"- `{s.get('COD')}` (per {periodicidad}) — {s.get('Nombre')}")
        lineas.append("")

    (SALIDA / "series.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"[{len(lineas)} líneas escritas en data/_catalogo/series.md]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
