"""Sondeo de los lanzamientos: desahucios por hipoteca y por alquiler.

La estadística de Ejecuciones Hipotecarias del INE, que ya está en el panel,
sólo cuenta hipotecas: no existe en ella la variante de alquiler. Lo que sí se
reparte entre una cosa y otra son los **lanzamientos practicados**, que publica
el Consejo General del Poder Judicial separando los derivados de la Ley
Hipotecaria de los derivados de la Ley de Arrendamientos Urbanos.

Este sondeo busca esa fuente en tres sitios, porque no se sabe de antemano cuál
da un fichero estable y provincial: el catálogo de datos.gob.es, las
direcciones del propio CGPJ, y -por si acaso- el INE, que podría publicar algo
equivalente bajo otro nombre.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import ine_api  # noqa: E402
import ine_series as motor  # noqa: E402

SALIDA = RAIZ / "sondeos"
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

BUSQUEDAS = [
    "lanzamientos", "desahucios", "ejecuciones hipotecarias",
    "efectos de la crisis en los organos judiciales", "estadistica judicial",
]

# El CGPJ publica los datos de coyuntura en su portal de estadística; se
# prueban las formas en que los ha ido sirviendo.
DIRECTAS = [
    "https://www.poderjudicial.es/cgpj/es/Temas/Estadistica-Judicial/Estadistica-por-temas/Datos-penales--civiles-y-laborales/Series-y-Temas/Efecto-de-la-Crisis-en-los-organos-judiciales/",
    "https://www.poderjudicial.es/cgpj/es/Temas/Estadistica-Judicial/",
    "https://www.poderjudicial.es/portal/site/cgpj/",
    "https://datos.gob.es/apidata/catalog/publisher",
]

PALABRAS_INE = ("lanzamiento", "desahucio", "arrendamiento", "judicial")


def sondea(url: str, limite: int = 4000):
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=90) as respuesta:
            trozo = respuesta.read(limite)
            for codificacion in ("utf-8", "latin-1"):
                try:
                    return (respuesta.status, respuesta.headers.get("Content-Type", "?"),
                            trozo.decode(codificacion))
                except UnicodeDecodeError:
                    continue
            return respuesta.status, "binario", repr(trozo[:120])
    except urllib.error.HTTPError as exc:
        return exc.code, "-", str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}"


def del_catalogo(consulta: str) -> list[str]:
    url = ("https://datos.gob.es/apidata/catalog/dataset/title/"
           + urllib.parse.quote(consulta) + "?_pageSize=15&_page=0")
    codigo, _, cuerpo = sondea(url, 200_000)
    lineas = [f"## «{consulta}» → {codigo}"]
    if codigo != 200:
        return lineas + [f"- {cuerpo[:200]}", ""]
    try:
        items = (json.loads(cuerpo).get("result") or {}).get("items") or []
    except json.JSONDecodeError:
        return lineas + ["- respuesta no JSON", ""]
    if not items:
        return lineas + ["- sin resultados", ""]
    for item in items[:10]:
        titulos = item.get("title")
        titulo = (next((t.get("_value") for t in titulos if t.get("_lang") in (None, "es")),
                       titulos[0].get("_value")) if isinstance(titulos, list) else titulos)
        editor = item.get("publisher")
        lineas.append(f"- **{titulo}**  ·  {editor}")
        distribuciones = item.get("distribution") or []
        if isinstance(distribuciones, dict):
            distribuciones = [distribuciones]
        for dist in distribuciones[:5]:
            if isinstance(dist, dict):
                lineas.append(f"    - {dist.get('format', {}).get('value', '?')} "
                              f"{dist.get('accessURL')}")
    return lineas + [""]


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Sondeo de lanzamientos (hipoteca y alquiler)", ""]

    lineas += ["# Catálogo de datos.gob.es", ""]
    for consulta in BUSQUEDAS:
        print(f"· catálogo: {consulta}")
        lineas += del_catalogo(consulta)

    lineas += ["# Direcciones del CGPJ", ""]
    for url in DIRECTAS:
        print(f"· directa: {url}")
        codigo, tipo, cuerpo = sondea(url)
        lineas += [f"## {url}", f"- {codigo} · {tipo}"]
        if codigo == 200:
            # Interesa saber si la página enlaza ficheros descargables.
            enlaces = [t for t in cuerpo.split('"') if t.lower().endswith((".xlsx", ".xls", ".csv"))]
            lineas.append(f"- {len(enlaces)} enlaces a hoja de cálculo en los primeros 4 KB")
            for enlace in enlaces[:6]:
                lineas.append(f"    - {enlace}")
        else:
            lineas.append(f"- {cuerpo[:200]}")
        lineas.append("")

    lineas += ["# Operaciones del INE que suenen a esto", ""]
    try:
        operaciones = ine_api.get("OPERACIONES_DISPONIBLES")
        for operacion in operaciones:
            nombre = motor.normaliza(operacion.get("Nombre", ""))
            if any(palabra in nombre for palabra in PALABRAS_INE):
                lineas.append(f"- `{operacion.get('Codigo')}` · {operacion.get('Nombre')}")
    except ine_api.INEError as exc:
        lineas.append(f"- no se ha podido consultar el INE: {exc}")
    lineas.append("")

    (SALIDA / "lanzamientos.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/lanzamientos.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
