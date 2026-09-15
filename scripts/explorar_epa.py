"""Explorador del catálogo EPA del INE.

Se ejecuta en GitHub Actions (que sí tiene salida a servicios.ine.es) para
descubrir los identificadores reales de las tablas y variables que necesita el
panel, y volcarlos al log y a data/_catalogo/ para poder fijarlos en
config/tablas-epa.json.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402

SALIDA = Path(__file__).resolve().parents[1] / "data" / "_catalogo"

# Lo que buscamos: las cuatro magnitudes, en los tres ámbitos territoriales.
PATRONES_INTERES = [
    r"por provincia",
    r"comunidad aut",
    r"comunidades y ciudades aut",
    r"tasas de actividad",
    r"tasas de paro",
    r"tasas de empleo",
]


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def interesa(nombre: str) -> bool:
    n = normaliza(nombre)
    return any(re.search(normaliza(p), n) for p in PATRONES_INTERES)


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)

    print("== VARIABLES de la operación EPA ==")
    variables = ine_api.get("VARIABLES_OPERACION", "EPA")
    (SALIDA / "variables_epa.json").write_text(
        json.dumps(variables, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for v in variables:
        print(f"  var {v.get('Id')}: {v.get('Nombre')} (cod {v.get('Codigo')})")

    print("\n== TABLAS de la operación EPA ==")
    tablas = ine_api.get("TABLAS_OPERACION", "EPA", det=2)
    (SALIDA / "tablas_epa.json").write_text(
        json.dumps(tablas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  total de tablas publicadas: {len(tablas)}")

    candidatas = [t for t in tablas if interesa(t.get("Nombre", ""))]
    print(f"  tablas que encajan con los patrones: {len(candidatas)}\n")
    for t in candidatas:
        periodicidad = (t.get("Periodicidad") or {}).get("Nombre", "?")
        print(f"  [{t.get('Id')}] {t.get('Nombre')}  ({periodicidad})")

    # Volcado de los valores de las variables territoriales y de sexo, que es
    # lo que hace falta para filtrar España / C. Valenciana / Castellón.
    print("\n== VALORES de las variables territoriales y de sexo ==")
    for v in variables:
        n = normaliza(v.get("Nombre", ""))
        if not any(k in n for k in ("provincia", "comunidad", "sexo", "nacional")):
            continue
        idv = v.get("Id")
        try:
            valores = ine_api.get("VALORES_VARIABLEOPERACION", f"{idv}/EPA")
        except ine_api.INEError as exc:
            print(f"  ! no se pudieron leer los valores de {idv}: {exc}")
            continue
        (SALIDA / f"valores_var_{idv}.json").write_text(
            json.dumps(valores, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n  -- variable {idv} ({v.get('Nombre')}): {len(valores)} valores")
        for val in valores:
            nv = normaliza(val.get("Nombre", ""))
            if any(k in nv for k in ("total", "nacional", "valencia", "castell", "hombre", "mujer", "ambos", "espana")):
                print(f"     {val.get('Id')}: {val.get('Nombre')}")

    # Estructura de una tabla de ejemplo, para diseñar el parser de series.
    if candidatas:
        ejemplo = candidatas[0]
        print(f"\n== MUESTRA de DATOS_TABLA {ejemplo.get('Id')} ({ejemplo.get('Nombre')}) ==")
        datos = ine_api.get("DATOS_TABLA", str(ejemplo.get("Id")), nult=2, det=2, tip="A")
        (SALIDA / "muestra_datos_tabla.json").write_text(
            json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  series devueltas: {len(datos)}")
        for serie in datos[:3]:
            print(json.dumps(serie, ensure_ascii=False, indent=2)[:2500])
            print("  ---")

    print("\nCatálogo completo guardado en data/_catalogo/ (artifact del workflow).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
