"""Descarga de la EPA (INE) las series que alimentan el panel.

Estrategia: la API del INE nombra cada serie con los valores de sus variables
separados por puntos, por ejemplo

    "Mujeres. Castellón/Castelló. Total. Parados. Valor absoluto."

así que una serie es «la del total» cuando el conjunto de sus segmentos es
exactamente el esperado: sexo, territorio, la magnitud, «Total» para el resto
de desgloses y, en los absolutos, «Valor absoluto». Al exigir igualdad de
conjuntos (y no que uno contenga al otro) la resolución es determinista: o hay
una única serie o el script se para y dice qué ha encontrado.

Los códigos resueltos se guardan en config/series-epa.json, de modo que las
siguientes ejecuciones van directas a DATOS_SERIE sin volver a buscar.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "data" / "epa"
CONFIG = RAIZ / "config" / "series-epa.json"  # procedencia de cada serie

# Identificadores descubiertos en la API (VARIABLES_OPERACION/EPA).
VAR_NACIONAL, VAR_CCAA, VAR_PROVINCIAS = 349, 70, 115

AMBITOS = [
    {
        "id": "espana",
        "nombre": "España",
        "tipo": "Nacional",
        "filtro": f"{VAR_NACIONAL}:16473",
        "segmento": "total nacional",
    },
    {
        "id": "comunitat-valenciana",
        "nombre": "Comunitat Valenciana",
        "tipo": "Comunidad autónoma",
        "filtro": f"{VAR_CCAA}:9006",
        "segmento": "comunitat valenciana",
    },
    {
        "id": "castellon",
        "nombre": "Castellón",
        "tipo": "Provincia",
        "filtro": f"{VAR_PROVINCIAS}:13",
        "segmento": "castellon/castello",
    },
]

SEXOS = {"ambos": "ambos sexos", "hombres": "hombres", "mujeres": "mujeres"}

# Segmentos que pueden sobrar en el nombre de una serie sin cambiar lo que mide:
# son formas de decir «el total» de una variable.
EXTRAS_ADMITIDOS = {"total", "de 16 y mas anos", "ambos sexos", "valor absoluto"}

# magnitud -> (segmento que la identifica, es_tasa)
MAGNITUDES = {
    "ocupados": ("ocupados", False),
    "parados": ("parados", False),
    "activos": ("activos", False),
    "tasa_actividad": ("tasa de actividad", True),
    "tasa_paro": ("tasa de paro de la poblacion", True),
    "tasa_empleo": ("tasa de empleo de la poblacion", True),
}

UNIDADES = {
    "ocupados": "miles de personas",
    "parados": "miles de personas",
    "activos": "miles de personas",
    "tasa_actividad": "%",
    "tasa_paro": "%",
    "tasa_empleo": "%",
}


def normaliza(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def segmentos(nombre: str) -> set[str]:
    return {normaliza(p) for p in (nombre or "").split(".") if normaliza(p)}


def esperado(sexo: str, ambito: dict, magnitud: str) -> set[str]:
    clave, es_tasa = MAGNITUDES[magnitud]
    partes = {SEXOS[sexo], ambito["segmento"], "total", clave}
    if not es_tasa:
        partes.add("valor absoluto")
    return partes


TRIMESTRE = re.compile(r"\d{4}T[1-4]")
ROMANOS = {"I": "T1", "II": "T2", "III": "T3", "IV": "T4"}
# Trimestres tal y como los numera Tempus 3 en FK_Periodo.
FK_TRIMESTRES = {19: "T1", 20: "T2", 21: "T3", 22: "T4"}


def periodo_de(dato: dict) -> str | None:
    """'2026T2' a partir de un punto de la serie.

    La forma del periodo depende del nivel de detalle pedido: con det=2 llega
    `NombrePeriodo` ya formateado, con tip=A un `T3_Periodo` ("T2") y a secas
    un `FK_Periodo` numérico. Se aceptan las tres.
    """
    nombre_directo = dato.get("NombrePeriodo")
    if nombre_directo and TRIMESTRE.fullmatch(str(nombre_directo).strip().upper()):
        return str(nombre_directo).strip().upper()

    anyo = dato.get("Anyo") or dato.get("Anio")
    if not anyo:
        return None

    periodo = dato.get("Periodo")
    nombre = periodo.get("Nombre") if isinstance(periodo, dict) else periodo
    nombre = nombre or dato.get("T3_Periodo")
    if nombre:
        nombre = str(nombre).strip().upper()
        if nombre in ("T1", "T2", "T3", "T4"):
            return f"{anyo}{nombre}"
        if nombre in ROMANOS:
            return f"{anyo}{ROMANOS[nombre]}"

    trimestre = FK_TRIMESTRES.get(dato.get("FK_Periodo"))
    return f"{anyo}{trimestre}" if trimestre else None


def orden_periodo(periodo: str) -> tuple[int, int]:
    return (int(periodo[:4]), int(periodo[5:]))


def cobertura(codigo: str) -> dict[str, float]:
    """Trimestres con dato de una serie."""
    return {p: v for p, v in descarga_serie(codigo).items() if v is not None}


def concuerdan(a: dict[str, float], b: dict[str, float]) -> bool:
    """¿Dos series miden lo mismo allí donde se solapan?

    Sin solape no se puede afirmar que lo hagan, y mezclarlas podría encadenar
    metodologías distintas, así que se responde que no.
    """
    comunes = set(a) & set(b)
    if not comunes:
        return False
    for periodo in comunes:
        referencia = max(abs(a[periodo]), abs(b[periodo]), 1e-9)
        if abs(a[periodo] - b[periodo]) / referencia > 0.01:
            return False
    return True


def fusiona(candidatas: list[dict], etiqueta: str, tope: int = 12) -> tuple[dict[str, float], list[str]]:
    """Reúne en una sola serie las candidatas que miden lo mismo.

    El INE reparte la misma cifra entre varias series -y a veces estrena una
    serie nueva con dos trimestres mientras la histórica sigue publicándose
    aparte-, así que se parte de la más completa y se rellenan sus huecos con
    las demás, pero sólo con aquellas cuyos valores coinciden en los
    trimestres compartidos.
    """
    orden = sorted(candidatas, key=lambda c: len(segmentos(c.get("Nombre", ""))))[:tope]
    descargadas = [(c["COD"], cobertura(c["COD"])) for c in orden]
    descargadas = [(codigo, valores) for codigo, valores in descargadas if valores]
    if not descargadas:
        print(f"      {etiqueta}: {len(candidatas)} candidatas, ninguna con datos")
        return {}, []

    descargadas.sort(key=lambda t: (len(t[1]), max(orden_periodo(p) for p in t[1])), reverse=True)
    base_codigo, fusionada = descargadas[0]
    usados = [base_codigo]

    for codigo, valores in descargadas[1:]:
        nuevos = {p: v for p, v in valores.items() if p not in fusionada}
        if not nuevos or not concuerdan(fusionada, valores):
            continue
        fusionada.update(nuevos)
        usados.append(codigo)

    if len(usados) > 1:
        print(f"      {etiqueta}: {len(fusionada)} trimestres uniendo {len(usados)} series "
              f"({', '.join(usados)})")
    else:
        print(f"      {etiqueta}: {len(fusionada)} trimestres ({base_codigo})")
    return fusionada, usados


def resuelve_ambito(ambito: dict) -> tuple[dict[str, dict[str, dict[str, float]]], dict]:
    """Series de un ámbito: {sexo: {magnitud: {periodo: valor}}} y su procedencia."""
    print(f"  · {ambito['nombre']}: buscando series…")
    series = ine_api.get("SERIE_METADATAOPERACION", "EPA", g1=ambito["filtro"])
    porsegmentos: dict[frozenset, list[dict]] = {}
    for serie in series:
        porsegmentos.setdefault(frozenset(segmentos(serie.get("Nombre", ""))), []).append(serie)

    datos: dict[str, dict[str, dict[str, float]]] = {}
    procedencia: dict[str, dict[str, list[str]]] = {}

    for sexo in SEXOS:
        datos[sexo] = {}
        procedencia[sexo] = {}
        for magnitud in MAGNITUDES:
            etiqueta = f"{sexo}/{magnitud}"
            clave = frozenset(esperado(sexo, ambito, magnitud))

            # El INE no siempre nombra igual el total de una variable ("Total",
            # "De 16 y más años"…), así que se admite cualquier serie que
            # contenga lo obligatorio y no añada más que totales.
            obligatorio = clave - EXTRAS_ADMITIDOS
            candidatas, vistos = [], set()
            for segs, grupo in porsegmentos.items():
                if not (obligatorio <= segs and (segs - obligatorio) <= EXTRAS_ADMITIDOS):
                    continue
                for serie in grupo:
                    if serie["COD"] not in vistos:
                        vistos.add(serie["COD"])
                        candidatas.append(serie)

            if not candidatas:
                print(f"      sin serie para {etiqueta} ({sorted(clave)})")
                continue

            valores, usados = fusiona(candidatas, etiqueta)
            if valores:
                datos[sexo][magnitud] = valores
                procedencia[sexo][magnitud] = usados

    return datos, procedencia


def completa_derivando(datos: dict[str, dict[str, dict[str, float]]], procedencia: dict) -> None:
    """Rellena lo que el INE no publica como serie propia.

    Ocupados, parados y activos son las tres caras de la misma identidad, así
    que basta con dos para tener la tercera. Se aplica trimestre a trimestre y
    sólo donde falta el dato, nunca sobre lo publicado.
    """
    identidades = [
        ("parados", "activos", "ocupados"),   # parados  = activos - ocupados
        ("ocupados", "activos", "parados"),   # ocupados = activos - parados
    ]
    for sexo, magnitudes in datos.items():
        for destino, menos, sustraendo in identidades:
            if menos not in magnitudes or sustraendo not in magnitudes:
                continue
            actual = magnitudes.setdefault(destino, {})
            derivados = 0
            for periodo, valor in magnitudes[menos].items():
                if periodo in actual or periodo not in magnitudes[sustraendo]:
                    continue
                actual[periodo] = round(valor - magnitudes[sustraendo][periodo], 3)
                derivados += 1
            if derivados:
                procedencia[sexo].setdefault(destino, [])
                procedencia[sexo][destino].append(f"derivado:{menos}-{sustraendo}")
                print(f"      {sexo}/{destino}: {derivados} trimestres derivados "
                      f"de {menos} − {sustraendo}")

        # activos = ocupados + parados
        if "ocupados" in magnitudes and "parados" in magnitudes:
            actual = magnitudes.setdefault("activos", {})
            derivados = 0
            for periodo, valor in magnitudes["ocupados"].items():
                if periodo in actual or periodo not in magnitudes["parados"]:
                    continue
                actual[periodo] = round(valor + magnitudes["parados"][periodo], 3)
                derivados += 1
            if derivados:
                procedencia[sexo].setdefault("activos", [])
                procedencia[sexo]["activos"].append("derivado:ocupados+parados")
                print(f"      {sexo}/activos: {derivados} trimestres derivados "
                      f"de ocupados + parados")


_descargadas: dict[str, dict[str, float | None]] = {}


def descarga_serie(codigo: str) -> dict[str, float | None]:
    """Serie completa (nult muy alto: el INE devuelve lo que tenga)."""
    if codigo in _descargadas:
        return _descargadas[codigo]
    try:
        datos = ine_api.get("DATOS_SERIE", codigo, nult=400, det=2)
    except ine_api.INEError as exc:
        print(f"      ! no se pudo descargar {codigo}: {exc}")
        _descargadas[codigo] = {}
        return {}
    if isinstance(datos, list):
        datos = datos[0] if datos else {}
    valores: dict[str, float | None] = {}
    for punto in datos.get("Data", []):
        periodo = periodo_de(punto)
        if periodo:
            valores[periodo] = punto.get("Valor")
    _descargadas[codigo] = valores
    return valores


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    print("Buscando y descargando series de la EPA…")
    por_ambito: dict[str, dict] = {}
    procedencias: dict[str, dict] = {}
    periodos_vistos: set[str] = set()

    for ambito in AMBITOS:
        datos, procedencia = resuelve_ambito(ambito)
        completa_derivando(datos, procedencia)
        por_ambito[ambito["id"]] = datos
        procedencias[ambito["id"]] = procedencia
        for magnitudes in datos.values():
            for valores in magnitudes.values():
                periodos_vistos.update(valores)

    if not periodos_vistos:
        print("No se ha descargado ningún dato; no se toca nada.")
        return 1

    # Rejilla temporal común: así todas las series comparten índice y la web no
    # tiene que alinear nada.
    periodos = sorted(periodos_vistos, key=orden_periodo)

    indice = {
        "actualizado": ahora,
        "ultimo_periodo": periodos[-1],
        "primer_periodo": periodos[0],
        "fuente": {
            "organismo": "Instituto Nacional de Estadística",
            "operacion": "Encuesta de Población Activa (EPA)",
            "api": "https://servicios.ine.es/wstempus/js/ES/",
        },
        "ambitos": [],
    }

    print("\nEscribiendo ficheros…")
    for ambito in AMBITOS:
        datos = por_ambito[ambito["id"]]
        series: dict[str, dict[str, list]] = {}
        for sexo in SEXOS:
            series[sexo] = {}
            for magnitud in MAGNITUDES:
                valores = datos.get(sexo, {}).get(magnitud)
                if not valores:
                    continue
                series[sexo][magnitud] = [valores.get(p) for p in periodos]
                huecos = sum(1 for p in periodos if p not in valores)
                if huecos:
                    print(f"  aviso: {ambito['id']}/{sexo}/{magnitud} "
                          f"tiene {huecos} trimestres sin dato")

        contenido = {
            "ambito": {"id": ambito["id"], "nombre": ambito["nombre"], "tipo": ambito["tipo"]},
            "actualizado": ahora,
            "periodos": periodos,
            "series": series,
            "unidades": UNIDADES,
            "series_origen": procedencias[ambito["id"]],
            "fuentes": [{
                "tabla": "EPA",
                "nombre": f"Encuesta de Población Activa · {ambito['nombre']}",
                "url": "https://www.ine.es/dyngs/INEbase/es/operacion.htm"
                       "?c=Estadistica_C&cid=1254736176918&menu=ultiDatos&idp=1254735976595",
            }],
        }
        fichero = f"{ambito['id']}.json"
        (DESTINO / fichero).write_text(
            json.dumps(contenido, ensure_ascii=False), encoding="utf-8"
        )
        indice["ambitos"].append({
            "id": ambito["id"], "nombre": ambito["nombre"], "fichero": fichero
        })
        print(f"  data/epa/{fichero}")

    (DESTINO / "index.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    CONFIG.write_text(
        json.dumps(procedencias, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nListo: {len(periodos)} trimestres, de {periodos[0]} a {periodos[-1]}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
