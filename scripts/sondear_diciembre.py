"""El fichero de diciembre de las huelgas, que no es como los demás.

Los once avances mensuales de cada año se leen sin problema y el de diciembre
no: se baja bien, se abre bien, y dentro no aparece la tabla que reparte por
territorio. Diciembre no es un avance, es el cierre del año, y eso suele
significar otra numeración de hojas.

Sin ese mes, el total anual que pide la página se queda cojo justo en el mes
que más pesa en muchos conflictos. Así que hay que mirar por dentro.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import red_ministerio as red  # noqa: E402
import xls  # noqa: E402

SALIDA = RAIZ / "sondeos"
BASE = "https://www.mites.gob.es/estadisticas/hue"

FICHEROS = [
    ("diciembre de 2024", f"{BASE}/hue24dicpublicacion/hue_12_24.xls"),
    ("noviembre de 2024, que sí funciona",
     f"{BASE}/hue24novpublicacion/hue_11_24.xls"),
]


def suave(t: str) -> str:
    plano = (t or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return " ".join(plano.split())


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# El diciembre de las huelgas", "",
              "Se baja y se abre, pero dentro no aparece la tabla territorial.",
              "Diciembre no es un avance: es el cierre del año.", ""]

    for etiqueta, url in FICHEROS:
        print(f"· {etiqueta}")
        estado, _, datos = red.abre(url)
        lineas += [f"## {etiqueta}", "", f"`{url}` → {estado}, {len(datos)} bytes", ""]
        if estado != 200 or datos[:8] != xls.FIRMA:
            lineas.append("No se ha podido bajar.")
            continue
        libro = xls.Libro(datos)
        hojas = list(libro.hojas)
        lineas.append(f"- {len(hojas)} hojas: {', '.join(hojas)}")
        indice = next((h for h in hojas if suave(h).startswith("indice")), None)
        if indice:
            lineas += ["", "### Su índice", "```"]
            for fila in libro.filas(indice):
                celdas = [str(c) for c in fila if c not in (None, "")]
                if celdas:
                    lineas.append(" | ".join(celdas))
            lineas += ["```", ""]
            # Y el volcado de las que reparten por territorio, que en el
            # cierre de año van en tres hojas -una por magnitud- en vez de en
            # una con tres bloques de columnas.
            for hoja in hojas:
                if not suave(hoja).startswith("hue-3"):
                    continue
                filas = libro.filas(hoja)
                lineas += [f"#### Hoja «{hoja}» · {len(filas)} filas", "```"]
                for i, fila in enumerate(filas[:22]):
                    celdas = [("" if c is None else str(c)) for c in fila[:16]]
                    while celdas and celdas[-1] == "":
                        celdas.pop()
                    if celdas:
                        lineas.append(f"{i:>3} | " + " | ".join(celdas))
                lineas += ["```", ""]
        else:
            lineas += ["", "**No tiene hoja de índice.**", ""]
            # Sin índice hay que mirar los títulos de las propias hojas.
            for hoja in hojas[:25]:
                try:
                    filas = libro.filas(hoja)
                except Exception:  # noqa: BLE001
                    continue
                titulo = " ".join(str(c) for fila in filas[:4]
                                  for c in fila if c not in (None, ""))
                lineas.append(f"- «{hoja}» → {titulo[:150]}")
            lineas.append("")

    (SALIDA / "diciembre.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/diciembre.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
