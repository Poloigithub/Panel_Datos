"""Tercera ronda: resumen compacto y commiteable de lo que la API del INE
ofrece para cada ámbito, con la cobertura temporal de las tablas candidatas."""

from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "data" / "_catalogo"

VAR_CCAA, VAR_PROV = 70, 115
VAL_CASTELLON, VAL_CVALENCIANA = 13, 9006

# Tablas que salieron del catálogo y que podrían servir para cada magnitud.
CANDIDATAS = [
    65349, 72989,          # tasas por provincia y sexo
    14506, 65295, 66023,   # tasas de paro / actividad por CCAA
    65296, 66024,          # tasas de actividad 16+ por CCAA
    65293, 66021,          # activos por CCAA
    65332, 66053,          # parados por CCAA
    65080, 72977,          # activos nacional por sexo y edad
    65218, 72985,          # parados nacional
    65081, 72978,          # tasas de actividad nacional
]


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def magnitud(nombre: str) -> str:
    return (nombre or "").split(".")[0].strip()


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas: list[str] = ["# Resumen del catálogo EPA del INE", ""]

    # --- Qué magnitudes existen para cada ámbito subestatal ----------------
    for etiqueta, filtro in (
        ("Castellón (provincia)", f"{VAR_PROV}:{VAL_CASTELLON}"),
        ("Comunitat Valenciana", f"{VAR_CCAA}:{VAL_CVALENCIANA}"),
    ):
        lineas += [f"## Series EPA disponibles para {etiqueta} (`g1={filtro}`)", ""]
        try:
            series = ine_api.get("SERIE_METADATAOPERACION", "EPA", g1=filtro, det=2)
        except ine_api.INEError as exc:
            lineas += [f"ERROR: {exc}", ""]
            continue
        lineas += [f"Series totales: {len(series)}", ""]
        cuenta = Counter(magnitud(s.get("Nombre", "")) for s in series)
        for nombre, n in cuenta.most_common():
            lineas.append(f"- `{n}` · {nombre}")
        lineas.append("")

    # --- Cobertura temporal y contenido de cada tabla candidata ------------
    lineas += ["## Tablas candidatas", ""]
    for tabla in CANDIDATAS:
        try:
            datos = ine_api.get("DATOS_TABLA", str(tabla), nult=500, tip="A")
        except ine_api.INEError as exc:
            lineas.append(f"### {tabla} — ERROR: {exc}")
            continue
        if not datos:
            lineas.append(f"### {tabla} — sin series")
            continue
        primera = datos[0]
        periodos = [f"{d['Anyo']}{d['Periodo']['Nombre']}" for d in primera.get("Data", [])]
        lineas += [
            f"### Tabla {tabla}",
            f"- series: {len(datos)}",
            f"- periodos en la primera serie: {len(periodos)} "
            f"({periodos[-1] if periodos else '-'} … {periodos[0] if periodos else '-'})",
            f"- unidad: {(primera.get('Unidad') or {}).get('Nombre')} · escala: {(primera.get('Escala') or {}).get('Factor')}",
        ]
        muestra = [s.get("Nombre", "") for s in datos[:6]]
        lineas.append("- nombres de serie de muestra:")
        lineas += [f"    - {m}" for m in muestra]
        for clave in ("castell", "comunitat valenciana", "total nacional"):
            hits = [s.get("Nombre", "") for s in datos if clave in normaliza(s.get("Nombre", ""))]
            lineas.append(f"- series con «{clave}»: {len(hits)}")
            lineas += [f"    - {h}" for h in hits[:8]]
        lineas.append("")

    (SALIDA / "resumen.md").write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas[:80]))
    print(f"\n[resumen completo en data/_catalogo/resumen.md, {len(lineas)} líneas]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
