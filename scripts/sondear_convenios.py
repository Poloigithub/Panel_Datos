"""Los convenios colectivos, ahora que se pueden abrir.

La subida salarial pactada es el dato que le falta al panel para cerrar el
círculo de la cesta de la compra: allí se compara lo que sube la comida con lo
que sube el salario, pero el salario viene de una encuesta que llega con año y
medio de retraso. Los convenios se publican **cada mes**.

El fichero se abre desde que el panel tiene lector de `.xls`. Falta lo de
siempre: qué hoja trae la subida pactada, si baja a provincia, y cómo está
montada la tabla.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import red_ministerio as red  # noqa: E402
import xls  # noqa: E402

SALIDA = RAIZ / "sondeos"
CCT = "https://www.mites.gob.es/estadisticas/cct/cct26agoav/CCT_08_2026.xls"

# Lo que se busca en el índice, y hacen falta las dos cosas a la vez: media
# docena de tablas hablan de variación salarial, y sólo una de ellas la reparte
# por territorio. Pedir cualquiera de las dos palabras traía las seis.
INTERESA = ("variacion salarial", "comunidad autonoma y provincia")


def normaliza(texto: str) -> str:
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return " ".join(plano.split())


def vuelca(lineas: list[str], libro, hoja: str, tope: int = 40) -> None:
    try:
        filas = libro.filas(hoja)
    except Exception as exc:  # noqa: BLE001
        lineas.append(f"    - no se ha podido leer: {type(exc).__name__}: {exc}")
        return
    lineas += [f"### Hoja «{hoja}» · {len(filas)} filas", "```"]
    for i, fila in enumerate(filas[:tope]):
        celdas = [("" if c is None else str(c)) for c in fila[:10]]
        while celdas and celdas[-1] == "":
            celdas.pop()
        if celdas:
            lineas.append(f"{i:>3} | " + " | ".join(celdas))
    lineas += ["```", ""]


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Los convenios colectivos por dentro", "",
              "La subida salarial pactada se publica cada mes, frente al año y",
              "medio de retraso de la encuesta salarial. Es lo que le falta a la",
              "cesta de la compra para cerrar el círculo.", ""]

    estado, _, datos = red.abre(CCT)
    lineas += [f"`{CCT}` → {estado}, {len(datos)} bytes", ""]
    if estado != 200 or len(datos) < 1000:
        lineas.append("No se ha podido bajar.")
        (SALIDA / "convenios.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return 1

    libro = xls.Libro(datos)
    nombres = list(libro.hojas)
    print(f"  {len(nombres)} hojas")

    indice = next((h for h in nombres if normaliza(h).startswith("indice")), None)
    interesantes: list[str] = []
    if indice:
        lineas += ["## Lo que dice su índice", "```"]
        for fila in libro.filas(indice):
            celdas = [str(c) for c in fila if c not in (None, "")]
            if not celdas:
                continue
            texto = " | ".join(celdas)
            lineas.append(texto)
            plano = normaliza(" ".join(celdas))
            if all(p in plano for p in INTERESA):
                codigo = normaliza(celdas[0]).rstrip(". ")
                for nombre in nombres:
                    if normaliza(nombre).rstrip(". ") == codigo:
                        interesantes.append(nombre)
        lineas += ["```", ""]

    print(f"  {len(interesantes)} hojas interesantes: {interesantes[:6]}")
    lineas += [f"## {len(interesantes)} hojas que suenan a lo que se busca", ""]
    for hoja in interesantes[:4]:
        vuelca(lineas, libro, hoja, tope=60)

    (SALIDA / "convenios.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/convenios.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
