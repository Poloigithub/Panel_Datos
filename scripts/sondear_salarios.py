"""Sondeo de las fuentes salariales, antes de decidir si la fase 5 es viable.

La hoja de ruta da por supuesto que los salarios sólo existen por comunidad
autónoma -Encuesta de Estructura Salarial y ETCL-, lo que dejaría a Castellón
sin cifra en su propia página. Antes de escribir nada hay que comprobar dos
cosas:

1. Qué operaciones del INE hablan de salarios y hasta qué nivel territorial
   llegan de verdad. La prueba buena no es el nombre sino si la operación
   tiene la variable 115, «Provincias», y si con ella devuelve series.
2. Si la Agencia Tributaria publica de forma descargable su estadística de
   «Mercado de trabajo y pensiones en las fuentes tributarias», que sí da
   salario medio por provincia. Si eso se puede bajar, la fase 5 cambia de
   sentido: Castellón tendría dato propio.
"""

from __future__ import annotations

import html
import json
import re
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

PALABRAS = ("salari", "salario", "ganancia", "coste laboral", "retribuc", "renta de")

AMBITOS = [("España", "349:16473"), ("Comunitat Valenciana", "70:9006"),
           ("Castellón", "115:13")]

PAGINAS_AEAT = [
    ("Estadísticas AEAT",
     "https://sede.agenciatributaria.gob.es/Sede/datos-abiertos/catalogo-informacion-publica.html"),
    ("Mercado de trabajo y pensiones",
     "https://sede.agenciatributaria.gob.es/Sede/datos-abiertos/catalogo-informacion-publica/"
     "estadisticas-tributarias/mercado-trabajo-pensiones-fuentes-tributarias.html"),
    ("Portal estadístico AEAT",
     "https://sede.agenciatributaria.gob.es/Sede/estadisticas.html"),
]

BUSQUEDAS = ["mercado de trabajo y pensiones", "salarios", "estructura salarial",
             "coste laboral"]

FICHERO = re.compile(r'href="([^"]*(?:\.xlsx?|\.csv|\.zip)(?:\?[^"]*)?)"', re.I)
ENLACE = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
ETIQUETAS = re.compile(r"<[^>]+>")


def sondea(url: str, limite: int = 900_000):
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=120) as respuesta:
            trozo = respuesta.read(limite)
            tipo = respuesta.headers.get("Content-Type", "?")
            for codificacion in ("utf-8", "latin-1"):
                try:
                    return respuesta.status, tipo, trozo.decode(codificacion)
                except UnicodeDecodeError:
                    continue
            return respuesta.status, tipo, ""
    except urllib.error.HTTPError as exc:
        return exc.code, "-", str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}"


def mira_operacion(operacion: dict) -> list[str]:
    codigo = operacion.get("Codigo") or operacion.get("Cod_IOE")
    lineas = [f"### {operacion.get('Nombre')}", f"- código `{codigo}`"]
    try:
        variables = ine_api.get("VARIABLES_OPERACION", str(codigo))
    except ine_api.INEError as exc:
        return lineas + [f"- sin variables: {exc}", ""]

    territoriales = [v for v in variables if v.get("Id") in (19, 70, 115, 349)]
    lineas.append("- variables territoriales: " +
                  (", ".join(f"{v['Id']} {v['Nombre']}" for v in territoriales) or "**ninguna**"))
    if not any(v.get("Id") == 115 for v in territoriales):
        lineas.append("- **no llega a provincia**")

    # Aunque no baje de comunidad autónoma interesa ver qué publica: una
    # sección de salarios puede darse por comunidad diciendo que es lo que hay.
    ambitos = AMBITOS if any(v.get("Id") == 115 for v in territoriales) else AMBITOS[:2]
    for nombre_ambito, filtro in ambitos:
        try:
            indice = motor.indexa_por_segmentos(str(codigo), filtro)
        except ine_api.INEError as exc:
            lineas.append(f"- {nombre_ambito}: error {exc}")
            continue
        total = sum(len(v) for v in indice.values())
        lineas.append(f"- **{nombre_ambito}**: {total} series, {len(indice)} combinaciones")
        for segs in sorted(indice, key=lambda s: (len(s), sorted(s)))[:16]:
            lineas.append(f"    - {sorted(segs)} → `{indice[segs][0]['COD']}`")
    lineas.append("")
    return lineas


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Sondeo de fuentes salariales", "",
              "La pregunta es una: ¿hay salario con dato propio de Castellón?", ""]

    lineas += ["## Operaciones del INE que hablan de salarios", ""]
    operaciones = ine_api.get("OPERACIONES_DISPONIBLES")
    candidatas = [o for o in operaciones
                  if any(p in motor.normaliza(o.get("Nombre", "")) for p in PALABRAS)]
    lineas.append(f"{len(candidatas)} operaciones:")
    for operacion in candidatas:
        lineas.append(f"- `{operacion.get('Codigo')}` · {operacion.get('Nombre')}")
    lineas.append("")
    for operacion in candidatas:
        print(f"· {operacion.get('Nombre')}")
        lineas += mira_operacion(operacion)

    lineas += ["## Agencia Tributaria", ""]
    for nombre, url in PAGINAS_AEAT:
        print(f"· {nombre}")
        codigo, tipo, cuerpo = sondea(url)
        lineas += [f"### {nombre}", f"- `{codigo}` · {tipo} · {url}"]
        if codigo != 200 or not cuerpo:
            lineas += [f"- {cuerpo[:200]}", ""]
            continue
        ficheros = {urllib.parse.urljoin(url, html.unescape(h)) for h in FICHERO.findall(cuerpo)}
        lineas.append(f"- {len(ficheros)} ficheros descargables")
        for f in sorted(ficheros)[:15]:
            lineas.append(f"    - {f}")
        interesantes = []
        for href, texto in ENLACE.findall(cuerpo):
            limpio = " ".join(html.unescape(ETIQUETAS.sub(" ", texto)).split())
            if any(p in motor.normaliza(href + " " + limpio)
                   for p in ("mercado de trabajo", "salario", "asalariado")):
                interesantes.append((urllib.parse.urljoin(url, html.unescape(href)), limpio))
        lineas.append(f"- {len(interesantes)} enlaces que mencionan salarios")
        for destino, texto in interesantes[:15]:
            lineas.append(f"    - **{texto[:70] or '(sin texto)'}** → {destino}")
        lineas.append("")

    lineas += ["## Catálogo de datos.gob.es", ""]
    for consulta in BUSQUEDAS:
        url = ("https://datos.gob.es/apidata/catalog/dataset/title/"
               + urllib.parse.quote(consulta) + "?_pageSize=10&_page=0")
        codigo, _, cuerpo = sondea(url, 150_000)
        lineas.append(f"### «{consulta}» → {codigo}")
        try:
            items = (json.loads(cuerpo).get("result") or {}).get("items") or []
        except (json.JSONDecodeError, AttributeError):
            items = []
        if not items:
            lineas += ["- sin resultados", ""]
            continue
        for item in items[:6]:
            titulos = item.get("title")
            titulo = (next((t.get("_value") for t in titulos if t.get("_lang") in (None, "es")),
                           titulos[0].get("_value")) if isinstance(titulos, list) else titulos)
            lineas.append(f"- **{titulo}**")
            distribuciones = item.get("distribution") or []
            if isinstance(distribuciones, dict):
                distribuciones = [distribuciones]
            for dist in distribuciones[:3]:
                if isinstance(dist, dict):
                    lineas.append(f"    - {dist.get('accessURL')}")
        lineas.append("")

    (SALIDA / "salarios.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/salarios.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
