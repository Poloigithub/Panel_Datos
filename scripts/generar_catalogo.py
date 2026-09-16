"""El catálogo de indicadores y la descarga completa del panel.

Dos ficheros que salen de los datos ya publicados, sin tocar ninguna API:

- `data/indicadores.json`: qué indicadores hay, en qué sección viven, con qué
  unidad, para qué ámbitos y desde cuándo. Es lo que busca el buscador, y
  también lo que permite darse cuenta de que algo se publica dos veces con dos
  nombres distintos.
- `data/panel-completo.csv`: todas las series en formato largo -una fila por
  cifra- para quien quiera abrirlo con una hoja de cálculo o cargarlo en R sin
  pelearse con nueve ficheros JSON.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_series as motor  # noqa: E402
from secciones import SECCIONES  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data"

SEXOS = {"ambos": "Ambos sexos", "hombres": "Hombres", "mujeres": "Mujeres"}

# La EPA es anterior al motor de bloques y su índice no lleva la ficha de cada
# indicador, sólo las unidades dentro de cada ámbito. Se compone aquí para que
# el buscador no se deje fuera la sección más consultada del panel.
TITULOS_EPA = {
    "ocupados": "Ocupados", "parados": "Parados", "activos": "Activos",
    "tasa_actividad": "Tasa de actividad", "tasa_paro": "Tasa de paro",
    "tasa_empleo": "Tasa de empleo",
}


def carga(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def bloques_publicados() -> list[dict]:
    """Las secciones que tienen datos, en el orden en que se presentan."""
    conocidas = {s["bloque"]: s for s in SECCIONES}
    encontradas = []
    for carpeta in sorted(d for d in DATOS.iterdir() if d.is_dir()):
        indice = carga(carpeta / "index.json")
        if not indice:
            continue
        seccion = conocidas.get(carpeta.name, {})
        encontradas.append({
            "id": carpeta.name,
            "titulo": seccion.get("titulo") or indice.get("titulo") or carpeta.name,
            "enlace": seccion.get("enlace", ""),
            "fuente": seccion.get("fuente", ""),
            "indice": indice,
            "carpeta": carpeta,
        })
    # Primero las que tienen sección declarada, en su orden; luego el resto.
    orden = {s["bloque"]: i for i, s in enumerate(SECCIONES)}
    return sorted(encontradas, key=lambda b: (orden.get(b["id"], 99), b["id"]))


def contenidos(bloque: dict) -> dict:
    return {a["id"]: carga(bloque["carpeta"] / a["fichero"])
            for a in bloque["indice"].get("ambitos", [])
            if carga(bloque["carpeta"] / a["fichero"])}


def fichas_de_las_series(por_ambito: dict) -> dict:
    """Ficha mínima de un bloque cuyo índice no las trae, como el de la EPA."""
    fichas: dict[str, dict] = {}
    for contenido in por_ambito.values():
        unidades = contenido.get("unidades", {})
        sexos = list(contenido.get("series", {}))
        for sexo, magnitudes in contenido.get("series", {}).items():
            for clave in magnitudes:
                fichas.setdefault(clave, {
                    "titulo": TITULOS_EPA.get(clave, clave.replace("_", " ").capitalize()),
                    "unidad": unidades.get(clave),
                    "por_sexo": len(sexos) > 1,
                })
    return fichas


def cobertura(contenido: dict, clave: str) -> tuple[str, str] | None:
    """Primer y último periodo con dato de una serie, mire el sexo que mire."""
    periodos = []
    for magnitudes in contenido.get("series", {}).values():
        valores = magnitudes.get(clave)
        if not valores:
            continue
        periodos += [p for p, v in zip(contenido["periodos"], valores) if v is not None]
    if not periodos:
        return None
    return min(periodos, key=motor.orden_periodo), max(periodos, key=motor.orden_periodo)


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    catalogo = []
    filas = 0

    destino_csv = DATOS / "panel-completo.csv"
    with destino_csv.open("w", encoding="utf-8", newline="") as fichero:
        escritor = csv.writer(fichero)
        escritor.writerow(["seccion", "indicador", "titulo", "ambito", "sexo",
                           "periodo", "valor", "unidad"])

        for bloque in bloques_publicados():
            por_ambito = contenidos(bloque)
            fichas = bloque["indice"].get("indicadores", {}) or fichas_de_las_series(por_ambito)
            for clave, ficha in fichas.items():
                ambitos, desde, hasta = [], None, None
                for ambito_id, contenido in por_ambito.items():
                    rango = cobertura(contenido, clave)
                    if not rango:
                        continue
                    ambitos.append(ambito_id)
                    desde = min(filter(None, [desde, rango[0]]), key=motor.orden_periodo)
                    hasta = max(filter(None, [hasta, rango[1]]), key=motor.orden_periodo)

                    for sexo, magnitudes in contenido.get("series", {}).items():
                        valores = magnitudes.get(clave)
                        if not valores:
                            continue
                        for periodo, valor in zip(contenido["periodos"], valores):
                            if valor is None:
                                continue
                            escritor.writerow([
                                bloque["id"], clave, ficha.get("titulo", clave),
                                ambito_id, SEXOS.get(sexo, sexo), periodo, valor,
                                ficha.get("unidad", "")])
                            filas += 1

                if not ambitos:
                    continue
                catalogo.append({
                    "clave": clave,
                    "titulo": ficha.get("titulo", clave),
                    "seccion": bloque["titulo"],
                    "seccion_id": bloque["id"],
                    "enlace": bloque["enlace"],
                    "fuente": bloque["fuente"],
                    "unidad": ficha.get("unidad"),
                    "unidad_texto": ficha.get("unidad_texto"),
                    "nota": ficha.get("nota"),
                    "por_sexo": bool(ficha.get("por_sexo")),
                    "ambitos": ambitos,
                    "desde": desde,
                    "hasta": hasta,
                })

    (DATOS / "indicadores.json").write_text(
        json.dumps({"actualizado": ahora, "indicadores": catalogo},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    peso = destino_csv.stat().st_size / 1024 / 1024
    print(f"catálogo: {len(catalogo)} indicadores en "
          f"{len({i['seccion_id'] for i in catalogo})} secciones")
    print(f"descarga completa: {filas:,} filas · {peso:.1f} MB")
    sin_provincia = [i["titulo"] for i in catalogo if "castellon" not in i["ambitos"]]
    if sin_provincia:
        print(f"sin dato de Castellón ({len(sin_provincia)}): "
              f"{', '.join(sin_provincia[:6])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
