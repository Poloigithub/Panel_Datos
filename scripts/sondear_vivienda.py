"""Sondeo de las fuentes de vivienda antes de escribir el descargador.

Hacen falta tres cosas y ninguna se puede dar por supuesta:

- qué operaciones del INE publican compraventas, hipotecas y precio de la
  vivienda, y hasta qué nivel territorial llegan (la hoja de ruta ya avisa de
  que el índice de precios sólo existe por comunidad autónoma);
- cómo se llaman sus series, porque el panel las localiza por el nombre;
- si el precio de referencia del alquiler del MIVAU está en una dirección
  estable que se pueda descargar sin autenticación.

Escribe el volcado en `sondeos/vivienda.md` para poder leerlo desde el repo:
este sondeo sólo corre dentro de una Action, que es lo único con salida a
internet hacia el INE.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import ine_api  # noqa: E402
import ine_series as motor  # noqa: E402

SALIDA = RAIZ / "sondeos"
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

PALABRAS = ("vivienda", "hipotec", "transmision", "transmisiones", "inmobiliar",
            "alquiler", "compraventa", "edificacion", "construccion")

AMBITOS = [
    ("España", "349:16473"),
    ("Comunitat Valenciana", "70:9006"),
    ("Castellón", "115:13"),
]

# Direcciones que el ministerio y el catálogo publican para el Sistema Estatal
# de Referencia del Precio del Alquiler.
DIRECTAS = [
    "https://www.mivau.gob.es/recursos_mvs/comun/archivos/serpavi/serpavi_municipios.csv",
    "https://www.mivau.gob.es/vivienda/alquila-bien-es-tu-derecho/serpavi",
    "https://apps.fomento.gob.es/CVP/handlers/serpavi.ashx",
    "https://www.mivau.gob.es/informacion-estadistica/vivienda-y-actuaciones-urbanas",
]

BUSQUEDAS = ["alquiler", "precio de referencia del alquiler", "vivienda municipios"]


def sondea(url: str, limite: int = 3000):
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=90) as respuesta:
            trozo = respuesta.read(limite)
            for codificacion in ("utf-8", "latin-1"):
                try:
                    return respuesta.status, respuesta.headers.get("Content-Type", "?"), trozo.decode(codificacion)
                except UnicodeDecodeError:
                    continue
            return respuesta.status, "binario", repr(trozo[:120])
    except urllib.error.HTTPError as exc:
        return exc.code, "-", str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}"


def operaciones_candidatas() -> list[dict]:
    operaciones = ine_api.get("OPERACIONES_DISPONIBLES")
    elegidas = []
    for operacion in operaciones:
        nombre = motor.normaliza(operacion.get("Nombre", ""))
        if any(palabra in nombre for palabra in PALABRAS):
            elegidas.append(operacion)
    return elegidas


def describe_operacion(operacion: dict) -> list[str]:
    codigo = operacion.get("Codigo") or operacion.get("Cod_IOE")
    lineas = [f"## {operacion.get('Nombre')}",
              f"- código: `{codigo}` · id {operacion.get('Id')} · IOE {operacion.get('Cod_IOE')}"]

    try:
        variables = ine_api.get("VARIABLES_OPERACION", str(codigo))
    except ine_api.INEError as exc:
        lineas += [f"- sin variables: {exc}", ""]
        return lineas
    territoriales = [v for v in variables if v.get("Id") in (70, 115, 349, 19)]
    lineas.append("- variables territoriales: " +
                  (", ".join(f"{v['Id']} {v['Nombre']}" for v in territoriales) or "ninguna"))
    lineas.append("- todas las variables: " +
                  ", ".join(f"{v['Id']} {v['Nombre']}" for v in variables[:20]))

    for nombre_ambito, filtro in AMBITOS:
        try:
            indice = motor.indexa_por_segmentos(str(codigo), filtro)
        except ine_api.INEError as exc:
            lineas.append(f"- {nombre_ambito}: error {exc}")
            continue
        total = sum(len(v) for v in indice.values())
        lineas.append(f"- **{nombre_ambito}**: {total} series, {len(indice)} combinaciones")
        # Las combinaciones más simples son las que nombran los totales, que
        # es justo lo que el panel busca.
        simples = sorted(indice, key=lambda s: (len(s), sorted(s)))[:18]
        for segs in simples:
            ejemplo = indice[segs][0]
            lineas.append(f"    - {sorted(segs)} → `{ejemplo['COD']}`")
    lineas.append("")
    return lineas


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Sondeo de las fuentes de vivienda", ""]

    candidatas = operaciones_candidatas()
    lineas.append(f"{len(candidatas)} operaciones del INE mencionan vivienda o afines:")
    for operacion in candidatas:
        lineas.append(f"- `{operacion.get('Codigo')}` · {operacion.get('Nombre')}")
    lineas.append("")

    for operacion in candidatas:
        print(f"· {operacion.get('Nombre')}")
        lineas += describe_operacion(operacion)

    lineas += ["# Precio de referencia del alquiler (MIVAU)", ""]
    for url in DIRECTAS:
        codigo, tipo, cuerpo = sondea(url)
        lineas += [f"## {url}", f"- {codigo} · {tipo}"]
        if codigo == 200:
            lineas.append("```")
            lineas += cuerpo.splitlines()[:6]
            lineas.append("```")
        else:
            lineas.append(f"- {cuerpo[:200]}")
        lineas.append("")

    lineas += ["# Catálogo de datos.gob.es", ""]
    for consulta in BUSQUEDAS:
        url = ("https://datos.gob.es/apidata/catalog/dataset/title/"
               + urllib.parse.quote(consulta) + "?_pageSize=12&_page=0")
        codigo, _, cuerpo = sondea(url, 120000)
        lineas.append(f"## «{consulta}» → {codigo}")
        if codigo != 200:
            lineas += [f"- {cuerpo[:200]}", ""]
            continue
        try:
            items = (json.loads(cuerpo).get("result") or {}).get("items") or []
        except json.JSONDecodeError:
            lineas += ["- respuesta no JSON", ""]
            continue
        for item in items[:8]:
            titulos = item.get("title")
            titulo = (next((t.get("_value") for t in titulos if t.get("_lang") in (None, "es")),
                           titulos[0].get("_value")) if isinstance(titulos, list) else titulos)
            lineas.append(f"- **{titulo}**")
            distribuciones = item.get("distribution") or []
            if isinstance(distribuciones, dict):
                distribuciones = [distribuciones]
            for dist in distribuciones[:4]:
                if isinstance(dist, dict):
                    lineas.append(f"    - {dist.get('accessURL')}")
        lineas.append("")

    (SALIDA / "vivienda.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/vivienda.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
