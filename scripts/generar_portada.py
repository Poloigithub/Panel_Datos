"""Compone `data/portada.json`: los titulares del panel y su calendario.

La portada era una lista de tarjetas sin una sola cifra, así que para saber qué
había de nuevo había que entrar en las nueve secciones. Este script recorre los
datos ya publicados y deja un fichero pequeño con lo último de cada sección, su
variación en un año y cada cuánto se actualiza.

Se ejecuta al final de la actualización, cuando los descargadores ya han
escrito lo suyo: no consulta ninguna API, sólo lee lo que hay en `data/`.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_series as motor  # noqa: E402
from secciones import AMBITOS, SECCIONES  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data"

def carga(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def hace_un_anyo(periodo: str) -> str | None:
    """'2026T2' → '2025T2'; '2026M08' → '2025M08'; '2023' → '2022'."""
    coincidencia = motor.PERIODO.match(periodo or "")
    if not coincidencia:
        return None
    anyo, letra, numero = coincidencia.groups()
    anterior = int(anyo) - 1
    return f"{anterior}{letra}{numero}" if letra else str(anterior)


def valores_de(contenido: dict, clave: str) -> dict[str, float]:
    if not contenido:
        return {}
    serie = (contenido.get("series", {}).get("ambos", {}) or {}).get(clave)
    if not serie:
        return {}
    return {periodo: valor for periodo, valor in zip(contenido["periodos"], serie)
            if valor is not None}


def compone(seccion: dict, ahora: str) -> dict | None:
    carpeta = DATOS / seccion["bloque"]
    indice = carga(carpeta / "index.json")
    if not indice:
        print(f"  {seccion['bloque']}: sin índice; se salta")
        return None

    contenidos = {}
    for ambito in indice.get("ambitos", []):
        contenido = carga(carpeta / ambito["fichero"])
        if contenido:
            contenidos[ambito["id"]] = contenido

    destacados = []
    for destacado in seccion["destacados"]:
        series = {a: valores_de(contenidos.get(a), destacado["clave"]) for a in AMBITOS}
        # El periodo de referencia es el último que tenga alguien: si una
        # provincia va con retraso, se dice con un hueco, no se rellena.
        periodos = {p for valores in series.values() for p in valores}
        if not periodos:
            print(f"  {seccion['bloque']}/{destacado['clave']}: sin datos")
            continue
        ultimo = max(periodos, key=motor.orden_periodo)
        previo = hace_un_anyo(ultimo)

        ficha = dict(destacado)
        ficha["periodo"] = ultimo
        ficha["valores"] = {a: series[a].get(ultimo) for a in AMBITOS}
        ficha["hace_un_anyo"] = {a: series[a].get(previo) for a in AMBITOS} if previo else {}
        if destacado.get("sobre"):
            totales = {a: valores_de(contenidos.get(a), destacado["sobre"]) for a in AMBITOS}
            ficha["sobre_valores"] = {a: totales[a].get(ultimo) for a in AMBITOS}
        destacados.append(ficha)

    if not destacados:
        return None
    return {
        "id": seccion["bloque"],
        "titulo": seccion["titulo"],
        "enlace": seccion["enlace"],
        "fuente": seccion["fuente"],
        "cadencia": seccion["cadencia"],
        "actualizado": indice.get("actualizado", ahora),
        "ultimo_periodo": indice.get("ultimo_periodo"),
        "destacados": destacados,
    }


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    secciones = [s for s in (compone(seccion, ahora) for seccion in SECCIONES) if s]

    portada = {
        "actualizado": ahora,
        "ambitos": [
            {"id": "espana", "nombre": "España", "etiqueta": "España"},
            {"id": "comunitat-valenciana", "nombre": "Comunitat Valenciana",
             "etiqueta": "C. Valenciana"},
            {"id": "castellon", "nombre": "Castellón", "etiqueta": "Castellón"},
        ],
        "secciones": secciones,
    }
    destino = DATOS / "portada.json"
    destino.write_text(json.dumps(portada, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
    print(f"escrito data/portada.json con {len(secciones)} secciones "
          f"({destino.stat().st_size // 1024} KB)")
    for seccion in secciones:
        print(f"  {seccion['titulo']}: {seccion['ultimo_periodo']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
