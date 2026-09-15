"""Prueba combinaciones de parámetros de DATOS_SERIE hasta dar con la que
devuelve datos. La API del INE está poco documentada en este punto."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402

CODIGO = "EPA459553"  # Tasa de actividad. Castellón/Castelló. Ambos sexos. Total.

PRUEBAS = [
    ("sin parámetros", {}),
    ("nult=8", {"nult": 8}),
    ("nult=8&tip=A", {"nult": 8, "tip": "A"}),
    ("nult=8&det=2", {"nult": 8, "det": 2}),
    ("nult=400", {"nult": 400}),
    ("nult=400&tip=A", {"nult": 400, "tip": "A"}),
    ("date=20200101:20260630", {"date": "20200101:20260630"}),
    ("date=20200101:", {"date": "20200101:"}),
]


def resume(respuesta) -> str:
    if isinstance(respuesta, list):
        return f"lista de {len(respuesta)}: " + json.dumps(respuesta[:1], ensure_ascii=False)[:600]
    if isinstance(respuesta, dict):
        data = respuesta.get("Data")
        claves = sorted(respuesta.keys())
        cabeza = json.dumps(data[:2], ensure_ascii=False)[:500] if isinstance(data, list) and data else "—"
        return (f"dict claves={claves} · Data={len(data) if isinstance(data, list) else type(data).__name__}"
                f" · primeros={cabeza}")
    return f"{type(respuesta).__name__}: {str(respuesta)[:300]}"


def main() -> int:
    print(f"== DATOS_SERIE/{CODIGO} ==\n")
    for etiqueta, params in PRUEBAS:
        try:
            respuesta = ine_api.get("DATOS_SERIE", CODIGO, reintentos=1, **params)
            print(f"[{etiqueta}]\n  {resume(respuesta)}\n")
        except Exception as exc:  # noqa: BLE001
            print(f"[{etiqueta}]\n  ERROR: {exc}\n")

    print("== SERIE (metadatos) ==")
    try:
        print("  " + json.dumps(ine_api.get("SERIE", CODIGO, det=2), ensure_ascii=False)[:900])
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR: {exc}")

    # ¿Y la misma serie pedida por tabla, que sí sabemos que funciona?
    print("\n== DATOS_TABLA/65349 (tasas por provincia), muestra ==")
    try:
        datos = ine_api.get("DATOS_TABLA", "65349", nult=3, tip="A")
        print(f"  series: {len(datos)}")
        castellon = [s for s in datos if "astell" in (s.get("Nombre") or "")]
        print(f"  con Castellón: {len(castellon)}")
        for s in castellon[:4]:
            print("   " + json.dumps(s, ensure_ascii=False)[:520])
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
