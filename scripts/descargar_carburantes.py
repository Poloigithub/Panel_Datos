"""El precio de los carburantes: veintidós años de España y el detalle de hoy.

Dos fuentes, porque ninguna de las dos sola vale:

- **El boletín petrolero de la Comisión Europea** publica desde enero de 2005,
  semana a semana, lo que cuesta la gasolina 95, el gasóleo A y el GLP en cada
  estado miembro, con impuestos y sin ellos. Son veintidós años de historia y
  permiten además decir **cuánto de lo que se paga en el surtidor es impuesto**,
  que es la mitad larga. Pero es sólo España: no tiene provincia.

- **La API del Ministerio para la Transición Ecológica** publica el precio de
  las once mil y pico gasolineras del país en tiempo real. No tiene histórico
  -da la foto de hoy y nada más- pero cada estación dice de qué provincia es,
  así que es la única forma de saber lo que cuesta llenar el depósito **en
  Castellón**.

**Las dos series no se empalman.** La Comisión publica el precio más frecuente,
ponderado, que le comunica cada estado; el ministerio da la media simple de las
gasolineras. Miden cosas parecidas con métodos distintos, y unirlas en una sola
línea sería inventarse una continuidad que no existe. Van separadas y la página
dice cuál es cuál.

Otras tres decisiones:

- **Un solo viaje, tres ámbitos.** Cada estación trae su `IDProvincia`, así que
  con una petición -12 MB, unos veinte segundos- salen España, la Comunitat y
  Castellón. Provincia por provincia serían cincuenta y dos viajes.

- **Lo del ministerio se guarda, porque no se puede recuperar.** Igual que con
  la luz, `data/carburantes/diario.json` acumula la media de cada día. Un día
  que no se recoja está perdido para siempre: ese fichero es el dato, no un
  caché. La media nacional diaria desde el 30 de marzo de 2026 ya estaba
  calculada en `preciodiariogasolina`, con esta misma fuente y el mismo método,
  y se lee de allí para que España no empiece el día que se enchufó esto. La
  provincia sí empieza hoy, y la página lo dice.

- **No hace falta relajar el TLS.** El script de aquel repositorio apaga la
  verificación del certificado para hablar con el ministerio. Se probó con el
  contexto por defecto de Python y con los cifrados relajados, y las dos veces
  el servidor contestó a la primera, incluidos los 12 MB de toda España. Lo que
  hace falta es paciencia, porque la API corta la conexión de vez en cuando.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import bloques_ine as bloques  # noqa: E402
import xlsx  # noqa: E402

DESTINO = RAIZ / "data" / "carburantes"
DIARIO = DESTINO / "diario.json"
HOY = DESTINO / "hoy.json"

API = ("https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
       "PreciosCarburantes/EstacionesTerrestres/")
API_PROVINCIA = API + "FiltroProvincia/{id}"
API_PROVINCIAS = ("https://sedeaplicaciones.minetur.gob.es/"
                  "ServiciosRESTCarburantes/PreciosCarburantes/Listados/"
                  "Provincias/")

# Cuántas provincias tienen que contestar para que la media nacional valga.
# No hacen falta las cincuenta y dos: la media de las estaciones de cuarenta y
# cinco provincias sigue siendo una media nacional razonable, y perder el día
# entero porque una falle sería peor. Menos de eso, no se publica.
PROVINCIAS_MINIMAS = 45

# La media nacional que ya estaba calculada, con esta misma fuente y este mismo
# método, antes de que el panel tuviera sección de carburantes.
SEMILLA = ("https://raw.githubusercontent.com/Poloigithub/"
           "preciodiariogasolina/main/precios_carburantes.csv")

# El histórico de la Comisión Europea. Como con el Pink Sheet, la dirección se
# lee de la página en vez de escribirse: lleva dentro un identificador que
# cambia con cada publicación.
BOLETIN_PAGINA = ("https://energy.ec.europa.eu/data-and-analysis/"
                  "weekly-oil-bulletin_en")
HOJA_CON = "Prices with taxes"
HOJA_SIN = "Prices wo taxes"

# Excel cuenta los días desde el 30 de diciembre de 1899: se saltó el bulo del
# año bisiesto de 1900 y por eso la base es esa y no el 1 de enero.
EPOCA_EXCEL = dt.date(1899, 12, 30)

# Qué columnas de España se leen del boletín. El nombre es el literal de la
# cabecera, que es como se busca: por texto y no por posición, porque el
# fichero tiene 226 columnas y contarlas a mano es pedir un error.
DEL_BOLETIN = [
    ("gasolina_95_serie", "ES_price_with_tax_euro95",
     "ES_price_wo_tax_euro95", "Gasolina 95 desde 2005"),
    ("gasoleo_a_serie", "ES_price_with_tax_diesel",
     "ES_price_wo_tax_diesel", "Gasóleo A desde 2005"),
    ("glp_serie", "ES_price_with_tax_LPG",
     "ES_price_wo_tax_LPG", "GLP desde 2005"),
]

# De los dos precios sale la pregunta que de verdad interesa: qué parte de lo
# que se paga en el surtidor son impuestos.
IMPUESTOS = [
    ("gasolina_95_impuesto", "gasolina_95_serie", "Impuestos en la gasolina 95"),
    ("gasoleo_a_impuesto", "gasoleo_a_serie", "Impuestos en el gasóleo A"),
]

# El boletín publica en euros por mil litros.
DE_MIL_LITROS = 1000

CABECERAS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9",
}

# Provincia 12 es Castellón; la Comunitat son Alicante, Castellón y Valencia.
CASTELLON = "12"
COMUNITAT = {"03", "12", "46"}

# Qué carburantes se publican, con el nombre que les da la API, el que usa el
# CSV de la semilla y el que llevan en el panel.
CARBURANTES = [
    ("gasolina_95", "Precio Gasolina 95 E5", "Gasolina 95",
     "Gasolina 95", "la más común"),
    ("gasoleo_a", "Precio Gasoleo A", "Diésel",
     "Gasóleo A (diésel)", "el diésel corriente"),
    ("gasolina_98", "Precio Gasolina 98 E5", "Gasolina 98",
     "Gasolina 98", None),
    ("gasoleo_premium", "Precio Gasoleo Premium", "Diésel Premium",
     "Gasóleo premium", None),
    ("glp", "Precio Gases licuados del petróleo", "GLP",
     "GLP (gas licuado)", None),
]

# Un mes entra en la serie mensual cuando se han recogido al menos veinte días.
# Con menos, la media diría más de los días que faltan que del precio.
DIAS_MINIMOS = 20

AVISO_METODO = ("Media simple de las gasolineras que publican ese precio, sin "
                "ponderar por cuánto vende cada una. Es el mismo método que "
                "usa todo el mundo con este dato, pero conviene saberlo: una "
                "gasolinera de pueblo pesa lo mismo que una de autopista.")

AVISO_BOLETIN = ("Del boletín petrolero de la Comisión Europea, que publica el "
                 "precio más frecuente comunicado por cada estado, ponderado. "
                 "Es un método distinto del de la media de gasolineras del "
                 "ministerio, así que las dos series no se empalman: miden lo "
                 "mismo de dos maneras y se publican por separado. No tiene "
                 "desglose provincial.")


def pide(url: str, intentos: int = 5, limite: int = 60_000_000) -> bytes:
    """La API corta la conexión de vez en cuando; no es un no."""
    espera, ultimo = 3, ""
    for intento in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=CABECERAS)
            with urllib.request.urlopen(peticion, timeout=240) as respuesta:
                return respuesta.read(limite)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{exc.code} en {url[:80]}") from exc
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            print(f"      intento {intento}: {ultimo}")
            if intento < intentos:
                time.sleep(espera)
                espera *= 2
    raise RuntimeError(f"no se pudo bajar {url[:80]}: {ultimo}")


def precio(crudo) -> float | None:
    """La API escribe los precios con coma decimal y deja vacío lo que no vende."""
    texto = str(crudo or "").strip()
    if not texto:
        return None
    try:
        valor = float(texto.replace(",", "."))
    except ValueError:
        return None
    # Un euro y pico por litro. Fuera de ahí es que la celda dice otra cosa.
    return valor if 0.1 <= valor <= 10 else None


def _lista(cuerpo: dict) -> list[dict]:
    return cuerpo.get("ListaEESSPrecio") or []


def _todas_de_una(intentos: int) -> tuple[list[dict], str] | None:
    """Plan A: las once mil gasolineras en una sola petición.

    Son 12 MB y el servidor corta la conexión a menudo con esa carga. Cuando
    sale, sale en veinte segundos; cuando no, es mejor no insistir mucho y
    pasar al plan B que insistir diez veces en lo mismo.
    """
    try:
        cuerpo = json.loads(pide(API, intentos=intentos).decode("utf-8-sig",
                                                                "replace"))
    except RuntimeError as exc:
        print(f"    de una vez, no: {exc}")
        return None
    estaciones = _lista(cuerpo)
    if not estaciones:
        return None
    print(f"    de una vez: {len(estaciones):,} gasolineras")
    return estaciones, str(cuerpo.get("Fecha") or "")


def _provincia_a_provincia() -> tuple[list[dict], str] | None:
    """Plan B: una petición por provincia.

    Cada una son 200 KB y contestan sin queja donde la grande se ahoga. Son
    cincuenta y dos viajes en vez de uno, pero es la diferencia entre tener el
    dato del día y no tenerlo.
    """
    try:
        provincias = json.loads(
            pide(API_PROVINCIAS, intentos=4, limite=400_000)
            .decode("utf-8-sig", "replace"))
    except RuntimeError as exc:
        print(f"    tampoco se puede listar las provincias: {exc}")
        return None

    codigos = sorted({str(p.get("IDPovincia") or p.get("IDProvincia") or "").strip()
                      for p in provincias} - {""})
    print(f"    provincia a provincia: {len(codigos)} provincias que pedir")

    estaciones: list[dict] = []
    fecha, fallidas = "", []
    for codigo in codigos:
        try:
            cuerpo = json.loads(
                pide(API_PROVINCIA.format(id=codigo), intentos=3,
                     limite=8_000_000).decode("utf-8-sig", "replace"))
        except RuntimeError:
            fallidas.append(codigo)
            continue
        estaciones.extend(_lista(cuerpo))
        fecha = fecha or str(cuerpo.get("Fecha") or "")

    conseguidas = len(codigos) - len(fallidas)
    print(f"    {conseguidas} de {len(codigos)} provincias, "
          f"{len(estaciones):,} gasolineras"
          + (f"; fallaron {fallidas}" if fallidas else ""))

    if CASTELLON in fallidas:
        raise RuntimeError("no ha contestado Castellón, que es media sección")
    if conseguidas < PROVINCIAS_MINIMAS:
        raise RuntimeError(
            f"sólo {conseguidas} provincias de {len(codigos)}: con eso la media "
            f"nacional no es nacional")
    return estaciones, fecha


def medias_de_hoy() -> tuple[str, dict[str, dict[str, float]], dict[str, dict[str, int]]]:
    """Media por ámbito y carburante, y cuántas estaciones la sostienen."""
    print("  pidiendo las gasolineras")
    conseguido = _todas_de_una(intentos=2) or _provincia_a_provincia()
    if not conseguido:
        raise RuntimeError("el ministerio no ha contestado por ninguna de las "
                           "dos vías")
    estaciones, crudo_fecha = conseguido

    # La API declara la fecha con hora: «17/09/2026 17:06:18».
    try:
        dia = dt.datetime.strptime(crudo_fecha.split()[0],
                                   "%d/%m/%Y").date().isoformat()
    except (ValueError, IndexError):
        dia = dt.date.today().isoformat()
    print(f"  {len(estaciones):,} gasolineras, fecha declarada {crudo_fecha!r}")

    suma: dict[str, dict[str, list[float]]] = {
        ambito["id"]: {clave: [] for clave, *_ in CARBURANTES}
        for ambito in bloques.AMBITOS
    }
    for estacion in estaciones:
        provincia = str(estacion.get("IDProvincia") or "").strip()
        donde = ["espana"]
        if provincia in COMUNITAT:
            donde.append("comunitat-valenciana")
        if provincia == CASTELLON:
            donde.append("castellon")
        for clave, campo, *_ in CARBURANTES:
            valor = precio(estacion.get(campo))
            if valor is None:
                continue
            for ambito in donde:
                suma[ambito][clave].append(valor)

    medias, cuantas = {}, {}
    for ambito, magnitudes in suma.items():
        medias[ambito] = {}
        cuantas[ambito] = {}
        for clave, valores in magnitudes.items():
            cuantas[ambito][clave] = len(valores)
            if valores:
                medias[ambito][clave] = round(sum(valores) / len(valores), 4)
    return dia, medias, cuantas


def lee_semilla() -> dict[str, dict[str, float]]:
    """La media nacional diaria ya calculada, de `preciodiariogasolina`.

    Se lee una vez y sólo rellena días de España que no estén ya recogidos: lo
    que mida este panel manda siempre sobre lo que venga de fuera.
    """
    try:
        texto = pide(SEMILLA, intentos=3, limite=4_000_000).decode("utf-8-sig",
                                                                   "replace")
    except RuntimeError as exc:
        print(f"    sin semilla ({exc}); la serie de España empieza donde empiece")
        return {}

    columnas = {csv_nombre: clave for clave, _api, csv_nombre, *_ in CARBURANTES}
    dias: dict[str, dict[str, float]] = {}
    for fila in csv.DictReader(io.StringIO(texto)):
        dia = (fila.get("Fecha") or "").strip()
        if len(dia) != 10:
            continue
        valores = {}
        for csv_nombre, clave in columnas.items():
            valor = precio(fila.get(csv_nombre))
            if valor is not None:
                valores[clave] = valor
        if valores:
            # Ese CSV tiene un día repetido; se queda la última lectura.
            dias[dia] = valores
    print(f"    semilla: {len(dias)} días, {min(dias)} … {max(dias)}")
    return dias


def direccion_del_boletin() -> str:
    """El enlace al histórico que publica hoy la Comisión Europea.

    Misma precaución que con el Pink Sheet: la URL lleva un identificador de
    versión, así que se lee de la página. Si desaparece, esto revienta en vez
    de servir un fichero viejo en silencio.
    """
    import re
    html = pide(BOLETIN_PAGINA, intentos=3, limite=4_000_000).decode("utf-8",
                                                                     "replace")
    for crudo in re.findall(r'href="([^"]+\.xlsx[^"]*)"', html, re.I):
        if "history" in crudo.lower():
            entero = crudo if crudo.startswith("http") else \
                "https://energy.ec.europa.eu" + crudo
            return entero.replace("&amp;", "&")
    raise RuntimeError(
        f"la Comisión ya no enlaza el histórico en {BOLETIN_PAGINA}")


def _columnas_de(filas: list[list], nombres: set[str]) -> dict[str, int]:
    """Dónde está cada columna, buscándola por su nombre de cabecera."""
    if not filas:
        return {}
    return {str(celda).strip(): i
            for i, celda in enumerate(filas[0])
            if str(celda or "").strip() in nombres}


def _semanas(filas: list[list], donde: dict[str, int]) -> dict[str, dict[str, float]]:
    """De las filas semanales a `{columna: {fecha: euros por litro}}`."""
    salida: dict[str, dict[str, float]] = {nombre: {} for nombre in donde}
    for fila in filas[1:]:
        if not fila or not isinstance(fila[0], (int, float)):
            continue
        serial = int(fila[0])
        # Del primer boletín (2005) a hoy caben de sobra en este rango; un
        # serial fuera de él es una celda que no es una fecha.
        if not 30_000 <= serial <= 80_000:
            continue
        fecha = (EPOCA_EXCEL + dt.timedelta(days=serial)).isoformat()
        for nombre, columna in donde.items():
            if columna >= len(fila):
                continue
            valor = fila[columna]
            if not isinstance(valor, (int, float)) or valor <= 0:
                continue
            salida[nombre][fecha] = valor / DE_MIL_LITROS
    return salida


def lee_boletin() -> dict[str, dict[str, float]]:
    """Las series mensuales de España, del boletín petrolero europeo."""
    direccion = direccion_del_boletin()
    print(f"  la Comisión publica hoy: {direccion[:100]}…")
    datos = pide(direccion, intentos=3, limite=40_000_000)
    print(f"    {len(datos):,} bytes")
    libro = xlsx.Libro(datos)

    faltan = [h for h in (HOJA_CON, HOJA_SIN) if h not in libro.hojas]
    if faltan:
        raise RuntimeError(f"el boletín ya no trae las hojas {faltan}; "
                           f"tiene {list(libro.hojas)}")

    con = _semanas(list(libro.filas(HOJA_CON)),
                   _columnas_de(list(libro.filas(HOJA_CON)),
                                {c for _, c, _s, _t in DEL_BOLETIN}))
    sin = _semanas(list(libro.filas(HOJA_SIN)),
                   _columnas_de(list(libro.filas(HOJA_SIN)),
                                {s for _, _c, s, _t in DEL_BOLETIN}))

    # De semanal a mensual: la media de las semanas cuyo lunes cae en el mes.
    def a_meses(semanal: dict[str, float]) -> dict[str, float]:
        por_mes: dict[str, list[float]] = {}
        for fecha, valor in semanal.items():
            por_mes.setdefault(a_mes(fecha), []).append(valor)
        return {mes: round(sum(v) / len(v), 4) for mes, v in por_mes.items()}

    series: dict[str, dict[str, float]] = {}
    for clave, columna_con, columna_sin, _titulo in DEL_BOLETIN:
        mensual = a_meses(con.get(columna_con, {}))
        if mensual:
            series[clave] = mensual
            print(f"    {clave}: {len(mensual)} meses, "
                  f"{min(mensual)} … {max(mensual)}")
        else:
            print(f"    {clave}: VACÍO")
        series[f"_sin_{clave}"] = a_meses(sin.get(columna_sin, {}))

    # Qué parte del precio son impuestos: lo que separa los dos precios,
    # dividido por el precio final.
    for clave_impuesto, clave_precio, _titulo in IMPUESTOS:
        final = series.get(clave_precio, {})
        limpio = series.get(f"_sin_{clave_precio}", {})
        parte = {}
        for mes, valor in final.items():
            base = limpio.get(mes)
            if base is None or valor <= 0:
                continue
            parte[mes] = round((valor - base) / valor * 100, 2)
        if parte:
            series[clave_impuesto] = parte
            print(f"    {clave_impuesto}: {len(parte)} meses, "
                  f"último {parte[max(parte)]} %")

    # Las series auxiliares del precio sin impuestos no se publican: sólo
    # servían para sacar el porcentaje.
    return {k: v for k, v in series.items() if not k.startswith("_sin_")}


def carga_diario() -> dict:
    if not DIARIO.exists():
        return {}
    try:
        return json.loads(DIARIO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("    diario.json ilegible; se empieza de cero")
        return {}


def a_mes(dia: str) -> str:
    return f"{dia[:4]}M{dia[5:7]}"


def series_mensuales(dias: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """De la media de cada día a la media de cada mes."""
    por_mes: dict[str, dict[str, list[float]]] = {}
    for dia, valores in dias.items():
        mes = por_mes.setdefault(a_mes(dia), {})
        for clave, valor in valores.items():
            mes.setdefault(clave, []).append(valor)

    salida: dict[str, dict[str, float]] = {}
    for mes, magnitudes in por_mes.items():
        for clave, valores in magnitudes.items():
            if len(valores) < DIAS_MINIMOS:
                continue
            salida.setdefault(clave, {})[mes] = round(sum(valores) / len(valores), 4)
    return salida


def construye_bloque() -> dict:
    indicadores = {}
    for clave, _campo, _csv, titulo, coletilla in CARBURANTES:
        nota = AVISO_METODO
        if clave == "glp":
            nota = ("Sólo unas mil gasolineras de once mil venden GLP, así que "
                    "esta media sale de una muestra pequeña y muy concreta. "
                    "En Castellón puede haber pocas o ninguna. " + AVISO_METODO)
        elif clave in ("gasolina_98", "gasoleo_premium"):
            nota = ("Lo venden alrededor de la mitad de las gasolineras, así "
                    "que la media cubre menos estaciones que la del 95 o la "
                    "del gasóleo A. " + AVISO_METODO)
        indicadores[clave] = {
            "titulo": titulo,
            "unidad": "€/l",
            "unidad_texto": "euros por litro, media del mes"
                            + (f" · {coletilla}" if coletilla else ""),
            "decimales": 3,
            "por_sexo": False,
            "nota": nota,
        }

    # Y las del boletín europeo, que son España sola pero llegan a 2005.
    for clave, _con, _sin, titulo in DEL_BOLETIN:
        indicadores[clave] = {
            "titulo": titulo,
            "unidad": "€/l",
            "unidad_texto": "euros por litro con impuestos, media del mes",
            "decimales": 3,
            "por_sexo": False,
            "sin_ambitos": ("castellon", "comunitat-valenciana"),
            "nota": AVISO_BOLETIN,
        }
    for clave, _precio, titulo in IMPUESTOS:
        indicadores[clave] = {
            "titulo": titulo,
            "unidad": "%",
            "unidad_texto": "porcentaje del precio final que son impuestos",
            "decimales": 2,
            "por_sexo": False,
            "sin_ambitos": ("castellon", "comunitat-valenciana"),
            "nota": "Lo que separa al precio con impuestos del precio sin "
                    "ellos, sobre el precio final. Incluye el impuesto de "
                    "hidrocarburos y el IVA. " + AVISO_BOLETIN,
        }

    return {"titulo": "El precio de los carburantes", "indicadores": indicadores}


def main() -> None:
    ahora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    DESTINO.mkdir(parents=True, exist_ok=True)

    print("Carburantes")
    diario = carga_diario()
    antes = sum(len(v) for v in diario.values())

    # La semilla sólo se lee mientras España tenga menos días que ella; en
    # cuanto el panel la alcanza, deja de hacer falta pedirla cada día.
    semilla = lee_semilla()
    espana = diario.setdefault("espana", {})
    nuevos_semilla = 0
    for dia, valores in semilla.items():
        if dia not in espana:
            espana[dia] = valores
            nuevos_semilla += 1
    if nuevos_semilla:
        print(f"    {nuevos_semilla} días de España vienen de la semilla")

    # Las dos fuentes son independientes y se tratan como tales: que el
    # ministerio esté caído no puede llevarse por delante el histórico europeo
    # ni lo que ya se había recogido. Un día perdido es un hueco, y los huecos
    # el panel los enseña.
    try:
        dia, medias, cuantas = medias_de_hoy()
    except RuntimeError as exc:
        print(f"  el ministerio no ha contestado hoy: {exc}")
        print("  se sigue con lo ya recogido y con el boletín europeo")
    else:
        for ambito, valores in medias.items():
            if valores:
                # Lo que mide el panel manda sobre la semilla.
                diario.setdefault(ambito, {})[dia] = valores
        for ambito in bloques.AMBITOS:
            detalle = ", ".join(
                f"{clave}={medias[ambito['id']].get(clave, '—')}"
                f" ({cuantas[ambito['id']].get(clave, 0)})"
                for clave, *_ in CARBURANTES)
            print(f"    {ambito['id']}: {detalle}")

        # El detalle del último día, para el panel de arriba de la página.
        HOY.write_text(json.dumps({
            "fecha": dia,
            "actualizado": ahora,
            "ambitos": {a: medias.get(a, {})
                        for a in (x["id"] for x in bloques.AMBITOS)},
            "estaciones": {a: cuantas.get(a, {})
                           for a in (x["id"] for x in bloques.AMBITOS)},
        }, ensure_ascii=False), encoding="utf-8")

    DIARIO.write_text(json.dumps(diario, ensure_ascii=False, sort_keys=True),
                      encoding="utf-8")
    despues = sum(len(v) for v in diario.values())
    print(f"  diario.json: {antes} → {despues} días-ámbito")

    por_ambito = {}
    for ambito in bloques.AMBITOS:
        mensual = series_mensuales(diario.get(ambito["id"], {}))
        if mensual:
            por_ambito[ambito["id"]] = {"ambos": mensual}
        print(f"    {ambito['id']}: {len(mensual)} indicadores con mes cerrado")

    # El histórico europeo, que es sólo España y va junto a lo anterior sin
    # mezclarse: son indicadores distintos porque miden de otra manera.
    print("  boletín petrolero de la Comisión Europea")
    try:
        del_boletin = lee_boletin()
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"    no se ha podido leer: {exc}")
        del_boletin = {}
    if del_boletin:
        por_ambito.setdefault("espana", {}).setdefault("ambos", {}).update(del_boletin)

    if not por_ambito:
        print("  todavía no hay ningún mes con suficientes días; sólo se guarda "
              "el diario")
        return

    bloques.escribe_bloque("carburantes", construye_bloque(), por_ambito, ahora,
                           RAIZ)


if __name__ == "__main__":
    main()
