"""¿Están completos los últimos trimestres de lanzamientos?

En la serie trimestral, España cae de 7.334 lanzamientos en el 1T de 2025 a
4.005 en el 1T de 2026, y Castellón de 86 a 24. Puede ser real o puede ser que
los últimos trimestres lleguen incompletos y el CGPJ los revise al alza
después. Publicar un titular de «−72 % en un año» sin saberlo sería temerario.

El contraste está en el propio CGPJ: publica aparte los lanzamientos por
partido judicial y por años (2013-2025). Si la suma de los cuatro trimestres de
un año coincide con el total anual de ese otro fichero, la serie trimestral
está completa hasta donde llega.
"""

from __future__ import annotations

import html
import sys
import urllib.parse
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import cgpj_lanzamientos as cgpj  # noqa: E402
from xlsx import Libro  # noqa: E402

SALIDA = RAIZ / "sondeos"


def fichero_por_partidos() -> tuple[str, str]:
    cuerpo = cgpj.descarga(cgpj.PAGINA, 3_000_000).decode("utf-8", errors="replace")
    for href in cgpj.HOJA_CALCULO.findall(cuerpo):
        url = urllib.parse.urljoin(cgpj.PAGINA, html.unescape(href))
        nombre = urllib.parse.unquote(url.split("/")[-1].split("?")[0])
        if "lanzamientos por pj" in cgpj.normaliza(nombre):
            return url, nombre
    raise RuntimeError("no está el fichero de lanzamientos por partido judicial")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# ¿Vienen completos los últimos trimestres de lanzamientos?", ""]

    # 1. La serie trimestral, sumada por años.
    url, nombre = cgpj.localiza_fichero()
    series = cgpj.series_del_libro(Libro(cgpj.descarga(url)))
    lineas += [f"## Serie trimestral · `{nombre}`", ""]
    por_anyo = {}
    for ambito, indicadores in series.items():
        valores = indicadores.get("lanzamientos", {})
        anyos = {}
        for periodo, valor in valores.items():
            anyos.setdefault(periodo[:4], []).append(valor)
        por_anyo[ambito] = {a: (sum(v), len(v)) for a, v in anyos.items()}
        ultimos = sorted(por_anyo[ambito])[-4:]
        lineas.append(f"- **{ambito}**: " + " · ".join(
            f"{a}: {por_anyo[ambito][a][0]:,.0f} ({por_anyo[ambito][a][1]}T)"
            for a in ultimos))
    lineas.append("")

    # 2. El fichero por partidos judiciales, que es anual.
    url_pj, nombre_pj = fichero_por_partidos()
    libro = Libro(cgpj.descarga(url_pj))
    hoja = list(libro.hojas)[0]
    filas = libro.filas(hoja)
    lineas += [f"## Por partidos judiciales · `{nombre_pj}`", f"- hoja «{hoja}», {len(filas)} filas", ""]

    # La fila de años está por encima de la de conceptos; el total de cada año
    # es la primera de sus cuatro columnas.
    fila_anyos = next((f for f in filas[:6]
                       if sum(1 for c in f if isinstance(c, (int, float)) and 2000 < c < 2100) >= 3),
                      None)
    if not fila_anyos:
        lineas.append("- no se ha encontrado la fila de años")
    else:
        columnas = {int(c): j for j, c in enumerate(fila_anyos)
                    if isinstance(c, (int, float)) and 2000 < c < 2100}
        lineas.append(f"- años: {sorted(columnas)}")
        cabecera = filas.index(fila_anyos)
        for anyo in sorted(columnas)[-3:]:
            columna = columnas[anyo]
            total = 0.0
            cuantos = 0
            castellon = 0.0
            partidos_castellon = ("CASTELLON", "VILA-REAL", "VILLARREAL", "NULES",
                                  "SEGORBE", "VINAROS", "VINAROZ")
            for fila in filas[cabecera + 2:]:
                nombre_fila = next((str(c) for c in fila[:2] if isinstance(c, str)), "")
                valor = fila[columna] if columna < len(fila) else None
                if not isinstance(valor, (int, float)):
                    continue
                total += valor
                cuantos += 1
                if any(p in cgpj.normaliza(nombre_fila).upper() for p in partidos_castellon):
                    castellon += valor
            lineas.append(f"- **{anyo}**: {total:,.0f} sumando {cuantos} partidos · "
                          f"Castellón (sus partidos) {castellon:,.0f}")

    lineas += ["", "## Comparación", ""]
    for anyo in ("2024", "2025"):
        nacional = por_anyo.get("espana", {}).get(anyo)
        castellon = por_anyo.get("castellon", {}).get(anyo)
        lineas.append(f"- {anyo}: serie trimestral España {nacional} · Castellón {castellon}")

    (SALIDA / "lanzamientos-revisiones.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
