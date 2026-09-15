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
CONFIG = RAIZ / "config" / "series-epa.json"

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


def elige_mejor(candidatas: list[dict], etiqueta: str) -> str | None:
    """De varias series equivalentes, la que mejor cubre la historia.

    El INE publica la misma cifra en tablas distintas y conserva versiones
    antiguas, algunas con sólo un par de trimestres. Gana la de más datos y,
    a igualdad, la que llega más lejos en el tiempo. Se prueban antes las de
    nombre más simple, que suelen ser las series principales.
    """
    orden = sorted(candidatas, key=lambda c: len(segmentos(c.get("Nombre", ""))))[:8]
    mejor, mejor_clave = None, None
    for candidata in orden:
        valores = {p: v for p, v in descarga_serie(candidata["COD"]).items() if v is not None}
        if not valores:
            continue
        clave = (len(valores), max(orden_periodo(p) for p in valores))
        if mejor_clave is None or clave > mejor_clave:
            mejor, mejor_clave = candidata["COD"], clave
    if mejor:
        print(f"      {etiqueta}: {len(candidatas)} candidatas, se toma {mejor} "
              f"({mejor_clave[0]} trimestres)")
    else:
        print(f"      {etiqueta}: {len(candidatas)} candidatas, ninguna con datos")
    return mejor


def resuelve_codigos(ambito: dict, cache: dict) -> dict:
    """Devuelve {sexo: {magnitud: código}} para un ámbito territorial."""
    guardado = cache.get(ambito["id"])
    completo = guardado and all(
        magnitud in (guardado.get(sexo) or {})
        for sexo in SEXOS
        for magnitud in MAGNITUDES
    )
    if completo:
        print(f"  · {ambito['nombre']}: códigos en caché")
        return guardado

    print(f"  · {ambito['nombre']}: resolviendo códigos contra la API…")
    series = ine_api.get("SERIE_METADATAOPERACION", "EPA", g1=ambito["filtro"])
    porsegmentos: dict[frozenset, list[dict]] = {}
    for serie in series:
        porsegmentos.setdefault(frozenset(segmentos(serie.get("Nombre", ""))), []).append(serie)

    resuelto: dict[str, dict[str, str]] = {}
    for sexo in SEXOS:
        resuelto[sexo] = {}
        for magnitud in MAGNITUDES:
            etiqueta = f"{sexo}/{magnitud}"
            clave = frozenset(esperado(sexo, ambito, magnitud))

            # El INE no siempre nombra igual el total de una variable ("Total",
            # "De 16 y más años"…), y la coincidencia exacta puede dar con una
            # serie testimonial de dos trimestres. Se juntan las exactas y las
            # que contienen lo obligatorio sin añadir más que totales, y se
            # elige entre todas por cobertura.
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
            elif len(candidatas) == 1:
                resuelto[sexo][magnitud] = candidatas[0]["COD"]
            else:
                codigo = elige_mejor(candidatas, etiqueta)
                if codigo:
                    resuelto[sexo][magnitud] = codigo

    encontradas = sum(len(v) for v in resuelto.values())
    print(f"    resueltas {encontradas} de {len(SEXOS) * len(MAGNITUDES)} series")
    cache[ambito["id"]] = resuelto
    return resuelto


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

    cache = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    print("Resolviendo series…")
    codigos = {a["id"]: resuelve_codigos(a, cache) for a in AMBITOS}
    CONFIG.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\nDescargando datos…")
    crudo: dict[str, dict[str, dict[str, dict[str, float | None]]]] = {}
    periodos_vistos: set[str] = set()

    for ambito in AMBITOS:
        crudo[ambito["id"]] = {}
        for sexo in SEXOS:
            crudo[ambito["id"]][sexo] = {}
            for magnitud in MAGNITUDES:
                codigo = codigos[ambito["id"]][sexo].get(magnitud)
                if not codigo:
                    continue
                valores = descarga_serie(codigo)
                crudo[ambito["id"]][sexo][magnitud] = valores
                periodos_vistos.update(valores)
                print(f"  {ambito['id']:22s} {sexo:8s} {magnitud:16s} "
                      f"{len(valores):4d} periodos ({codigo})")

    if not periodos_vistos:
        print("No se ha descargado ningún dato; no se toca nada.")
        return 1

    # Rejilla temporal común: así todas las series comparten índice y la web
    # no tiene que alinear nada.
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

    for ambito in AMBITOS:
        series: dict[str, dict[str, list]] = {}
        for sexo in SEXOS:
            series[sexo] = {}
            for magnitud in MAGNITUDES:
                valores = crudo[ambito["id"]][sexo].get(magnitud)
                if valores is None:
                    continue
                series[sexo][magnitud] = [valores.get(p) for p in periodos]

        contenido = {
            "ambito": {"id": ambito["id"], "nombre": ambito["nombre"], "tipo": ambito["tipo"]},
            "actualizado": ahora,
            "periodos": periodos,
            "series": series,
            "unidades": UNIDADES,
            "codigos_serie": codigos[ambito["id"]],
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
        print(f"  escrito data/epa/{fichero}")

    (DESTINO / "index.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nListo: {len(periodos)} trimestres, "
          f"de {periodos[0]} a {periodos[-1]}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
