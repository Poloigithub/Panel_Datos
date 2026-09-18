"""Bajas laborales, tercer sondeo: dejar de filtrar y mirar.

Los dos anteriores fallaron por lo mismo, y el fallo es mío: iba con
expresiones regulares que decidían de antemano qué forma tendría la respuesta.
Busqué `href="...xlsx"` en un portal que sirve los documentos **sin extensión**,
y busqué carpetas con un patrón que en el índice del anuario no existe. Las dos
veces concluí «no hay nada» cuando lo que había era un filtro mal puesto.

Así que esto no filtra. Vuelca:

- el **índice del anuario del ministerio**, con todos sus enlaces y su texto;
- la página de **Incapacidad Temporal de la Seguridad Social**, con todos sus
  enlaces y su texto.

Sale un volcado más largo, pero se lee una vez y se decide con lo que hay
delante en vez de con lo que uno supone que habrá.
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
import red_ministerio  # noqa: E402

SALIDA = RAIZ / "sondeos"

ANUARIO_INDICE = ("https://www.mites.gob.es/ficheros/ministerio/estadisticas/"
                  "anuarios/2024/index.htm")
SS_IT = ("https://www.seg-social.es/wps/portal/wss/internet/"
         "EstadisticasPresupuestosEstudios/Estadisticas/EST45/EST46")

NAVEGADOR = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "es-ES,es;q=0.9",
}


def pide(url, intentos=3, limite=12_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(
                    peticion, timeout=90,
                    context=ssl.create_default_context()) as r:
                return r.status, r.read(limite), ""
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(400), ""
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * numero)
    return 0, b"", ultimo


def limpia(trozo: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", trozo))).strip()


def enlaces_de(html: str, base: str) -> list[tuple[str, str]]:
    """Todos los enlaces con su texto. Sin filtrar por nada."""
    salida, vistos = [], set()
    for href, dentro in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                                   html, re.I | re.S):
        texto = limpia(dentro)
        entero = urllib.parse.urljoin(base, htmllib.unescape(href))
        clave = (texto, entero)
        if clave not in vistos:
            vistos.add(clave)
            salida.append(clave)
    return salida


def vuelca(l: list[str], titulo: str, url: str, html: str) -> None:
    l += [f"## {titulo}", "", f"`{url}`", ""]
    enlaces = enlaces_de(html, url)
    l.append(f"- {len(enlaces)} enlaces en la página, **todos**:")
    for texto, destino in enlaces:
        # El texto primero, que es lo que dice de qué va.
        l.append(f"    · «{texto[:70] or '(sin texto)'}»")
        l.append(f"      {destino[:150]}")
    l.append("")

    # Y el texto visible de la página, por si el dato está fuera de un enlace.
    cuerpo = limpia(re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", html))
    l.append("- texto visible de la página:")
    for trozo in range(0, min(len(cuerpo), 6000), 110):
        l.append("    " + cuerpo[trozo:trozo + 110])
    l.append("")


def main() -> None:
    l = ["# Bajas laborales, tercer sondeo: sin filtros", "",
         "Los dos anteriores dieron «no hay nada» donde lo que había era un",
         "filtro mal puesto: busqué ficheros por su extensión en un portal que",
         "los sirve sin ella. Esto vuelca las dos páginas enteras.", ""]

    # El anuario necesita la cadena de certificados completada.
    try:
        estado, tipo, datos = red_ministerio.abre(ANUARIO_INDICE, intentos=3,
                                                  limite=8_000_000)
        l.append(f"- anuario: {estado} ({tipo}), {len(datos)} bytes")
        if estado == 200 and len(datos) > 800:
            vuelca(l, "El índice del anuario del ministerio", ANUARIO_INDICE,
                   datos.decode("utf-8", "replace"))
        else:
            l.append("")
    except Exception as exc:  # noqa: BLE001
        l += [f"- anuario: reventó · {type(exc).__name__}: {exc}", ""]

    estado, datos, fallo = pide(SS_IT, limite=8_000_000)
    l.append(f"- Seguridad Social: {estado}"
             + (f" · {fallo}" if fallo else f" · {len(datos)} bytes"))
    if estado == 200 and len(datos) > 800:
        vuelca(l, "Incapacidad Temporal · Seguridad Social", SS_IT,
               datos.decode("utf-8", "replace"))
    else:
        l.append("")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "bajas-iii.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print(f"escrito sondeos/bajas-iii.md ({len(l)} líneas)")


if __name__ == "__main__":
    main()
