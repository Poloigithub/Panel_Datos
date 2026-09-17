"""Huelgas: cuántas hay, cuánta gente las secunda y cuántas jornadas cuestan.

Es la única medida de conflicto laboral que existe, y estuvo a punto de
quedarse fuera del panel por un error mío: un sondeo buscó la palabra
«provincia» en el índice del fichero, no la encontró y dio la estadística por
nacional. La tabla provincial está ahí, pero su título la llama **«según
repercusión territorial de las huelgas»**, sin nombrar la provincia. Está a dos
líneas de lo que se miró.

De cada avance mensual se lee esa tabla, la `HUE-3`, que reparte por comunidad
autónoma y provincia las huelgas desarrolladas, los trabajadores participantes
y las jornadas no trabajadas.

Dos cosas sobre lo que significa «repercusión territorial»: una huelga estatal
aparece en todas las provincias donde tuvo seguimiento, y una huelga de empresa
sólo donde está la empresa. Así que la suma de provincias no da el total
nacional de huelgas -una misma huelga se cuenta en varias- pero sí el de
participantes y jornadas, que es lo que de verdad mide el conflicto.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import urllib.parse
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import bloques_ine as bloques  # noqa: E402
import red_ministerio as red  # noqa: E402
import xls  # noqa: E402

BASE = "https://www.mites.gob.es/estadisticas/hue"
PORTADA = ("https://www.mites.gob.es/es/estadisticas/"
           "condiciones_trabajo_relac_laborales/HUE/welcome.htm")
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
         "sep", "oct", "nov", "dic")
FICHERO = "{base}/hue{aa}{mes}publicacion/hue_{mm:02d}_{aa}.xls"

# El nombre del fichero lleva el mes y el año en dos cifras.
NOMBRE = re.compile(r"hue_(\d{2})_(\d{2})\.xls", re.I)
ENLACE = re.compile(r'href="([^"#]+\.xls)"', re.I)

# Más margen que en las otras estadísticas, y por un motivo medido: las
# huelgas salen con unos cuatro meses de retraso, así que rendirse a los
# cuatro meses vacíos es rendirse justo antes del primero que existe.
FALLOS_SEGUIDOS = 8

FILAS = {
    "espana": "total",
    "comunitat-valenciana": "comunitatvalenciana",
    "castellon": "castellon",
}

# Cómo se llama en el fichero el bloque de cada magnitud. La columna del mes es
# la primera de cada bloque; la segunda es el acumulado del año, que aquí no se
# usa porque lo interesante de una huelga es cuándo pasó.
CABECERAS = {
    "huelgas": "huelgas",
    "participantes": "participantes",
    "jornadas_perdidas": "jornadas no trabajadas",
}

# El fichero de diciembre no es un avance más: es el cierre del año y trae los
# doce meses, uno por columna, repartidos en tres hojas -una por magnitud- en
# vez de en una sola con tres bloques. Leerlo bien vale por doce: sus cifras
# son las definitivas, mientras que las de los avances aún se revisan.
NOMBRES_DE_MES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11,
    "diciembre": 12,
}
# Cómo se reconoce cada hoja del cierre, por lo que dice su propio título.
TITULOS = {
    "huelgas": "huelgas desarrolladas",
    "participantes": "trabajadores participantes",
    "jornadas_perdidas": "jornadas no trabajadas",
}

AVISO_REPERCUSION = (
    "Es la repercusión territorial: una huelga estatal aparece en todas las "
    "provincias donde tuvo seguimiento. Por eso la suma de provincias no da el "
    "total nacional de huelgas -una misma huelga se cuenta en varias- aunque "
    "sí el de participantes y jornadas.")

BLOQUE = {
    "titulo": "Huelgas",
    "indicadores": {
        "participantes": {
            "titulo": "Personas que secundaron una huelga",
            "unidad": "personas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "trabajadores participantes en el mes",
            "nota": AVISO_REPERCUSION,
        },
        "jornadas_perdidas": {
            "titulo": "Jornadas no trabajadas",
            "unidad": "jornadas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "jornadas de trabajo perdidas por huelga en el mes",
            "nota": "Es la medida del tamaño de un conflicto: no es lo mismo "
                    "que mil personas paren una hora que una semana.",
        },
        "huelgas": {
            "titulo": "Huelgas con repercusión en el territorio",
            "unidad": "huelgas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "huelgas desarrolladas con seguimiento en el mes",
            "nota": AVISO_REPERCUSION,
        },
    },
}


def normaliza(texto: str) -> str:
    """Sin acentos, sin espacios y en minúsculas.

    Sin espacios del todo: la fila del total viene escrita «T O T A L».
    """
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return "".join(plano.split())


def suave(texto: str) -> str:
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return " ".join(plano.split())


BUSCADOS = {normaliza(n): c for c, n in FILAS.items()}


def hoja_provincial(libro) -> str | None:
    """La tabla que reparte por territorio.

    Se busca por «repercusión territorial», que es como el ministerio la llama
    en el índice, y no por «provincia», que no aparece ahí aunque sí dentro.
    """
    indice = next((h for h in libro.hojas if suave(h).startswith("indice")), None)
    if not indice:
        return None
    for fila in libro.filas(indice):
        celdas = [str(c) for c in fila if c not in (None, "")]
        if not celdas:
            continue
        descripcion = suave(" ".join(celdas))
        if "repercusion territorial" not in descripcion:
            continue
        # En el índice hay dos con ese nombre: el cuadro resumen y la tabla
        # entera. La buena es la que no está entre los resúmenes, y se
        # distingue porque su código no lleva erre.
        codigo = suave(celdas[0]).rstrip(". ")
        if "-r" in codigo:
            continue
        for nombre in libro.hojas:
            if suave(nombre).rstrip(". ") == codigo:
                return nombre
    return None


def columnas_del_mes(filas: list[list]) -> dict[str, int]:
    """Dónde empieza cada bloque, por su cabecera. La primera columna es el mes.

    La columna cero no se mira, y es importante: ahí van el título del cuadro
    -«HUELGAS Y CIERRES PATRONALES»- y el nombre del territorio. Sin saltarla,
    el bloque de huelgas se situaba en la columna del nombre de la provincia y
    la serie salía vacía.
    """
    encontradas: dict[str, int] = {}
    for fila in filas[:10]:
        for columna, celda in enumerate(fila):
            if columna == 0 or not isinstance(celda, str):
                continue
            plano = suave(celda)
            for clave, cabecera in CABECERAS.items():
                if clave not in encontradas and plano.startswith(cabecera):
                    encontradas[clave] = columna
        if len(encontradas) == len(CABECERAS):
            break
    return encontradas


def lee_mes(datos: bytes) -> dict[str, dict[str, float]]:
    libro = xls.Libro(datos)
    hoja = hoja_provincial(libro)
    if not hoja:
        return {}
    filas = libro.filas(hoja)
    columnas = columnas_del_mes(filas)
    if len(columnas) < len(CABECERAS):
        return {}

    salida: dict[str, dict[str, float]] = {}
    for fila in filas:
        if not fila:
            continue
        clave = BUSCADOS.get(normaliza(str(fila[0] or "")))
        if not clave or clave in salida:
            continue
        valores = {}
        for magnitud, columna in columnas.items():
            valor = fila[columna] if columna < len(fila) else None
            if isinstance(valor, (int, float)):
                valores[magnitud] = float(valor)
        if valores:
            salida[clave] = valores
    return salida


def direcciones_publicadas() -> dict[str, str]:
    """Las direcciones que la propia página del ministerio enlaza.

    Construir la dirección a partir del mes funciona casi siempre y falla justo
    en diciembre: su carpeta existe pero el fichero no se llama como los demás,
    así que la serie perdía un mes cada año sin decir nada. Leer los enlaces de
    la página es dejar de adivinar.
    """
    estado, tipo, datos = red.abre(PORTADA, limite=4_000_000)
    if estado != 200 or "html" not in tipo.lower():
        print("  no se ha podido leer la página del ministerio; "
              "se tirará de direcciones construidas")
        return {}
    for codigo in ("utf-8", "iso-8859-15", "cp1252"):
        try:
            pagina = datos.decode(codigo)
            break
        except UnicodeDecodeError:
            continue
    else:
        pagina = datos.decode("utf-8", "replace")

    publicadas: dict[str, str] = {}
    for bruto in ENLACE.findall(pagina):
        destino = urllib.parse.urljoin(PORTADA, html.unescape(bruto))
        coincide = NOMBRE.search(destino)
        if not coincide:
            continue
        mes, anyo = int(coincide.group(1)), 2000 + int(coincide.group(2))
        publicadas[f"{anyo}M{mes:02d}"] = destino
    print(f"  la página enlaza {len(publicadas)} ficheros")
    return publicadas


def columnas_de_meses(filas: list[list]) -> dict[int, int]:
    """Qué columna es cada mes, en las hojas del cierre de año.

    La cabecera alterna meses y acumulados -«Enero, Febrero, Acumulado
    Enero-Febrero, Marzo…»-, así que sólo valen las celdas cuyo texto es
    exactamente un mes. Y la de julio viene con una errata, «Acumullado», que
    da igual: no se parece a ningún mes y se descarta sola.
    """
    encontradas: dict[int, int] = {}
    for fila in filas[:10]:
        for columna, celda in enumerate(fila):
            if columna == 0 or not isinstance(celda, str):
                continue
            mes = NOMBRES_DE_MES.get(suave(celda))
            if mes and mes not in encontradas:
                encontradas[mes] = columna
        if len(encontradas) >= 12:
            break
    return encontradas


def lee_cierre(datos: bytes, anyo: int) -> dict[str, dict[str, dict[str, float]]]:
    """El año entero, sacado del fichero de diciembre."""
    libro = xls.Libro(datos)
    por_periodo: dict[str, dict[str, dict[str, float]]] = {}

    for magnitud, titulo in TITULOS.items():
        # La hoja se reconoce por su propio título, no por su código: en el
        # cierre se llaman HUE-3-I, -II y -III, y ese orden no está garantizado.
        hoja = None
        for nombre in libro.hojas:
            if not suave(nombre).startswith("hue-3"):
                continue
            cabecera = " ".join(
                suave(str(c)) for fila in libro.filas(nombre)[:4]
                for c in fila if c not in (None, ""))
            if titulo in cabecera and "repercusion territorial" in cabecera:
                hoja = nombre
                break
        if not hoja:
            continue

        filas = libro.filas(hoja)
        meses = columnas_de_meses(filas)
        if not meses:
            continue
        for fila in filas:
            if not fila:
                continue
            clave = BUSCADOS.get(normaliza(str(fila[0] or "")))
            if not clave:
                continue
            for mes, columna in meses.items():
                valor = fila[columna] if columna < len(fila) else None
                if isinstance(valor, (int, float)):
                    periodo = f"{anyo}M{mes:02d}"
                    por_periodo.setdefault(periodo, {}) \
                        .setdefault(clave, {})[magnitud] = float(valor)
    return por_periodo


def ya_bajados() -> dict[str, dict[str, dict[str, float]]]:
    """Lo que ya está en el repositorio, para no volver a pedirlo.

    Un mes sólo cuenta como bajado si trae **todas** las magnitudes que hoy se
    esperan. Sin esa condición, el día que se añade un indicador el caché
    congela la forma vieja: los meses antiguos nunca se vuelven a pedir y la
    serie nueva se queda vacía para siempre, que es exactamente lo que pasó con
    el número de huelgas.
    """
    guardado: dict[str, dict[str, dict[str, float]]] = {}
    for ambito in FILAS:
        fichero = RAIZ / "data" / "huelgas" / f"{ambito}.json"
        if not fichero.exists():
            continue
        contenido = json.loads(fichero.read_text(encoding="utf-8"))
        for magnitud, valores in contenido["series"]["ambos"].items():
            for periodo, valor in zip(contenido["periodos"], valores):
                if valor is not None:
                    guardado.setdefault(periodo, {}) \
                        .setdefault(ambito, {})[magnitud] = valor

    esperadas = set(BLOQUE["indicadores"])
    return {periodo: ambitos for periodo, ambitos in guardado.items()
            if all(esperadas <= set(magnitudes) for magnitudes in ambitos.values())}


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    hoy = dt.date.today()
    print("\n=== Huelgas ===")

    guardado = ya_bajados()
    print(f"  {len(guardado)} meses ya guardados")
    publicadas = direcciones_publicadas()

    anyo, mes = hoy.year, hoy.month
    fallos, pedidos = 0, 0
    while fallos < FALLOS_SEGUIDOS:
        periodo = f"{anyo}M{mes:02d}"
        reciente = (hoy.year * 12 + hoy.month) - (anyo * 12 + mes) < 3
        if periodo in guardado and not reciente:
            fallos = 0
        else:
            url = publicadas.get(periodo) or FICHERO.format(
                base=BASE, aa=f"{anyo % 100:02d}", mes=MESES[mes - 1], mm=mes)
            estado, _, datos = red.abre(url)
            pedidos += 1
            if estado != 200 or datos[:8] != xls.FIRMA:
                print(f"    {periodo}: sin fichero")
                fallos += 1
            elif mes == 12:
                # Diciembre cierra el año y trae los doce meses de una vez.
                cierre = lee_cierre(datos, anyo)
                if cierre:
                    guardado.update(cierre)
                    fallos = 0
                    print(f"    {anyo}: cierre con {len(cierre)} meses")
                else:
                    print(f"    {periodo}: el cierre no trae tabla territorial")
                    fallos += 1
            else:
                leido = lee_mes(datos)
                if leido:
                    guardado[periodo] = leido
                    fallos = 0
                    print(f"    {periodo}: Castellón "
                          f"{leido.get('castellon', {}).get('participantes')} "
                          f"participantes")
                else:
                    print(f"    {periodo}: sin tabla territorial")
                    fallos += 1
        anyo, mes = (anyo - 1, 12) if mes == 1 else (anyo, mes - 1)

    por_ambito: dict[str, dict] = {a: {"ambos": {}} for a in FILAS}
    for periodo, ambitos in guardado.items():
        for ambito, magnitudes in ambitos.items():
            for magnitud, valor in magnitudes.items():
                por_ambito[ambito]["ambos"].setdefault(magnitud, {})[periodo] = valor

    print(f"  {pedidos} peticiones · {len(guardado)} meses en total")
    periodos = bloques.escribe_bloque("huelgas", BLOQUE, por_ambito, ahora, RAIZ)
    return 0 if periodos else 1


if __name__ == "__main__":
    raise SystemExit(main())
