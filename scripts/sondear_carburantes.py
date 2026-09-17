"""Carburantes: cuánto detalle hay, y desde cuándo.

Tres preguntas que deciden la forma de la sección:

1. **¿Un solo viaje o cincuenta y dos?** La API del ministerio sirve todas las
   gasolineras de España de una vez, pero sólo sirve para los tres ámbitos del
   panel si cada estación dice de qué provincia es. Aquí se mira qué campos
   trae de verdad una estación y cuánto pesa la respuesta entera.

2. **¿Hay histórico oficial?** La API da la foto de hoy y nada más. La Comisión
   Europea publica un boletín semanal con los precios de cada estado miembro
   desde hace veinte años: si se puede leer, España tendría serie de verdad en
   vez de empezar el día que se enchufe esto.

3. **¿Se puede leer lo ya calculado?** En `preciodiariogasolina` hay media
   nacional diaria desde marzo. Es un CSV en un repositorio público, que es
   justo lo que la biblioteca estándar sabe leer sin ayuda.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import xls  # noqa: E402
import xlsx  # noqa: E402

SALIDA = RAIZ / "sondeos"

NAVEGADOR = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9",
}

TODAS = ("https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
         "PreciosCarburantes/EstacionesTerrestres/")
PROVINCIAS = ("https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
              "PreciosCarburantes/Listados/Provincias/")

BOLETIN_PAGINA = ("https://energy.ec.europa.eu/data-and-analysis/"
                  "weekly-oil-bulletin_en")
BOLETIN_DIRECTO = ("https://energy.ec.europa.eu/document/download/"
                   "Oil_Bulletin_Prices_History.xlsx")

YA_CALCULADO = ("https://raw.githubusercontent.com/Poloigithub/"
                "preciodiariogasolina/main/precios_carburantes.csv")


def pide(url: str, intentos: int = 4, limite: int = 60_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(peticion, timeout=180) as respuesta:
                return (respuesta.status,
                        respuesta.headers.get("Content-Type", "?"),
                        respuesta.read(limite), numero)
        except urllib.error.HTTPError as exc:
            return exc.code, "-", exc.read(600), numero
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(2 ** numero)
    return 0, "-", ultimo.encode(), intentos


def main() -> None:
    l = ["# Carburantes: cuánto detalle hay, y desde cuándo", ""]

    # ---------------------------------------------------- 1. toda España
    l += ["## Todas las estaciones de España, de un viaje", ""]
    inicio = time.time()
    estado, tipo, datos, intento = pide(TODAS)
    tardanza = time.time() - inicio
    l += [f"`{TODAS}`", "",
          f"- {estado} ({tipo}), {len(datos):,} bytes, intento {intento}, "
          f"{tardanza:.1f} s"]
    if estado == 200 and datos[:1] in (b"{", b"["):
        cuerpo = json.loads(datos.decode("utf-8-sig", "replace"))
        lista = cuerpo.get("ListaEESSPrecio", []) if isinstance(cuerpo, dict) else cuerpo
        l += [f"- fecha que declara: {cuerpo.get('Fecha')!r}" if isinstance(cuerpo, dict) else "",
              f"- {len(lista):,} estaciones"]
        if lista:
            l += ["- **todos** los campos de la primera estación:"]
            for clave, valor in lista[0].items():
                l.append(f"    · {clave}: {valor!r}")
            # ¿Se puede agrupar por provincia sin pedir nada más?
            campos = [c for c in lista[0] if "provinc" in c.lower()]
            l += ["", f"- campos con «provincia» en el nombre: {campos}"]
            for campo in campos:
                valores = sorted({str(e.get(campo, "")) for e in lista})
                l.append(f"    · {campo}: {len(valores)} valores distintos, "
                         f"p. ej. {valores[:6]}")
            # Cuántas estaciones caen en Castellón y en la Comunitat
            for campo in campos:
                cuenta = {}
                for e in lista:
                    cuenta[str(e.get(campo, ""))] = cuenta.get(str(e.get(campo, "")), 0) + 1
                interesantes = {k: v for k, v in cuenta.items()
                                if k in ("12", "03", "46", "CASTELLON", "CASTELLÓN",
                                         "VALENCIA", "ALICANTE")}
                if interesantes:
                    l.append(f"    · estaciones por {campo}: {interesantes}")
            # Cuántas publican cada precio
            for campo in ("Precio Gasolina 95 E5", "Precio Gasoleo A",
                          "Precio Gasolina 98 E5", "Precio Gasoleo Premium",
                          "Precio Gases licuados del petróleo"):
                con = sum(1 for e in lista if str(e.get(campo, "")).strip())
                l.append(f"    · con «{campo}»: {con:,} de {len(lista):,}")
    else:
        l.append(f"    · {datos[:300]!r}")
    l.append("")

    # ---------------------------------------------------- 2. provincias
    l += ["## Listado de provincias, para saber cuáles son la Comunitat", ""]
    estado, tipo, datos, intento = pide(PROVINCIAS)
    l += [f"- {estado} ({tipo}), {len(datos)} bytes"]
    if estado == 200:
        lista = json.loads(datos.decode("utf-8-sig", "replace"))
        valencianas = [p for p in lista
                       if "valencia" in str(p.get("CCAA", "")).lower()]
        l += [f"- {len(lista)} provincias", "- las de la Comunitat Valenciana:"]
        for p in valencianas:
            l.append(f"    · {json.dumps(p, ensure_ascii=False)}")
    l.append("")

    # ---------------------------------------------------- 3. boletín europeo
    l += ["## Boletín petrolero de la Comisión Europea (histórico)", ""]
    for nombre, url in [("página", BOLETIN_PAGINA), ("fichero", BOLETIN_DIRECTO)]:
        estado, tipo, datos, intento = pide(url, limite=20_000_000)
        l += [f"### {nombre}", "", f"`{url}`", "",
              f"- {estado} ({tipo}), {len(datos):,} bytes, intento {intento}"]
        if estado == 200 and nombre == "página":
            html = datos.decode("utf-8", "replace")
            hojas = re.findall(r'href="([^"]+\.(?:xlsx|xls))"', html, re.I)
            l.append(f"- hojas de cálculo enlazadas: {len(hojas)}")
            for h in hojas[:12]:
                l.append(f"    · {h}")
        elif estado == 200 and (datos[:2] == b"PK" or datos[:8] == xls.FIRMA):
            libro = xlsx.Libro(datos) if datos[:2] == b"PK" else xls.Libro(datos)
            l.append(f"- hojas: {list(libro.hojas)[:12]}")
            primera = list(libro.hojas)[0]
            filas = list(libro.filas(primera))
            l.append(f"- «{primera}», {len(filas)} filas; primeras:")
            for fila in filas[:8]:
                l.append("    · " + " | ".join(str(c or "") for c in fila[:10]))
        elif estado == 200:
            l.append(f"    · empieza por {datos[:60]!r}")
        else:
            l.append(f"    · {datos[:200]!r}")
        l.append("")

    # ---------------------------------------------------- 4. lo ya calculado
    l += ["## Lo que ya está calculado en `preciodiariogasolina`", ""]
    estado, tipo, datos, intento = pide(YA_CALCULADO, limite=4_000_000)
    l += [f"`{YA_CALCULADO}`", "", f"- {estado} ({tipo}), {len(datos):,} bytes"]
    if estado == 200:
        texto = datos.decode("utf-8-sig", "replace")
        filas = list(csv.DictReader(io.StringIO(texto)))
        l += [f"- {len(filas)} días, de {filas[0]['Fecha']} a {filas[-1]['Fecha']}",
              f"- columnas: {list(filas[0])}",
              f"- primera: {json.dumps(filas[0], ensure_ascii=False)}",
              f"- última:  {json.dumps(filas[-1], ensure_ascii=False)}"]
        # ¿Hay días sin dato en medio?
        import datetime as dt
        fechas = [dt.date.fromisoformat(f["Fecha"]) for f in filas]
        huecos = (fechas[-1] - fechas[0]).days + 1 - len(fechas)
        l.append(f"- días que faltan entre el primero y el último: {huecos}")
    l.append("")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "carburantes.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
