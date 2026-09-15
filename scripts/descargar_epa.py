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


ROMANOS = {"I": "T1", "II": "T2", "III": "T3", "IV": "T4"}


def periodo_de(dato: dict) -> str | None:
    """'2026T2' a partir de un punto de la serie.

    Con tip=A el INE devuelve `Periodo` como objeto; sin él, un `FK_Periodo`
    numérico. Se aceptan las dos formas.
    """
    anyo = dato.get("Anyo") or dato.get("Anio")
    if not anyo:
        return None

    periodo = dato.get("Periodo")
    nombre = periodo.get("Nombre") if isinstance(periodo, dict) else periodo
    if nombre:
        nombre = str(nombre).strip().upper()
        if nombre.startswith("T") and nombre[1:].isdigit():
            return f"{anyo}{nombre}"
        if nombre in ROMANOS:
            return f"{anyo}{ROMANOS[nombre]}"

    fk = dato.get("FK_Periodo")
    if isinstance(fk, int) and 1 <= fk <= 4:
        return f"{anyo}T{fk}"
    return None


def orden_periodo(periodo: str) -> tuple[int, int]:
    return (int(periodo[:4]), int(periodo[5:]))


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
    for s in series:
        porsegmentos.setdefault(frozenset(segmentos(s.get("Nombre", ""))), []).append(s)

    resuelto: dict[str, dict[str, str]] = {}
    for sexo in SEXOS:
        resuelto[sexo] = {}
        for magnitud in MAGNITUDES:
            clave = frozenset(esperado(sexo, ambito, magnitud))
            candidatas = porsegmentos.get(clave, [])
            if len(candidatas) == 1:
                resuelto[sexo][magnitud] = candidatas[0]["COD"]
            elif not candidatas:
                print(f"      sin serie para {sexo}/{magnitud} ({sorted(clave)})")
            else:
                # Varias series con los mismos metadatos: el INE mantiene
                # versiones antiguas junto a la vigente. Gana la que llega más
                # lejos en el tiempo y, a igualdad, la más larga.
                mejor, mejor_clave = None, None
                for candidata in candidatas:
                    valores = descarga_serie(candidata["COD"])
                    if not valores:
                        continue
                    orden = (max(orden_periodo(p) for p in valores), len(valores))
                    if mejor_clave is None or orden > mejor_clave:
                        mejor, mejor_clave = candidata["COD"], orden
                if mejor:
                    resuelto[sexo][magnitud] = mejor
                    print(f"      {sexo}/{magnitud}: {len(candidatas)} candidatas, "
                          f"se toma la más actual ({mejor})")
                else:
                    print(f"      ¡ambiguo y sin datos! {sexo}/{magnitud}: "
                          f"{[c['COD'] for c in candidatas]}")
    encontradas = sum(len(v) for v in resuelto.values())
    print(f"    resueltas {encontradas} de {len(SEXOS) * len(MAGNITUDES)} series")
    cache[ambito["id"]] = resuelto
    return resuelto


def descarga_serie(codigo: str) -> dict[str, float | None]:
    """Serie completa (nult muy alto: el INE devuelve lo que tenga)."""
    datos = ine_api.get("DATOS_SERIE", codigo, nult=400, tip="A")
    if isinstance(datos, list):
        datos = datos[0] if datos else {}
    valores: dict[str, float | None] = {}
    for punto in datos.get("Data", []):
        periodo = periodo_de(punto)
        if periodo:
            valores[periodo] = punto.get("Valor")
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
