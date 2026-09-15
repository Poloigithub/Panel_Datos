"""Segunda ronda: qué series simples ofrece cada operación para Castellón.

El INE nombra cada serie encadenando los valores de sus variables, así que las
series «del total» son las de nombre más corto. Se vuelcan ordenadas por
número de segmentos para poder escribir los descargadores contra nombres
reales.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402

SALIDA = Path(__file__).resolve().parents[1] / "data" / "_catalogo"

VAR_PROVINCIAS, CASTELLON = 115, 13

# operación -> palabras que deben aparecer para que la serie nos interese
OPERACIONES = {
    "ECP": ("poblacion",),
    "IDB": ("edad media", "esperanza de vida", "indice de envejecimiento",
            "tasa bruta", "numero medio de hijos", "edad media a la maternidad",
            "crecimiento", "dependencia"),
    "ADRH": ("renta", "gini", "mediana"),
    "MNPN": ("nacidos", "nacimientos"),
    "MNPD": ("defunciones", "fallecidos"),
    "EMCR": ("saldo migratorio", "inmigracion", "emigracion"),
}


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).lower().split())


def segmentos(nombre: str) -> list[str]:
    partes = [normaliza(p) for p in (nombre or "").replace(",", ".").split(".")]
    return [p for p in partes if p]


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Series simples por operación (provincia de Castellón)", ""]

    for codigo, claves in OPERACIONES.items():
        lineas += [f"## {codigo}", ""]
        try:
            series = ine_api.get("SERIE_METADATAOPERACION", codigo,
                                 g1=f"{VAR_PROVINCIAS}:{CASTELLON}")
        except Exception as exc:  # noqa: BLE001
            lineas += [f"ERROR: {exc}", ""]
            continue

        elegidas = []
        for s in series:
            n = normaliza(s.get("Nombre", ""))
            if not any(clave in n for clave in claves):
                continue
            segs = segmentos(s.get("Nombre", ""))
            if len(segs) <= 7:
                elegidas.append((len(segs), s))

        elegidas.sort(key=lambda t: (t[0], t[1].get("Nombre", "")))
        lineas.append(f"Series totales: {len(series)} · simples que encajan: {len(elegidas)}")
        lineas.append("")
        for nsegs, s in elegidas[:150]:
            lineas.append(f"- `{s.get('COD')}` ({nsegs}) — {s.get('Nombre', '').strip()}")
        lineas.append("")

    (SALIDA / "series_simples.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"[{len(lineas)} líneas en data/_catalogo/series_simples.md]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
