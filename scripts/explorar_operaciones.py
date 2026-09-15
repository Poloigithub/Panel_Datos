"""Tercera ronda: qué conceptos publica cada operación para Castellón.

Volcar series una a una se llena de desgloses por edad, así que se agrupan por
concepto -el nombre sin territorio, sexo ni muletillas- y se muestra un
ejemplo de cada uno.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402

SALIDA = Path(__file__).resolve().parents[1] / "data" / "_catalogo"
VAR_PROVINCIAS, CASTELLON = 115, 13

OPERACIONES = ("IDB", "MNPN", "MNPD", "ECP", "ADRH", "EMCR")

# Segmentos que no distinguen un concepto de otro.
RUIDO = {
    "castellon/castello", "ambos sexos", "hombres", "mujeres", "total", "anual",
    "dato base", "numero", "porcentaje", "ambas nacionalidades", "espanola",
    "extranjera", "todas las edades", "totales",
}
# Un desglose por edad no crea concepto nuevo.
EDAD = ("anos", "ano", "y mas", "menos de", "de 1", "de 2", "de 3", "de 4",
        "de 5", "de 6", "de 7", "de 8", "de 9", "de 0")


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).lower().split())


def concepto(nombre: str) -> tuple[str, ...]:
    partes = [normaliza(p) for p in (nombre or "").replace(",", ".").split(".")]
    limpias = []
    for p in partes:
        if not p or p in RUIDO:
            continue
        if any(p.endswith(s) or p.startswith(s) for s in EDAD):
            continue
        limpias.append(p)
    return tuple(limpias)


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Conceptos por operación (provincia de Castellón)", ""]

    for codigo in OPERACIONES:
        lineas += [f"## {codigo}", ""]
        try:
            series = ine_api.get("SERIE_METADATAOPERACION", codigo,
                                 g1=f"{VAR_PROVINCIAS}:{CASTELLON}")
        except Exception as exc:  # noqa: BLE001
            lineas += [f"ERROR: {exc}", ""]
            continue

        conceptos: dict[tuple[str, ...], dict] = {}
        for s in series:
            clave = concepto(s.get("Nombre", ""))
            if not clave or len(clave) > 4:
                continue
            anterior = conceptos.get(clave)
            # nos quedamos con el ejemplo de nombre más corto
            if anterior is None or len(s.get("Nombre", "")) < len(anterior.get("Nombre", "")):
                conceptos[clave] = s

        lineas.append(f"Series: {len(series)} · conceptos distintos: {len(conceptos)}")
        lineas.append("")
        for clave in sorted(conceptos):
            s = conceptos[clave]
            lineas.append(f"- `{s.get('COD')}` — {s.get('Nombre', '').strip()}")
        lineas.append("")

    (SALIDA / "conceptos.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"[{len(lineas)} líneas en data/_catalogo/conceptos.md]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
