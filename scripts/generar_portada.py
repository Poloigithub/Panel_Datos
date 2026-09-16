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

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data"

AMBITOS = ["espana", "comunitat-valenciana", "castellon"]

# Qué se enseña de cada sección y cada cuánto se revisa. La cadencia es la de
# la fuente: la tarea de actualización mira todos los días, pero un dato anual
# no cambia por mirarlo más.
SECCIONES = [
    {
        "bloque": "epa", "enlace": "mercado-laboral.html", "titulo": "Mercado laboral",
        "fuente": "EPA · INE",
        "cadencia": "Trimestral. El INE publica a finales de enero, abril, julio y octubre.",
        "destacados": [
            {"clave": "tasa_paro", "titulo": "Tasa de paro", "unidad": "%", "decimales": 2},
            {"clave": "ocupados", "titulo": "Ocupados", "unidad": "miles de personas",
             "decimales": 1},
        ],
    },
    {
        "bloque": "paro-registrado", "enlace": "paro-registrado.html",
        "titulo": "Paro registrado", "fuente": "SEPE",
        "cadencia": "Mensual. El SEPE publica en los primeros días de cada mes.",
        "destacados": [
            {"clave": "paro_total", "titulo": "Personas apuntadas al paro",
             "unidad": "personas", "decimales": 0},
        ],
    },
    {
        "bloque": "contratos", "enlace": "contratos.html", "titulo": "Contratación",
        "fuente": "SEPE",
        "cadencia": "Mensual, a la vez que el paro registrado.",
        "destacados": [
            {"clave": "contratos_total", "titulo": "Contratos del mes",
             "unidad": "contratos", "decimales": 0},
            {"clave": "contratos_indefinidos", "titulo": "De ellos, indefinidos",
             "unidad": "contratos", "decimales": 0, "sobre": "contratos_total"},
        ],
    },
    {
        "bloque": "precios", "enlace": "precios.html", "titulo": "Precios",
        "fuente": "IPC · INE",
        "cadencia": "Mensual. El INE publica hacia la mitad del mes siguiente.",
        "destacados": [
            {"clave": "ipc_variacion", "titulo": "Inflación interanual", "unidad": "%",
             "decimales": 2},
        ],
    },
    {
        "bloque": "vivienda", "enlace": "vivienda.html", "titulo": "Vivienda",
        "fuente": "INE y CGPJ",
        "cadencia": "Mensual las compraventas y las hipotecas; trimestral el precio "
                    "y los lanzamientos; anual el alquiler.",
        "destacados": [
            {"clave": "compraventas", "titulo": "Compraventas de vivienda",
             "unidad": "operaciones", "decimales": 0},
            # Los lanzamientos no entran aquí a propósito: sus últimos
            # trimestres son provisionales y un titular de «−72 % en un año»
            # sería, en parte, el retraso de los juzgados en informar.
            {"clave": "hipoteca_media", "titulo": "Hipoteca media", "unidad": "euros",
             "decimales": 0},
        ],
    },
    {
        "bloque": "renta", "enlace": "renta.html", "titulo": "Renta y desigualdad",
        "fuente": "Atlas de Distribución de Renta · INE",
        "cadencia": "Anual, con unos dos años de retraso.",
        "destacados": [
            {"clave": "renta_persona", "titulo": "Renta neta media por persona",
             "unidad": "euros", "decimales": 0},
        ],
    },
    {
        "bloque": "poblacion", "enlace": "poblacion.html", "titulo": "Población",
        "fuente": "Estadística Continua de Población · INE",
        "cadencia": "Trimestral.",
        "destacados": [
            {"clave": "poblacion", "titulo": "Población", "unidad": "personas",
             "decimales": 0},
        ],
    },
    {
        "bloque": "demografia", "enlace": "demografia.html",
        "titulo": "Natalidad, mortalidad y migración",
        "fuente": "Indicadores Demográficos Básicos · INE",
        "cadencia": "Anual.",
        "destacados": [
            {"clave": "saldo_migratorio", "titulo": "Saldo migratorio", "unidad": "por mil",
             "decimales": 2},
        ],
    },
]


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
