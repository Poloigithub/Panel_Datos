"""Descarga el bloque de salarios y rentas del trabajo.

El sondeo previo (`sondeos/salarios.md`) dejó claro lo que hay y lo que no:

- **Ninguna** de las seis operaciones salariales del INE -índice de coste
  laboral armonizado, encuestas de estructura salarial anual y cuatrienal,
  encuestas de coste laboral anual y trimestral- tiene la variable de
  provincias. El salario medio de Castellón no existe publicado.
- La Agencia Tributaria sí lo publica, pero en páginas HTML cuyos nombres de
  fichero son hashes que cambian cada año. No hay forma de atarse a eso sin
  atarse a que no lo toquen, así que queda fuera.
- El **Atlas de renta** sí baja a provincia, y reparte la renta de cada
  territorio según de dónde viene: salario, pensiones, prestaciones por
  desempleo, otras prestaciones y otros ingresos. No es el salario medio, pero
  dice qué parte de lo que entra en una casa viene del trabajo, y eso sí se
  puede comparar entre Castellón, la Comunitat y España.

Así que el bloque tiene dos mitades: lo del Atlas, con los tres ámbitos, y lo
de las encuestas salariales, que sólo existe por comunidad autónoma y lo dice
en la propia gráfica.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bloques_ine as bloques  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "config"

# Lo que no baja de comunidad autónoma. Se declara una vez y se reparte, para
# que añadir un indicador de estas encuestas no se olvide de decirlo.
SOLO_COMUNIDAD = ("castellon",)
AVISO_COMUNIDAD = ("El INE no publica esta encuesta por provincia: sólo por "
                   "comunidad autónoma y para el conjunto de España.")

BLOQUE = {
    "titulo": "Salarios y rentas del trabajo",
    "operaciones": ["ADRH", "EAES", "ETCL"],
    "indicadores": {
        # ---------------------------------------------- de dónde viene la renta
        "renta_salario": {
            "titulo": "Renta que viene del salario", "unidad": "%", "decimales": 2,
            "unidad_texto": "porcentaje de la renta bruta del territorio",
            "rango": (0, 100), "operacion": "ADRH",
            "busquedas": [{"fuente de ingreso: salario"}],
            "nota": "Del Atlas de renta, que sí llega a provincia. Dice qué parte "
                    "de lo que entra en los hogares viene del trabajo, no cuánto "
                    "se cobra.",
            "por_sexo": False,
        },
        "renta_pensiones": {
            "titulo": "Renta que viene de pensiones", "unidad": "%", "decimales": 2,
            "unidad_texto": "porcentaje de la renta bruta del territorio",
            "rango": (0, 100), "operacion": "ADRH",
            "busquedas": [{"fuente de ingreso: pensiones"}],
            "por_sexo": False,
        },
        "renta_desempleo": {
            "titulo": "Renta que viene de prestaciones por desempleo",
            "unidad": "%", "decimales": 2,
            "unidad_texto": "porcentaje de la renta bruta del territorio",
            "rango": (0, 100), "operacion": "ADRH",
            "busquedas": [{"fuente de ingreso: prestaciones por desempleo"}],
            "por_sexo": False,
        },
        "renta_otras_prestaciones": {
            "titulo": "Renta que viene de otras prestaciones",
            "unidad": "%", "decimales": 2,
            "unidad_texto": "porcentaje de la renta bruta del territorio",
            "rango": (0, 100), "operacion": "ADRH",
            "busquedas": [{"fuente de ingreso: otras prestaciones"}],
            "por_sexo": False,
        },
        # ------------------------------------------- lo que pagan por trabajar
        "salario_bruto": {
            "titulo": "Salario bruto anual", "unidad": "euros", "decimales": 0,
            "unidad_texto": "euros brutos al año por trabajador",
            "rango": (5_000, 120_000), "operacion": "EAES",
            "busquedas": [
                {"componente del salario bruto anual", "salario bruto"},
                {"ganancia media anual por trabajador"},
            ],
            "sin_ambitos": SOLO_COMUNIDAD, "nota": AVISO_COMUNIDAD,
            "por_sexo": True,
        },
        "brecha_salarial": {
            "titulo": "Brecha salarial entre mujeres y hombres",
            "unidad": "%", "decimales": 2,
            "unidad_texto": "cuánto menos cobra una mujer por cada 100 € de un hombre",
            "rango": (-50, 80), "operacion": "EAES",
            "busquedas": [{"brecha salarial entre mujeres y hombres"}],
            "sin_ambitos": SOLO_COMUNIDAD, "nota": AVISO_COMUNIDAD,
            "por_sexo": False,
        },
        "desigualdad_salarial": {
            "titulo": "Distancia entre los salarios altos y los bajos",
            "unidad": "ratio", "decimales": 2,
            "unidad_texto": "veces que la novena decila de la ganancia por hora "
                            "supera a la primera",
            "rango": (1, 20), "operacion": "EAES",
            "busquedas": [
                {"d9/d1 (9a decila dividida por la 1a decila de la ganancia por hora)"},
                {"d9/d1"},
            ],
            "sin_ambitos": SOLO_COMUNIDAD, "nota": AVISO_COMUNIDAD,
            "por_sexo": False,
        },
        "gini_salarial": {
            "titulo": "Índice de Gini de los salarios", "unidad": "índice",
            "decimales": 2,
            "unidad_texto": "a mayor valor, salarios más desiguales",
            "rango": (0, 100), "operacion": "EAES",
            "busquedas": [{"indice de gini"}],
            "sin_ambitos": SOLO_COMUNIDAD, "nota": AVISO_COMUNIDAD,
            "por_sexo": False,
        },
        "coste_salarial": {
            "titulo": "Coste salarial por trabajador y mes", "unidad": "euros",
            "decimales": 2,
            "unidad_texto": "euros al mes que le cuesta al empleador el salario",
            "rango": (500, 6_000), "operacion": "ETCL",
            "busquedas": [
                {"coste salarial total", "costes laborales", "euros"},
                {"coste salarial total", "euros"},
                {"coste salarial total"},
            ],
            "sin_ambitos": SOLO_COMUNIDAD, "nota": AVISO_COMUNIDAD,
            "por_sexo": False,
        },
    },
}

# El salario en euros constantes, que es la pregunta de verdad: si sube un 3 %
# con una inflación del 4 %, se cobra menos que antes.
DEFLACTABLES = ("salario_bruto", "coste_salarial")


def posproceso(ambito, series, origen):
    base = bloques.deflacta(series, bloques.descarga_deflactor(ambito), origen,
                            DEFLACTABLES)
    if base:
        print(f"      salarios en euros constantes de {base}")


def fichas_derivadas(por_ambito: dict) -> dict:
    """Ficha de las series en euros constantes, a partir de su nominal."""
    fichas = {}
    publicadas = {clave for series in por_ambito.values()
                  for magnitudes in series.values() for clave in magnitudes}
    for clave in sorted(publicadas):
        if not clave.endswith("_real"):
            continue
        origen = BLOQUE["indicadores"].get(clave[: -len("_real")])
        if not origen:
            continue
        fichas[clave] = {
            "titulo": origen["titulo"] + " (euros constantes)",
            "unidad": origen["unidad"], "decimales": origen["decimales"],
            "unidad_texto": "euros del último año disponible, descontada la inflación",
            "por_sexo": origen["por_sexo"],
            "nota": origen.get("nota"),
            "nominal": clave[: -len("_real")],
        }
    return fichas


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    CONFIG.mkdir(parents=True, exist_ok=True)
    print("\n=== Salarios y rentas del trabajo ===")
    por_ambito, procedencias, faltantes = bloques.descarga_bloque(
        "salarios", BLOQUE, posproceso)
    bloques.escribe_bloque("salarios", BLOQUE, por_ambito, ahora, RAIZ,
                           fichas_derivadas(por_ambito))

    (CONFIG / "series-salarios.json").write_text(
        json.dumps(procedencias, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if faltantes:
        print(f"\nNo se ha encontrado serie para {len(faltantes)} combinaciones:")
        for f in faltantes:
            print(f"  - {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
