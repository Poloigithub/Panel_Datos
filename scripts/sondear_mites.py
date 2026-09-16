"""¿Qué publica el Ministerio de Trabajo, y en qué formato?

Dos estadísticas interesan y ninguna es del INE:

- **Accidentes de trabajo** (EAT): cuántos accidentes con baja hay, cuántos
  son mortales y en qué sector. Es el dato que falta para hablar de la calidad
  del empleo y no sólo de su cantidad.
- **Convenios colectivos** (CCT): la subida salarial pactada, que se publica
  **cada mes**. Al lado de la encuesta salarial del INE, que llega con año y
  medio de retraso, esto es lectura casi en directo de lo que se está
  firmando, y es el complemento natural del cruce comida-salario que ya está
  en la página de la cesta.

Lo que decide si entran en el panel es siempre lo mismo: si hay fichero
legible por máquina y si el dato baja a provincia. Esto lo averigua andando
por el sitio desde unas cuantas páginas de entrada, listando todo lo que
huela a hoja de cálculo o a CSV, y abriendo por dentro las primeras que
encuentre de cada estadística.
"""

from __future__ import annotations

import html
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
from xlsx import Libro  # noqa: E402

SALIDA = RAIZ / "sondeos"
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

BASE = "https://www.mites.gob.es"
SEMILLAS = [
    ("accidentes", f"{BASE}/estadisticas/eat/welcome.htm"),
    ("accidentes", f"{BASE}/estadisticas/eat/eat22/index.htm"),
    ("convenios", f"{BASE}/estadisticas/cct/welcome.htm"),
    ("índice", f"{BASE}/estadisticas/Index.htm"),
]

ENLACE = re.compile(r'href="([^"#]+)"', re.I)
DATOS = re.compile(r"\.(xlsx?|csv|ods)(\?|$)", re.I)
# Andar por el sitio entero sería infinito; sólo interesa la parte de
# estadísticas, y dentro de ella las dos que se están sondeando.
DENTRO = re.compile(r"/estadisticas/", re.I)

TOPE_PAGINAS = 70


def codifica(url: str) -> str:
    partes = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        partes.scheme, partes.netloc,
        urllib.parse.quote(partes.path, safe="/%"),
        urllib.parse.quote(partes.query, safe="=&%"),
        partes.fragment,
    ))


def descarga(url: str, limite: int = 12_000_000) -> tuple[int, str, bytes]:
    try:
        peticion = urllib.request.Request(codifica(url), headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=120) as respuesta:
            return (respuesta.status, respuesta.headers.get("Content-Type", "?"),
                    respuesta.read(limite))
    except urllib.error.HTTPError as exc:
        return exc.code, "-", str(exc.reason).encode()
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}".encode()


def texto(datos: bytes) -> str:
    for codigo in ("utf-8", "iso-8859-15", "cp1252"):
        try:
            return datos.decode(codigo)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", "replace")


def enlaces_de(pagina: str, desde: str) -> list[str]:
    salida = []
    for bruto in ENLACE.findall(pagina):
        destino = urllib.parse.urljoin(desde, html.unescape(bruto))
        if destino.startswith(BASE):
            salida.append(destino)
    return salida


def recorre() -> tuple[dict[str, set[str]], list[str]]:
    """Anda por las páginas de estadísticas y se queda con los ficheros."""
    pendientes = [(tema, url, 0) for tema, url in SEMILLAS]
    vistas: set[str] = set()
    ficheros: dict[str, set[str]] = {}
    bitacora: list[str] = []

    while pendientes and len(vistas) < TOPE_PAGINAS:
        tema, url, hondura = pendientes.pop(0)
        if url in vistas:
            continue
        vistas.add(url)
        estado, tipo, datos = descarga(url)
        bitacora.append(f"- `{url}` → {estado} ({tipo.split(';')[0]})")
        print(f"    {estado} {url}")
        if estado != 200 or "html" not in tipo.lower():
            continue

        pagina = texto(datos)
        for destino in enlaces_de(pagina, url):
            if DATOS.search(destino):
                ficheros.setdefault(tema, set()).add(destino)
            elif hondura < 2 and DENTRO.search(destino) and destino not in vistas:
                pendientes.append((tema, destino, hondura + 1))

    return ficheros, bitacora


def resume(lineas: list[str], datos: bytes) -> None:
    """Enseña la estructura de un libro: hojas, y las primeras filas de cada una."""
    try:
        libro = Libro(datos)
    except Exception as exc:  # noqa: BLE001
        lineas.append(f"    - no se ha podido abrir: {type(exc).__name__}: {exc}")
        return
    lineas.append(f"    - {len(libro.hojas)} hojas: "
                  + ", ".join(f"«{h}»" for h in libro.hojas[:12]))
    for nombre in libro.hojas[:3]:
        filas = libro.filas(nombre)
        lineas.append(f"    - hoja «{nombre}», {len(filas)} filas:")
        for fila in filas[:12]:
            celdas = [str(c) for c in fila[:8] if c not in (None, "")]
            if celdas:
                lineas.append(f"        · {' | '.join(celdas)}")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    print("=== Ministerio de Trabajo: accidentes y convenios ===")
    ficheros, bitacora = recorre()

    lineas = ["# Accidentes de trabajo y convenios colectivos: qué publica el "
              "Ministerio", "",
              "Lo que decide si entran en el panel es si hay fichero legible por",
              "máquina y si el dato baja a provincia.", "",
              "## Páginas recorridas", ""] + bitacora + [""]

    for tema in sorted(ficheros):
        encontrados = sorted(ficheros[tema])
        print(f"  {tema}: {len(encontrados)} ficheros")
        lineas += [f"## {tema} · {len(encontrados)} ficheros", ""]
        for url in encontrados[:60]:
            lineas.append(f"- `{urllib.parse.unquote(url)}`")
        lineas.append("")

        # Abrir por dentro los primeros que sean hoja de cálculo.
        abiertos = 0
        for url in encontrados:
            if abiertos >= 2 or not re.search(r"\.xlsx?($|\?)", url, re.I):
                continue
            estado, tipo, datos = descarga(url)
            lineas.append(f"### Por dentro: `{urllib.parse.unquote(url.split('/')[-1])}`")
            lineas.append(f"    - descarga: {estado}, {len(datos)} bytes")
            print(f"      abriendo {url.split('/')[-1]}: {estado}, {len(datos)} bytes")
            if estado == 200:
                resume(lineas, datos)
            lineas.append("")
            abiertos += 1

    (SALIDA / "mites.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/mites.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
