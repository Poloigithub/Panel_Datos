"""Qué cambió y cuándo, sacado del historial de git.

Cada actualización de datos es un commit, así que el repositorio ya guarda
cuándo cambió cada cifra sin que haya que llevar un registro aparte. Esto lo
convierte en algo que se pueda leer desde la web: qué secciones cambiaron cada
día y cuántas cifras se tocaron.

Incluye las revisiones de los propios organismos, que es lo interesante: el INE
corrige series hacia atrás con frecuencia y eso no suele verse en ningún sitio.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secciones import SECCIONES  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data"
TOPE = 80  # commits a mirar; más atrás deja de interesar

# Los ensayos y volcados son commits de desarrollo -probar un descargador
# nuevo contra la fuente de verdad- y no novedades para quien consulta el
# panel: la cifra que dejan es la misma que traerá la actualización siguiente.
DESARROLLO = ("ensayo de ", "volcado de ", "prueba de ")

# Un tabulador, y no el separador de registro que parecería lo suyo: el
# `splitlines()` de Python también parte por \x1e, así que cada commit salía
# convertido en tres líneas.
SEPARADOR = "\t"
FORMATO = SEPARADOR.join(["%H", "%aI", "%s"])


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

    contenido = {
        "actualizado": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "repositorio": "https://github.com/Poloigithub/Panel_Datos",
        "novedades": novedades,
    }
    (DATOS / "novedades.json").write_text(
        json.dumps(contenido, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"novedades: {len(novedades)} actualizaciones con datos")
    for novedad in novedades[:5]:
        print(f"  {novedad['fecha'][:10]} · {novedad['asunto'][:60]} · "
              + ", ".join(s["titulo"] for s in novedad["secciones"][:3]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
