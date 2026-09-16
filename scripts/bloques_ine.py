"""Motor de bloques del panel: de una declaración de indicadores a su JSON.

Un bloque es una página del panel -precios, renta, vivienda- y se declara como
un diccionario: qué operaciones del INE mirar y, por cada indicador, qué
segmentos deben aparecer en el nombre de su serie. Este módulo se encarga del
resto, que es igual para todos: probar las formulaciones alternativas hasta dar
con la serie, comprobar que mide lo que decimos que mide, y escribir los
ficheros que lee el front-end.

Lo que cambia de un bloque a otro -deflactar la renta, componer una población a
partir de los dos sexos- entra por el gancho `posproceso`, que recibe las
series ya descargadas de un ámbito y puede añadirle las derivadas.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_series as motor  # noqa: E402

VAR_NACIONAL, VAR_CCAA, VAR_PROVINCIAS = 349, 70, 115

AMBITOS = [
    {"id": "espana", "nombre": "España", "tipo": "Nacional",
     "filtro": f"{VAR_NACIONAL}:16473", "segmento": "total nacional",
     # El IPC y el índice de precios de vivienda nombran el ámbito nacional
     # «Nacional» a secas.
     "segmentos_alternativos": ["nacional"]},
    {"id": "comunitat-valenciana", "nombre": "Comunitat Valenciana", "tipo": "Comunidad autónoma",
     "filtro": f"{VAR_CCAA}:9006", "segmento": "comunitat valenciana"},
    {"id": "castellon", "nombre": "Castellón", "tipo": "Provincia",
     "filtro": f"{VAR_PROVINCIAS}:13", "segmento": "castellon/castello"},
]

# Cómo se llama cada sexo en cada operación: el INE alterna «Total» y
# «Ambos sexos» según la estadística.
SEXOS = {
    "ambos": {"total", "ambos sexos"},
    "hombres": {"hombres", "varones"},
    "mujeres": {"mujeres"},
}


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


def deflacta(series: dict, deflactor: dict[str, float], procedencia: dict,
             claves) -> str | None:
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
        for clave in claves:
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


def base_del_indice(valores: dict[str, float]) -> str | None:
    """El año en que el índice vale 100, deducido de la propia serie.

    El INE rebasa el IPC cada pocos años y la etiqueta escrita a mano se queda
    vieja sin que nadie lo note: el panel decía «base 2021 = 100» cuando el
    índice ya estaba en base 2025. Como la base es, por definición, el año cuya
    media vale 100, se puede leer de los datos en vez de mantenerla a mano.
    """
    por_anyo: dict[str, list[float]] = {}
    for periodo, valor in valores.items():
        por_anyo.setdefault(periodo[:4], []).append(valor)
    medias = {anyo: sum(v) / len(v) for anyo, v in por_anyo.items() if len(v) >= 4}
    if not medias:
        return None
    anyo = min(medias, key=lambda a: abs(medias[a] - 100))
    return anyo if abs(medias[anyo] - 100) < 0.5 else None


def filtro_de_rango(indicador):
    """Convierte el rango declarado en un filtro de candidatas.

    Aplicarlo durante la búsqueda, y no sólo al final, evita quedarse con una
    serie del mismo indicador en otra base: el IPC de España llegaba con
    valores de 8,18 porque el INE conserva el índice con bases viejas.
    """
    rango = indicador.get("rango")
    if not rango:
        return None
    minimo, maximo = rango

    def acepta(valores: dict) -> bool:
        # Toda la serie, no sólo la cola: el índice de España terminaba en
        # valores correctos y arrancaba en otra escala.
        return all(minimo <= v <= maximo for v in valores.values())

    return acepta


def en_rango(valores, indicador, etiqueta) -> bool:
    """¿La serie encontrada mide lo que creemos que mide?

    Los nombres del INE se parecen entre sí y una búsqueda laxa puede acabar
    en otra cosa -la esperanza de vida al nacer y la mortalidad infantil se
    confundían así-. Un rango plausible lo detecta antes de publicarlo.
    """
    rango = indicador.get("rango")
    if not rango:
        return True
    minimo, maximo = rango
    ultimos = [v for _, v in sorted(valores.items())][-3:]
    fuera = [v for v in ultimos if not (minimo <= v <= maximo)]
    if fuera:
        print(f"      {etiqueta}: descartada, los valores {fuera} quedan fuera "
              f"del rango esperado {rango}")
        return False
    return True


def busca(indice, ambito, indicador, alias_sexo, etiqueta, avisar=True):
    """Primera formulación que dé datos, de entre las declaradas.

    Se prueban los alias del sexo y, al final, la variante sin sexo: hay
    operaciones (el Atlas de renta, por ejemplo) cuyas series no llevan esa
    variable en el nombre.
    """
    intentos = [{a} for a in sorted(alias_sexo)] + [set()]
    territorios = [ambito["segmento"]] + ambito.get("segmentos_alternativos", [])
    acepta = filtro_de_rango(indicador)
    for busqueda in indicador["busquedas"]:
        for territorio in territorios:
            for alias in intentos:
                obligatorio = set(busqueda) | {territorio} | alias
                valores, usados = motor.resuelve(indice, obligatorio, etiqueta,
                                                 extras=indicador.get("extras"),
                                                 avisar=False, acepta=acepta)
                if valores:
                    return valores, usados

    # Nada ha encajado: mostrar los conjuntos de segmentos más parecidos, que
    # es lo único que permite corregir la declaración sin adivinar.
    if not avisar:
        return {}, []
    buscado = set(indicador["busquedas"][0]) | {ambito["segmento"]}
    parecidos = sorted(
        ((len(buscado & segs), segs) for segs in indice),
        key=lambda t: -t[0],
    )[:4]
    print(f"      sin serie para {etiqueta}; lo más parecido:")
    for comunes, segs in parecidos:
        print(f"        ({comunes} coinciden) {sorted(segs)}")
    return {}, []


def describe_indicadores(bloque: dict, por_ambito: dict, derivados=None) -> dict:
    """Metadatos de cada indicador, incluidos los que se derivan al vuelo."""
    descripcion = {
        clave: {"titulo": ind["titulo"], "unidad": ind["unidad"],
                "unidad_texto": ind.get("unidad_texto"),
                "decimales": ind["decimales"], "por_sexo": ind["por_sexo"],
                "nota": ind.get("nota"), "sobre_total": ind.get("sobre_total")}
        for clave, ind in bloque["indicadores"].items()
    }
    for clave, ficha in (derivados or {}).items():
        descripcion[clave] = ficha
    # Sólo se describe lo que se ha publicado: un indicador que el INE no da
    # para ningún ámbito no debe aparecer en la ficha del bloque.
    publicados = {clave for series in por_ambito.values()
                  for magnitudes in series.values() for clave in magnitudes}
    return {clave: ficha for clave, ficha in descripcion.items() if clave in publicados}


def descarga_bloque(nombre: str, bloque: dict, posproceso=None):
    """Descarga todos los indicadores de un bloque para los tres ámbitos."""
    por_ambito: dict[str, dict] = {}
    procedencias: dict[str, dict] = {}
    faltantes: list[str] = []

    for ambito in AMBITOS:
        print(f"  · {ambito['nombre']}")
        indices = {}
        for operacion in bloque["operaciones"]:
            indices[operacion] = motor.indexa_por_segmentos(operacion, ambito["filtro"])
            print(f"      ({operacion}: {sum(len(v) for v in indices[operacion].values())} series)")

        series: dict[str, dict[str, dict[str, float]]] = {}
        origen: dict[str, dict[str, list[str]]] = {}

        for clave, indicador in bloque["indicadores"].items():
            operaciones = indicador["operacion"]
            if isinstance(operaciones, str):
                operaciones = [operaciones]
            # Un indicador puede existir sólo en algunos ámbitos: el índice de
            # precios de vivienda no baja de comunidad autónoma.
            if ambito["id"] in indicador.get("sin_ambitos", ()):
                continue
            sexos = SEXOS if indicador["por_sexo"] else {"ambos": SEXOS["ambos"]}
            for sexo, alias in sexos.items():
                etiqueta = f"{clave}/{sexo}"
                # Se juntan las operaciones: la Estadística Continua de
                # Población arranca en 2021 y Cifras de Población viene de
                # 1971, así que por separado ninguna da la serie entera.
                valores, usados = {}, []
                for operacion in operaciones:
                    parciales, procedencia = busca(
                        indices[operacion], ambito, indicador, alias, etiqueta,
                        avisar=(operacion == operaciones[-1] and not valores))
                    if not parciales:
                        continue
                    if not valores:
                        valores, usados = dict(parciales), list(procedencia)
                    elif motor.concuerdan(valores, parciales):
                        nuevos = {p: v for p, v in parciales.items() if p not in valores}
                        if nuevos:
                            valores.update(nuevos)
                            usados += procedencia

                desde = indicador.get("desde", bloque.get("desde"))
                if valores and desde:
                    recortada = {p: v for p, v in valores.items()
                                 if motor.orden_periodo(p)[0] >= desde}
                    if len(recortada) != len(valores):
                        print(f"      {etiqueta}: recortada a {len(recortada)} periodos "
                              f"desde {desde}")
                    valores = recortada

                if valores and not en_rango(valores, indicador, etiqueta):
                    valores, usados = {}, []
                if not valores:
                    faltantes.append(f"{nombre}/{ambito['id']}/{etiqueta}")
                    continue
                series.setdefault(sexo, {})[clave] = valores
                origen.setdefault(sexo, {})[clave] = usados

        if posproceso:
            posproceso(ambito, series, origen)

        por_ambito[ambito["id"]] = series
        procedencias[ambito["id"]] = origen

    return por_ambito, procedencias, faltantes


def escribe_bloque(nombre: str, bloque: dict, por_ambito: dict, ahora: str,
                   raiz: Path, derivados=None) -> list[str]:
    """Escribe `data/<bloque>/` y devuelve los periodos publicados."""
    periodos_vistos = {periodo
                       for series in por_ambito.values()
                       for magnitudes in series.values()
                       for valores in magnitudes.values()
                       for periodo in valores}
    if not periodos_vistos:
        print(f"  sin datos para {nombre}; se salta")
        return []

    destino = raiz / "data" / nombre
    destino.mkdir(parents=True, exist_ok=True)
    periodos = sorted(periodos_vistos, key=motor.orden_periodo)
    indice_bloque = {
        "actualizado": ahora,
        "titulo": bloque["titulo"],
        "ultimo_periodo": periodos[-1],
        "primer_periodo": periodos[0],
        "indicadores": describe_indicadores(bloque, por_ambito, derivados),
        "ambitos": [],
    }

    for ambito in AMBITOS:
        series = por_ambito.get(ambito["id"], {})
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
        print(f"    escrito data/{nombre}/{fichero}")

    (destino / "index.json").write_text(
        json.dumps(indice_bloque, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  {len(periodos)} periodos: {periodos[0]} … {periodos[-1]}")
    return periodos
