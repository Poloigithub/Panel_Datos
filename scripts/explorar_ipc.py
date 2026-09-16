"""Qué publica el INE del IPC para nuestros tres ámbitos.

Diagnóstico de un solo uso, como los que precedieron a cada bloque de datos:
el volcado se escribe a un fichero porque el log de Actions se trunca.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402
import ine_series as motor  # noqa: E402

SALIDA = Path(__file__).resolve().parents[1] / "data" / "_catalogo"

AMBITOS = [("Castellón", "115:13"), ("Total Nacional", "349:16473")]

RUIDO = {"castellon/castello", "total nacional", "comunitat valenciana", "total",
         "indice", "dato base", "anual", "mensual"}


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).lower().split())


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# IPC: qué hay por ámbito", ""]

    # ¿Cómo se llama la operación? Puede no ser exactamente «IPC».
    operaciones = ine_api.get("OPERACIONES_DISPONIBLES")
    candidatas = [o for o in operaciones
                  if "precios de consumo" in normaliza(o.get("Nombre", ""))
                  or normaliza(o.get("Codigo", "")) in ("ipc", "ipca")]
    lineas.append("## Operaciones de precios")
    for o in candidatas:
        lineas.append(f"- `{o.get('Codigo')}` (id {o.get('Id')}) — {o.get('Nombre')}")
    lineas.append("")

    for codigo in [o.get("Codigo") for o in candidatas if o.get("Codigo")]:
        for etiqueta, filtro in AMBITOS:
            lineas += [f"## {codigo} · {etiqueta}", ""]
            try:
                series = ine_api.get("SERIE_METADATAOPERACION", codigo, g1=filtro)
            except Exception as exc:  # noqa: BLE001
                lineas += [f"ERROR: {exc}", ""]
                continue
            lineas.append(f"Series: {len(series)}")

            # Conceptos: el nombre sin territorio ni muletillas.
            conceptos: dict[tuple, dict] = {}
            for s in series:
                partes = tuple(p for p in sorted(motor.segmentos(s.get("Nombre", "")))
                               if p not in RUIDO)
                if len(partes) > 3:
                    continue
                anterior = conceptos.get(partes)
                if anterior is None or len(s.get("Nombre", "")) < len(anterior.get("Nombre", "")):
                    conceptos[partes] = s
            lineas.append(f"Conceptos simples: {len(conceptos)}")
            lineas.append("")
            for partes in sorted(conceptos)[:70]:
                s = conceptos[partes]
                lineas.append(f"- `{s.get('COD')}` — {s.get('Nombre', '').strip()}")
            lineas.append("")

            # Una muestra de datos para ver periodicidad y forma del periodo.
            if conceptos:
                muestra = conceptos[sorted(conceptos)[0]]
                valores = motor.descarga_serie(muestra["COD"])
                periodos = sorted(valores, key=motor.orden_periodo)
                lineas.append(f"Muestra {muestra['COD']}: {len(periodos)} periodos "
                              f"({periodos[0] if periodos else '-'} … "
                              f"{periodos[-1] if periodos else '-'}), "
                              f"último valor {valores.get(periodos[-1]) if periodos else '-'}")
                lineas.append("")

    (SALIDA / "ipc.md").write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas[:60]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
