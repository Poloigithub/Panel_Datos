"""¿Hasta dónde baja el IPC en el detalle de la cesta de la compra?

La pregunta es cuánto ha subido la comida estos años, y para responderla hace
falta saber qué publica el INE por debajo del grupo «alimentos y bebidas no
alcohólicas», que es lo único que el panel tiene ahora. El IPC tiene grupos,
subgrupos, clases y subclases -el aceite de oliva es una subclase-, pero no
todos los niveles llegan a todos los territorios: el dato provincial suele
quedarse en el grupo.

Esto lista, para los tres ámbitos, las series del IPC que mencionan algo de
comer, para ver qué nivel de detalle existe en cada uno.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import ine_series as motor  # noqa: E402

SALIDA = RAIZ / "sondeos"

AMBITOS = [("España", "349:16473"), ("Comunitat Valenciana", "70:9006"),
           ("Castellón", "115:13")]

# Lo que la gente compra y mira el ticket.
COMIDA = ("aceite", "leche", "pan", "huevo", "carne", "fruta", "pescado", "verdura",
          "hortaliza", "legumbre", "arroz", "pasta", "azucar", "cafe", "cereal",
          "alimento", "lacteo", "queso", "patata", "agua mineral", "refresco")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# El IPC por dentro: qué detalle hay de la cesta de la compra", "",
              "El panel sólo tiene el grupo «alimentos y bebidas no alcohólicas».",
              "Aquí se mira qué hay por debajo y en qué ámbitos existe.", ""]

    for nombre, filtro in AMBITOS:
        print(f"· {nombre}")
        indice = motor.indexa_por_segmentos("IPC", filtro)
        total = sum(len(v) for v in indice.values())
        lineas += [f"## {nombre}", f"- {total} series, {len(indice)} combinaciones", ""]

        # Sólo las del índice, no las variaciones, y sin desgloses raros.
        del_indice = {segs for segs in indice
                      if any(s in ("indice", "media anual") for s in segs)}
        comestibles = [segs for segs in indice
                       if any(c in s for s in segs for c in COMIDA)]
        lineas.append(f"- {len(comestibles)} combinaciones mencionan algo de comer, "
                      f"y {len(del_indice)} son del índice")

        # Interesa el nombre exacto del producto y si tiene serie de índice.
        productos = {}
        for segs in comestibles:
            etiquetas = [s for s in segs
                         if any(c in s for c in COMIDA) and s != "alimentos"]
            for etiqueta in etiquetas:
                productos.setdefault(etiqueta, set()).update(
                    s for s in segs if s not in etiquetas)
        lineas.append(f"- {len(productos)} productos distintos:")
        for producto in sorted(productos)[:60]:
            acompanan = sorted(a for a in productos[producto]
                               if a not in ("dato base", "indice"))[:4]
            lineas.append(f"    - **{producto}** · con: {acompanan}")
        lineas.append("")

    (SALIDA / "cesta.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/cesta.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
