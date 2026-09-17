"""Comprueba los datos publicados antes de que lleguen al repositorio.

Se ejecuta después de descargar y antes de commitear: si algo no cuadra, el
workflow se para y no se publica nada.

Busca cuatro cosas distintas:

- **Estructura**: que cada fichero diga lo que dice su índice.
- **Identidades contables**: donde dos series están ligadas por definición
  -activos = ocupados + parados-, tienen que cumplirse.
- **Rangos plausibles**: una esperanza de vida de tres años significa que la
  búsqueda acabó en otra serie. Ya pasó.
- **Cobertura**: ningún indicador puede perder periodos respecto a la última
  descarga. Esto es lo que delata que el INE ha renombrado una serie y el
  descargador ha dejado de encontrarla, que es el fallo silencioso peligroso.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data"
COBERTURA = DATOS / "cobertura.json"

# Rangos plausibles por indicador, comunes a todos los ámbitos. La clave es el
# nombre del indicador tal y como aparece en los ficheros de datos.
RANGOS = {
    # mercado laboral (miles de personas y porcentajes)
    "ocupados": (1, 50_000),
    "parados": (0, 20_000),
    "activos": (1, 60_000),
    "tasa_actividad": (20, 90),
    "tasa_paro": (0, 70),
    "tasa_empleo": (10, 90),
    # población
    "poblacion": (10_000, 100_000_000),
    "edad_media": (20, 60),
    "mayores_70": (0, 50),
    "espanoles": (0, 100),
    "crecimiento": (-100, 100),
    # demografía
    "mortalidad_infantil": (0, 100),
    "edad_maternidad": (20, 45),
    "saldo_migratorio": (-100, 100),
    "nacidos_por_defuncion": (0, 5_000),
    # renta
    "renta_persona": (1_000, 100_000),
    "renta_hogar": (1_000, 200_000),
    "renta_uc": (1_000, 150_000),
    "gini": (0, 100),
    "p80p20": (0, 50),
    "bajo_60": (0, 100),
    "tamano_hogar": (1, 10),
    "hogares_unipersonales": (0, 100),
    "renta_persona_real": (1_000, 200_000),
    "renta_hogar_real": (1_000, 400_000),
    "renta_uc_real": (1_000, 300_000),
    # paro registrado (personas)
    "paro_total": (0, 10_000_000),
    "paro_menores_25": (0, 5_000_000),
    "paro_25_44": (0, 5_000_000),
    "paro_45_mas": (0, 5_000_000),
    "paro_agricultura": (0, 5_000_000),
    "paro_industria": (0, 5_000_000),
    "paro_construccion": (0, 5_000_000),
    "paro_servicios": (0, 5_000_000),
    "paro_sin_empleo_anterior": (0, 5_000_000),
    # contratos registrados
    "contratos_total": (0, 5_000_000),
    "contratos_indefinidos": (0, 3_000_000),
    "contratos_temporales": (0, 3_000_000),
    "contratos_convertidos": (0, 3_000_000),
    "contratos_agricultura": (0, 3_000_000),
    "contratos_industria": (0, 3_000_000),
    "contratos_construccion": (0, 3_000_000),
    "contratos_servicios": (0, 3_000_000),
    # vivienda
    "compraventas": (0, 300_000),
    "compraventas_nueva": (0, 300_000),
    "compraventas_usada": (0, 300_000),
    "compraventas_protegida": (0, 300_000),
    "hipotecas": (0, 300_000),
    "importe_hipotecas": (0, 50_000_000),
    "hipoteca_media": (20_000, 600_000),
    "ejecuciones": (0, 100_000),
    "ipv": (30, 400),
    "ipv_variacion": (-40, 40),
    "ipva": (30, 400),
    "ipva_variacion": (-40, 40),
    "esfuerzo": (0.5, 20),
    "lanzamientos": (0, 50_000),
    "lanzamientos_hipoteca": (0, 50_000),
    "lanzamientos_alquiler": (0, 50_000),
    "lanzamientos_otros": (0, 50_000),
    # salarios y rentas del trabajo
    "renta_salario": (0, 100),
    "renta_pensiones": (0, 100),
    "renta_desempleo": (0, 100),
    "renta_otras_prestaciones": (0, 100),
    "salario_bruto": (5_000, 120_000),
    "salario_bruto_real": (5_000, 200_000),
    "brecha_salarial": (-50, 80),
    "desigualdad_salarial": (1, 20),
    "gini_salarial": (0, 100),
    # cesta de la compra: índices, todos en la base vigente del IPC
    "alimentos": (30, 400),
    "aceite_oliva": (30, 400),
    "leche": (30, 400),
    "huevos": (30, 400),
    "pan": (30, 400),
    "cereales": (30, 400),
    "carne_vacuno": (30, 400),
    "carne_ave": (30, 400),
    "carne_porcino": (30, 400),
    "pescado": (30, 400),
    "frutas": (30, 400),
    "hortalizas": (30, 400),
    "patatas": (30, 400),
    "cafe": (30, 400),
    "azucar": (30, 400),
    "preparados": (30, 400),
    "agua": (30, 400),
    "restaurantes": (30, 400),
    "restauracion": (30, 400),
    # huelgas
    "huelgas": (0, 10_000),
    "participantes": (0, 10_000_000),
    "jornadas_perdidas": (0, 50_000_000),
    # despidos y regulación de empleo
    "ere_afectados": (0, 5_000_000),
    "ere_despido": (0, 1_000_000),
    "ere_suspension": (0, 5_000_000),
    "despidos": (0, 5_000_000),
    # convenios colectivos
    "subida_pactada": (-5, 30),
    "trabajadores_convenio": (0, 20_000_000),
    "convenios": (0, 20_000),
    "jornada_pactada": (1_000, 2_200),
    # el precio de la luz, en céntimos por kWh
    "pvpc_medio": (0, 100),
    "pvpc_barata": (-10, 100),
    "pvpc_cara": (0, 200),
    "pvpc_brecha": (0, 150),
    # afiliación a la Seguridad Social (medias anuales de personas)
    "afiliados": (1_000, 50_000_000),
    "autonomos": (100, 10_000_000),
    "autonomos_mes": (100, 10_000_000),
    # accidentes de trabajo (cifras absolutas de un año entero)
    "accidentes_jornada": (0, 2_000_000),
    "accidentes_leves": (0, 2_000_000),
    "accidentes_graves": (0, 50_000),
    "accidentes_mortales": (0, 5_000),
    "accidentes_itinere": (0, 500_000),
    "mortales_itinere": (0, 2_000),
    # precios
    "ipc_general": (50, 200),
    "ipc_variacion": (-30, 60),
    "ipc_alimentos": (-30, 60),
    "ipc_transporte": (-40, 60),
    # materias primas, en la moneda y la unidad en que las publica el Banco
    # Mundial. Los rangos son anchos a propósito: no están para vigilar el
    # mercado -el oro ha pasado de 35 dólares a más de 5.000 sin que nada
    # fallara- sino para cazar el día en que se lea la columna de al lado.
    "materias/brent": (0.5, 500),
    "materias/gas_europa": (0.1, 200),
    "materias/carbon": (1, 1_000),
    "materias/trigo": (10, 2_000),
    "materias/maiz": (10, 2_000),
    "materias/aceite_girasol": (100, 5_000),
    # Estas dos van con el bloque por delante porque «azucar» y «cafe» ya
    # existen en la cesta de la compra, donde son índices del IPC con base
    # 100. Son cosas distintas con el mismo nombre, y sin el prefijo el
    # rango de una tumbaba a la otra.
    "materias/azucar": (0.01, 5),
    "materias/cafe": (0.1, 30),
    "materias/cacao": (0.1, 30),
    "materias/naranja": (0.02, 10),
    "materias/urea": (5, 2_000),
    "materias/cobre": (100, 30_000),
    "materias/aluminio": (100, 10_000),
    "materias/oro": (20, 20_000),
    "materias/euro_dolar": (0.5, 2),
    "materias/wti": (0.5, 500),
    "materias/gas_eeuu": (0.1, 200),
    "materias/aceite_soja": (50, 5_000),
    "materias/aceite_palma": (50, 5_000),
    "materias/arroz": (10, 3_000),
    "materias/ternera": (0.1, 30),
    "materias/pollo": (0.1, 20),
    "materias/platano": (0.05, 10),
    "materias/azucar_mundial": (0.01, 5),
    "materias/dap": (10, 2_000),
    "materias/potasa": (5, 2_000),
    "materias/algodon": (0.05, 20),
    "materias/caucho": (0.05, 20),
    "materias/hierro": (0.05, 500),
    "materias/niquel": (100, 100_000),
    "materias/zinc": (50, 20_000),
    "materias/plata": (0.1, 500),
    # carburantes, en euros por litro. El GLP ronda un euro y la gasolina dos;
    # el rango es ancho para no volver a tocarlo en la próxima crisis.
    "gasolina_95": (0.3, 5),
    "gasoleo_a": (0.3, 5),
    "gasolina_98": (0.3, 5),
    "gasoleo_premium": (0.3, 5),
    "glp": (0.2, 5),
    "gasolina_95_serie": (0.3, 5),
    "gasoleo_a_serie": (0.3, 5),
    "glp_serie": (0.2, 5),
    "gasolina_95_impuesto": (0, 90),
    "gasoleo_a_impuesto": (0, 90),
}

# Relaciones que se cumplen por definición, con la holgura del redondeo del
# INE: (nombre, función sobre las series, tolerancia absoluta).
IDENTIDADES = [
    ("activos = ocupados + parados",
     ("activos", "ocupados", "parados"),
     lambda a, o, p: abs(a - (o + p)),
     0.35),
    ("tasa de paro = parados / activos",
     ("tasa_paro", "parados", "activos"),
     lambda t, p, a: abs(t - (p / a * 100)) if a else 0.0,
     0.1),
    ("tasa de empleo = tasa de actividad × (1 − tasa de paro)",
     ("tasa_empleo", "tasa_actividad", "tasa_paro"),
     lambda te, ta, tp: abs(te - ta * (1 - tp / 100)),
     0.15),
    # Toda vivienda comprada es nueva o de segunda mano: si esto deja de
    # cuadrar, alguna de las tres series ha dejado de ser la que creemos.
    ("compraventas = nueva + segunda mano",
     ("compraventas", "compraventas_nueva", "compraventas_usada"),
     lambda t, n, u: abs(t - (n + u)),
     0.5),
    # El INE publica el importe en miles de euros, pero la media se calcula
    # eligiendo la escala que da una cifra plausible, así que aquí vale
    # cualquiera de las dos: lo que se comprueba es que sea ese cociente.
    # Todo lanzamiento sale de una hipoteca, de un alquiler o de otra cosa: si
    # esto no cuadra, se ha leído mal alguna hoja del fichero del CGPJ. La
    # holgura es de un lanzamiento porque el propio CGPJ tiene un descuadre de
    # uno en el total nacional del 4T de 2022 -publica 8.981 donde sus columnas
    # suman 8.982-, y no es cosa de la lectura: los otros 52 trimestres y los
    # tres ámbitos cuadran exactos.
    ("lanzamientos = hipoteca + alquiler + otros",
     ("lanzamientos", "lanzamientos_hipoteca", "lanzamientos_alquiler",
      "lanzamientos_otros"),
     lambda t, h, a, o: abs(t - (h + a + o)),
     1.5),
    # Todo accidente en jornada es leve, grave o mortal: si esto deja de
    # cuadrar es que se ha leído mal alguna columna de la tabla del ministerio,
    # que además cambia de sitio las columnas cada pocos años.
    ("accidentes en jornada = leves + graves + mortales",
     ("accidentes_jornada", "accidentes_leves", "accidentes_graves",
      "accidentes_mortales"),
     lambda t, l, g, m: abs(t - (l + g + m)),
     0.5),
    # La hora más cara nunca puede salir más barata que la más barata, y la
    # diferencia es exactamente eso: si esto no cuadra, se han mezclado meses.
    ("diferencia horaria = hora cara − hora barata",
     ("pvpc_brecha", "pvpc_cara", "pvpc_barata"),
     lambda b, c, m: abs(b - (c - m)),
     0.01),
    ("hipoteca media = importe / número",
     ("hipoteca_media", "importe_hipotecas", "hipotecas"),
     lambda m, i, n: min(abs(m - i * 1000 / n), abs(m - i / n)) if n else 0.0,
     0.5),
]


# Cada cuánto publica cada fuente y cuánto se puede tardar en notarlo. El
# margen es generoso a propósito: cuenta desde el final del periodo, no desde
# el día de publicación, e incluye el retraso normal del organismo. Lo que
# detecta no es que una fuente vaya lenta, sino que ha dejado de llegar.
FRESCURA = {
    "epa": ("trimestral", 6),
    # La encuesta de estructura salarial publica con año y medio de retraso
    # y el Atlas con dos años, así que un dato de hace dos años y medio
    # todavía es normal aquí.
    "salarios": ("anual", 30),
    "paro-registrado": ("mensual", 3),
    "contratos": ("mensual", 3),
    "precios": ("mensual", 3),
    "cesta": ("mensual", 3),
    "vivienda": ("mensual", 6),
    # La serie de accidentes es anual y se cierra con el fichero de diciembre,
    # que el ministerio publica en febrero o marzo del año siguiente. Con menos
    # de quince meses de margen saltaría la alarma todos los eneros.
    "siniestralidad": ("anual", 15),
    # El anuario del año sale a mediados del siguiente, así que hasta bien
    # entrado el otoño el último dato es el del año anterior.
    # El bloque mezcla cadencias: la afiliación total es anual y sale con el
    # anuario, pero los autónomos son mensuales y llegan con dos meses de
    # retraso. Manda el más rápido, que es el que primero delataría un corte.
    "afiliacion": ("mensual los autónomos, anual el resto", 4),
    # La serie mensual se cierra cuando el mes termina, así que hasta que no
    # acaba el mes en curso el último dato es el del anterior.
    "luz": ("mensual", 2),
    # El Pink Sheet sale el primer día hábil del mes con el mes anterior
    # cerrado, así que dos meses de margen ya es señal de que algo pasa.
    "materias": ("mensual", 2),
    # El ministerio publica a diario y la Comisión cada semana, así que aquí un
    # mes de retraso ya es mucho.
    "carburantes": ("mensual", 2),
    "convenios": ("mensual", 4),
    "despidos": ("mensual los expedientes, anual los despidos", 4),
    # El avance de huelgas sale con unos cuatro meses de retraso, más que
    # ninguna otra fuente del panel, así que el margen tiene que ser mayor.
    "huelgas": ("mensual", 7),
    "poblacion": ("anual o trimestral, según el indicador", 15),
    "demografia": ("anual", 30),
    "renta": ("anual", 36),
}

# Los ficheros municipales no son bloques -no tienen índice- pero también
# pueden quedarse atrás sin que nadie se entere.
FRESCURA_MUNICIPAL = {
    "municipios/poblacion-castellon.json": ("anual", 24),
    "municipios/renta-castellon.json": ("anual", 36),
    "paro-registrado/municipios-castellon.json": ("mensual", 3),
}

PERIODO = re.compile(r"^(\d{4})(?:([TSM])(\d{1,2}))?$")


def fin_de_periodo(periodo: str) -> dt.date | None:
    """El último día del periodo, que es desde cuando se puede esperar el dato."""
    coincidencia = PERIODO.match(periodo or "")
    if not coincidencia:
        return None
    anyo, letra, numero = coincidencia.groups()
    anyo = int(anyo)
    if not letra:
        return dt.date(anyo, 12, 31)
    numero = int(numero)
    ultimo_mes = {"M": numero, "T": numero * 3, "S": numero * 6}.get(letra)
    if not ultimo_mes or not 1 <= ultimo_mes <= 12:
        return None
    siguiente = dt.date(anyo + ultimo_mes // 12, ultimo_mes % 12 + 1, 1)
    return siguiente - dt.timedelta(days=1)


def meses_desde(fecha: dt.date, hoy: dt.date) -> float:
    return (hoy - fecha).days / 30.44


def revisa_frescura(informe: Informe, hoy: dt.date | None = None) -> None:
    """¿Sigue llegando lo que se descarga?

    La validación de cobertura detecta que una serie pierda periodos, no que
    deje de ganarlos. Sin esto, una fuente puede morirse en silencio: el
    descargador de lanzamientos, por ejemplo, publica el bloque sin ellos si un
    día no encuentra el fichero del CGPJ, y eso es lo que se quiere -que una
    fuente caída no tumbe el resto- pero hay que enterarse.
    """
    hoy = hoy or dt.date.today()

    for nombre, (cadencia, margen) in sorted(FRESCURA.items()):
        indice = DATOS / nombre / "index.json"
        if not indice.exists():
            informe.error(f"{nombre}: no hay datos publicados")
            continue
        ultimo = carga(indice).get("ultimo_periodo")
        fecha = fin_de_periodo(ultimo)
        if not fecha:
            informe.error(f"{nombre}: no se entiende el último periodo ({ultimo!r})")
            continue
        retraso = meses_desde(fecha, hoy)
        estado = "✓" if retraso <= margen else "✗"
        print(f"  {estado} {nombre}: {ultimo} ({cadencia}), {retraso:.1f} meses "
              f"del margen de {margen}")
        if retraso > margen:
            informe.error(
                f"{nombre}: el último dato es de {ultimo}, hace {retraso:.0f} meses, "
                f"y es una fuente {cadencia}; o el organismo ha dejado de publicar "
                f"o el descargador ha dejado de encontrarlo")

    for ruta, (cadencia, margen) in sorted(FRESCURA_MUNICIPAL.items()):
        fichero = DATOS / ruta
        if not fichero.exists():
            informe.error(f"{ruta}: no está publicado")
            continue
        periodos = carga(fichero).get("periodos") or []
        fecha = fin_de_periodo(periodos[-1]) if periodos else None
        if not fecha:
            informe.error(f"{ruta}: sin periodos legibles")
            continue
        retraso = meses_desde(fecha, hoy)
        estado = "✓" if retraso <= margen else "✗"
        print(f"  {estado} {ruta}: {periodos[-1]} ({cadencia}), {retraso:.1f} meses "
              f"del margen de {margen}")
        if retraso > margen:
            informe.error(
                f"{ruta}: el último dato es de {periodos[-1]}, hace {retraso:.0f} meses, "
                f"y es una fuente {cadencia}")


class Informe:
    def __init__(self) -> None:
        self.errores: list[str] = []
        self.avisos: list[str] = []

    def error(self, mensaje: str) -> None:
        self.errores.append(mensaje)

    def aviso(self, mensaje: str) -> None:
        self.avisos.append(mensaje)


def bloques() -> list[Path]:
    """Carpetas de datos que tienen índice, en orden estable."""
    return sorted(d for d in DATOS.iterdir() if d.is_dir() and (d / "index.json").exists())


def carga(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


def revisa_estructura(bloque: Path, indice: dict, informe: Informe) -> dict:
    """Comprueba el índice y devuelve el contenido de cada ámbito."""
    contenidos = {}
    for ambito in indice.get("ambitos", []):
        ruta = bloque / ambito["fichero"]
        if not ruta.exists():
            informe.error(f"{bloque.name}: falta el fichero {ambito['fichero']}")
            continue
        contenido = carga(ruta)
        periodos = contenido.get("periodos") or []
        if not periodos:
            informe.error(f"{bloque.name}/{ambito['id']}: no tiene periodos")
            continue
        for sexo, magnitudes in contenido.get("series", {}).items():
            for clave, valores in magnitudes.items():
                if len(valores) != len(periodos):
                    informe.error(
                        f"{bloque.name}/{ambito['id']}/{sexo}/{clave}: "
                        f"{len(valores)} valores para {len(periodos)} periodos"
                    )
        contenidos[ambito["id"]] = contenido
    return contenidos


def revisa_rangos(bloque: str, ambito: str, contenido: dict, informe: Informe) -> None:
    for sexo, magnitudes in contenido.get("series", {}).items():
        for clave, valores in magnitudes.items():
            # Un rango puede declararse para todo el panel -«tasa_paro»- o
            # sólo para un bloque -«materias/azucar»-, y el del bloque manda.
            # Hace falta porque dos bloques pueden llamar igual a cosas
            # distintas: el azúcar de la cesta es un índice del IPC y el de
            # materias primas son dólares por kilo.
            rango = RANGOS.get(f"{bloque}/{clave}") or RANGOS.get(clave)
            if not rango:
                continue
            minimo, maximo = rango
            fuera = [v for v in valores if v is not None and not (minimo <= v <= maximo)]
            if fuera:
                informe.error(
                    f"{bloque}/{ambito}/{sexo}/{clave}: {len(fuera)} valores fuera "
                    f"del rango {rango}, por ejemplo {fuera[:3]}"
                )


def revisa_identidades(bloque: str, ambito: str, contenido: dict, informe: Informe) -> None:
    periodos = contenido["periodos"]
    for sexo, magnitudes in contenido.get("series", {}).items():
        for nombre, claves, calcula, tolerancia in IDENTIDADES:
            if not all(c in magnitudes for c in claves):
                continue
            peor, cuando = 0.0, None
            for i in range(len(periodos)):
                partes = [magnitudes[c][i] for c in claves]
                if any(v is None for v in partes):
                    continue
                desvio = calcula(*partes)
                if desvio > peor:
                    peor, cuando = desvio, periodos[i]
            if peor > tolerancia:
                informe.error(
                    f"{bloque}/{ambito}/{sexo}: no se cumple «{nombre}» "
                    f"(desviación {peor:.3f} en {cuando}, tolerancia {tolerancia})"
                )


def revisa_continuidad(bloque: str, ambito: str, contenido: dict, informe: Informe) -> None:
    """Un salto enorme entre dos periodos seguidos suele ser un empalme malo."""
    periodos = contenido["periodos"]
    for sexo, magnitudes in contenido.get("series", {}).items():
        for clave, valores in magnitudes.items():
            for i in range(1, len(valores)):
                anterior, actual = valores[i - 1], valores[i]
                # Con valores pequeños, o que cruzan el cero, la variación
                # relativa se dispara sin que signifique nada: la inflación
                # pasando de 0,2 % a 1 % no es un salto sospechoso.
                if anterior is None or actual is None or abs(anterior) < 5:
                    continue
                cambio = abs(actual - anterior) / abs(anterior)
                if cambio > 3:
                    informe.aviso(
                        f"{bloque}/{ambito}/{sexo}/{clave}: salto de "
                        f"{anterior} a {actual} entre {periodos[i-1]} y {periodos[i]}"
                    )


# Desgloses que deberían sumar su total, con la holgura del secreto
# estadístico: (nombre, total, partes).
DESGLOSES = [
    ("por edad", "paro_total", ("paro_menores_25", "paro_25_44", "paro_45_mas")),
    ("por sector", "paro_total", ("paro_agricultura", "paro_industria",
                                  "paro_construccion", "paro_servicios",
                                  "paro_sin_empleo_anterior")),
    ("por tipo de contrato", "contratos_total",
     ("contratos_indefinidos", "contratos_temporales", "contratos_convertidos")),
    ("por sector", "contratos_total",
     ("contratos_agricultura", "contratos_industria", "contratos_construccion",
      "contratos_servicios")),
]


def revisa_desgloses(bloque: str, ambito: str, contenido: dict, informe: Informe) -> None:
    """Los desgloses del paro registrado no suman el total, y es correcto.

    El SEPE publica como «<5» los valores menores de cinco, que no se pueden
    sumar, así que cada desglose se queda algo por debajo. Lo que sí sería
    sospechoso es que la diferencia fuese grande.
    """
    periodos = contenido["periodos"]
    for sexo, magnitudes in contenido.get("series", {}).items():
        for nombre, clave_total, claves in DESGLOSES:
            total = magnitudes.get(clave_total)
            if not total or not all(c in magnitudes for c in claves):
                continue
            peor, cuando = 0.0, None
            for i in range(len(periodos)):
                if total[i] in (None, 0):
                    continue
                partes = [magnitudes[c][i] for c in claves]
                if any(v is None for v in partes):
                    continue
                desvio = (total[i] - sum(partes)) / total[i]
                if desvio > peor:
                    peor, cuando = desvio, periodos[i]
            if peor > 0.05:
                informe.error(
                    f"{bloque}/{ambito}/{sexo}: el desglose {nombre} se queda un "
                    f"{peor:.1%} por debajo del total en {cuando}; el secreto "
                    f"estadístico no explica tanto"
                )
            elif peor > 0.02:
                informe.aviso(
                    f"{bloque}/{ambito}/{sexo}: el desglose {nombre} se queda un "
                    f"{peor:.1%} por debajo del total en {cuando} (valores ocultos)"
                )


def cobertura_actual(bloque: str, ambito: str, contenido: dict) -> dict[str, int]:
    """Cuántos periodos con dato tiene cada serie."""
    resultado = {}
    for sexo, magnitudes in contenido.get("series", {}).items():
        for clave, valores in magnitudes.items():
            con_dato = sum(1 for v in valores if v is not None)
            resultado[f"{bloque}/{ambito}/{sexo}/{clave}"] = con_dato
    return resultado


def revisa_cobertura(actual: dict[str, int], informe: Informe) -> None:
    """Compara con la descarga anterior: nada puede encoger.

    Es la comprobación que detecta que el INE ha renombrado una serie y el
    descargador ha dejado de encontrarla, porque eso no produce ningún error:
    simplemente el indicador deja de estar.
    """
    if not COBERTURA.exists():
        print("  (no hay cobertura anterior con la que comparar; se crea ahora)")
        return

    anterior = carga(COBERTURA).get("series", {})
    for clave, periodos_antes in anterior.items():
        periodos_ahora = actual.get(clave)
        if periodos_ahora is None:
            informe.error(f"desaparecida: {clave} tenía {periodos_antes} periodos y ya no está")
        elif periodos_ahora < periodos_antes:
            informe.error(
                f"encogida: {clave} pasa de {periodos_antes} a {periodos_ahora} periodos"
            )

    nuevas = sorted(set(actual) - set(anterior))
    for clave in nuevas:
        print(f"  nueva serie: {clave} ({actual[clave]} periodos)")


def main() -> int:
    if not DATOS.exists():
        print("No hay carpeta data/; nada que validar.")
        return 1

    # La frescura se comprueba aparte, después de publicar: que una fuente se
    # haya quedado atrás no es motivo para no publicar lo que sí ha llegado,
    # pero sí para que el run salga en rojo y se entere alguien.
    if "--frescura" in sys.argv:
        informe = Informe()
        print("== frescura ==")
        revisa_frescura(informe)
        if informe.errores:
            print(f"\n{len(informe.errores)} fuentes se han quedado atrás:")
            for error in informe.errores:
                print(f"  ✗ {error}")
            return 1
        print("\nTodas las fuentes están al día.")
        return 0

    informe = Informe()
    cobertura: dict[str, int] = {}

    for bloque in bloques():
        indice = carga(bloque / "index.json")
        print(f"\n== {bloque.name} ==")
        contenidos = revisa_estructura(bloque, indice, informe)
        for ambito_id, contenido in contenidos.items():
            revisa_rangos(bloque.name, ambito_id, contenido, informe)
            revisa_identidades(bloque.name, ambito_id, contenido, informe)
            revisa_continuidad(bloque.name, ambito_id, contenido, informe)
            revisa_desgloses(bloque.name, ambito_id, contenido, informe)
            cobertura.update(cobertura_actual(bloque.name, ambito_id, contenido))
        series = sum(1 for k in cobertura if k.startswith(bloque.name + "/"))
        print(f"  {len(contenidos)} ámbitos · {series} series")

    print("\n== cobertura ==")
    revisa_cobertura(cobertura, informe)

    if informe.avisos:
        print(f"\n{len(informe.avisos)} avisos (no bloquean la publicación):")
        for aviso in informe.avisos[:15]:
            print(f"  · {aviso}")
        if len(informe.avisos) > 15:
            print(f"  · … y {len(informe.avisos) - 15} más")

    if informe.errores:
        print(f"\n{len(informe.errores)} ERRORES; no se publica nada:")
        for error in informe.errores:
            print(f"  ✗ {error}")
        return 1

    COBERTURA.write_text(
        json.dumps({"series": dict(sorted(cobertura.items()))}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nTodo correcto: {len(cobertura)} series validadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
