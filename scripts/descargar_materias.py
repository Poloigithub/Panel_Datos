"""Materias primas: el Brent y compañía, mes a mes desde 1960.

La fuente es el **Pink Sheet del Banco Mundial**, que es la referencia mundial
de precios de materias primas: ochenta y ocho series mensuales -crudo, gas,
trigo, café, cobre, oro, urea- desde enero de 1960, en una hoja de cálculo que
se publica el primer día hábil de cada mes.

Tres decisiones que conviene dejar dichas:

- **La dirección se lee de la página, no se escribe aquí.** La URL del fichero
  lleva dentro un identificador de versión que cambia con cada publicación. Al
  sondear se vio lo que pasa si se fija a mano: la dirección de 2025 seguía
  contestando 200 y sirviendo un fichero congelado en diciembre de 2025. Es el
  fallo silencioso peor de todos, así que el descargador entra por la página
  del Banco Mundial y coge el enlace que publique ese día.

- **Los precios se guardan en dólares, que es como los publica la fuente.** No
  se convierten aquí. Lo que sí se baja es el **tipo de cambio oficial del
  Banco Central Europeo**, como un indicador más, y la conversión a euros la
  hace la página. Así el dato publicado es exactamente el de la fuente y la
  división queda a la vista de quien quiera comprobarla.

- **Esto no tiene provincia.** El Brent vale lo mismo en Castellón que en
  Singapur. Es la segunda sección del panel sin desglose territorial, después
  de la luz, y lo dice en vez de repetir la misma cifra tres veces.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import bloques_ine as bloques  # noqa: E402
import xlsx  # noqa: E402

PAGINA = "https://www.worldbank.org/en/research/commodity-markets"
FICHERO = "CMO-Historical-Data-Monthly.xlsx"
HOJA = "Monthly Prices"

BCE = ("https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A"
       "?format=csvdata")

CABECERAS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9",
}

AVISO_MUNDIAL = ("El precio de una materia prima es el mismo en todo el mundo: "
                 "se fija en mercados internacionales, no en Castellón. Esta "
                 "sección no tiene desglose territorial porque no existe.")

AVISO_DOLARES = ("Publicado en dólares, que es la moneda en la que cotiza y en "
                 "la que lo da el Banco Mundial. La página puede pasarlo a "
                 "euros con el tipo de cambio oficial del BCE, que está aquí "
                 "abajo como un indicador más para que la cuenta se pueda "
                 "comprobar.")

# Qué columnas del Pink Sheet se publican y cómo se llaman aquí. El nombre de
# la izquierda es el del panel; el de la derecha, el literal de la hoja, que se
# busca por texto y no por posición: el Banco Mundial ha añadido columnas entre
# versiones y contarlas a mano sería empezar a publicar la de al lado.
COLUMNAS = [
    ("brent", "Crude oil, Brent", "Petróleo Brent",
     "$/barril", "dólares por barril", 2),
    ("gas_europa", "Natural gas, Europe", "Gas natural en Europa",
     "$/mmbtu", "dólares por millón de BTU", 2),
    ("carbon", "Coal, Australian", "Carbón",
     "$/t", "dólares por tonelada", 2),
    ("trigo", "Wheat, US HRW", "Trigo",
     "$/t", "dólares por tonelada", 2),
    ("maiz", "Maize", "Maíz",
     "$/t", "dólares por tonelada", 2),
    ("aceite_girasol", "Sunflower oil", "Aceite de girasol",
     "$/t", "dólares por tonelada", 2),
    ("azucar", "Sugar, EU", "Azúcar",
     "$/kg", "dólares por kilo", 3),
    ("cafe", "Coffee, Arabica", "Café",
     "$/kg", "dólares por kilo", 3),
    ("cacao", "Cocoa", "Cacao",
     "$/kg", "dólares por kilo", 3),
    ("naranja", "Orange", "Naranja",
     "$/kg", "dólares por kilo", 3),
    ("urea", "Urea", "Urea",
     "$/t", "dólares por tonelada", 2),
    ("cobre", "Copper", "Cobre",
     "$/t", "dólares por tonelada", 2),
    ("aluminio", "Aluminum", "Aluminio",
     "$/t", "dólares por tonelada", 2),
    ("oro", "Gold", "Oro",
     "$/onza", "dólares por onza troy", 2),
]

NOTAS = {
    "naranja": "Está aquí por Castellón: el precio internacional de la naranja "
               "es el que marca lo que cobra quien la cultiva.",
    "urea": "El abono nitrogenado más usado. Se fabrica con gas natural, así "
            "que su precio sigue al del gas: cuando se disparó en 2022, se "
            "disparó lo que costaba abonar un campo.",
    "aceite_girasol": "Ucrania y Rusia producían más de la mitad del aceite de "
                      "girasol del mundo. Lo que pasó en 2022 se ve aquí antes "
                      "que en el supermercado.",
    "gas_europa": "El precio de referencia del gas en Europa, que es lo que "
                  "acaba marcando el precio de la luz en las horas en que la "
                  "fija un ciclo combinado.",
}


def pide(url: str, intentos: int = 4, limite: int = 20_000_000) -> bytes:
    """Pedir con reintentos: el ministerio y el Banco Mundial cortan a veces.

    Un `connection reset` no es un no. En el primer sondeo de carburantes la
    conexión se cortó al primer intento y a la segunda contestó sin queja.
    """
    espera, ultimo = 2, ""
    for intento in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=CABECERAS)
            with urllib.request.urlopen(peticion, timeout=180) as respuesta:
                return respuesta.read(limite)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{exc.code} en {url}") from exc
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            if intento < intentos:
                time.sleep(espera)
                espera *= 2
    raise RuntimeError(f"no se pudo bajar {url}: {ultimo}")


def direccion_de_la_hoja() -> str:
    """El enlace al Pink Sheet mensual que publica hoy el Banco Mundial.

    Si la página cambia y el enlace no aparece, esto revienta a propósito. La
    alternativa -tirar de una dirección guardada- es la que hace que el panel
    publique durante meses un fichero viejo sin que nadie se entere.
    """
    html = pide(PAGINA, limite=4_000_000).decode("utf-8", "replace")
    for crudo in re.findall(r'href="([^"]+\.xlsx)"', html, re.I):
        if FICHERO.lower() in crudo.lower():
            return crudo if crudo.startswith("http") else \
                "https://www.worldbank.org" + crudo
    raise RuntimeError(
        f"la página del Banco Mundial ya no enlaza {FICHERO}; hay que mirar "
        f"{PAGINA} antes de tocar nada")


def normaliza(texto) -> str:
    """El nombre de una columna, sin adornos.

    La hoja trae asteriscos de nota al pie -«Coal, South African **»- y espacios
    de sobra al final -«Urea  »-, y ninguno de los dos significa nada.
    """
    return re.sub(r"\s+", " ", str(texto or "").replace("*", "")).strip().lower()


ES_PERIODO = re.compile(r"^\s*(\d{4})M(\d{2})\s*$")


def lee_pink_sheet(datos: bytes) -> dict[str, dict[str, float]]:
    """De la hoja de cálculo a `{indicador: {periodo: valor}}`."""
    libro = xlsx.Libro(datos)
    if HOJA not in libro.hojas:
        raise RuntimeError(f"no hay hoja «{HOJA}»; hay {list(libro.hojas)}")
    filas = list(libro.filas(HOJA))

    # La fila de cabecera es la que nombra el Brent, no la cuarta: el Banco
    # Mundial ha cambiado ya el número de filas de preámbulo entre versiones.
    referencia = normaliza("Crude oil, Brent")
    cabecera = next((f for f in filas
                     if any(normaliza(c) == referencia for c in f)), None)
    if cabecera is None:
        raise RuntimeError("no se encuentra la fila de nombres de columna")

    posicion = {}
    for numero, celda in enumerate(cabecera):
        nombre = normaliza(celda)
        if nombre and nombre not in posicion:
            posicion[nombre] = numero

    faltan = [literal for _, literal, *_ in COLUMNAS
              if normaliza(literal) not in posicion]
    if faltan:
        raise RuntimeError(f"el Pink Sheet ya no trae estas columnas: {faltan}")

    series: dict[str, dict[str, float]] = {clave: {} for clave, *_ in COLUMNAS}
    for fila in filas:
        if not fila:
            continue
        casa = ES_PERIODO.match(str(fila[0] or ""))
        if not casa:
            continue
        anyo, mes = casa.groups()
        if not 1 <= int(mes) <= 12:
            continue
        periodo = f"{anyo}M{mes}"
        for clave, literal, *_ in COLUMNAS:
            numero = posicion[normaliza(literal)]
            if numero >= len(fila):
                continue
            valor = fila[numero]
            # Los huecos vienen como «…» o como celda vacía, y se quedan como
            # huecos: el panel no interpola.
            if isinstance(valor, (int, float)):
                series[clave][periodo] = float(valor)
    return series


def lee_tipo_de_cambio() -> dict[str, float]:
    """Dólares por euro, media del mes, del Banco Central Europeo."""
    texto = pide(BCE, limite=4_000_000).decode("utf-8-sig", "replace")
    lineas = texto.splitlines()
    if not lineas:
        return {}
    cabecera = [c.strip() for c in lineas[0].split(",")]
    try:
        donde_fecha = cabecera.index("TIME_PERIOD")
        donde_valor = cabecera.index("OBS_VALUE")
    except ValueError as exc:
        raise RuntimeError(f"el CSV del BCE ya no trae esas columnas: {cabecera[:12]}") from exc

    valores: dict[str, float] = {}
    for linea in lineas[1:]:
        trozos = linea.split(",")
        if len(trozos) <= max(donde_fecha, donde_valor):
            continue
        fecha, crudo = trozos[donde_fecha].strip(), trozos[donde_valor].strip()
        if not re.fullmatch(r"\d{4}-\d{2}", fecha) or not crudo:
            continue
        try:
            valores[f"{fecha[:4]}M{fecha[5:7]}"] = float(crudo)
        except ValueError:
            continue
    return valores


def construye_bloque() -> dict:
    indicadores = {}
    for clave, _literal, titulo, unidad, unidad_texto, decimales in COLUMNAS:
        indicadores[clave] = {
            "titulo": titulo,
            "unidad": unidad,
            "unidad_texto": unidad_texto,
            "decimales": decimales,
            "por_sexo": False,
            "sin_ambitos": ("castellon", "comunitat-valenciana"),
            "nota": NOTAS.get(clave, AVISO_MUNDIAL),
        }
    indicadores["euro_dolar"] = {
        "titulo": "Dólares por euro",
        "unidad": "$/€",
        "unidad_texto": "tipo de cambio oficial de referencia, media del mes",
        "decimales": 4,
        "por_sexo": False,
        "sin_ambitos": ("castellon", "comunitat-valenciana"),
        "nota": "Está aquí para que la conversión a euros del resto de la "
                "página se pueda rehacer a mano. Fuente: Banco Central Europeo.",
    }
    return {"titulo": "Materias primas", "indicadores": indicadores}


def main() -> None:
    ahora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    print("Materias primas")
    direccion = direccion_de_la_hoja()
    print(f"  el Banco Mundial publica hoy: {direccion}")
    datos = pide(direccion)
    print(f"  {len(datos)} bytes")
    series = lee_pink_sheet(datos)
    for clave, *_ in COLUMNAS:
        valores = series[clave]
        if valores:
            primero, ultimo = min(valores), max(valores)
            print(f"    {clave}: {len(valores)} meses, {primero} … {ultimo}")
        else:
            print(f"    {clave}: VACÍO")

    print("  tipo de cambio del BCE")
    cambio = lee_tipo_de_cambio()
    if cambio:
        print(f"    euro_dolar: {len(cambio)} meses, "
              f"{min(cambio)} … {max(cambio)}")
        series["euro_dolar"] = cambio
    else:
        print("    sin tipo de cambio: la página no podrá pasar a euros")

    vacias = [clave for clave, valores in series.items() if not valores]
    if vacias:
        raise SystemExit(f"series vacías, no se publica nada: {vacias}")

    por_ambito = {"espana": {"ambos": series}}
    bloques.escribe_bloque("materias", construye_bloque(), por_ambito, ahora, RAIZ)


if __name__ == "__main__":
    main()
