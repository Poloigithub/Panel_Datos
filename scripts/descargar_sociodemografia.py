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
import ine_series as motor  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data"
CONFIG = RAIZ / "config"

VAR_NACIONAL, VAR_CCAA, VAR_PROVINCIAS = 349, 70, 115

AMBITOS = [
    {"id": "espana", "nombre": "España", "tipo": "Nacional",
     "filtro": f"{VAR_NACIONAL}:16473", "segmento": "total nacional"},
    {"id": "comunitat-valenciana", "nombre": "Comunitat Valenciana", "tipo": "Comunidad autónoma",
     "filtro": f"{VAR_CCAA}:9006", "segmento": "comunitat valenciana"},
    {"id": "castellon", "nombre": "Castellón", "tipo": "Provincia",
     "filtro": f"{VAR_PROVINCIAS}:13", "segmento": "castellon/castello"},
]

# Un indicador: cómo se llama en el panel, qué unidad tiene y por qué
# combinaciones de segmentos buscarlo (la primera que dé datos, gana).
BLOQUES = {
    "poblacion": {
        "titulo": "Población y estructura",
        "operaciones": ["ECP", "IDB", "ADRH"],
        "indicadores": {
            "poblacion": {
                "titulo": "Población", "unidad": "personas", "decimales": 0,
                "operacion": "ECP",
                "busquedas": [{"poblacion"}],
                "por_sexo": True,
            },
            "edad_media": {
                "titulo": "Edad media", "unidad": "años", "decimales": 1,
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
                "operacion": "IDB",
                "busquedas": [
                    {"proporcion de personas mayores de cierta edad", "70 y mas anos"},
                ],
                "por_sexo": False,
            },
            # La proporción de extranjeros de IDB sólo existe desglosada por
            # edad; el Atlas de renta sí publica el porcentaje de población
            # española, del que sale el complementario.
            "espanoles": {
                "titulo": "Población de nacionalidad española", "unidad": "%", "decimales": 2,
                "operacion": "ADRH",
                "busquedas": [{"porcentaje de poblacion espanola"}],
                "por_sexo": False,
            },
            "crecimiento": {
                "titulo": "Crecimiento de la población", "unidad": "%", "decimales": 2,
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
                "busquedas": [
                    {"mortalidad", "esperanza de vida", "0 anos"},
                    {"mortalidad", "esperanza de vida", "menos de 1 ano"},
                    {"mortalidad", "esperanza de vida", "al nacimiento"},
                ],
                "por_sexo": True,
            },
            "mortalidad_infantil": {
                "titulo": "Mortalidad infantil (menores de 5 años)", "unidad": "por mil",
                "decimales": 2, "operacion": "IDB",
                "busquedas": [{"mortalidad", "tasa de mortalidad infantil de menores de 5 anos"}],
                "por_sexo": True,
            },
            "edad_maternidad": {
                # El INE sólo la publica por orden de nacimiento, así que se
                # toma la del primer hijo, que es la que marca la tendencia.
                "titulo": "Edad media al primer hijo", "unidad": "años", "decimales": 2,
                "operacion": "IDB",
                "busquedas": [{"fecundidad", "edad media a la maternidad", "primero"}],
                "por_sexo": False,
            },
            "saldo_migratorio": {
                "titulo": "Saldo migratorio", "unidad": "por mil", "decimales": 2,
                "operacion": "IDB",
                "busquedas": [
                    {"indicadores de crecimiento y estructura de la poblacion", "saldo migratorio"},
                ],
                "por_sexo": False,
            },
            "nacidos_por_defuncion": {
                "titulo": "Nacidos por cada 1.000 defunciones", "unidad": "por mil",
                "decimales": 1, "operacion": "IDB",
                "busquedas": [{"nacidos por cada 1000 defunciones"}],
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
            "renta_mediana_hogar": {
                "titulo": "Renta mediana por hogar", "unidad": "euros", "decimales": 0,
                "operacion": "ADRH",
                "busquedas": [{"renta mediana por hogar"}],
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
                "operacion": "ADRH",
                "busquedas": [{"indice de gini"}],
                "por_sexo": False,
            },
            "p80p20": {
                "titulo": "Distribución de la renta P80/P20", "unidad": "ratio", "decimales": 2,
                "operacion": "ADRH",
                "busquedas": [{"distribucion de la renta p80/p20"}],
                "por_sexo": False,
            },
            "bajo_60": {
                "titulo": "Población bajo el 60 % de la renta mediana", "unidad": "%", "decimales": 2,
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

# Cómo se llama cada sexo en cada operación: el INE alterna «Total» y
# «Ambos sexos» según la estadística.
SEXOS = {
    "ambos": {"total", "ambos sexos"},
    "hombres": {"hombres", "varones"},
    "mujeres": {"mujeres"},
}


def busca(indice, ambito, indicador, alias_sexo, etiqueta):
    """Primera formulación que dé datos, de entre las declaradas.

    Se prueban los alias del sexo y, al final, la variante sin sexo: hay
    operaciones (el Atlas de renta, por ejemplo) cuyas series no llevan esa
    variable en el nombre.
    """
    intentos = [{a} for a in sorted(alias_sexo)] + [set()]
    for busqueda in indicador["busquedas"]:
        for alias in intentos:
            obligatorio = set(busqueda) | {ambito["segmento"]} | alias
            valores, usados = motor.resuelve(indice, obligatorio, etiqueta, avisar=False)
            if valores:
                return valores, usados

    # Nada ha encajado: mostrar los conjuntos de segmentos más parecidos, que
    # es lo único que permite corregir la declaración sin adivinar.
    buscado = set(indicador["busquedas"][0]) | {ambito["segmento"]}
    parecidos = sorted(
        ((len(buscado & segs), segs) for segs in indice),
        key=lambda t: -t[0],
    )[:4]
    print(f"      sin serie para {etiqueta}; lo más parecido:")
    for comunes, segs in parecidos:
        print(f"        ({comunes} coinciden) {sorted(segs)}")
    return {}, []


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    CONFIG.mkdir(parents=True, exist_ok=True)
    procedencias: dict[str, dict] = {}
    faltantes: list[str] = []

    for nombre_bloque, bloque in BLOQUES.items():
        print(f"\n=== {bloque['titulo']} ===")
        destino = DATOS / nombre_bloque
        destino.mkdir(parents=True, exist_ok=True)
        procedencias[nombre_bloque] = {}
        por_ambito: dict[str, dict] = {}
        periodos_vistos: set[str] = set()

        for ambito in AMBITOS:
            print(f"  · {ambito['nombre']}")
            indices = {}
            for operacion in bloque["operaciones"]:
                indices[operacion] = motor.indexa_por_segmentos(operacion, ambito["filtro"])
                print(f"      ({operacion}: {sum(len(v) for v in indices[operacion].values())} series)")

            series: dict[str, dict[str, dict[str, float]]] = {}
            origen: dict[str, dict[str, list[str]]] = {}

            for clave, indicador in bloque["indicadores"].items():
                indice = indices[indicador["operacion"]]
                sexos = SEXOS if indicador["por_sexo"] else {"ambos": SEXOS["ambos"]}
                for sexo, alias in sexos.items():
                    etiqueta = f"{clave}/{sexo}"
                    valores, usados = busca(indice, ambito, indicador, alias, etiqueta)
                    if not valores:
                        faltantes.append(f"{nombre_bloque}/{ambito['id']}/{etiqueta}")
                        continue
                    series.setdefault(sexo, {})[clave] = valores
                    origen.setdefault(sexo, {})[clave] = usados
                    periodos_vistos.update(valores)

            por_ambito[ambito["id"]] = series
            procedencias[nombre_bloque][ambito["id"]] = origen

        if not periodos_vistos:
            print(f"  sin datos para {nombre_bloque}; se salta")
            continue

        periodos = sorted(periodos_vistos, key=motor.orden_periodo)
        indice_bloque = {
            "actualizado": ahora,
            "titulo": bloque["titulo"],
            "ultimo_periodo": periodos[-1],
            "primer_periodo": periodos[0],
            "indicadores": {
                clave: {"titulo": ind["titulo"], "unidad": ind["unidad"],
                        "decimales": ind["decimales"], "por_sexo": ind["por_sexo"]}
                for clave, ind in bloque["indicadores"].items()
            },
            "ambitos": [],
        }

        for ambito in AMBITOS:
            series = por_ambito[ambito["id"]]
            contenido = {
                "ambito": {"id": ambito["id"], "nombre": ambito["nombre"], "tipo": ambito["tipo"]},
                "actualizado": ahora,
                "periodos": periodos,
                "series": {
                    sexo: {clave: [valores.get(p) for p in periodos]
                           for clave, valores in magnitudes.items()}
                    for sexo, magnitudes in series.items()
                },
            }
            fichero = f"{ambito['id']}.json"
            (destino / fichero).write_text(json.dumps(contenido, ensure_ascii=False),
                                          encoding="utf-8")
            indice_bloque["ambitos"].append(
                {"id": ambito["id"], "nombre": ambito["nombre"], "fichero": fichero})
            print(f"    escrito data/{nombre_bloque}/{fichero}")

        (destino / "index.json").write_text(
            json.dumps(indice_bloque, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  {len(periodos)} periodos: {periodos[0]} … {periodos[-1]}")

    (CONFIG / "series-sociodemografia.json").write_text(
        json.dumps(procedencias, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if faltantes:
        print(f"\nNo se ha encontrado serie para {len(faltantes)} combinaciones:")
        for f in faltantes:
            print(f"  - {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
