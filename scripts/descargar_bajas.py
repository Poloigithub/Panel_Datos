"""Las bajas laborales: incapacidad temporal, por provincia y por año.

De la **Seguridad Social**, que es quien paga la prestación y quien lleva la
cuenta de los procesos. Es la fuente buena, y encontrarla costó siete sondeos
porque está escondida detrás de tres clics y porque dos veces di por vacío lo
que en realidad no sabía buscar.

Publica un fichero por ejercicio, de 2005 en adelante, con dos tablas dentro.
Se usa la primera, **«Estadística»**, que trae por provincia ocho magnitudes
con el nombre escrito en claro. La segunda, «Datos mensuales», sería mejor
-tiene mes y sexo- pero identifica sus magnitudes con un código numérico sin
leyenda: se comprobó que el 25 son los procesos iniciados, porque agregando sus
meses sale exactamente la cifra que la tabla anual da con ese nombre, pero de
los otros cinco no hay certeza. Un indicador que no se puede identificar con
seguridad se queda fuera, así que de momento la sección es anual.

Cuatro cosas que esta fuente obliga a decir:

- **Las direcciones no se pueden construir.** Cada ejercicio vive en una página
  con un UUID, y el nombre del fichero cambia de un año a otro: «Publicación IT
  mcss 2026», «Publicacion_IT_SISTEMA_2026_Junio», «Publicación IT cierre
  Sistema 2024». Hay que leerlas del índice cada vez, como ya se hace con las
  huelgas y con el Pink Sheet.

- **El año en curso está a medias.** El fichero de 2026 llega a junio, así que
  sus «procesos iniciados» son los de medio año y compararlos con un año
  entero sería mentir. Un ejercicio sólo entra cuando su tabla mensual trae los
  doce meses.

- **El covid cambió de sitio.** Hasta junio de 2023 esos procesos contaban como
  contingencia profesional y después como común. La página lo dice, porque si
  no la profesional parece desplomarse sola.

- **Los años cerrados se revisan.** El propio fichero avisa de que en marzo de
  2026 se rehicieron 2024 y 2025. Por eso aquí no hay caché: se vuelven a bajar
  todos los ejercicios en cada actualización.
"""

from __future__ import annotations

import datetime as dt
import html as htmllib
import math
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import bloques_ine as bloques  # noqa: E402
import xls  # noqa: E402
import xlsx  # noqa: E402

INDICE = ("https://www.seg-social.es/wps/portal/wss/internet/"
          "EstadisticasPresupuestosEstudios/Estadisticas/EST45/EST46")

CABECERAS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9",
}

HOJA_ANUAL = "Estadística"
HOJA_MENSUAL = "Datos mensuales"

# Qué columna de la tabla anual es cada indicador. Se busca por el texto de la
# cabecera, nunca por su posición: la hoja es una tabla dinámica y la tabla
# empieza en la columna 5, no en la 0.
COLUMNAS = [
    ("procesos_iniciados", "numero de procesos iniciados",
     "Bajas iniciadas", "procesos", "procesos de baja iniciados en el año", 0),
    ("procesos_finalizados", "numero de procesos finalizados",
     "Bajas terminadas", "procesos", "procesos de baja que acabaron en el año", 0),
    ("procesos_vigor", "numero de procesos en vigor",
     "Bajas abiertas a fin de año", "procesos",
     "procesos todavía abiertos al cerrar el año", 0),
    ("duracion_media", "duracion media de los procesos",
     "Duración media de una baja", "días",
     "días que dura de media un proceso terminado", 1),
    ("incidencia", "incidencia media mensual",
     "Bajas nuevas al mes por cada mil trabajadores", "‰",
     "procesos iniciados al mes por cada mil trabajadores protegidos", 2),
    ("prevalencia", "prevalencia por cada mil",
     "Trabajadores de baja por cada mil", "‰",
     "procesos en vigor por cada mil trabajadores protegidos", 2),
    ("trabajadores_protegidos", "trabajadores protegidos al final",
     "Trabajadores protegidos", "personas",
     "personas cubiertas por la prestación al cerrar el año", 0),
]

NOTAS = {
    "prevalencia": "Mide cuánta gente está de baja en un momento dado; la "
                   "incidencia mide cuántas bajas empiezan. Una plantilla con "
                   "pocas bajas pero muy largas tiene prevalencia alta e "
                   "incidencia baja.",
    "procesos_vigor": "Es una foto del 31 de diciembre, no una suma del año: "
                      "cuenta las bajas que seguían abiertas ese día.",
}

# Cómo se llama cada ámbito dentro de la hoja. Castellón viene con las dos
# lenguas, que es como lo escribe la Seguridad Social.
CASTELLON = re.compile(r"castell[oó]n", re.I)
COMUNITAT = re.compile(r"comunitat|comunidad\s+valenciana", re.I)


def normaliza(texto) -> str:
    """Sin tildes, sin dobles espacios y en minúsculas, para comparar."""
    crudo = str(texto or "")
    tildes = str.maketrans("áéíóúÁÉÍÓÚàèìòùÀÈÌÒÙ", "aeiouAEIOUaeiouAEIOU")
    return re.sub(r"\s+", " ", crudo.translate(tildes)).strip().lower()


def pide(url: str, intentos: int = 4, limite: int = 60_000_000) -> bytes:
    espera, ultimo = 3, ""
    for intento in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=CABECERAS)
            with urllib.request.urlopen(
                    peticion, timeout=240,
                    context=ssl.create_default_context()) as respuesta:
                return respuesta.read(limite)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{exc.code} en {url[:90]}") from exc
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            if intento < intentos:
                time.sleep(espera)
                espera *= 2
    raise RuntimeError(f"no se pudo bajar {url[:90]}: {ultimo}")


def limpia(trozo: str) -> str:
    return re.sub(r"\s+", " ",
                  htmllib.unescape(re.sub(r"<[^>]+>", " ", trozo))).strip()


def enlaces(html: str, base: str) -> list[tuple[str, str]]:
    salida, vistos = [], set()
    for href, dentro in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                                   html, re.I | re.S):
        texto = limpia(dentro)
        entero = urllib.parse.urljoin(base, htmllib.unescape(href))
        if (texto, entero) not in vistos:
            vistos.add((texto, entero))
            salida.append((texto, entero))
    return salida


def ejercicios_publicados() -> dict[int, str]:
    """Qué años publica hoy la Seguridad Social y en qué página está cada uno.

    Las direcciones de los últimos años llevan un UUID, así que construirlas es
    imposible: se leen del índice en cada ejecución.
    """
    html = pide(INDICE, limite=8_000_000).decode("utf-8", "replace")
    salida = {}
    for texto, destino in enlaces(html, INDICE):
        casa = re.fullmatch(r"Ejercicio\s+(\d{4})", texto)
        if casa:
            salida[int(casa.group(1))] = destino
    if not salida:
        raise RuntimeError(
            f"el índice de la Seguridad Social ya no enlaza ejercicios; hay "
            f"que mirar {INDICE} antes de tocar nada")
    return salida


def hoja_del_ejercicio(url: str) -> bytes | None:
    """El fichero del sistema entero de ese año.

    Cada ejercicio publica dos: el de las mutuas colaboradoras y el del sistema
    completo -mutuas más el instituto nacional y el social de la marina-. Se
    quiere el segundo, que es el que cubre a todo el mundo, y además es el
    pequeño. Como el nombre cambia cada año, se eligen por lo que dicen.
    """
    html = pide(url, limite=8_000_000).decode("utf-8", "replace")
    hojas = [(texto, destino) for texto, destino in enlaces(html, url)
             if re.search(r"\.xlsx?(\?|$)", destino, re.I)]
    if not hojas:
        return None

    def prioridad(par) -> int:
        nombre = normaliza(urllib.parse.unquote(par[1]))
        if "sistema" in nombre:
            return 0
        if "inss" in nombre and "ism" in nombre:
            return 1
        return 2

    for _texto, destino in sorted(hojas, key=prioridad):
        try:
            datos = pide(destino, intentos=2)
        except RuntimeError as exc:
            print(f"      no se pudo bajar: {exc}")
            continue
        if datos[:2] == b"PK" or datos[:8] == xls.FIRMA:
            return datos
        # La Seguridad Social contesta 200 con su portal cuando el fichero no
        # está: el código no basta, hay que mirar los primeros bytes.
        print(f"      lo que llegó no es una hoja de cálculo ({datos[:16]!r})")
    return None


def cobertura_del_ejercicio(libro) -> tuple[int, bool]:
    """Cuántos meses trae el fichero y si es un cierre de año.

    Un año a medias no se puede comparar con uno entero, pero hay dos formas de
    traer el año entero. Los ficheros mensuales listan sus doce meses; los de
    **cierre** ponen literalmente «Cierre» en la columna del mes, y eso también
    es el año completo. Al no distinguirlos, el primer ensayo descartó 2024 por
    «sólo 1 mes» siendo un año cerrado.
    """
    if HOJA_MENSUAL not in libro.hojas:
        return 0, False
    filas = list(libro.filas(HOJA_MENSUAL))
    if not filas:
        return 0, False
    cabecera = [normaliza(c) for c in filas[0]]
    try:
        donde = cabecera.index("mes")
    except ValueError:
        return 0, False
    valores = {normaliza(f[donde]) for f in filas[1:]
               if donde < len(f) and f[donde]}
    cierre = any("cierre" in v for v in valores)
    meses = len({v for v in valores if "cierre" not in v})
    return meses, cierre


def hoja_anual(libro) -> tuple[str, list] | None:
    """La hoja con la tabla provincial, buscada por lo que contiene.

    El nombre no sirve: se llama «Estadística» en los últimos años, pero
    «Hoja1», «INSS SIN SEXO» o «datos IT cierre 22» en los anteriores. Lo que
    no cambia es que la tabla buena nombra la comunidad autónoma en su
    cabecera, así que se busca eso.
    """
    for nombre in libro.hojas:
        try:
            filas = list(libro.filas(nombre))
        except Exception:  # noqa: BLE001
            continue
        for fila in filas[:40]:
            if any("comunidad autonoma" in normaliza(c) for c in fila):
                return nombre, filas
    return None


def lee_tabla_anual(libro) -> dict[str, dict[str, float]]:
    """Las magnitudes de cada ámbito, buscadas por el texto de su columna."""
    encontrada = hoja_anual(libro)
    if not encontrada:
        raise RuntimeError(
            f"ninguna hoja trae una tabla por comunidad autónoma; "
            f"hay {list(libro.hojas)}")
    _nombre_hoja, filas = encontrada

    # La cabecera es la fila que nombra la comunidad autónoma, no la primera:
    # encima hay un rótulo de tabla dinámica y filas en blanco.
    cabecera_n, cabecera = None, None
    for numero, fila in enumerate(filas):
        if any("comunidad autonoma" in normaliza(c) for c in fila):
            cabecera_n, cabecera = numero, fila
            break
    if cabecera is None:
        raise RuntimeError("no se encuentra la cabecera de la tabla anual")

    donde_ccaa = next(i for i, c in enumerate(cabecera)
                      if "comunidad autonoma" in normaliza(c))
    donde_prov = next((i for i, c in enumerate(cabecera)
                       if normaliza(c) == "provincia"), donde_ccaa + 1)

    columnas = {}
    for clave, pista, *_ in COLUMNAS:
        for i, celda in enumerate(cabecera):
            if pista in normaliza(celda):
                columnas[clave] = i
                break
    faltan = [c for c, *_ in COLUMNAS if c not in columnas]
    if faltan:
        raise RuntimeError(f"la tabla anual ya no trae estas columnas: {faltan}")

    def valores(fila) -> dict[str, float]:
        salida = {}
        for clave, numero in columnas.items():
            if numero < len(fila) and isinstance(fila[numero], (int, float)):
                salida[clave] = float(fila[numero])
        return salida

    por_ambito: dict[str, dict[str, float]] = {}
    # Todas las provincias, no sólo los tres ámbitos: son las que permiten
    # demostrar qué mide cada columna de la otra tabla de la hoja.
    por_provincia: dict[str, dict[str, float]] = {}
    # Y el total de cada comunidad, que sumados son España por definición: las
    # diecisiete comunidades más Ceuta y Melilla no dejan nada fuera.
    por_ccaa: dict[str, dict[str, float]] = {}
    ccaa_actual = ""
    for fila in filas[cabecera_n + 1:]:
        if donde_ccaa < len(fila) and str(fila[donde_ccaa] or "").strip():
            ccaa_actual = str(fila[donde_ccaa]).strip()
        provincia = str(fila[donde_prov] or "").strip() if donde_prov < len(fila) else ""
        if not provincia:
            continue

        if normaliza(provincia) not in ("total", "total general"):
            medidas = valores(fila)
            if medidas:
                por_provincia[normaliza(provincia)] = medidas

        if CASTELLON.search(provincia):
            por_ambito["castellon"] = valores(fila)
        # El total de la Comunitat es la fila «Total» de su grupo.
        if normaliza(provincia) == "total" and ccaa_actual:
            if COMUNITAT.search(ccaa_actual):
                por_ambito["comunitat-valenciana"] = valores(fila)
            medidas = valores(fila)
            if medidas:
                por_ccaa[normaliza(ccaa_actual)] = medidas
        # Y el de España, que en una tabla dinámica de Excel se llama «Total
        # general» y puede estar en cualquiera de las dos columnas.
        etiquetas = {normaliza(fila[i]) for i in (donde_ccaa, donde_prov)
                     if i < len(fila) and fila[i]}
        if "total general" in etiquetas:
            por_ambito["espana"] = valores(fila)

    if "espana" not in por_ambito:
        nacional = espana_por_calibracion(filas, por_provincia)
        nacional = completa_espana(nacional, por_ccaa, por_provincia)
        if nacional:
            por_ambito["espana"] = nacional

    return por_ambito


def completa_espana(nacional: dict, por_ccaa: dict, por_provincia: dict) -> dict:
    """Rellenar España sumando comunidades, pero sólo tras comprobar que suma.

    Las magnitudes absolutas -bajas iniciadas, terminadas, abiertas,
    trabajadores protegidos- son sumables por definición: las comunidades
    parten el país sin solaparse. Aun así no se suma a ciegas. Primero se
    comprueba contra las magnitudes que la calibración **ya ha demostrado**: si
    sumar las comunidades reproduce esos totales, el método vale para las
    demás; si no los reproduce, es que falta o sobra alguna fila y no se suma
    nada.

    Las tasas -incidencia y prevalencia- no se suman. Se derivan, y sólo si la
    fórmula se cumple en las provincias, donde sí están las tres cifras.
    """
    if not por_ccaa:
        return nacional

    sumas = {}
    for clave, *_ in COLUMNAS:
        trozos = [m[clave] for m in por_ccaa.values() if clave in m]
        if len(trozos) == len(por_ccaa):
            sumas[clave] = sum(trozos)

    # El control: lo ya demostrado tiene que salir de la suma.
    controles = [c for c in nacional if c in sumas]
    if not controles:
        print("      sin ninguna magnitud demostrada con la que contrastar la "
              "suma de comunidades; no se suma nada")
        return nacional
    for clave in controles:
        if not math.isclose(nacional[clave], sumas[clave], rel_tol=1e-4):
            print(f"      sumar las comunidades no reproduce {clave} "
                  f"({sumas[clave]:,.0f} frente a {nacional[clave]:,.0f}); "
                  f"no se suma nada")
            return nacional
    print(f"      la suma de {len(por_ccaa)} comunidades reproduce "
          f"{controles}: se acepta para las magnitudes que se pueden sumar")

    ABSOLUTAS = ("procesos_iniciados", "procesos_finalizados", "procesos_vigor",
                 "trabajadores_protegidos")
    for clave in ABSOLUTAS:
        if clave not in nacional and clave in sumas:
            nacional[clave] = sumas[clave]

    # Las tasas, con la fórmula demostrada en las provincias.
    FORMULAS = {
        "incidencia": (("procesos_iniciados", "trabajadores_protegidos"),
                       lambda a, b: a / b * 1000 / 12),
        "prevalencia": (("procesos_vigor", "trabajadores_protegidos"),
                        lambda a, b: a / b * 1000),
    }
    for clave, (partes, formula) in FORMULAS.items():
        if clave in nacional:
            continue
        casan = fallan = 0
        for medidas in por_provincia.values():
            if not all(p in medidas for p in partes) or clave not in medidas:
                continue
            try:
                calculado = formula(*(medidas[p] for p in partes))
            except ZeroDivisionError:
                continue
            if math.isclose(calculado, medidas[clave], rel_tol=2e-2):
                casan += 1
            else:
                fallan += 1
        if casan >= 10 and fallan == 0 and all(p in nacional for p in partes):
            nacional[clave] = formula(*(nacional[p] for p in partes))
            print(f"      {clave}: la fórmula se cumple en {casan} provincias, "
                  f"así que se aplica a España")
        else:
            print(f"      {clave}: la fórmula no se cumple ({casan} sí, "
                  f"{fallan} no); España se queda sin ella")

    return nacional


def espana_por_calibracion(filas: list, por_provincia: dict) -> dict[str, float]:
    """El total nacional, demostrando antes qué mide cada columna.

    La hoja no trae una tabla sino varias, en paralelo. La que tiene los
    nombres escritos -comunidad, provincia, duración media...- **no lleva fila
    de total nacional**. Otra de la misma hoja sí la lleva, pero identifica sus
    columnas con el código numérico que ya dio guerra, sin leyenda.

    En vez de suponer la correspondencia por el tamaño de las cifras, se
    demuestra: una columna de la segunda tabla sólo se acepta como una magnitud
    concreta cuando coincide con ella **en todas las provincias que están en
    las dos tablas**. Con cincuenta provincias, que dos columnas cuadren en las
    cincuenta por casualidad no pasa. Lo que no se pueda demostrar así, no se
    publica: España se queda sin esa magnitud y se ve el hueco.
    """
    if not por_provincia:
        return {}

    # Dónde hay una fila «total general», y con qué columna de etiquetas.
    candidatas: dict[int, int] = {}
    for numero, fila in enumerate(filas):
        for i, celda in enumerate(fila):
            if normaliza(celda) == "total general":
                candidatas[i] = numero

    reunido: dict[str, float] = {}
    for columna_etiqueta, fila_total in sorted(candidatas.items()):
        # Las provincias de esta tabla, con lo que dice cada columna de valores.
        observado: dict[str, dict[int, float]] = {}
        for fila in filas:
            if columna_etiqueta >= len(fila):
                continue
            etiqueta = normaliza(fila[columna_etiqueta])
            if not etiqueta or etiqueta not in por_provincia:
                continue
            fila_valores = {}
            for i in range(columna_etiqueta + 1, min(len(fila), columna_etiqueta + 14)):
                if isinstance(fila[i], (int, float)):
                    fila_valores[i] = float(fila[i])
            if fila_valores:
                observado[etiqueta] = fila_valores

        comunes = [p for p in observado if p in por_provincia]
        if len(comunes) < 10:
            continue

        # Qué columna mide qué, demostrado provincia a provincia.
        probado: dict[str, int] = {}
        for clave, *_ in COLUMNAS:
            for columna in sorted({c for p in comunes for c in observado[p]}):
                casan = fallan = 0
                for provincia in comunes:
                    esperado = por_provincia[provincia].get(clave)
                    visto = observado[provincia].get(columna)
                    if esperado is None or visto is None:
                        continue
                    if math.isclose(esperado, visto, rel_tol=1e-6, abs_tol=1e-6):
                        casan += 1
                    else:
                        fallan += 1
                if fallan == 0 and casan >= 10:
                    probado[clave] = columna
                    break

        if not probado:
            continue

        total = filas[fila_total]
        nacional = {}
        for clave, columna in probado.items():
            if columna < len(total) and isinstance(total[columna], (int, float)):
                nacional[clave] = float(total[columna])
        if nacional:
            nuevas = [c for c in nacional if c not in reunido]
            if nuevas:
                print(f"      tabla en la columna {columna_etiqueta}: "
                      f"demostradas {sorted(nuevas)}")
            reunido.update(nacional)

    if reunido:
        sin_probar = [c for c, *_ in COLUMNAS if c not in reunido]
        if sin_probar:
            print(f"      sin demostrar por calibración: {sin_probar}")
    else:
        print("      ninguna tabla con total nacional se ha podido identificar")
    return reunido


def construye_bloque() -> dict:
    indicadores = {}
    for clave, _pista, titulo, unidad, unidad_texto, decimales in COLUMNAS:
        indicadores[clave] = {
            "titulo": titulo,
            "unidad": unidad,
            "unidad_texto": unidad_texto,
            "decimales": decimales,
            "por_sexo": False,
            "nota": NOTAS.get(clave),
        }
    return {"titulo": "Las bajas laborales", "indicadores": indicadores}


def main() -> None:
    ahora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    print("Bajas laborales · incapacidad temporal")

    paginas = ejercicios_publicados()
    print(f"  la Seguridad Social publica {len(paginas)} ejercicios: "
          f"{min(paginas)} … {max(paginas)}")

    por_ambito: dict[str, dict[str, dict[str, float]]] = {}
    completos, saltados = 0, []
    for anyo in sorted(paginas):
        try:
            datos = hoja_del_ejercicio(paginas[anyo])
        except RuntimeError as exc:
            print(f"    {anyo}: {exc}")
            saltados.append((anyo, "no se pudo abrir la página"))
            continue
        if not datos:
            print(f"    {anyo}: sin hoja de cálculo")
            saltados.append((anyo, "sin hoja de cálculo"))
            continue

        try:
            libro = xlsx.Libro(datos) if datos[:2] == b"PK" else xls.Libro(datos)
            meses, cierre = cobertura_del_ejercicio(libro)
            valores = lee_tabla_anual(libro)
        except Exception as exc:  # noqa: BLE001
            print(f"    {anyo}: no se pudo leer · {type(exc).__name__}: {exc}")
            saltados.append((anyo, "no se pudo leer"))
            continue

        # Un año a medias no se publica: sus procesos iniciados serían los de
        # medio año al lado de los de un año entero. Un cierre sí es entero.
        if not cierre and meses and meses < 12:
            print(f"    {anyo}: sólo {meses} meses y no es un cierre; se salta")
            saltados.append((anyo, f"sólo {meses} meses"))
            continue

        encontrados = {a: len(v) for a, v in valores.items() if v}
        cobertura = "cierre" if cierre else f"{meses or '?'} meses"
        print(f"    {anyo}: {cobertura} · {encontrados}")
        for ambito, magnitudes in valores.items():
            for clave, valor in magnitudes.items():
                por_ambito.setdefault(ambito, {}).setdefault(clave, {})[str(anyo)] = valor
        if encontrados:
            completos += 1

    if not por_ambito:
        raise SystemExit("no se ha podido leer ningún ejercicio; no se publica nada")

    print(f"  {completos} ejercicios con datos")
    for ambito in bloques.AMBITOS:
        magnitudes = por_ambito.get(ambito["id"], {})
        for clave, valores in sorted(magnitudes.items()):
            print(f"    {ambito['id']}/{clave}: {len(valores)} años, "
                  f"{min(valores)} … {max(valores)}")

    listo = {a: {"ambos": m} for a, m in por_ambito.items() if m}
    bloques.escribe_bloque("bajas", construye_bloque(), listo, ahora, RAIZ)


if __name__ == "__main__":
    main()
