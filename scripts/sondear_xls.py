"""El lector nuevo del .xls, contra ficheros de verdad.

Las pruebas de `tests/test_xls.py` cubren las piezas difíciles -el número
comprimido, las cadenas partidas por un empalme- pero no pueden cubrir lo que
de verdad decide si esto sirve: un fichero real del ministerio, con sus
cuarenta hojas y sus manías.

Se abren tres, de tres estadísticas distintas y de años distintos, y se enseña
lo que salga. Si el lector funciona, esto desbloquea de golpe los convenios
colectivos, las huelgas y los despidos, que llevan años publicándose en un
formato de 1997.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import red_ministerio as red  # noqa: E402
import xls  # noqa: E402

SALIDA = RAIZ / "sondeos"
BASE = "https://www.mites.gob.es/estadisticas"

FICHEROS = [
    ("convenios colectivos, agosto de 2026", f"{BASE}/cct/cct26agoav/CCT_08_2026.xls"),
    ("huelgas, julio de 2026", f"{BASE}/hue/hue26julpublicacion/HUE_07_2026.xls"),
    ("convenios colectivos, definitivo de 2012", f"{BASE}/cct/CCT12DEF/CCT_2012_DEF.xls"),
]


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# El lector del .xls, contra ficheros de verdad", "",
              "Si esto funciona, se desbloquean los convenios colectivos, las",
              "huelgas y los despidos, que llevan años en un formato de 1997.",
              ""]
    buenos = 0

    for etiqueta, url in FICHEROS:
        print(f"· {etiqueta}")
        estado, _, datos = red.abre(url)
        lineas += [f"## {etiqueta}", "", f"`{url}` → {estado}, {len(datos)} bytes", ""]
        if estado != 200 or len(datos) < 1000:
            lineas.append("No se ha podido bajar.")
            print("    no se ha podido bajar")
            continue
        try:
            libro = xls.Libro(datos)
        except Exception as exc:  # noqa: BLE001
            lineas.append(f"**No se ha podido abrir**: {type(exc).__name__}: {exc}")
            print(f"    no se ha podido abrir: {type(exc).__name__}: {exc}")
            continue

        nombres = list(libro.hojas)
        lineas.append(f"- {len(nombres)} hojas, {len(libro.cadenas)} cadenas")
        lineas.append(f"- se llaman: {', '.join(nombres[:30])}")
        print(f"    {len(nombres)} hojas, {len(libro.cadenas)} cadenas")

        # Las que suenen a provincia, que es lo que decide si entra en el panel.
        provinciales = [h for h in nombres if "prov" in h.lower()]
        for hoja in (provinciales or nombres)[:2]:
            try:
                filas = libro.filas(hoja)
            except Exception as exc:  # noqa: BLE001
                lineas.append(f"    - hoja «{hoja}»: {type(exc).__name__}: {exc}")
                continue
            lineas += ["", f"### Hoja «{hoja}» · {len(filas)} filas", "```"]
            for i, fila in enumerate(filas[:35]):
                celdas = [("" if c is None else str(c)) for c in fila[:9]]
                while celdas and celdas[-1] == "":
                    celdas.pop()
                if celdas:
                    lineas.append(f"{i:>3} | " + " | ".join(celdas))
            lineas += ["```", ""]
            print(f"      «{hoja}»: {len(filas)} filas")
        buenos += 1

    lineas += ["", f"## Resultado: {buenos} de {len(FICHEROS)} ficheros abiertos", ""]
    (SALIDA / "xls.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/xls.md · {buenos}/{len(FICHEROS)} abiertos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
