"""Bajas laborales, cuarto sondeo: qué hay dentro de un ejercicio.

El tercero encontró la estructura: la Seguridad Social publica la incapacidad
temporal **con una página por ejercicio**, de 2005 a 2026. Las de los últimos
años llevan un UUID en la dirección, así que habrá que leerlas del índice y no
construirlas, igual que con las huelgas y con el Pink Sheet.

Falta lo que decide todo: **qué hay dentro de una de esas páginas**, en qué
formato, y sobre todo **si baja a provincia**. De eso depende que esta sección
tenga Castellón -y entonces es mejor que la del INE- o no lo tenga.

Se miran tres ejercicios y no uno: el del año en curso puede estar a medias, y
comparar con los dos anteriores dice si la forma se mantiene de un año a otro,
que es lo que determina si un descargador puede vivir de esto.
"""

from __future__ import annotations

import html as htmllib
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
BASE = ("https://www.seg-social.es/wps/portal/wss/internet/"
        "EstadisticasPresupuestosEstudios/Estadisticas/EST45/EST46")

EJERCICIOS = [
    ("2026", BASE + "/e28473ce-69f2-4048-af5f-5b81e140f5c4"),
    ("2025", BASE + "/e166660f-31fd-433d-b24e-869400759998"),
    ("2024", BASE + "/0cb37f8c-e3ae-49a2-b182-53866c9d16c2"),
]

NAVEGADOR = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9",
}


def pide(url, intentos=3, limite=30_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(
                    peticion, timeout=120,
                    context=ssl.create_default_context()) as r:
                return (r.status, r.headers.get("Content-Type", "?"),
                        r.read(limite), "")
        except urllib.error.HTTPError as exc:
            return exc.code, "-", exc.read(400), ""
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * numero)
    return 0, "-", b"", ultimo


def limpia(t: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def enlaces_de(html: str, base: str):
    salida, vistos = [], set()
    for href, dentro in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                                   html, re.I | re.S):
        texto = limpia(dentro)
        entero = urllib.parse.urljoin(base, htmllib.unescape(href))
        if (texto, entero) not in vistos:
            vistos.add((texto, entero))
            salida.append((texto, entero))
    return salida


# Los enlaces de navegación se repiten en todas las páginas del portal y no
# dicen nada; lo que interesa es lo propio de este ejercicio.
NAVEGACION = re.compile(
    r"inicio|conocenos|trabajadores|pensionistas|empresarios|clases pasivas|"
    r"sugerencias|consultas|idiomas|castellano|buscador|cookies|"
    r"ir a contenido|desplegar|acceso directo|ejercicio \d{4}|"
    r"series historicas|estadisticas|otras prestaciones", re.I)


def describe_fichero(l, texto, url):
    """Bajarlo y decir qué es de verdad, no lo que promete la extensión."""
    estado, tipo, datos, fallo = pide(url, intentos=2, limite=30_000_000)
    l.append(f"    - descarga: {estado} ({tipo}), {len(datos):,} bytes"
             + (f" · {fallo}" if fallo else ""))
    if estado != 200 or len(datos) < 200:
        return
    if datos[:2] == b"PK" or datos[:8] == xls.FIRMA:
        libro = xlsx.Libro(datos) if datos[:2] == b"PK" else xls.Libro(datos)
        hojas = list(libro.hojas)
        l.append(f"    - hoja de cálculo, {len(hojas)} hojas: {hojas[:14]}")
        for nombre in hojas[:3]:
            filas = list(libro.filas(nombre))
            l.append(f"    - «{nombre}», {len(filas)} filas:")
            for fila in filas[:14]:
                celdas = [str(c) for c in fila[:9] if c not in (None, "")]
                if celdas:
                    l.append("        · " + " | ".join(c[:26] for c in celdas))
            # La pregunta que decide la sección.
            texto_hoja = " ".join(str(c) for f in filas for c in f if c)
            for palabra in ("provincia", "Castell", "comunidad", "Valencia"):
                cuantas = len(re.findall(palabra, texto_hoja, re.I))
                l.append(f"        · «{palabra}» aparece {cuantas} veces")
    elif datos[:4] == b"%PDF":
        l.append("    - es un PDF")
    else:
        l.append(f"    - empieza por {datos[:60]!r}")


def main() -> None:
    l = ["# Bajas laborales, cuarto sondeo: dentro de un ejercicio", "",
         "La Seguridad Social publica la incapacidad temporal con una página",
         "por ejercicio, de 2005 a 2026. Aquí se mira qué hay dentro de tres de",
         "ellas y, sobre todo, **si baja a provincia**: de eso depende que esta",
         "sección tenga Castellón o no.", ""]

    for anyo, url in EJERCICIOS:
        l += [f"## Ejercicio {anyo}", "", f"`{url[:130]}`", ""]
        estado, tipo, datos, fallo = pide(url, limite=8_000_000)
        l.append(f"- {estado} ({tipo}), {len(datos)} bytes"
                 + (f" · {fallo}" if fallo else ""))
        if estado != 200 or len(datos) < 800:
            l.append("")
            continue
        html = datos.decode("utf-8", "replace")
        propios = [(t, u) for t, u in enlaces_de(html, url)
                   if t and not NAVEGACION.search(t)]
        l.append(f"- {len(propios)} enlaces propios de este ejercicio:")
        for texto, destino in propios[:25]:
            l.append(f"    · «{texto[:80]}»")
            l.append(f"      {destino[:140]}")
        l.append("")

        # Del primer año se baja lo que parezca dato para ver su forma.
        if anyo == EJERCICIOS[0][0] or anyo == "2025":
            for texto, destino in propios[:4]:
                l += [f"### «{texto[:70]}»", ""]
                describe_fichero(l, texto, destino)
                l.append("")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "bajas-iv.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
