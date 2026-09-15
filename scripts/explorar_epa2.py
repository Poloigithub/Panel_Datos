"""Segunda ronda de exploración: qué series EPA existen realmente para
Castellón (provincia), la Comunitat Valenciana y el total nacional, y qué
tablas cubren cada magnitud."""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402

SALIDA = Path(__file__).resolve().parents[1] / "data" / "_catalogo"

VAR_SEXO, VAR_CCAA, VAR_PROV = 18, 70, 115
VAL_CASTELLON, VAL_CVALENCIANA, VAL_NACIONAL = 13, 9006, 16473


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)

    # 1. ¿Qué series EPA hay para la provincia de Castellón?
    for etiqueta, filtro in (
        ("CASTELLÓN (provincia)", f"{VAR_PROV}:{VAL_CASTELLON}"),
        ("COMUNITAT VALENCIANA", f"{VAR_CCAA}:{VAL_CVALENCIANA}"),
    ):
        print(f"\n== SERIES EPA para {etiqueta} (g1={filtro}) ==")
        try:
            series = ine_api.get("SERIE_METADATAOPERACION", "EPA", g1=filtro, det=2)
        except ine_api.INEError as exc:
            print(f"  ! error: {exc}")
            continue
        print(f"  series encontradas: {len(series)}")
        (SALIDA / f"series_{filtro.replace(':', '_')}.json").write_text(
            json.dumps(series, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Sólo nos interesa el reparto de magnitudes, no las 5.000 series.
        nombres = sorted({s.get("Nombre", "") for s in series})
        vistos: set[str] = set()
        for n in nombres:
            clave = normaliza(n).split(".")[0].strip()
            if clave in vistos:
                continue
            vistos.add(clave)
            print(f"   · {n}")
        print(f"  magnitudes distintas: {len(vistos)}")

    # 2. Rango temporal de las dos tablas de tasas por provincia.
    print("\n== TABLAS DE TASAS POR PROVINCIA: cobertura temporal ==")
    for tabla in (65349, 72989):
        datos = ine_api.get("DATOS_TABLA", str(tabla), nult=400, det=2, tip="A")
        print(f"\n  tabla {tabla}: {len(datos)} series")
        for serie in datos[:2]:
            fechas = [f"{d['Anyo']}{d['Periodo']['Nombre']}" for d in serie.get("Data", [])]
            print(f"    {serie.get('Nombre')}")
            print(f"    periodos: {len(fechas)} | {fechas[-1] if fechas else '-'} .. {fechas[0] if fechas else '-'}")
        # Guardamos los nombres de serie para ver el patrón de filtrado.
        (SALIDA / f"tabla_{tabla}_nombres.json").write_text(
            json.dumps([s.get("Nombre") for s in datos], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        castellon = [s for s in datos if "castell" in normaliza(s.get("Nombre", ""))]
        print(f"    series de Castellón: {len(castellon)}")
        for s in castellon[:12]:
            print(f"      - {s.get('Nombre')}")

    # 3. Catálogo completo por magnitud, para elegir las tablas nacionales/CCAA.
    print("\n== TABLAS por magnitud (catálogo completo) ==")
    tablas = ine_api.get("TABLAS_OPERACION", "EPA", det=2)
    for arranque in ("ocupados por", "parados por", "activos por", "tasas de actividad"):
        print(f"\n  --- '{arranque}' ---")
        for t in tablas:
            n = normaliza(t.get("Nombre", ""))
            if not n.startswith(arranque):
                continue
            if "error" in n:
                continue
            if "sexo" not in n:
                continue
            # nos quedamos con lo simple: sin desgloses sectoriales/educativos
            print(f"    [{t.get('Id')}] {t.get('Nombre')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
