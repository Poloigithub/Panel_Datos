"""Lanzamientos practicados, del CGPJ: por hipoteca, por alquiler y otros.

La Estadística sobre Ejecuciones Hipotecarias del INE cuenta ejecuciones, que
son procedimientos, y sólo de hipoteca. Quien cuenta desahucios de verdad
-lanzamientos practicados- y los reparte según de dónde vienen es el Consejo
General del Poder Judicial, en las series de «Efecto de la crisis en los
órganos judiciales»:

- lanzamientos consecuencia de una ejecución hipotecaria,
- lanzamientos consecuencia de la Ley de Arrendamientos Urbanos, que en la
  práctica son alquileres impagados,
- otros (laudos arbitrales, procesos de familia…).

El fichero es un XLSX trimestral cuyo nombre cambia cada vez («… por provincias
1T-2026_revisado.xlsx»), así que hay que buscarlo en su página en vez de
apuntar a una dirección fija.

Dos avisos de la propia metodología del CGPJ que este módulo respeta:

- Los lanzamientos de los **servicios comunes** no son exhaustivos -no todos
  los partidos judiciales tienen uno- y el CGPJ advierte en mayúsculas de que
  no deben sumarse con los de los juzgados. Aquí sólo se usan los de los
  juzgados, que sí son completos y arrancan en 2013.
- El fichero trae, debajo de la tabla, un segundo bloque con variaciones en
  tanto por uno y las mismas provincias. Se corta en la fila del total para no
  mezclarlos.
"""

from __future__ import annotations

import html
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xlsx import Libro  # noqa: E402

PAGINA = ("https://www.poderjudicial.es/cgpj/es/Temas/Estadistica-Judicial/"
          "Estadistica-por-temas/Datos-penales--civiles-y-laborales/Civil-y-laboral/"
          "Efecto-de-la-Crisis-en-los-organos-judiciales/")
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

HOJA_CALCULO = re.compile(r'href="([^"]*\.xlsx?(?:\?[^"]*)?)"', re.I)
TRIMESTRE_EN_NOMBRE = re.compile(r"(\d)T[ -]?(\d{4})", re.I)
PERIODO = re.compile(r"^(\d{2}|\d{4})\s*[-/]?\s*T(\d)$", re.I)

# Qué hoja da cada indicador del panel. Los nombres llevan las abreviaturas y
# los espacios sobrantes con que vienen en el fichero.
HOJAS = {
    "lanzamientos": "lanzamientos pract. total prov",
    "lanzamientos_hipoteca": "lanzamientos e.hipotecaria prov",
    "lanzamientos_alquiler": "lanzamientos l.a.u. prov",
    "lanzamientos_otros": "lanzamientos. otros prov",
}

# La Comunitat no viene como fila: son sus tres provincias sumadas.
PROVINCIAS_CV = ("alicante", "castellon", "valencia")


def normaliza(texto) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def codifica(url: str) -> str:
    """Los nombres de fichero del CGPJ llevan espacios: hay que escaparlos."""
    partes = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        partes.scheme, partes.netloc,
        urllib.parse.quote(partes.path, safe="/%"),
        urllib.parse.quote(partes.query, safe="=&%"),
        partes.fragment,
    ))


def descarga(url: str, limite: int = 20_000_000, reintentos: int = 4) -> bytes:
    """GET con reintentos: el servidor del CGPJ corta conexiones a ratos."""
    ultimo: Exception | None = None
    for intento in range(reintentos):
        try:
            peticion = urllib.request.Request(codifica(url), headers=CABECERAS)
            with urllib.request.urlopen(peticion, timeout=180) as respuesta:
                return respuesta.read(limite)
        except (urllib.error.URLError, TimeoutError) as exc:
            ultimo = exc
            if intento < reintentos - 1:
                espera = 2 ** (intento + 1)
                print(f"      ! {url.split('/')[-1][:50]}: {exc}; reintento en {espera}s")
                time.sleep(espera)
    raise RuntimeError(f"no se ha podido descargar {url}: {ultimo}")


def localiza_fichero(pagina: str = PAGINA) -> tuple[str, str]:
    """La serie por provincias más reciente que haya publicada.

    El nombre cambia cada trimestre, así que se elige por el trimestre que
    lleva dentro y no por el orden en que aparezcan los enlaces.
    """
    cuerpo = descarga(pagina, 3_000_000).decode("utf-8", errors="replace")
    candidatos = []
    for href in HOJA_CALCULO.findall(cuerpo):
        url = urllib.parse.urljoin(pagina, html.unescape(href))
        nombre = urllib.parse.unquote(url.split("/")[-1].split("?")[0])
        limpio = normaliza(nombre)
        if "series" not in limpio or "provincia" not in limpio:
            continue
        coincidencia = TRIMESTRE_EN_NOMBRE.search(nombre)
        orden = ((int(coincidencia.group(2)), int(coincidencia.group(1)))
                 if coincidencia else (0, 0))
        candidatos.append((orden, url, nombre))
    if not candidatos:
        raise RuntimeError("no hay ningún fichero de series por provincias en la página")
    candidatos.sort(reverse=True)
    _, url, nombre = candidatos[0]
    return url, nombre


def etiqueta_periodo(celda) -> str | None:
    """'13-T1' o '2026-T1' → '2013T1'."""
    coincidencia = PERIODO.match(str(celda or "").strip())
    if not coincidencia:
        return None
    anyo, trimestre = coincidencia.groups()
    if len(anyo) == 2:
        anyo = f"20{anyo}"
    return f"{anyo}T{trimestre}"


def lee_hoja(libro: Libro, nombre_hoja: str) -> dict[str, dict[str, float]]:
    """Una hoja del fichero, como {territorio normalizado: {periodo: valor}}.

    Se para en la fila del total: lo que viene después es el mismo cuadro en
    variaciones, con las provincias repetidas.
    """
    filas = libro.filas(nombre_hoja)

    cabecera, periodos = None, {}
    for i, fila in enumerate(filas):
        etiquetas = {j: etiqueta_periodo(c) for j, c in enumerate(fila)}
        etiquetas = {j: p for j, p in etiquetas.items() if p}
        if len(etiquetas) >= 4:
            cabecera, periodos = i, etiquetas
            break
    if cabecera is None:
        raise ValueError(f"la hoja {nombre_hoja!r} no tiene cabecera de trimestres")

    # El nombre del territorio no siempre está en la primera columna: alguna
    # hoja lleva delante la comunidad o un código. Se toma la primera celda de
    # texto de la fila, que es la que lo nombra.
    def nombre_de(fila) -> str:
        for celda in fila[:3]:
            if isinstance(celda, str) and normaliza(celda):
                return normaliza(celda)
        return ""

    territorios: dict[str, dict[str, float]] = {}
    for fila in filas[cabecera + 1:]:
        if not fila:
            continue
        nombre = nombre_de(fila)
        if not nombre:
            continue
        valores = {}
        for columna, periodo in periodos.items():
            valor = fila[columna] if columna < len(fila) else None
            if isinstance(valor, (int, float)):
                valores[periodo] = float(valor)
        if valores:
            territorios[nombre] = valores
        if nombre.startswith("total"):
            break
    return territorios


def series_del_libro(libro: Libro) -> dict[str, dict[str, dict[str, float]]]:
    """Las cuatro series de lanzamientos, por ámbito del panel."""
    disponibles = {normaliza(n): n for n in libro.hojas}
    por_ambito: dict[str, dict[str, dict[str, float]]] = {
        "espana": {}, "comunitat-valenciana": {}, "castellon": {}}

    for clave, buscada in HOJAS.items():
        hoja = disponibles.get(buscada)
        if not hoja:
            # Sin la hoja no se inventa nada: se deja el indicador sin serie.
            print(f"    ! el fichero no trae la hoja «{buscada}»")
            continue
        territorios = lee_hoja(libro, hoja)
        if not any(n.startswith(("total", "castellon")) for n in territorios):
            # Sin esto no hay forma de saber por qué no encaja: el CGPJ no usa
            # el mismo formato en todas las hojas del mismo fichero.
            print(f"    ! en «{hoja}» no aparecen ni Castellón ni el total; "
                  f"{len(territorios)} filas leídas: {list(territorios)[:8]}")

        nacional = next((v for n, v in territorios.items() if n.startswith("total")), None)
        if nacional:
            por_ambito["espana"][clave] = nacional
        castellon = next((v for n, v in territorios.items() if n.startswith("castellon")), None)
        if castellon:
            por_ambito["castellon"][clave] = castellon

        # La Comunitat se compone sumando sus tres provincias, y sólo para los
        # trimestres en que están las tres: si falta una, el total engañaría.
        partes = [v for n, v in territorios.items()
                  if any(n.startswith(p) for p in PROVINCIAS_CV)]
        if len(partes) == 3:
            comunes = set(partes[0])
            for parte in partes[1:]:
                comunes &= set(parte)
            if comunes:
                por_ambito["comunitat-valenciana"][clave] = {
                    periodo: sum(parte[periodo] for parte in partes) for periodo in comunes}
        else:
            print(f"    ! sólo {len(partes)} de las 3 provincias valencianas en «{hoja}»")

    return por_ambito


def descarga_lanzamientos() -> tuple[dict, str]:
    """Baja el fichero vigente y devuelve las series y de dónde salen."""
    url, nombre = localiza_fichero()
    print(f"    fichero del CGPJ: {nombre}")
    libro = Libro(descarga(url))
    series = series_del_libro(libro)
    for ambito, indicadores in series.items():
        for clave, valores in indicadores.items():
            ultimo = max(valores, key=lambda p: (p[:4], p[5:]))
            print(f"      {ambito}/{clave}: {len(valores)} trimestres, "
                  f"{ultimo} = {valores[ultimo]:,.0f}")
    return series, nombre
