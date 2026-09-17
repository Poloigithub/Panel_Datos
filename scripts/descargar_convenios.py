"""Convenios colectivos: cuánto se está pactando de subida salarial.

Es la pieza que cierra el círculo de la cesta de la compra. Allí se compara lo
que sube la comida con lo que sube el salario, pero el salario sale de una
encuesta que llega con año y medio de retraso: en 2026 lo más reciente es 2024.
Los convenios se publican **cada mes**, con dos de retraso, y dicen qué se está
firmando ahora mismo.

Del fichero mensual del ministerio se lee la tabla `CCT-2.6`, que reparte por
comunidad autónoma y provincia los convenios registrados, los trabajadores
afectados, la subida pactada y la jornada. Es un `.xls` binario de los de 1997,
que el panel puede abrir desde que tiene `scripts/xls.py`.

Dos cosas que hay que entender para leer bien esta cifra:

- **Es acumulada dentro del año.** El fichero de agosto no dice lo pactado en
  agosto, sino lo pactado en todos los convenios con efectos económicos en ese
  año registrados hasta agosto. Por eso la serie se mueve poco dentro de un año
  y da un salto en enero: empieza a contar de cero.
- **Es de los convenios registrados, no de toda la economía.** Sólo cuenta a
  quien tiene convenio y sólo a quien lo tiene ya registrado.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import bloques_ine as bloques  # noqa: E402
import red_ministerio as red  # noqa: E402
import xls  # noqa: E402

BASE = "https://www.mites.gob.es/estadisticas/cct"
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
         "sep", "oct", "nov", "dic")
# El ministerio escribe la carpeta en minúsculas desde 2018 y con mayúsculas
# antes, así que se prueban las dos formas.
CARPETAS = ("cct{aa}{mes}av", "CCT{aa}{Mes}Av", "CCT{aa}{Mes}AV")

FALLOS_SEGUIDOS = 4

FILAS = {
    "espana": "total",
    "comunitat-valenciana": "comunitat valenciana",
    "castellon": "castellon",
}

# Las columnas de la tabla, contadas desde el nombre del territorio.
COLUMNAS = {
    "convenios": 1,
    "trabajadores_convenio": 3,
    "subida_pactada": 4,
    "jornada_pactada": 5,
}

BLOQUE = {
    "titulo": "Convenios colectivos",
    "indicadores": {
        "subida_pactada": {
            "titulo": "Subida salarial pactada en convenio",
            "unidad": "%", "decimales": 2, "por_sexo": False,
            "unidad_texto": "variación salarial media pactada, en porcentaje",
            "nota": "Acumulada dentro del año: el dato de agosto recoge todos "
                    "los convenios con efectos económicos en ese año "
                    "registrados hasta agosto, no lo firmado en agosto. Por eso "
                    "la serie se mueve poco dentro de un año y da un salto en "
                    "enero, cuando empieza a contar de cero.",
        },
        "trabajadores_convenio": {
            "titulo": "Personas cubiertas por un convenio",
            "unidad": "personas", "decimales": 0, "por_sexo": False,
            "unidad_texto": "trabajadores afectados por convenios registrados",
            "nota": "Sólo cuenta a quien tiene convenio y lo tiene ya "
                    "registrado, así que no es toda la gente que trabaja.",
        },
        "convenios": {
            "titulo": "Convenios registrados",
            "unidad": "convenios", "decimales": 0, "por_sexo": False,
            "unidad_texto": "convenios con efectos económicos en el año",
        },
        "jornada_pactada": {
            "titulo": "Jornada media pactada",
            "unidad": "horas al año", "decimales": 2, "por_sexo": False,
            "unidad_texto": "horas de trabajo al año pactadas en convenio",
        },
    },
}


def normaliza(texto: str) -> str:
    """Sin acentos, sin espacios y en minúsculas.

    Aquí se quitan **todos** los espacios y no sólo los repetidos, porque la
    fila del total viene escrita «T O T A L», con las letras separadas, que es
    una floritura de maquetación de las que sólo se ven leyendo el fichero.
    """
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return "".join(plano.split())


BUSCADOS = {normaliza(nombre): clave for clave, nombre in FILAS.items()}

HOJA = ("variacion salarial", "comunidad autonoma y provincia")


def hoja_por_descripcion(libro) -> str | None:
    """La hoja que el índice del fichero describe con esas palabras."""
    def suave(texto: str) -> str:
        plano = (texto or "").strip().lower()
        for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                             ("ú", "u"), ("ñ", "n")):
            plano = plano.replace(viejo, nuevo)
        return " ".join(plano.split())

    indice = next((h for h in libro.hojas if suave(h).startswith("indice")), None)
    if not indice:
        return None
    for fila in libro.filas(indice):
        celdas = [str(c) for c in fila if c not in (None, "")]
        if not celdas:
            continue
        if not all(p in suave(" ".join(celdas)) for p in HOJA):
            continue
        codigo = suave(celdas[0]).rstrip(". ")
        for nombre in libro.hojas:
            if suave(nombre).rstrip(". ") == codigo:
                return nombre
    return None


def lee_mes(datos: bytes) -> dict[str, dict[str, float]]:
    libro = xls.Libro(datos)
    hoja = hoja_por_descripcion(libro)
    if not hoja:
        return {}
    salida: dict[str, dict[str, float]] = {}
    for fila in libro.filas(hoja):
        if not fila:
            continue
        clave = BUSCADOS.get(normaliza(str(fila[0] or "")))
        if not clave or clave in salida:
            continue
        magnitudes = {}
        for magnitud, columna in COLUMNAS.items():
            valor = fila[columna] if columna < len(fila) else None
            if isinstance(valor, (int, float)):
                magnitudes[magnitud] = float(valor)
        if magnitudes:
            salida[clave] = magnitudes
    return salida


def baja(anyo: int, mes: int) -> bytes | None:
    """El fichero de un mes, probando las formas en que el ministerio nombra
    su carpeta. Como con los accidentes, no vale mirar el estado: para lo que
    no existe devuelve su portada con un 200."""
    for plantilla in CARPETAS:
        carpeta = plantilla.format(aa=f"{anyo % 100:02d}", mes=MESES[mes - 1],
                                   Mes=MESES[mes - 1].capitalize())
        url = f"{BASE}/{carpeta}/CCT_{mes:02d}_{anyo}.xls"
        estado, _, datos = red.abre(url)
        if estado == 200 and datos[:8] == xls.FIRMA:
            return datos
    return None


def ya_bajados() -> dict[str, dict[str, dict[str, float]]]:
    """Lo que ya está en el repositorio, para no volver a pedirlo."""
    guardado: dict[str, dict[str, dict[str, float]]] = {}
    for ambito in FILAS:
        fichero = RAIZ / "data" / "convenios" / f"{ambito}.json"
        if not fichero.exists():
            continue
        contenido = json.loads(fichero.read_text(encoding="utf-8"))
        for magnitud, valores in contenido["series"]["ambos"].items():
            for periodo, valor in zip(contenido["periodos"], valores):
                if valor is not None:
                    guardado.setdefault(periodo, {}).setdefault(ambito, {})[magnitud] = valor
    return guardado


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    hoy = dt.date.today()
    print("\n=== Convenios colectivos ===")

    guardado = ya_bajados()
    print(f"  {len(guardado)} meses ya guardados")

    anyo, mes = hoy.year, hoy.month
    fallos, pedidos = 0, 0
    while fallos < FALLOS_SEGUIDOS:
        periodo = f"{anyo}M{mes:02d}"
        reciente = (hoy.year * 12 + hoy.month) - (anyo * 12 + mes) < 2
        if periodo in guardado and not reciente:
            fallos = 0
        else:
            datos = baja(anyo, mes)
            pedidos += 1
            if not datos:
                print(f"    {periodo}: sin fichero")
                fallos += 1
            else:
                leido = lee_mes(datos)
                if leido:
                    guardado[periodo] = leido
                    fallos = 0
                    print(f"    {periodo}: Castellón "
                          f"{leido.get('castellon', {}).get('subida_pactada')} %")
                else:
                    print(f"    {periodo}: el fichero está pero no se encuentra "
                          f"la tabla provincial")
                    fallos += 1
        anyo, mes = (anyo - 1, 12) if mes == 1 else (anyo, mes - 1)

    por_ambito: dict[str, dict] = {a: {"ambos": {}} for a in FILAS}
    for periodo, ambitos in guardado.items():
        for ambito, magnitudes in ambitos.items():
            for magnitud, valor in magnitudes.items():
                por_ambito[ambito]["ambos"].setdefault(magnitud, {})[periodo] = valor

    print(f"  {pedidos} peticiones · {len(guardado)} meses en total")
    periodos = bloques.escribe_bloque("convenios", BLOQUE, por_ambito, ahora, RAIZ)
    return 0 if periodos else 1


if __name__ == "__main__":
    raise SystemExit(main())
