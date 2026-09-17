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
import red_ministerio as red  # noqa: E402
from xlsx import Libro  # noqa: E402

SALIDA = RAIZ / "sondeos"
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

BASE = "https://www.mites.gob.es"
# Hay dos entradas para lo mismo: la corta, que casi no lleva enlaces, y la
# larga dentro del sitio en castellano, que es la que tiene el índice de
# verdad. Se prueban las dos.
SEMILLAS = [
    ("accidentes", f"{BASE}/estadisticas/eat/welcome.htm"),
    ("accidentes", f"{BASE}/es/estadisticas/condiciones_trabajo_relac_laborales/"
                   f"EAT/welcome.htm"),
    ("convenios", f"{BASE}/estadisticas/cct/welcome.htm"),
    ("convenios", f"{BASE}/es/estadisticas/condiciones_trabajo_relac_laborales/"
                  f"CCT/welcome.htm"),
]

# El ministerio ha cambiado de nombre y de dominio varias veces, y parte de sus
# datos cuelgan de otras máquinas. Si la principal no contesta hay que saber si
# es cosa del sitio o de la red, así que se prueban todas y se anota qué pasa
# con cada una.
PUERTAS = [
    f"{BASE}/estadisticas/eat/welcome.htm",
    "https://www.mitramiss.gob.es/estadisticas/eat/welcome.htm",
    "https://expinterweb.mites.gob.es/",
    "https://www.mites.gob.es/",
    "https://www.ine.es/",
    "https://datos.gob.es/",
]

ENLACE = re.compile(r'href="([^"#]+)"', re.I)
DATOS = re.compile(r"\.(xlsx?|csv|ods)(\?|$)", re.I)
# Andar por el sitio entero sería infinito, y además el ministerio devuelve su
# portada con un 200 para direcciones que no existen, así que un rastreo amplio
# se va a pastar por el organigrama y las notas de prensa. Pero ceñirse a
# /estadisticas/eat/ tampoco vale: el índice bueno cuelga de una ruta larga
# dentro del sitio en castellano. Así que se entra en todo lo que sea
# estadística y se sale de lo que claramente no lo es.
DENTRO = re.compile(r"/estadisticas/", re.I)
FUERA = re.compile(
    r"/(organizacion|mundo|plan_recuperacion|prensa|extras|sec_trabajo|"
    r"portada|buzon\w*|img\d*|css|js)/"
    r"|/(ca|eu|gl|en|fr)/"
    r"|\.(css|js|ico|png|jpe?g|gif|svg|pdf)($|\?)", re.I)

# Para quedarse con los ficheros recientes hay que saber de cuándo es cada uno,
# y el nombre lo dice: ATR_09_2025.xlsx, CCT_04_2016.xls, CCT_2015_DEF.xls.
FECHA_MES = re.compile(r"_(\d{2})_(\d{4})\.", re.I)
FECHA_ANYO = re.compile(r"_(\d{4})_", re.I)


def cuando(url: str) -> tuple[int, int]:
    """Año y mes del fichero, para poder ordenarlos por lo reciente."""
    nombre = url.split("/")[-1]
    mes = FECHA_MES.search(nombre)
    if mes:
        return int(mes.group(2)), int(mes.group(1))
    anyo = FECHA_ANYO.search(nombre)
    if anyo:
        return int(anyo.group(1)), 13   # el definitivo va después de sus meses
    return 0, 0

TOPE_PAGINAS = 120


def codifica(url: str) -> str:
    partes = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        partes.scheme, partes.netloc,
        urllib.parse.quote(partes.path, safe="/%"),
        urllib.parse.quote(partes.query, safe="=&%"),
        partes.fragment,
    ))


def descarga(url: str, limite: int = 12_000_000) -> tuple[int, str, bytes]:
    """El ministerio necesita que se le complete la cadena; los demás no."""
    destino = codifica(url)
    if "mites.gob.es" in urllib.parse.urlsplit(destino).netloc:
        return red.abre(destino, limite=limite)
    try:
        peticion = urllib.request.Request(destino, headers=CABECERAS)
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
        # Cuando falla, el motivo va en el cuerpo: sin él no hay forma de saber
        # si es que la máquina no llega, si el certificado no vale o si el
        # ministerio devuelve un 403 a quien no parezca un navegador.
        detalle = "" if estado == 200 else f" · {texto(datos)[:120]}"
        bitacora.append(f"- `{url}` → {estado} ({tipo.split(';')[0]}){detalle}")
        print(f"    {estado} {url}{detalle}")
        if estado != 200 or "html" not in tipo.lower():
            continue

        pagina = texto(datos)
        for destino in enlaces_de(pagina, url):
            if DATOS.search(destino):
                ficheros.setdefault(tema, set()).add(destino)
            elif (hondura < 2 and DENTRO.search(destino)
                  and not FUERA.search(destino) and destino not in vistas):
                pendientes.append((tema, destino, hondura + 1))

    return ficheros, bitacora


def resume(lineas: list[str], datos: bytes) -> None:
    """Enseña la estructura de un libro: hojas, y las primeras filas de cada una."""
    try:
        libro = Libro(datos)
    except Exception as exc:  # noqa: BLE001
        lineas.append(f"    - no se ha podido abrir: {type(exc).__name__}: {exc}")
        return
    # `hojas` es un diccionario de nombre a ruta dentro del zip, así que hay
    # que hacerlo lista antes de cortarlo.
    nombres = list(libro.hojas)
    lineas.append(f"    - {len(nombres)} hojas: "
                  + ", ".join(f"«{h}»" for h in nombres[:40]))
    # Lo que decide si esto entra en el panel es si el dato baja a provincia,
    # así que se enseñan las hojas que nombran provincias y, si no hay ninguna,
    # las primeras para ver por dónde van los tiros.
    provinciales = [h for h in nombres if "provinc" in h.lower()]
    for nombre in (provinciales or nombres)[:3]:
        filas = libro.filas(nombre)
        lineas.append(f"    - hoja «{nombre}», {len(filas)} filas:")
        for fila in filas[:22]:
            celdas = [str(c) for c in fila[:9] if c not in (None, "")]
            if celdas:
                lineas.append(f"        · {' | '.join(celdas)}")


def puertas() -> list[str]:
    """¿Contesta el ministerio? ¿Y los sitios que sí se sabe que contestan?"""
    lineas = ["## Quién contesta y quién no", ""]
    for url in PUERTAS:
        estado, tipo, datos = descarga(url, limite=2000)
        detalle = "" if estado == 200 else f" · {texto(datos)[:160]}"
        lineas.append(f"- `{url}` → {estado} ({tipo.split(';')[0]}){detalle}")
        print(f"  puerta {estado} {url}{detalle}")
    return lineas + [""]


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    print("=== Ministerio de Trabajo: accidentes y convenios ===")
    aduana = puertas()
    ficheros, bitacora = recorre()

    lineas = ["# Accidentes de trabajo y convenios colectivos: qué publica el "
              "Ministerio", "",
              "Lo que decide si entran en el panel es si hay fichero legible por",
              "máquina y si el dato baja a provincia.", ""] + aduana + [
              "## Páginas recorridas", ""] + bitacora + [""]

    for tema in sorted(ficheros):
        encontrados = sorted(ficheros[tema], key=cuando, reverse=True)
        print(f"  {tema}: {len(encontrados)} ficheros")
        lineas += [f"## {tema} · {len(encontrados)} ficheros", "",
                   "Ordenados del más reciente al más antiguo.", ""]
        for url in encontrados[:60]:
            lineas.append(f"- `{urllib.parse.unquote(url)}` · {cuando(url)}")
        lineas.append("")

        # Abrir por dentro los más recientes: lo viejo está en el .xls binario
        # de toda la vida, que el lector del panel no sabe leer, y lo que hay
        # que saber es de qué formato es lo que se va a descargar cada mes.
        abiertos = 0
        for url in encontrados:
            if abiertos >= 3 or not re.search(r"\.xlsx?($|\?)", url, re.I):
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
