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

# Y aparte del anuario, el ministerio publica **cada mes** una estadística de
# personas por cuenta propia con una hoja por provincia. No sustituye a la
# anual: cuenta otro universo, más amplio. Va como serie propia.
MENSUAL = "https://www.mites.gob.es/estadisticas/AUT/AUT_{mes:02d}_{anyo}.xlsx"
HOJA_MENSUAL = ("autonomos", "comunidad autonoma y provincia")
COLUMNA_MENSUAL = 4      # el total en valores absolutos
FALLOS_SEGUIDOS = 4      # meses vacíos antes de dar por terminado el histórico

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
    # Sólo la redacción con provincia, y es una decisión, no un descuido.
    # Desde 2024 el ministerio publica en su lugar «trabajadores autónomos por
    # asalariados según comunidad autónoma», que suena parecido y no lo es: da
    # 3,4 millones donde la serie venía dando 2,0. Enlazar las dos sería
    # publicar un cambio de definición como si fuera un crecimiento del 69 %
    # en un año. Así que la serie se corta donde el ministerio la cortó.
    "autonomos": [("autonomos", "comunidad autonoma y provincia"),
                  ("cuenta propia", "comunidad autonoma y provincia")],
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
        "autonomos_mes": {
            "titulo": "Personas por cuenta propia, mes a mes",
            "unidad": "personas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "personas trabajadoras por cuenta propia afiliadas",
            "nota": "De la estadística mensual del ministerio, que llega con "
                    "dos meses de retraso. Cuenta un universo más amplio que "
                    "la serie anual de aquí abajo -3,5 millones frente a 2,0-, "
                    "así que son dos series distintas y no se pueden enlazar: "
                    "ésta incluye colectivos que aquélla dejaba fuera.",
        },
        "autonomos": {
            "titulo": "Personas afiliadas por cuenta propia",
            "unidad": "personas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "media anual de autónomos en alta",
            "nota": "La serie se corta en 2023 porque el ministerio dejó de "
                    "publicar esta tabla. Desde 2024 saca otra que suena "
                    "parecida -autónomos por número de asalariados, y sólo por "
                    "comunidad autónoma- que cuenta 3,4 millones donde ésta "
                    "venía contando 2,0. Enlazarlas sería dar un cambio de "
                    "definición por un crecimiento del 69 % en un año.",
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
        if not codigo:
            continue
        # Primero el nombre exacto y, si no, el que empiece por el código: hay
        # años en que la tabla no cabe en una hoja y el ministerio la parte en
        # «AFI-27A» y «AFI-27B». La primera mitad es la que trae el principio
        # de la lista de provincias, que es donde está lo que se busca.
        candidatas = [n for n in libro.hojas
                      if normaliza(n).replace(" ", "").replace("-0", "-").startswith(codigo)]
        exacta = [n for n in candidatas
                  if normaliza(n).replace(" ", "").replace("-0", "-") == codigo]
        if exacta:
            return exacta[0]
        if candidatas:
            return sorted(candidatas)[0]
    return None


# Con qué palabra reconocer, en el índice, de qué habla cada hoja. Sirve para
# explicar por qué no se ha encontrado, que es lo único que permite corregir
# la declaración sin adivinar.
PISTAS = {"afiliados": ("afiliad",), "autonomos": ("autonom", "cuenta propia")}


def busca_hoja(libro: Libro, cual: str) -> str | None:
    for palabras in HOJAS[cual]:
        nombre = hoja_por_descripcion(libro, palabras)
        if nombre:
            return nombre

    # No ha encajado ninguna redacción: enseñar las del índice que hablan del
    # tema, que es de donde sale la redacción nueva.
    indice = next((h for h in libro.hojas if normaliza(h).startswith("indice")), None)
    if indice:
        for fila in libro.filas(indice):
            texto = " ".join(normaliza(str(c)) for c in fila if c not in (None, ""))
            if any(p in texto for p in PISTAS[cual]):
                print(f"        el índice dice: {texto[:150]}")
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


def lee_mes(datos: bytes) -> dict[str, float]:
    """Los tres ámbitos, de la hoja provincial del fichero mensual.

    Aquí el nombre del territorio no está siempre en la primera columna: la
    comunidad va en la segunda y la provincia en la tercera, que es como el
    ministerio distingue un nivel de otro. Se mira en las tres primeras.
    """
    libro = Libro(datos)
    hoja = hoja_por_descripcion(libro, HOJA_MENSUAL)
    if not hoja:
        return {}
    buscados = {nombre: clave for clave, nombre in FILAS.items()}
    salida: dict[str, float] = {}
    for fila in libro.filas(hoja):
        etiqueta = next((normaliza(str(c)) for c in fila[:3]
                         if isinstance(c, str) and c.strip()), "")
        clave = buscados.get(etiqueta)
        if not clave or clave in salida:
            continue
        valor = fila[COLUMNA_MENSUAL] if COLUMNA_MENSUAL < len(fila) else None
        if isinstance(valor, (int, float)):
            salida[clave] = float(valor)
    return salida


def meses_ya_bajados() -> dict[str, dict[str, float]]:
    """Lo que ya está en el repositorio, para no volver a pedirlo.

    El histórico mensual son más de cien ficheros de medio mega. Bajarlos
    todos los días sería maltratar al ministerio para llegar al mismo sitio:
    una vez guardado un mes, no cambia.
    """
    guardado: dict[str, dict[str, float]] = {}
    for ambito in FILAS:
        fichero = RAIZ / "data" / "afiliacion" / f"{ambito}.json"
        if not fichero.exists():
            continue
        contenido = json.loads(fichero.read_text(encoding="utf-8"))
        valores = contenido["series"]["ambos"].get("autonomos_mes") or []
        for periodo, valor in zip(contenido["periodos"], valores):
            if valor is not None and "M" in periodo:
                guardado.setdefault(periodo, {})[ambito] = valor
    return guardado


def descarga_mensual(hoy: dt.date, por_ambito: dict) -> None:
    """La serie mensual de autónomos, hacia atrás hasta donde el ministerio llegue."""
    guardado = meses_ya_bajados()
    print(f"  autónomos mes a mes: {len(guardado)} meses ya guardados")

    anyo, mes = hoy.year, hoy.month
    fallos, pedidos = 0, 0
    while fallos < FALLOS_SEGUIDOS:
        periodo = f"{anyo}M{mes:02d}"
        # Los dos últimos meses se vuelven a pedir: el ministerio los revisa.
        reciente = (hoy.year * 12 + hoy.month) - (anyo * 12 + mes) < 2
        if periodo in guardado and not reciente:
            fallos = 0
        else:
            estado, _, datos = red.abre(MENSUAL.format(anyo=anyo, mes=mes))
            pedidos += 1
            if estado == 200 and datos[:2] == b"PK":
                leido = lee_mes(datos)
                if leido:
                    guardado[periodo] = leido
                    fallos = 0
                    print(f"    {periodo}: Castellón {leido.get('castellon')}")
                else:
                    fallos += 1
            else:
                fallos += 1
        anyo, mes = (anyo - 1, 12) if mes == 1 else (anyo, mes - 1)

    for periodo, ambitos in guardado.items():
        for ambito, valor in ambitos.items():
            por_ambito[ambito]["ambos"].setdefault("autonomos_mes", {})[periodo] = valor
    print(f"  autónomos mes a mes: {pedidos} peticiones, "
          f"{len(guardado)} meses en total")


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

    descarga_mensual(hoy, por_ambito)

    periodos = bloques.escribe_bloque("afiliacion", BLOQUE, por_ambito, ahora, RAIZ)
    return 0 if periodos else 1


if __name__ == "__main__":
    raise SystemExit(main())
