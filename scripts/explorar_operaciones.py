"""Explorador del catálogo del INE para las operaciones sociodemográficas.

Diagnóstico de un solo uso: descubre qué operaciones existen, con qué variables
territoriales trabajan y qué series ofrecen para España, la Comunitat
Valenciana y la provincia de Castellón. El resultado se escribe a un fichero
porque el log de Actions se trunca al leerlo.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402

SALIDA = Path(__file__).resolve().parents[1] / "data" / "_catalogo"

# Lo que buscamos en el nombre de la operación.
INTERESAN = (
    "padron", "poblacion", "natural de la poblacion", "indicadores demograficos",
    "migracion", "renta", "atlas", "hogares", "nacimientos", "defunciones",
)


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).lower().split())


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Operaciones sociodemográficas del INE", ""]

    operaciones = ine_api.get("OPERACIONES_DISPONIBLES")
    lineas.append(f"Operaciones publicadas: {len(operaciones)}\n")

    candidatas = []
    for op in operaciones:
        nombre = normaliza(op.get("Nombre", ""))
        if any(clave in nombre for clave in INTERESAN):
            candidatas.append(op)
            lineas.append(f"- `{op.get('Codigo')}` (id {op.get('Id')}) — {op.get('Nombre')}")
    lineas.append("")

    # Para cada candidata: variables y disponibilidad territorial.
    for op in candidatas:
        codigo = op.get("Codigo")
        if not codigo:
            continue
        lineas += [f"## {codigo} — {op.get('Nombre')}", ""]
        try:
            variables = ine_api.get("VARIABLES_OPERACION", codigo)
        except Exception as exc:  # noqa: BLE001
            lineas += [f"  ERROR al leer variables: {exc}", ""]
            continue

        territoriales = []
        for v in variables:
            n = normaliza(v.get("Nombre", ""))
            if any(k in n for k in ("provincia", "comunidad", "nacional", "municipio", "sexo", "edad")):
                territoriales.append(v)
                lineas.append(f"- variable `{v.get('Id')}` — {v.get('Nombre')}")

        for v in territoriales:
            n = normaliza(v.get("Nombre", ""))
            if not any(k in n for k in ("provincia", "comunidad", "nacional")):
                continue
            try:
                valores = ine_api.get("VALORES_VARIABLEOPERACION", f"{v.get('Id')}/{codigo}")
            except Exception as exc:  # noqa: BLE001
                lineas.append(f"    (sin valores para {v.get('Id')}: {exc})")
                continue
            interesantes = [
                val for val in valores
                if any(k in normaliza(val.get("Nombre", ""))
                       for k in ("castell", "comunitat valenciana", "total nacional"))
            ]
            for val in interesantes:
                lineas.append(f"    valor `{val.get('Id')}` — {val.get('Nombre')} "
                              f"(variable {v.get('Id')})")

            # ¿Cuántas series hay realmente para Castellón en esta operación?
            castellon = next((val for val in interesantes
                              if "castell" in normaliza(val.get("Nombre", ""))), None)
            if castellon:
                try:
                    series = ine_api.get("SERIE_METADATAOPERACION", codigo,
                                         g1=f"{v.get('Id')}:{castellon.get('Id')}")
                    lineas.append(f"    → series para Castellón: {len(series)}")
                    for s in series[:25]:
                        lineas.append(f"        · {s.get('Nombre', '').strip()}")
                except Exception as exc:  # noqa: BLE001
                    lineas.append(f"    → error al pedir series de Castellón: {exc}")
        lineas.append("")

    (SALIDA / "operaciones.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"[{len(lineas)} líneas en data/_catalogo/operaciones.md]")
    print("\n".join(lineas[:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
