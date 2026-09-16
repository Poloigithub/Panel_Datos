"""Prepara el contorno de los municipios de Castellón para el mapa.

Las geometrías salen de GISCO (Eurostat), que publica las unidades
administrativas locales de toda la UE con direcciones estables y códigos que,
en España, son los del INE. Del fichero europeo sólo se guardan los municipios
de la provincia, ya simplificados: el trabajo pesado se queda en el runner y
al repositorio llega un fichero pequeño.

La simplificación usa Douglas-Peucker, escrito aquí mismo para no añadir
dependencias al proyecto.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "data" / "geo"

# Se prueban varios años: GISCO mantiene las ediciones anteriores publicadas.
URLS = [
    "https://gisco-services.ec.europa.eu/distribution/v2/lau/geojson/LAU_RG_01M_2021_4326.geojson",
    "https://gisco-services.ec.europa.eu/distribution/v2/lau/geojson/LAU_RG_01M_2020_4326.geojson",
    "https://gisco-services.ec.europa.eu/distribution/v2/lau/geojson/LAU_RG_01M_2019_4326.geojson",
]
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

PROVINCIA = "12"          # Castellón, en la codificación del INE
TOLERANCIA = 0.0008       # ≈ 80 metros: suficiente para una provincia en pantalla


def descarga(url: str) -> dict | None:
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=600) as respuesta:
            print(f"  {url} → {respuesta.status}")
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"  {url} → {exc.code}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {url} → {type(exc).__name__}: {exc}")
    return None


def distancia_a_recta(punto, inicio, fin) -> float:
    """Distancia perpendicular de un punto al segmento inicio-fin."""
    (x, y), (x1, y1), (x2, y2) = punto, inicio, fin
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / ((dx * dx + dy * dy) ** 0.5)


def simplifica(puntos: list, tolerancia: float) -> list:
    """Douglas-Peucker: conserva los vértices que definen la forma."""
    if len(puntos) < 3:
        return puntos

    peor, indice = 0.0, 0
    for i in range(1, len(puntos) - 1):
        d = distancia_a_recta(puntos[i], puntos[0], puntos[-1])
        if d > peor:
            peor, indice = d, i

    if peor <= tolerancia:
        return [puntos[0], puntos[-1]]

    izquierda = simplifica(puntos[: indice + 1], tolerancia)
    derecha = simplifica(puntos[indice:], tolerancia)
    return izquierda[:-1] + derecha


def simplifica_geometria(geometria: dict, tolerancia: float) -> dict:
    """Simplifica un polígono o multipolígono cerrando siempre el contorno."""
    def anillo(puntos):
        reducido = simplifica([tuple(p) for p in puntos], tolerancia)
        if len(reducido) < 4:                      # un anillo necesita 4 puntos
            reducido = [tuple(p) for p in puntos]
        if reducido[0] != reducido[-1]:
            reducido.append(reducido[0])
        return [list(p) for p in reducido]

    tipo = geometria.get("type")
    coordenadas = geometria.get("coordinates") or []
    if tipo == "Polygon":
        return {"type": tipo, "coordinates": [anillo(a) for a in coordenadas]}
    if tipo == "MultiPolygon":
        return {"type": tipo,
                "coordinates": [[anillo(a) for a in poligono] for poligono in coordenadas]}
    return geometria


def codigo_municipio(propiedades: dict) -> str | None:
    """El código INE del municipio, venga con el nombre de campo que venga."""
    for clave in ("LAU_ID", "LAU_CODE", "COMM_ID", "GISCO_ID"):
        valor = propiedades.get(clave)
        if not valor:
            continue
        texto = str(valor).split("_")[-1]
        if texto.isdigit():
            return texto.zfill(5)
    return None


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)

    print("Descargando las unidades administrativas locales de GISCO…")
    datos = None
    for url in URLS:
        datos = descarga(url)
        if datos:
            break
    if not datos:
        print("No se ha podido descargar ninguna edición.")
        return 1

    municipios = []
    puntos_antes = puntos_despues = 0
    for elemento in datos.get("features", []):
        propiedades = elemento.get("properties") or {}
        if (propiedades.get("CNTR_CODE") or "").upper() != "ES":
            continue
        codigo = codigo_municipio(propiedades)
        if not codigo or not codigo.startswith(PROVINCIA):
            continue

        geometria = elemento.get("geometry") or {}
        puntos_antes += sum(len(a) for a in json.loads(json.dumps(geometria)).get("coordinates", [])
                            if isinstance(a, list))
        simplificada = simplifica_geometria(geometria, TOLERANCIA)
        municipios.append({
            "type": "Feature",
            "properties": {
                "codigo": codigo,
                "nombre": (propiedades.get("LAU_NAME") or propiedades.get("NAME_LATN")
                           or propiedades.get("COMM_NAME") or codigo),
            },
            "geometry": simplificada,
        })

    if not municipios:
        print("No se ha encontrado ningún municipio de la provincia.")
        return 1

    municipios.sort(key=lambda m: m["properties"]["codigo"])
    coleccion = {"type": "FeatureCollection", "features": municipios}
    fichero = DESTINO / "municipios-castellon.geojson"
    fichero.write_text(json.dumps(coleccion, ensure_ascii=False, separators=(",", ":")),
                       encoding="utf-8")

    print(f"\n{len(municipios)} municipios · {fichero.stat().st_size // 1024} KB")
    print("Primeros:", ", ".join(m["properties"]["nombre"] for m in municipios[:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
