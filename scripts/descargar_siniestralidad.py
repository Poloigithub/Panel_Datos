"""Accidentes de trabajo: lo que le cuesta a la gente ir a trabajar.

El panel sabía cuánta gente trabaja y cuánto cobra, pero no en qué condiciones.
Esto lo llena con la Estadística de Accidentes de Trabajo del Ministerio de
Trabajo, que a diferencia de todas las estadísticas salariales **sí baja a
provincia**: la hoja `ATR-A1.1` de cada avance mensual trae España, cada
comunidad y cada provincia en la misma tabla.

Cómo está montado esto, y por qué:

- Los ficheros son acumulados del año: el de julio de 2026 dice lo que va de
  enero a julio. Por eso la serie se construye con **el fichero de diciembre de
  cada año**, que es el año entero, y el año en curso va aparte, en
  `avance.json`, comparado contra el mismo periodo del año anterior. Meter un
  año a medias en una serie anual haría que el último punto pareciera una
  caída del cuarenta por ciento.
- La serie empieza en 2021 porque antes de marzo de ese año el ministerio
  publicaba en el `.xls` binario de toda la vida, y el lector del panel -que no
  tiene dependencias- sólo sabe abrir XLSX. No es una decisión editorial: es
  hasta donde llega el formato.
- Se guardan los accidentes en jornada por gravedad y los in itinere, que son
  los del camino al trabajo. Se separan porque son cosas distintas: uno habla
  de cómo es el puesto y el otro de cómo se llega a él.
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

BASE = "https://www.mites.gob.es/estadisticas/eat"
HOJA = "ATR-A1.1"
PRIMER_ANYO = 2021   # antes de marzo de 2021 los ficheros son .xls binario

# Cómo se llama cada ámbito del panel dentro de la hoja. El TOTAL de la tabla
# es España; la comunidad va en mayúsculas y la provincia en minúsculas, que es
# como el ministerio distingue un nivel de otro.
FILAS = {
    "espana": "total",
    "comunitat-valenciana": "comunitat valenciana",
    "castellon": "castellon",
}

# Las columnas de la tabla, contadas desde el nombre del territorio.
COLUMNAS = {
    "accidentes_jornada": 2,
    "accidentes_leves": 3,
    "accidentes_graves": 4,
    "accidentes_mortales": 5,
    "accidentes_itinere": 7,
    "mortales_itinere": 10,
}

# La advertencia del formato va sólo en el primer indicador. Repetirla debajo
# de cada grupo de gráficas es ruido: se lee cinco veces la misma frase y deja
# de leerse ninguna.
NOTA_FORMATO = ("La serie empieza en 2021 porque antes el ministerio publicaba "
                "en el formato binario antiguo de Excel, que el panel no lee.")

BLOQUE = {
    "titulo": "Accidentes de trabajo",
    "indicadores": {
        "accidentes_jornada": {
            "titulo": "Accidentes con baja en jornada de trabajo",
            "unidad": "accidentes", "decimales": 0, "por_sexo": False,
            "unidad_texto": "accidentes con baja ocurridos en el puesto",
            "nota": NOTA_FORMATO,
        },
        "accidentes_graves": {
            "titulo": "Accidentes graves en jornada",
            "unidad": "accidentes", "decimales": 0, "por_sexo": False,
            "unidad_texto": "accidentes calificados de graves",
        },
        "accidentes_mortales": {
            "titulo": "Accidentes mortales en jornada",
            "unidad": "accidentes", "decimales": 0, "por_sexo": False,
            "unidad_texto": "personas muertas en el puesto de trabajo",
        },
        "accidentes_itinere": {
            "titulo": "Accidentes in itinere",
            "unidad": "accidentes", "decimales": 0, "por_sexo": False,
            "unidad_texto": "accidentes de ida o vuelta al trabajo",
            "nota": "Los del camino al trabajo. Se cuentan aparte de los de "
                    "jornada porque hablan de cosas distintas: uno de cómo es "
                    "el puesto y el otro de cómo se llega a él.",
        },
        "mortales_itinere": {
            "titulo": "Muertes in itinere",
            "unidad": "accidentes", "decimales": 0, "por_sexo": False,
            "unidad_texto": "personas muertas yendo o volviendo del trabajo",
        },
    },
}


def normaliza(texto: str) -> str:
    """Sin acentos, sin dobles espacios y en minúsculas, para poder comparar."""
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return re.sub(r"\s+", " ", plano)


def url_mensual(anyo: int, mes: int) -> str:
    return f"{BASE}/eat{anyo % 100:02d}_{mes:02d}/ATR_{mes:02d}_{anyo}.xlsx"


def lee_hoja(datos: bytes) -> dict[str, dict[str, float]]:
    """Los tres ámbitos del panel, sacados de la tabla por provincias."""
    libro = Libro(datos)
    if HOJA not in libro.hojas:
        raise RuntimeError(f"el fichero no trae la hoja {HOJA}")

    buscados = {nombre: clave for clave, nombre in FILAS.items()}
    encontrado: dict[str, dict[str, float]] = {}
    for fila in libro.filas(HOJA):
        if not fila:
            continue
        clave = buscados.get(normaliza(str(fila[0] or "")))
        if not clave or clave in encontrado:
            continue
        magnitudes = {}
        for magnitud, columna in COLUMNAS.items():
            valor = fila[columna] if columna < len(fila) else None
            if isinstance(valor, (int, float)):
                magnitudes[magnitud] = float(valor)
        if magnitudes:
            encontrado[clave] = magnitudes
    return encontrado


def periodo_del_fichero(datos: bytes) -> str | None:
    """Lo que el propio fichero dice que cubre: «Avance enero - julio 2026»."""
    libro = Libro(datos)
    for fila in libro.filas(HOJA)[:12]:
        for celda in fila[:3]:
            texto = normaliza(str(celda or ""))
            if "avance" in texto and re.search(r"\d{4}", texto):
                return str(celda).strip()
    return None


def baja(anyo: int, mes: int) -> bytes | None:
    """El fichero de un mes, o nada si ese mes no está publicado.

    El ministerio no devuelve 404 para un fichero que no existe: devuelve su
    portada con un 200 y tan tranquilo. Así que no vale mirar el estado, hay
    que mirar lo que ha llegado: un XLSX es un zip y empieza por «PK».
    """
    url = url_mensual(anyo, mes)
    estado, _, datos = red.abre(url)
    if estado != 200:
        print(f"    {anyo}-{mes:02d}: {estado}")
        return None
    if datos[:2] != b"PK":
        print(f"    {anyo}-{mes:02d}: todavía no publicado "
              f"(contestan {len(datos)} bytes que no son una hoja)")
        return None
    return datos


def ultimo_avance(hoy: dt.date) -> tuple[int, int, bytes] | None:
    """El avance más reciente que haya publicado el ministerio.

    Se empieza por el mes en curso y se va hacia atrás, porque el avance sale
    con un par de meses de retraso y preguntar por diciembre en septiembre es
    gastar peticiones en un 404 seguro. Si el año acaba de empezar y todavía no
    hay nada suyo, se sigue por el anterior.
    """
    for anyo, desde in ((hoy.year, hoy.month), (hoy.year - 1, 12)):
        for mes in range(desde, 0, -1):
            datos = baja(anyo, mes)
            if datos:
                return anyo, mes, datos
    return None


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    hoy = dt.date.today()
    print("\n=== Accidentes de trabajo ===")

    # ------------------------------------------------ la serie de años enteros
    por_ambito: dict[str, dict] = {a: {"ambos": {}} for a in FILAS}
    for anyo in range(PRIMER_ANYO, hoy.year):
        datos = baja(anyo, 12)
        if not datos:
            continue
        try:
            filas = lee_hoja(datos)
        except Exception as exc:  # noqa: BLE001
            print(f"    {anyo}: no se ha podido leer: {type(exc).__name__}: {exc}")
            continue
        for ambito, magnitudes in filas.items():
            for magnitud, valor in magnitudes.items():
                por_ambito[ambito]["ambos"].setdefault(magnitud, {})[str(anyo)] = valor
        print(f"    {anyo}: {filas.get('castellon', {}).get('accidentes_jornada')} "
              f"accidentes en jornada en Castellón, "
              f"{filas.get('castellon', {}).get('accidentes_mortales')} mortales")

    periodos = bloques.escribe_bloque("siniestralidad", BLOQUE, por_ambito, ahora, RAIZ)
    if not periodos:
        print("  no se ha podido montar la serie")
        return 1

    # ------------------------------------------- lo que va del año, y el pasado
    # El fichero del año en curso es acumulado, así que sólo se puede comparar
    # contra el mismo mes del año anterior: contra el año entero parecería que
    # los accidentes se han hundido.
    avance = ultimo_avance(hoy)
    destino = RAIZ / "data" / "siniestralidad"
    if avance:
        anyo, mes, datos = avance
        actual = lee_hoja(datos)
        previo_datos = baja(anyo - 1, mes)
        previo = lee_hoja(previo_datos) if previo_datos else {}
        ficha = {
            "actualizado": ahora,
            "anyo": anyo,
            "mes": mes,
            "periodo_texto": periodo_del_fichero(datos),
            "anyo_anterior": anyo - 1,
            "ambitos": {
                ambito: {"actual": actual.get(ambito, {}),
                         "anterior": previo.get(ambito, {})}
                for ambito in FILAS
            },
        }
        (destino / "avance.json").write_text(
            json.dumps(ficha, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  escrito data/siniestralidad/avance.json ({ficha['periodo_texto']})")
    else:
        print("  sin avance del año en curso")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
