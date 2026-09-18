"""Bajas laborales: ¿hay fuente oficial, y con cuánto detalle?

«Baja laboral» en las estadísticas se llama **incapacidad temporal** (IT), y
hay al menos cuatro sitios donde podría estar. No se parecen en nada, así que
conviene ver los cuatro antes de elegir:

1. **El INE**, que en la Encuesta Trimestral de Coste Laboral publica las horas
   no trabajadas por incapacidad temporal. Sería absentismo medido en horas por
   trabajador y mes, trimestral y por comunidad autónoma. Aquí se busca sin
   dar por hecho el nombre de la operación: se pide la lista entera al INE y se
   mira cuáles hablan de coste laboral, absentismo o incapacidad.

2. **El anuario del Ministerio de Trabajo**, del que el panel ya baja la
   afiliación, los convenios, las huelgas y los despidos. Si tiene un capítulo
   de prestaciones con la IT dentro, sería lo más barato de todo: la
   maquinaria está escrita.

3. **La Seguridad Social**, que es quien paga la prestación y quien lleva la
   cuenta de los procesos. Cuando se sondearon las enfermedades profesionales,
   el ministerio remitía precisamente aquí.

4. **datos.gob.es**, el catálogo oficial de datos abiertos, que sirve para
   descubrir lo que no se sabe buscar: se le pregunta por «incapacidad
   temporal» y él dice quién lo publica.

Lo que decide cuál entra no es sólo que exista, sino **hasta dónde baja**: este
panel enseña siempre España, la Comunitat y Castellón, y una fuente sin
provincia hay que decirlo desde el principio.
"""

from __future__ import annotations

import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import ine_api  # noqa: E402
import ine_series as motor  # noqa: E402

SALIDA = RAIZ / "sondeos"

NAVEGADOR = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9",
}

ANUARIO = "https://www.mites.gob.es/ficheros/ministerio/estadisticas/anuarios"

# Lo que se busca en el nombre de una operación o de una serie.
PISTAS = ("incapacidad", "coste laboral", "absentismo", "no trabajadas",
          "jornada laboral", "baja ")

AMBITOS = [("España", "349:16473"), ("Comunitat Valenciana", "70:9006"),
           ("Castellón", "115:13")]


def pide(url: str, intentos: int = 3, limite: int = 20_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(
                    peticion, timeout=120,
                    context=ssl.create_default_context()) as respuesta:
                return respuesta.status, respuesta.read(limite), ""
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(400), ""
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * numero)
    return 0, b"", ultimo


def suena(texto: str) -> bool:
    bajo = (texto or "").lower()
    return any(p in bajo for p in PISTAS)


def puerta_ine(l: list[str]) -> None:
    l += ["## 1. El INE: ¿qué operación habla de esto?", ""]
    try:
        operaciones = ine_api.get("OPERACIONES_DISPONIBLES")
    except Exception as exc:  # noqa: BLE001
        l.append(f"- no se pudo listar las operaciones: {exc}")
        return
    l.append(f"- {len(operaciones)} operaciones disponibles")

    interesantes = [o for o in operaciones if suena(o.get("Nombre", ""))]
    l.append(f"- las que suenan a esto ({len(interesantes)}):")
    for o in interesantes:
        l.append(f"    · {o.get('Codigo')} · {o.get('Id')} · {o.get('Nombre')}")
    l.append("")

    # De las prometedoras, qué series tienen y hasta dónde bajan.
    for o in interesantes[:3]:
        codigo = o.get("Codigo")
        l += [f"### {codigo} · {o.get('Nombre')}", ""]
        for nombre_ambito, filtro in AMBITOS:
            try:
                indice = motor.indexa_por_segmentos(codigo, filtro)
            except Exception as exc:  # noqa: BLE001
                l.append(f"- **{nombre_ambito}**: no se pudo indexar ({exc})")
                continue
            todas = [s for grupo in indice.values() for s in grupo]
            casan = [s for s in todas if suena(s.get("Nombre", ""))]
            l.append(f"- **{nombre_ambito}**: {len(todas)} series, "
                     f"{len(casan)} mencionan lo que se busca")
            for s in casan[:14]:
                l.append(f"    · {s.get('Nombre')}")
            if len(casan) > 14:
                l.append(f"    · … y {len(casan) - 14} más")
        l.append("")


def puerta_anuario(l: list[str]) -> None:
    l += ["## 2. El anuario del Ministerio de Trabajo", ""]
    # El índice del anuario dice qué capítulos hay ese año.
    for anyo in (2024, 2023):
        for ruta in (f"{ANUARIO}/{anyo}/index.htm",
                     f"{ANUARIO}/{anyo}/",
                     f"{ANUARIO}/{anyo}/indice.htm"):
            estado, datos, fallo = pide(ruta, intentos=2, limite=4_000_000)
            l.append(f"- `{ruta}` → {estado}"
                     + (f" · {fallo}" if fallo else f" · {len(datos)} bytes"))
            if estado == 200 and len(datos) > 500:
                html = datos.decode("utf-8", "replace")
                enlaces = sorted(set(re.findall(
                    r'href="\.?/?([A-Za-zÁÉÍÓÚÑ0-9_-]+)/[^"]*"', html)))
                l.append(f"    · carpetas enlazadas: {enlaces[:40]}")
                titulos = [t.strip() for t in re.findall(r">([^<>]{6,80})<", html)]
                suenan = [t for t in titulos if suena(t)]
                l.append(f"    · títulos que suenan a esto: {suenan[:10]}")
                break
        else:
            continue
        break
    l.append("")


def puerta_seguridad_social(l: list[str]) -> None:
    l += ["## 3. La Seguridad Social", ""]
    puertas = [
        "https://www.seg-social.es/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST45",
        "https://www.seg-social.es/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas",
    ]
    for url in puertas:
        estado, datos, fallo = pide(url, intentos=2, limite=4_000_000)
        l.append(f"- `{url[:95]}…` → {estado}"
                 + (f" · {fallo}" if fallo else f" · {len(datos)} bytes"))
        if estado == 200 and len(datos) > 500:
            html = datos.decode("utf-8", "replace")
            hojas = re.findall(r'href="([^"]+\.(?:xlsx?|csv))"', html, re.I)
            l.append(f"    · ficheros de datos enlazados: {len(hojas)}")
            for h in hojas[:10]:
                l.append(f"        {h[:110]}")
            titulos = [t.strip() for t in re.findall(r">([^<>]{8,90})<", html)]
            suenan = sorted({t for t in titulos if suena(t)})
            l.append(f"    · títulos que suenan a esto ({len(suenan)}):")
            for t in suenan[:12]:
                l.append(f"        {t}")
    l.append("")


def puerta_catalogo(l: list[str]) -> None:
    l += ["## 4. datos.gob.es: ¿quién lo publica?", ""]
    for palabra in ("incapacidad-temporal", "absentismo"):
        url = ("https://datos.gob.es/apidata/catalog/dataset/title/"
               + palabra + "?_format=json&_pageSize=20&_page=0")
        estado, datos, fallo = pide(url, intentos=2, limite=8_000_000)
        l.append(f"### «{palabra}» → {estado}"
                 + (f" · {fallo}" if fallo else ""))
        l.append("")
        if estado != 200:
            continue
        try:
            cuerpo = json.loads(datos.decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            l.append(f"- no es JSON legible: {exc}")
            continue
        items = (cuerpo.get("result") or {}).get("items") or []
        l.append(f"- {len(items)} conjuntos de datos")
        for item in items[:12]:
            titulo = item.get("title")
            if isinstance(titulo, list):
                titulo = next((t.get("_value") for t in titulo
                               if isinstance(t, dict)), titulo)
            elif isinstance(titulo, dict):
                titulo = titulo.get("_value")
            editor = item.get("publisher")
            if isinstance(editor, dict):
                editor = editor.get("notation") or editor.get("_about")
            l.append(f"    · {str(titulo)[:95]}")
            l.append(f"      editor: {str(editor)[:80]}")
            distribuciones = item.get("distribution") or []
            if isinstance(distribuciones, dict):
                distribuciones = [distribuciones]
            formatos = set()
            enlaces = []
            for d in distribuciones[:6]:
                if not isinstance(d, dict):
                    continue
                f = d.get("format")
                if isinstance(f, dict):
                    f = f.get("value") or f.get("_value")
                formatos.add(str(f)[:24])
                if d.get("accessURL"):
                    enlaces.append(str(d["accessURL"])[:100])
            if formatos:
                l.append(f"      formatos: {sorted(formatos)}")
            for e in enlaces[:2]:
                l.append(f"      {e}")
        l.append("")


def main() -> None:
    l = ["# Bajas laborales: ¿hay fuente oficial y con cuánto detalle?", "",
         "«Baja laboral» se llama **incapacidad temporal** en las estadísticas.",
         "Se prueban cuatro puertas porque no se parecen en nada y la que valga",
         "depende tanto de que exista como de hasta dónde baje: este panel",
         "enseña siempre España, la Comunitat y Castellón.", ""]
    for puerta in (puerta_ine, puerta_anuario, puerta_seguridad_social,
                   puerta_catalogo):
        try:
            puerta(l)
        except Exception as exc:  # noqa: BLE001
            l += [f"- **la puerta reventó**: {type(exc).__name__}: {exc}", ""]

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "bajas.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
