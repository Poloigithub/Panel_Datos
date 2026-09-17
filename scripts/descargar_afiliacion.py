"""Afiliación a la Seguridad Social: cuánta gente cotiza, por provincia.

Del Anuario de Estadísticas del Ministerio de Trabajo, que publica un
`AFI.xlsx` por año con una hoja que reparte los afiliados por comunidad
autónoma y provincia. Es la media anual, no la foto de un día, que es lo que
hay que comparar con una serie anual de accidentes.

Vale por sí sola -cuánta gente cotiza en Castellón y cómo ha ido- y vale para
otra cosa: convierte los accidentes de trabajo en una tasa. Hasta ahora la
página de siniestralidad tenía que reconocer que una subida podía venir de que
hubiera más accidentes o de que hubiera más gente trabajando; con esto se
puede separar.

Dos cosas que este fichero obliga a hacer bien:

- **La hoja no se puede llamar por su nombre.** En el anuario de 2015 se llama
  `Afi-07` y en el de 2025 `AFI-19`, y por el camino el fichero pasa de 22
  hojas a 40. Lo que no cambia es lo que el índice dice de ella, así que se
  busca por su descripción.
- **La columna tampoco.** Cada fichero trae dos años, el suyo y el anterior, y
  no siempre en el mismo sitio. Se localiza la fila de cabecera que lleva los
  años y se coge la columna cuyo valor es el año del fichero.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import bloques_ine as bloques  # noqa: E402
import red_ministerio as red  # noqa: E402
from xlsx import Libro  # noqa: E402

ANUARIO = "https://www.mites.gob.es/ficheros/ministerio/estadisticas/anuarios"
PRIMER_ANYO = 2015   # antes, el anuario está en el .xls binario que el panel no lee

FILAS = {
    "espana": "total",
    "comunitat-valenciana": "comunitat valenciana",
    "castellon": "castellon",
}

# Qué hoja se busca, descrita como la describe el índice del propio fichero.
# Se prueban varias redacciones porque el ministerio las cambia entre años.
HOJAS = {
    "afiliados": [("afiliados", "comunidad autonoma y provincia"),
                  ("afiliados en alta laboral", "provincia")],
    "autonomos": [("autonomos", "comunidad autonoma y provincia"),
                  ("cuenta propia", "comunidad autonoma y provincia"),
                  ("autonomos", "provincia")],
}

BLOQUE = {
    "titulo": "Afiliación a la Seguridad Social",
    "indicadores": {
        "afiliados": {
            "titulo": "Personas afiliadas a la Seguridad Social",
            "unidad": "personas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "media anual de personas en alta laboral",
            "nota": "Media anual, no la foto de un día concreto: es lo que se "
                    "puede comparar con una serie anual. La serie empieza en "
                    "2015 porque antes el anuario está en el formato binario "
                    "antiguo de Excel, que el panel no lee.",
        },
        "autonomos": {
            "titulo": "Personas afiliadas por cuenta propia",
            "unidad": "personas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "media anual de autónomos en alta",
        },
    },
}


def normaliza(texto: str) -> str:
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return " ".join(plano.split())


def hoja_por_descripcion(libro: Libro, palabras: tuple[str, ...]) -> str | None:
    """La hoja que el índice del fichero describe con todas esas palabras."""
    indice = next((h for h in libro.hojas if normaliza(h).startswith("indice")), None)
    if not indice:
        return None
    for fila in libro.filas(indice):
        celdas = [normaliza(str(c)) for c in fila if c not in (None, "")]
        if not celdas:
            continue
        if not all(p in " ".join(celdas) for p in palabras):
            continue
        codigo = celdas[0].rstrip(". ").replace(" ", "").replace("-0", "-")
        for nombre in libro.hojas:
            if normaliza(nombre).replace(" ", "").replace("-0", "-") == codigo:
                return nombre
    return None


def busca_hoja(libro: Libro, cual: str) -> str | None:
    for palabras in HOJAS[cual]:
        nombre = hoja_por_descripcion(libro, palabras)
        if nombre:
            return nombre
    return None


def columna_del_anyo(filas: list[list], anyo: int) -> int | None:
    """La columna del total del año, localizada por la fila de cabecera.

    Cada fichero trae su año y el anterior, y no siempre en el mismo sitio. La
    cabecera los escribe como números, así que se busca la primera fila que
    tenga el año del fichero y se devuelve esa columna.
    """
    for fila in filas[:20]:
        for columna, celda in enumerate(fila):
            if isinstance(celda, (int, float)) and int(celda) == anyo:
                return columna
            if isinstance(celda, str) and celda.strip() == str(anyo):
                return columna
    return None


def lee_anyo(datos: bytes, anyo: int) -> dict[str, dict[str, float]]:
    """Los tres ámbitos del panel, de las hojas provinciales de un anuario."""
    libro = Libro(datos)
    buscados = {nombre: clave for clave, nombre in FILAS.items()}
    salida: dict[str, dict[str, float]] = {}

    for magnitud in HOJAS:
        hoja = busca_hoja(libro, magnitud)
        if not hoja:
            print(f"    {anyo}: no se encuentra la hoja de {magnitud}")
            continue
        filas = libro.filas(hoja)
        columna = columna_del_anyo(filas, anyo)
        if columna is None:
            print(f"    {anyo}: la hoja «{hoja}» no dice dónde está el año")
            continue
        encontrados = set()
        for fila in filas:
            if not fila:
                continue
            clave = buscados.get(normaliza(str(fila[0] or "")))
            if not clave or clave in encontrados:
                continue
            valor = fila[columna] if columna < len(fila) else None
            if isinstance(valor, (int, float)):
                salida.setdefault(clave, {})[magnitud] = float(valor)
                encontrados.add(clave)
        print(f"    {anyo}: «{hoja}» col {columna} → "
              f"{magnitud} de Castellón: "
              f"{salida.get('castellon', {}).get(magnitud)}")
    return salida


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    hoy = dt.date.today()
    print("\n=== Afiliación a la Seguridad Social ===")

    por_ambito: dict[str, dict] = {a: {"ambos": {}} for a in FILAS}
    for anyo in range(PRIMER_ANYO, hoy.year + 1):
        url = f"{ANUARIO}/{anyo}/AFI/AFI.xlsx"
        estado, _, datos = red.abre(url)
        if estado != 200 or datos[:2] != b"PK":
            print(f"    {anyo}: todavía no publicado")
            continue
        try:
            filas = lee_anyo(datos, anyo)
        except Exception as exc:  # noqa: BLE001
            print(f"    {anyo}: no se ha podido leer: {type(exc).__name__}: {exc}")
            continue
        for ambito, magnitudes in filas.items():
            for magnitud, valor in magnitudes.items():
                por_ambito[ambito]["ambos"].setdefault(magnitud, {})[str(anyo)] = valor

    periodos = bloques.escribe_bloque("afiliacion", BLOQUE, por_ambito, ahora, RAIZ)
    return 0 if periodos else 1


if __name__ == "__main__":
    raise SystemExit(main())
