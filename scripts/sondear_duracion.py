"""¿Por qué una baja dura cincuenta y tantos días de media?

La cifra está comprobada: la duración media que publica la fuente es
exactamente los días de baja divididos entre los procesos terminados. Se
verificó con Zaragoza y da cero de diferencia. Pero cincuenta y tres días
parecen muchos comparados con los cuarenta y pico que se suelen citar, así que
hay que entender de qué hablan unos y otros.

**La hipótesis**: el fichero que usa el panel es el del *sistema* -mutuas
colaboradoras más el Instituto Nacional de la Seguridad Social más el Instituto
Social de la Marina-. Las mutuas llevan la mayoría de bajas por contingencias
comunes, que son las cortas; el instituto nacional se queda con los procesos
largos. Una media del sistema entero tiene que salir más alta que una media de
mutuas, que es la que suele aparecer en prensa.

Se comprueba de tres maneras:

1. Bajando **los dos ficheros del mismo año** -el de mutuas y el del sistema- y
   comparando su duración media provincia a provincia.
2. Separando **contingencias comunes de profesionales** en la tabla mensual, que
   ahora se puede porque están identificados los códigos de días (20) y de
   procesos terminados (19).
3. Buscando si en algún sitio hay **mediana o reparto por tramos** de duración,
   que es lo que de verdad contesta «cuánto dura una baja normal»: con unas
   pocas bajas muy largas, la media se dispara y la mediana no.
"""

from __future__ import annotations

import collections
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import xls  # noqa: E402
import xlsx  # noqa: E402

SALIDA = RAIZ / "sondeos"
WCM = "https://www.seg-social.es/wps/wcm/connect/wss/"

# Los dos ficheros de 2025: las mutuas solas y el sistema entero.
MUTUAS_2025 = (WCM + "5aa27c25-81ea-446e-9fc3-d96e090d1c65/"
               "Publicaci%C3%B3n%2BIT%2Bmcss%2B%2B2025.xlsx?MOD=AJPERES")
SISTEMA_2025 = (WCM + "58bb210f-343b-4591-a923-e11217cff5d1/"
                "Publicacion_IT_mcss%2Binss%2Bism%2B2025_.xlsx?MOD=AJPERES")

NAVEGADOR = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0 Safari/537.36"),
             "Accept": "*/*"}

# Palabras que delatarían un reparto por tramos o una mediana.
PISTAS_REPARTO = ("mediana", "percentil", "tramo", "intervalo", "duracion de",
                  "dias de duracion", "hasta 15", "mas de 365", "365 dias",
                  "distribucion")


def normaliza(texto) -> str:
    crudo = str(texto or "")
    tildes = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")
    return re.sub(r"\s+", " ", crudo.translate(tildes)).strip().lower()


def pide(url, intentos=3, limite=80_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            p = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(
                    p, timeout=300, context=ssl.create_default_context()) as r:
                return r.status, r.read(limite), ""
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(400), ""
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(4 * numero)
    return 0, b"", ultimo


def abre(url):
    estado, datos, fallo = pide(url)
    if estado != 200 or (datos[:2] != b"PK" and datos[:8] != xls.FIRMA):
        return None, f"{estado} · {fallo or datos[:40]!r}"
    libro = xlsx.Libro(datos) if datos[:2] == b"PK" else xls.Libro(datos)
    return libro, f"{len(datos):,} bytes"


def duraciones_de(libro) -> dict[str, float]:
    """Duración media por provincia, de la tabla que lleva los nombres."""
    for nombre in libro.hojas:
        filas = list(libro.filas(nombre))
        cabecera_n = None
        for numero, fila in enumerate(filas[:40]):
            if any("comunidad autonoma" in normaliza(c) for c in fila):
                cabecera_n = numero
                break
        if cabecera_n is None:
            continue
        cabecera = filas[cabecera_n]
        donde_prov = next((i for i, c in enumerate(cabecera)
                           if normaliza(c) == "provincia"), None)
        donde_dur = next((i for i, c in enumerate(cabecera)
                          if "duracion media" in normaliza(c)), None)
        if donde_prov is None or donde_dur is None:
            continue
        salida = {}
        for fila in filas[cabecera_n + 1:]:
            if max(donde_prov, donde_dur) >= len(fila):
                continue
            provincia = normaliza(fila[donde_prov])
            if provincia and provincia != "total" and isinstance(
                    fila[donde_dur], (int, float)):
                salida[provincia] = float(fila[donde_dur])
        if salida:
            return salida
    return {}


def main() -> None:
    l = ["# ¿Por qué una baja dura cincuenta y tantos días?", "",
         "La cifra está comprobada -es los días de baja entre los procesos",
         "terminados, cero de diferencia-. Lo que falta es entender de qué",
         "habla comparada con los cuarenta y pico que se suelen citar.", ""]

    # ---------------------------------------- 1. mutuas contra sistema
    l += ["## Mutuas solas contra el sistema entero, 2025", ""]
    libros = {}
    for etiqueta, url in (("mutuas", MUTUAS_2025), ("sistema", SISTEMA_2025)):
        libro, detalle = abre(url)
        l.append(f"- {etiqueta}: {detalle}")
        if libro:
            libros[etiqueta] = libro
            l.append(f"    hojas: {list(libro.hojas)}")
    l.append("")

    if len(libros) == 2:
        a = duraciones_de(libros["mutuas"])
        b = duraciones_de(libros["sistema"])
        comunes = sorted(set(a) & set(b))
        l.append(f"- provincias en los dos ficheros: {len(comunes)}")
        if comunes:
            media_a = sum(a[p] for p in comunes) / len(comunes)
            media_b = sum(b[p] for p in comunes) / len(comunes)
            l.append(f"- duración media (promedio simple de provincias):")
            l.append(f"    · sólo mutuas:   **{media_a:.1f} días**")
            l.append(f"    · sistema entero: **{media_b:.1f} días**")
            l.append(f"    · diferencia: {media_b - media_a:+.1f} días")
            l.append("")
            l.append("- provincia a provincia (las diez primeras y Castellón):")
            for p in comunes[:10] + [x for x in comunes if "castell" in x]:
                l.append(f"    · {p}: mutuas {a[p]:.1f} · sistema {b[p]:.1f} "
                         f"({b[p] - a[p]:+.1f})")
        l.append("")

    # ------------------------------- 2. común contra profesional, y por sexo
    l += ["## Separando contingencias, desde la tabla mensual", ""]
    libro = libros.get("sistema")
    if libro and "Datos mensuales" in libro.hojas:
        filas = list(libro.filas("Datos mensuales"))
        cabecera = [str(c or "").strip() for c in filas[0]]
        col = {n: i for i, n in enumerate(cabecera)}
        l.append(f"- columnas: {cabecera}")

        def celda(fila, nombre):
            i = col.get(nombre)
            return fila[i] if i is not None and i < len(fila) else None

        # Días (código 20) y procesos terminados (código 19), los dos probados.
        cuentas: dict[tuple, dict[str, float]] = collections.defaultdict(
            lambda: {"dias": 0.0, "fin": 0.0})
        for fila in filas[1:]:
            codigo = str(celda(fila, "Indicador") or "")
            cantidad = celda(fila, "Suma de Cantidad")
            if codigo not in ("19", "20") or not isinstance(cantidad, (int, float)):
                continue
            clave = (str(celda(fila, "Contingencia") or "")[:24],
                     str(celda(fila, "Sexo") or ""))
            cuentas[clave]["dias" if codigo == "20" else "fin"] += cantidad

        l.append("- duración media = días (código 20) / terminados (código 19):")
        for clave in sorted(cuentas):
            d, f = cuentas[clave]["dias"], cuentas[clave]["fin"]
            if f:
                l.append(f"    · {clave[0]} · {clave[1]}: {d/f:.1f} días "
                         f"({f:,.0f} procesos)")
        l.append("")

    # ---------------------------------------- 3. ¿hay mediana o tramos?
    l += ["## ¿Hay mediana o reparto por tramos en algún sitio?", ""]
    for etiqueta, libro in libros.items():
        l.append(f"### {etiqueta}")
        l.append("")
        for nombre in libro.hojas:
            filas = list(libro.filas(nombre))
            textos = {normaliza(c) for fila in filas[:200] for c in fila[:20]
                      if c and not str(c).replace(".", "").isdigit()}
            casan = sorted({t for t in textos
                            if any(p in t for p in PISTAS_REPARTO)})
            l.append(f"- «{nombre}»: {len(filas)} filas · "
                     f"{'nada que suene a tramos' if not casan else casan[:8]}")
        l.append("")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "duracion.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
