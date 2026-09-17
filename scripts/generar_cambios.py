"""Qué cambió y cuándo, sacado del historial de git.

Cada actualización de datos es un commit, así que el repositorio ya guarda
cuándo cambió cada cifra sin que haya que llevar un registro aparte. Esto lo
convierte en algo que se pueda leer desde la web, y son dos cosas distintas:

- **Altas**: qué dato es nuevo. Cuándo apareció por primera vez cada sección y
  cada indicador, que es el seguimiento de lo que va creciendo el panel. Sale
  de mirar el `index.json` de cada bloque en cada commit que lo tocó y
  quedarse con la primera vez que aparece cada clave. No hay ninguna lista
  escrita a mano que se pueda quedar vieja: si mañana se añade un indicador,
  la página lo cuenta sola.
- **Actualizaciones**: qué cifras se han movido. Incluye las revisiones de los
  propios organismos, que es lo interesante: el INE corrige series hacia atrás
  con frecuencia y eso no suele verse en ningún sitio.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generar_catalogo import TITULOS_EPA  # noqa: E402
from secciones import SECCIONES  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data"
TOPE = 80  # commits a mirar para las actualizaciones; más atrás deja de interesar

# Los ensayos y volcados son commits de desarrollo -probar un descargador
# nuevo contra la fuente de verdad- y no novedades para quien consulta el
# panel: la cifra que dejan es la misma que traerá la actualización siguiente.
DESARROLLO = ("ensayo de ", "volcado de ", "prueba de ")

# Un tabulador, y no el separador de registro que parecería lo suyo: el
# `splitlines()` de Python también parte por \x1e, así que cada commit salía
# convertido en tres líneas.
SEPARADOR = "\t"
FORMATO = SEPARADOR.join(["%H", "%aI", "%s"])
# Para el recorrido de altas hace falta separar commits que traen varias
# líneas de ficheros, así que va una marca propia delante de cada uno.
MARCA = "\x01"


def git(*argumentos: str) -> str:
    return subprocess.run(["git", *argumentos], cwd=RAIZ, check=True,
                          capture_output=True, text=True).stdout


# Carpetas de datos que no son una sección del panel.
EXTRA = {"municipios": "Municipios de Castellón", "geo": "Contornos municipales"}
# Y carpetas que no son datos: volcados de sondeos de la época en que se
# guardaban dentro de data/.
NO_SON_DATOS = ("_catalogo",)


def titulos() -> dict[str, str]:
    conocidas = {s["bloque"]: s["titulo"] for s in SECCIONES}
    conocidas.update(EXTRA)
    for carpeta in DATOS.iterdir():
        if carpeta.is_dir():
            conocidas.setdefault(carpeta.name, carpeta.name)
    return conocidas


def cambios(commit: str) -> dict[str, int]:
    """Cuántas líneas de datos cambiaron en cada sección, como medida de tamaño."""
    salida = git("show", "--numstat", "--format=", commit, "--", "data/")
    por_seccion: dict[str, int] = {}
    for linea in salida.splitlines():
        partes = linea.split("\t")
        if len(partes) != 3:
            continue
        anadidas, quitadas, ruta = partes
        trozos = ruta.split("/")
        if len(trozos) < 2:
            continue
        seccion = trozos[1] if trozos[0] == "data" else trozos[0]
        if seccion.endswith(".json") or seccion.endswith(".csv"):
            seccion = "panel"
        cuantas = sum(int(n) for n in (anadidas, quitadas) if n.isdigit())
        por_seccion[seccion] = por_seccion.get(seccion, 0) + cuantas
    return por_seccion


def indicadores_en(commit: str, ruta: str) -> tuple[str, dict[str, str]]:
    """El título del bloque y sus indicadores, tal y como estaban en un commit.

    Hay dos formas de guardarlo. Casi todos los bloques traen sus fichas en el
    `index.json`; el de la EPA no, y sus indicadores sólo se saben mirando qué
    series hay dentro del fichero de un ámbito. Se aceptan las dos.
    """
    try:
        crudo = git("show", f"{commit}:{ruta}")
    except subprocess.CalledProcessError:
        return "", {}
    try:
        ficha = json.loads(crudo)
    except json.JSONDecodeError:
        return "", {}

    if ficha.get("indicadores"):
        return ficha.get("titulo", ""), {
            clave: (datos or {}).get("titulo", clave)
            for clave, datos in ficha["indicadores"].items()
        }

    # El formato de la EPA: las claves están en las series de cada sexo.
    claves: set[str] = set()
    for magnitudes in (ficha.get("series") or {}).values():
        claves.update(magnitudes)
    return ficha.get("titulo", ""), {
        clave: TITULOS_EPA.get(clave, clave.replace("_", " ").capitalize())
        for clave in claves
    }


def altas(nombres: dict[str, str]) -> list[dict]:
    """La primera vez que apareció cada sección y cada indicador.

    Se recorre el historial de atrás hacia delante y se anota la primera vez
    que se ve cada clave. La fecha es la de ese commit, aunque sea un ensayo:
    el ensayo es, literalmente, cuando el dato entró en el repositorio. Lo que
    no se enseña es su asunto, que hablaría de probar un descargador y no de
    lo que el lector ha venido a ver.
    """
    bruto = git("log", "--reverse", f"--format={MARCA}%H{SEPARADOR}%aI",
                "--name-only", "--", "data/*/index.json", "data/*/espana.json")

    vistos: set[str] = set()
    secciones_vistas: set[str] = set()
    por_fecha: dict[str, dict] = {}

    for registro in bruto.split(MARCA):
        if not registro.strip():
            continue
        cabecera, *ficheros = registro.strip().split("\n")
        commit, fecha = cabecera.split(SEPARADOR)
        por_bloque: dict[str, dict] = {}
        # El índice va antes que el fichero de España a propósito: los dos
        # traen las mismas claves, pero sólo el índice trae el título de verdad
        # de cada indicador. Si ganara el otro, la página diría «Accidentes
        # itinere» en vez de «Accidentes in itinere».
        for ruta in sorted(ficheros, key=lambda r: not r.strip().endswith("/index.json")):
            ruta = ruta.strip()
            if not (ruta.endswith("/index.json") or ruta.endswith("/espana.json")):
                continue
            bloque = ruta.split("/")[1]
            titulo_bloque, indicadores = indicadores_en(commit, ruta)
            if not indicadores:
                continue

            nuevas = [(c, t) for c, t in sorted(indicadores.items())
                      if f"{bloque}/{c}" not in vistos]
            if not nuevas:
                continue
            vistos.update(f"{bloque}/{c}" for c, _ in nuevas)

            # Un commit puede tocar el índice y el fichero de España del mismo
            # bloque; las altas son las mismas y no se cuentan dos veces.
            junta = por_bloque.setdefault(bloque, {
                "id": bloque,
                # Manda el nombre con el que la sección aparece en el panel:
                # el bloque se llama «Contratos registrados» por dentro y
                # «Contratación» en el menú, y aquí interesa el del menú.
                "titulo": nombres.get(bloque) or titulo_bloque or bloque,
                "estreno": bloque not in secciones_vistas,
                "commit": commit[:7],
                "indicadores": [],
            })
            junta["indicadores"] += [t for _, t in nuevas]
            secciones_vistas.add(bloque)

        for bloque, ficha in por_bloque.items():
            dia = fecha[:10]
            entrada = por_fecha.setdefault(dia, {"fecha": dia, "secciones": {}})
            # Y varios commits del mismo día sobre el mismo bloque se juntan en
            # una sola línea: al lector le da igual en cuántas tandas entró.
            previa = entrada["secciones"].get(bloque)
            if previa:
                previa["indicadores"] += ficha["indicadores"]
                previa["estreno"] = previa["estreno"] or ficha["estreno"]
            else:
                entrada["secciones"][bloque] = ficha

    listado = []
    for entrada in por_fecha.values():
        secciones = sorted(entrada["secciones"].values(),
                           key=lambda s: (not s["estreno"], s["titulo"]))
        listado.append({"fecha": entrada["fecha"], "secciones": secciones})
    return sorted(listado, key=lambda e: e["fecha"], reverse=True)


def main() -> int:
    nombres = titulos()
    bruto = git("log", f"-{TOPE}", f"--format={FORMATO}", "--", "data/")
    lineas = bruto.split("\n")

    novedades = []
    for linea in lineas:
        if not linea.strip():
            continue
        commit, fecha, asunto = linea.split(SEPARADOR)
        if asunto.lower().startswith(DESARROLLO):
            continue
        secciones = cambios(commit)
        # Los ficheros del panel entero -portada, catálogo, cobertura- cambian
        # en cada actualización y no son una novedad en sí.
        secciones.pop("panel", None)
        secciones.pop("cobertura.json", None)
        for nombre in NO_SON_DATOS:
            secciones.pop(nombre, None)
        if not secciones:
            continue
        novedades.append({
            "commit": commit[:7],
            "fecha": fecha,
            "asunto": asunto,
            "secciones": [{"id": s, "titulo": nombres.get(s, s), "cambios": n}
                          for s, n in sorted(secciones.items(), key=lambda t: -t[1])],
        })

    listado_altas = altas(nombres)

    contenido = {
        "actualizado": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "repositorio": "https://github.com/Poloigithub/Panel_Datos",
        "altas": listado_altas,
        "novedades": novedades,
    }
    (DATOS / "cambios.json").write_text(
        json.dumps(contenido, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    cuantos = sum(len(s["indicadores"]) for e in listado_altas for s in e["secciones"])
    print(f"cambios: {cuantos} indicadores dados de alta en "
          f"{len(listado_altas)} días, y {len(novedades)} actualizaciones con datos")
    for entrada in listado_altas[:5]:
        print(f"  {entrada['fecha']} · " + ", ".join(
            ("estrena " if s["estreno"] else "amplía ") + s["titulo"]
            for s in entrada["secciones"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
