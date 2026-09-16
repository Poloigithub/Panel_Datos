"""Descarga del INE los bloques sociodemográficos del panel.

Tres bloques, cada uno de una operación distinta:

- población y estructura (ECP, Estadística Continua de Población, e IDB)
- natalidad, mortalidad y migración (IDB, Indicadores Demográficos Básicos)
- renta y desigualdad (ADRH, Atlas de Distribución de Renta de los Hogares)

Cada indicador se declara por los segmentos que deben aparecer en el nombre de
su serie. Como el INE no siempre usa la misma etiqueta para lo mismo, se
admiten varias formulaciones alternativas y gana la primera que da datos.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bloques_ine as bloques  # noqa: E402
import ine_series as motor  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "config"

# Un indicador: cómo se llama en el panel, qué unidad tiene y por qué
# combinaciones de segmentos buscarlo (la primera que dé datos, gana).
BLOQUES = {
    "poblacion": {
        "titulo": "Población y estructura",
        "operaciones": ["ECP", "CP", "IDB", "ADRH"],
        "indicadores": {
            "poblacion": {
                "titulo": "Población", "unidad": "personas", "decimales": 0,
                "rango": (10000, 100000000),
                "operacion": ["ECP", "CP"],
                "busquedas": [{"poblacion"}],
                "por_sexo": True,
            },
            "edad_media": {
                "titulo": "Edad media", "unidad": "años", "decimales": 1,
                "rango": (20, 60),
                "operacion": "IDB",
                "busquedas": [
                    {"indicadores de crecimiento y estructura de la poblacion", "edad media de la poblacion"},
                    {"edad media de la poblacion"},
                ],
                "por_sexo": True,
            },
            # El INE publica esta proporción a partir de los 70 años, no de
            # los 65: no hay serie de «65 y más» por provincia.
            "mayores_70": {
                "titulo": "Población de 70 y más años", "unidad": "%", "decimales": 2,
                "unidad_texto": "porcentaje de la población",
                "rango": (0, 50),
                "operacion": "IDB",
                "busquedas": [
                    {"indicadores de crecimiento y estructura de la poblacion",
                     "proporcion de personas mayores de cierta edad", "70 y mas anos"},
                    {"proporcion de personas mayores de cierta edad", "70 y mas anos"},
                ],
                "por_sexo": False,
            },
            # La proporción de extranjeros de IDB sólo existe desglosada por
            # edad; el Atlas de renta sí publica el porcentaje de población
            # española, del que sale el complementario.
            "espanoles": {
                "titulo": "Población de nacionalidad española", "unidad": "%", "decimales": 2,
                "rango": (0, 100),
                "operacion": "ADRH",
                "busquedas": [{"porcentaje de poblacion espanola"}],
                "por_sexo": False,
            },
            "crecimiento": {
                "titulo": "Crecimiento de la población", "unidad": "por mil", "decimales": 2,
                "unidad_texto": "por cada mil habitantes",
                "rango": (-100, 100),
                "operacion": "IDB",
                "busquedas": [
                    {"indicadores de crecimiento y estructura de la poblacion", "crecimiento de la poblacion"},
                    {"crecimiento de la poblacion"},
                ],
                "por_sexo": False,
            },
        },
    },
    "demografia": {
        "titulo": "Natalidad, mortalidad y migración",
        "operaciones": ["IDB"],
        "indicadores": {
            "esperanza_vida": {
                "titulo": "Esperanza de vida al nacer", "unidad": "años", "decimales": 2,
                "operacion": "IDB",
                "busquedas": [{"mortalidad", "esperanza de vida", "0 anos"}],
                "rango": (50, 100),
                "por_sexo": True,
            },
            "mortalidad_infantil": {
                "rango": (0, 100),
                "unidad_texto": "defunciones por cada mil nacidos",
                "titulo": "Mortalidad infantil (menores de 5 años)", "unidad": "por mil",
                "decimales": 2, "operacion": "IDB",
                "busquedas": [{"mortalidad", "tasa de mortalidad infantil de menores de 5 anos"}],
                "por_sexo": True,
            },
            "edad_maternidad": {
                # El INE sólo la publica por orden de nacimiento, así que se
                # toma la del primer hijo, que es la que marca la tendencia.
                "titulo": "Edad media al primer hijo", "unidad": "años", "decimales": 2,
                "rango": (20, 45),
                "operacion": "IDB",
                "busquedas": [{"fecundidad", "edad media a la maternidad", "primero"}],
                "por_sexo": False,
            },
            "saldo_migratorio": {
                "titulo": "Saldo migratorio", "unidad": "por mil", "decimales": 2,
                "unidad_texto": "por cada mil habitantes",
                "operacion": "IDB",
                "busquedas": [
                    {"indicadores de crecimiento y estructura de la poblacion", "saldo migratorio"},
                ],
                "por_sexo": False,
            },
            "nacidos_por_defuncion": {
                "unidad_texto": "nacidos por cada mil defunciones",
                "titulo": "Nacidos por cada 1.000 defunciones", "unidad": "por mil",
                "decimales": 1, "operacion": "IDB",
                "busquedas": [
                    {"indicadores de crecimiento y estructura de la poblacion",
                     "nacidos por cada 1000 defunciones"},
                    {"nacidos por cada 1000 defunciones"},
                ],
                "por_sexo": False,
            },
        },
    },
    "precios": {
        "titulo": "Precios",
        "operaciones": ["IPC"],
        # El IPC arrastra tramos anteriores al enlace de la base actual, con
        # valores en otra escala que no son comparables con los de hoy. La
        # serie enlazada vigente arranca en 2002.
        "desde": 2002,
        "indicadores": {
            "ipc_general": {
                "titulo": "IPC, índice general", "unidad": "índice", "decimales": 2,
                "unidad_texto": "índice, base 2021 = 100",
                "rango": (50, 200),
                "operacion": "IPC",
                "busquedas": [{"indice general", "indice"}],
                "por_sexo": False,
            },
            "ipc_variacion": {
                "titulo": "Inflación interanual", "unidad": "%", "decimales": 2,
                "unidad_texto": "variación del IPC respecto al mismo mes del año anterior",
                "rango": (-30, 60),
                "operacion": "IPC",
                "busquedas": [{"indice general", "variacion anual"}],
                "por_sexo": False,
            },
            "ipc_alimentos": {
                "titulo": "Alimentos", "unidad": "%", "decimales": 2,
                "unidad_texto": "variación interanual del grupo",
                "rango": (-30, 60),
                "operacion": "IPC",
                "busquedas": [
                    {"alimentos y bebidas no alcoholicas", "variacion anual"},
                    {"alimentos", "variacion anual"},
                ],
                "por_sexo": False,
            },
            "ipc_transporte": {
                "titulo": "Transporte", "unidad": "%", "decimales": 2,
                "unidad_texto": "variación interanual del grupo",
                "rango": (-40, 60),
                "operacion": "IPC",
                "busquedas": [{"transporte", "variacion anual"}],
                "por_sexo": False,
            },
        },
    },
    "renta": {
        "titulo": "Renta y desigualdad",
        "operaciones": ["ADRH"],
        "indicadores": {
            "renta_persona": {
                "titulo": "Renta neta media por persona", "unidad": "euros", "decimales": 0,
                "operacion": "ADRH",
                "busquedas": [{"renta neta media por persona"}],
                "por_sexo": False,
            },
            "renta_hogar": {
                "titulo": "Renta neta media por hogar", "unidad": "euros", "decimales": 0,
                "operacion": "ADRH",
                "busquedas": [{"renta neta media por hogar"}],
                "por_sexo": False,
            },
            "renta_uc": {
                "titulo": "Renta media por unidad de consumo", "unidad": "euros", "decimales": 0,
                "operacion": "ADRH",
                "busquedas": [{"media de la renta por unidad de consumo"}],
                "por_sexo": False,
            },
            "gini": {
                "titulo": "Índice de Gini", "unidad": "índice", "decimales": 2,
                "unidad_texto": "índice de 0 a 100; a mayor valor, más desigualdad",
                "rango": (0, 100),
                "operacion": "ADRH",
                "busquedas": [{"indice de gini"}],
                "por_sexo": False,
            },
            "p80p20": {
                "titulo": "Distribución de la renta P80/P20", "unidad": "ratio", "decimales": 2,
                "unidad_texto": "veces que la renta del 20 % más rico supera a la del 20 % más pobre",
                "operacion": "ADRH",
                "busquedas": [{"distribucion de la renta p80/p20"}],
                "por_sexo": False,
            },
            "bajo_60": {
                "titulo": "Población bajo el 60 % de la renta mediana", "unidad": "%", "decimales": 2,
                "unidad_texto": "porcentaje de la población",
                "operacion": "ADRH",
                "busquedas": [
                    {"poblacion con ingresos por unidad de consumo por debajo 60% de la mediana"},
                ],
                "por_sexo": True,
            },
            "tamano_hogar": {
                "titulo": "Tamaño medio del hogar", "unidad": "personas", "decimales": 2,
                "operacion": "ADRH",
                "busquedas": [{"tamano medio del hogar"}],
                "por_sexo": False,
            },
            "hogares_unipersonales": {
                "titulo": "Hogares unipersonales", "unidad": "%", "decimales": 2,
                "operacion": "ADRH",
                "busquedas": [{"porcentaje de hogares unipersonales"}],
                "por_sexo": False,
            },
        },
    },
}

# Indicadores de renta que tienen versión en euros constantes.
DEFLACTABLES = ("renta_persona", "renta_hogar", "renta_uc")


def descarga_deflactor(ambito: dict) -> dict[str, float]:
    """Media anual del IPC del ámbito, que es lo que deflacta una serie anual.

    No se publica como indicador: sólo sirve para convertir la renta a euros
    constantes, y mezclar una serie anual con el IPC mensual llenaría el
    bloque de precios de huecos.
    """
    indice = motor.indexa_por_segmentos("IPC", ambito["filtro"])
    for territorio in [ambito["segmento"]] + ambito.get("segmentos_alternativos", []):
        valores, _ = motor.resuelve(
            indice, {territorio, "indice general", "media anual"},
            f"deflactor/{ambito['id']}", avisar=False)
        if valores:
            # Sólo interesan los años completos, en formato «2023».
            return {p: v for p, v in valores.items() if p.isdigit()}
    print(f"      sin deflactor para {ambito['id']}: la renta se queda en euros corrientes")
    return {}


def deflacta(series: dict, deflactor: dict[str, float], procedencia: dict) -> str | None:
    """Añade las series de renta en euros del último año disponible.

    Renta real = renta nominal × (IPC del año base / IPC del año del dato). El
    año base es el último con IPC, de modo que la serie se lee «en euros de
    hoy», que es como la gente piensa el dinero.
    """
    if not deflactor:
        return None
    base = max(deflactor, key=lambda a: int(a))
    if not deflactor.get(base):
        return None

    convertidas = 0
    for sexo, magnitudes in list(series.items()):
        for clave in DEFLACTABLES:
            nominal = magnitudes.get(clave)
            if not nominal:
                continue
            real = {
                periodo: round(valor * deflactor[base] / deflactor[periodo], 2)
                for periodo, valor in nominal.items()
                if deflactor.get(periodo)
            }
            if not real:
                continue
            magnitudes[clave + "_real"] = real
            procedencia.setdefault(sexo, {})[clave + "_real"] = [
                f"deflactado con el IPC medio anual, base {base}"
            ]
            convertidas += 1
    return base if convertidas else None


def fichas_derivadas(por_ambito: dict, bloque: dict) -> dict:
    """Ficha de las series que no se descargan sino que se calculan.

    Las de euros constantes se componen a partir de la del indicador nominal
    del que salen, para que digan lo mismo salvo la unidad.
    """
    fichas = {}
    publicados = {clave for series in por_ambito.values()
                  for magnitudes in series.values() for clave in magnitudes}
    for clave in sorted(publicados):
        if not clave.endswith("_real"):
            continue
        origen = bloque["indicadores"].get(clave[: -len("_real")])
        if not origen:
            continue
        fichas[clave] = {
            "titulo": origen["titulo"] + " (euros constantes)",
            "unidad": origen["unidad"],
            "unidad_texto": "euros del último año disponible, descontada la inflación",
            "decimales": origen["decimales"],
            "por_sexo": origen["por_sexo"],
            "nominal": clave[: -len("_real")],
        }
    return fichas


def posproceso_renta(ambito, series, origen):
    base = deflacta(series, descarga_deflactor(ambito), origen)
    if base:
        print(f"      renta en euros constantes de {base}")


def posproceso_poblacion(ambito, series, origen):
    """La población total es la suma de los dos sexos.

    Si el INE no publica la serie agregada para un ámbito, se compone en vez
    de dejar el hueco.
    """
    hombres = series.get("hombres", {}).get("poblacion")
    mujeres = series.get("mujeres", {}).get("poblacion")
    if not hombres or not mujeres:
        return
    if series.setdefault("ambos", {}).get("poblacion"):
        return
    compuesta = {periodo: hombres[periodo] + mujeres[periodo]
                 for periodo in hombres if periodo in mujeres}
    if compuesta:
        series["ambos"]["poblacion"] = compuesta
        origen.setdefault("ambos", {})["poblacion"] = ["derivado:hombres+mujeres"]
        print(f"      poblacion/ambos: {len(compuesta)} periodos sumando hombres y mujeres")


POSPROCESOS = {"renta": posproceso_renta, "poblacion": posproceso_poblacion}


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    CONFIG.mkdir(parents=True, exist_ok=True)
    procedencias: dict[str, dict] = {}
    faltantes: list[str] = []

    for nombre, bloque in BLOQUES.items():
        print(f"\n=== {bloque['titulo']} ===")
        por_ambito, procedencia, sin_serie = bloques.descarga_bloque(
            nombre, bloque, POSPROCESOS.get(nombre))
        procedencias[nombre] = procedencia
        faltantes += sin_serie
        bloques.escribe_bloque(nombre, bloque, por_ambito, ahora, RAIZ,
                               fichas_derivadas(por_ambito, bloque))

    (CONFIG / "series-sociodemografia.json").write_text(
        json.dumps(procedencias, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if faltantes:
        print(f"\nNo se ha encontrado serie para {len(faltantes)} combinaciones:")
        for f in faltantes:
            print(f"  - {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
