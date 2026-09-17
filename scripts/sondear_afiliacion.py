"""Afiliación a la Seguridad Social y elecciones sindicales: ¿hay por dónde?

Las dos son del Ministerio de Trabajo y las dos importan por lo mismo que los
accidentes: bajan a provincia, que es donde se acaban casi todas las
estadísticas de este país.

- **Afiliación**: cuánta gente cotiza cada mes. Además de valer por sí sola,
  es lo que convierte los accidentes en una tasa: ahora mismo la página de
  siniestralidad tiene que reconocer que una subida puede venir de que haya
  más accidentes o de que haya más gente trabajando.
- **Autónomos**: los que cotizan por cuenta propia, que van aparte.

Las **elecciones sindicales** ya no se buscan aquí. El índice de «Condiciones
de trabajo y relaciones laborales» del ministerio lo tiene todo -accidentes,
convenios, huelgas, despidos, enfermedades profesionales, regulación de
empleo, FOGASA, mediación y arbitraje- y ahí no están: no las publica su
portal de estadística.

Lo que hay que averiguar es lo de siempre, y una cosa más que ya ha mordido:
si los ficheros son XLSX o el `.xls` binario anterior a 2007, que el lector
del panel no abre. Con los convenios colectivos pasó eso y se quedaron fuera.
"""

from __future__ import annotations

import html
import re
import sys
import urllib.parse
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import red_ministerio as red  # noqa: E402
from xlsx import Libro  # noqa: E402

SALIDA = RAIZ / "sondeos"
BASE = "https://www.mites.gob.es"

# Las entradas de verdad, que costó encontrar: el árbol de ficheros usa
# códigos -eat, cct, hue, reg- y ninguno se llama «afi», pero el índice de
# mercado de trabajo sí las nombra con todas las letras.
SEMILLAS = [
    ("afiliación", f"{BASE}/es/estadisticas/mercado_trabajo/AFI/welcome.htm"),
    ("afiliación", f"{BASE}/es/estadisticas/mercado_trabajo/index.htm"),
    ("autónomos", f"{BASE}/es/estadisticas/mercado_trabajo/TAASS/welcome.htm"),
    ("empresas", f"{BASE}/es/estadisticas/mercado_trabajo/EMP/welcome.htm"),
]

ENLACE = re.compile(r'href="([^"#]+)"', re.I)
DATOS = re.compile(r"\.(xlsx?|csv|ods)(\?|$)", re.I)
DENTRO = re.compile(r"/estadisticas/", re.I)
FUERA = re.compile(
    r"/(organizacion|mundo|plan_recuperacion|prensa|extras|sec_trabajo|"
    r"portada|buzon\w*|img\d*|css|js)/"
    r"|/(ca|eu|gl|en|fr)/"
    r"|\.(css|js|ico|png|jpe?g|gif|svg|pdf)($|\?)", re.I)

# Lo que se busca dentro de la maraña de ficheros del boletín. Las palabras
# van completas a propósito: la primera versión buscaba «afi» suelto y se
# traía todas las monográficas, porque «monogr-afi-ca» lo contiene.
TEMAS = {
    "afiliación": ("afiliad", "afiliacion", "cotizant", "/afi/", "_afi_",
                   "/afi", "afi_"),
    "autónomos": ("autonom", "taass", "cuenta propia"),
}

TOPE_PAGINAS = 120


def texto(datos: bytes) -> str:
    for codigo in ("utf-8", "iso-8859-15", "cp1252"):
        try:
            return datos.decode(codigo)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", "replace")


def codifica(url: str) -> str:
    partes = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        partes.scheme, partes.netloc,
        urllib.parse.quote(partes.path, safe="/%"),
        urllib.parse.quote(partes.query, safe="=&%"),
        partes.fragment))


def recorre() -> tuple[set[str], list[str]]:
    pendientes = [(url, 0) for _, url in SEMILLAS]
    vistas: set[str] = set()
    ficheros: set[str] = set()
    bitacora: list[str] = []

    while pendientes and len(vistas) < TOPE_PAGINAS:
        url, hondura = pendientes.pop(0)
        if url in vistas:
            continue
        vistas.add(url)
        estado, tipo, datos = red.abre(codifica(url), limite=4_000_000)
        bitacora.append(f"- `{url}` → {estado} ({tipo.split(';')[0]})")
        print(f"    {estado} {url}")
        if estado != 200 or "html" not in tipo.lower():
            continue
        pagina = texto(datos)
        for bruto in ENLACE.findall(pagina):
            destino = urllib.parse.urljoin(url, html.unescape(bruto))
            if not destino.startswith(BASE):
                continue
            if DATOS.search(destino):
                ficheros.add(destino)
            elif (hondura < 2 and DENTRO.search(destino)
                  and not FUERA.search(destino) and destino not in vistas):
                pendientes.append((destino, hondura + 1))

    return ficheros, bitacora


def resume(lineas: list[str], datos: bytes) -> None:
    try:
        libro = Libro(datos)
    except Exception as exc:  # noqa: BLE001
        lineas.append(f"    - no se ha podido abrir: {type(exc).__name__}: {exc}")
        return
    nombres = list(libro.hojas)
    lineas.append(f"    - {len(nombres)} hojas: "
                  + ", ".join(f"«{h}»" for h in nombres[:30]))
    provinciales = [h for h in nombres if "prov" in h.lower()]
    for nombre in (provinciales or nombres)[:2]:
        filas = libro.filas(nombre)
        lineas.append(f"    - hoja «{nombre}», {len(filas)} filas:")
        for fila in filas[:25]:
            celdas = [("" if c is None else str(c)) for c in fila[:9]]
            while celdas and celdas[-1] == "":
                celdas.pop()
            if celdas:
                lineas.append(f"        · {' | '.join(celdas)}")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    print("=== Afiliación y elecciones sindicales ===")
    ficheros, bitacora = recorre()

    lineas = ["# Afiliación y elecciones sindicales: qué publica el ministerio",
              "", "Lo que decide si entran: fichero legible -XLSX, no el .xls",
              "binario- y dato que baje a provincia.", "",
              "## Páginas recorridas", ""] + bitacora + [""]

    cuantos = {"xlsx": 0, "xls": 0, "csv": 0, "ods": 0}
    for url in ficheros:
        extension = url.rsplit(".", 1)[-1].split("?")[0].lower()
        if extension in cuantos:
            cuantos[extension] += 1
    lineas += [f"## {len(ficheros)} ficheros en total", "",
               "Por formato: " + ", ".join(f"{k}: {v}" for k, v in cuantos.items()),
               ""]

    # El mapa del terreno: qué carpetas hay y en qué formato publica cada una.
    # Buscar por palabras a ciegas ya ha fallado una vez; con las carpetas
    # delante se ve de un vistazo dónde está cada estadística.
    carpetas: dict[str, dict[str, int]] = {}
    for url in ficheros:
        trozos = urllib.parse.urlsplit(url).path.strip("/").split("/")
        carpeta = "/".join(trozos[1:3]) if len(trozos) > 2 else trozos[0]
        extension = url.rsplit(".", 1)[-1].split("?")[0].lower()
        carpetas.setdefault(carpeta, {}).setdefault(extension, 0)
        carpetas[carpeta][extension] += 1
    lineas += ["## Carpetas y en qué formato publica cada una", ""]
    for carpeta in sorted(carpetas):
        formatos = ", ".join(f"{k}: {v}" for k, v in sorted(carpetas[carpeta].items()))
        lineas.append(f"- `{carpeta}` · {formatos}")
    lineas.append("")

    for tema, palabras in TEMAS.items():
        tocan = sorted(u for u in ficheros
                       if any(p in u.lower() for p in palabras))
        print(f"  {tema}: {len(tocan)} ficheros")
        lineas += [f"## {tema} · {len(tocan)} ficheros", ""]
        for url in tocan[:50]:
            lineas.append(f"- `{urllib.parse.unquote(url)}`")
        lineas.append("")

        abiertos = 0
        for url in tocan:
            if abiertos >= 2 or not re.search(r"\.xlsx($|\?)", url, re.I):
                continue
            estado, _, datos = red.abre(codifica(url))
            lineas.append(f"### Por dentro: `{urllib.parse.unquote(url.split('/')[-1])}`")
            lineas.append(f"    - descarga: {estado}, {len(datos)} bytes")
            print(f"      abriendo {url.split('/')[-1]}: {estado}, {len(datos)} bytes")
            if estado == 200 and datos[:2] == b"PK":
                resume(lineas, datos)
            lineas.append("")
            abiertos += 1
        if abiertos == 0:
            lineas += ["*No hay ningún XLSX que abrir en este tema: o no hay "
                       "ficheros o están todos en el .xls binario.*", ""]

    (SALIDA / "afiliacion.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/afiliacion.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
