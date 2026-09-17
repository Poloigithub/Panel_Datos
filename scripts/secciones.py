"""Las secciones del panel: qué es cada una, dónde vive y cada cuánto publica.

Esto lo comparten tres scripts -los titulares de la portada, el catálogo de
indicadores y el buscador-, y tenerlo en un sitio evita que una sección nueva
aparezca en unos sitios y en otros no.
"""

from __future__ import annotations

AMBITOS = ["espana", "comunitat-valenciana", "castellon"]

# Qué se enseña de cada sección y cada cuánto se revisa. La cadencia es la de
# la fuente: la tarea de actualización mira todos los días, pero un dato anual
# no cambia por mirarlo más.
SECCIONES = [
    {
        "bloque": "epa", "enlace": "mercado-laboral.html", "titulo": "Mercado laboral",
        "fuente": "EPA · INE",
        "cadencia": "Trimestral. El INE publica a finales de enero, abril, julio y octubre.",
        "destacados": [
            {"clave": "tasa_paro", "titulo": "Tasa de paro", "unidad": "%", "decimales": 2},
            {"clave": "ocupados", "titulo": "Ocupados", "unidad": "miles de personas",
             "decimales": 1},
        ],
    },
    {
        "bloque": "paro-registrado", "enlace": "paro-registrado.html",
        "titulo": "Paro registrado", "fuente": "SEPE",
        "cadencia": "Mensual. El SEPE publica en los primeros días de cada mes.",
        "destacados": [
            {"clave": "paro_total", "titulo": "Personas apuntadas al paro",
             "unidad": "personas", "decimales": 0},
        ],
    },
    {
        "bloque": "contratos", "enlace": "contratos.html", "titulo": "Contratación",
        "fuente": "SEPE",
        "cadencia": "Mensual, a la vez que el paro registrado.",
        "destacados": [
            {"clave": "contratos_total", "titulo": "Contratos del mes",
             "unidad": "contratos", "decimales": 0},
            {"clave": "contratos_indefinidos", "titulo": "De ellos, indefinidos",
             "unidad": "contratos", "decimales": 0, "sobre": "contratos_total"},
        ],
    },
    {
        "bloque": "precios", "enlace": "precios.html", "titulo": "Precios",
        "fuente": "IPC · INE",
        "cadencia": "Mensual. El INE publica hacia la mitad del mes siguiente.",
        "destacados": [
            {"clave": "ipc_variacion", "titulo": "Inflación interanual", "unidad": "%",
             "decimales": 2},
        ],
    },
    {
        "bloque": "cesta", "enlace": "cesta.html", "titulo": "La cesta de la compra",
        "fuente": "IPC · INE",
        "cadencia": "Mensual, a la vez que el IPC.",
        "destacados": [
            # Un índice en portada no dice nada -«101,7» no es una noticia-, así
            # que lo que se enseña es cuánto ha subido desde 2021, que es la
            # pregunta que trae a nadie a esta sección.
            {"clave": "alimentos", "titulo": "Lo que ha subido la comida",
             "unidad": "%", "decimales": 1, "comparar_con": "2021"},
        ],
    },
    {
        "bloque": "vivienda", "enlace": "vivienda.html", "titulo": "Vivienda",
        "fuente": "INE y CGPJ",
        "cadencia": "Mensual las compraventas y las hipotecas; trimestral el precio "
                    "y los lanzamientos; anual el alquiler.",
        "destacados": [
            {"clave": "compraventas", "titulo": "Compraventas de vivienda",
             "unidad": "operaciones", "decimales": 0},
            # Los lanzamientos no entran aquí a propósito: sus últimos
            # trimestres son provisionales y un titular de «−72 % en un año»
            # sería, en parte, el retraso de los juzgados en informar.
            {"clave": "hipoteca_media", "titulo": "Hipoteca media", "unidad": "euros",
             "decimales": 0},
        ],
    },
    {
        "bloque": "huelgas", "enlace": "huelgas.html", "titulo": "Huelgas",
        "fuente": "Huelgas y Cierres Patronales · Ministerio de Trabajo",
        "cadencia": "Mensual, con unos cuatro meses de retraso.",
        "destacados": [
            {"clave": "participantes", "titulo": "Personas en huelga",
             "unidad": "personas", "decimales": 0},
            {"clave": "jornadas_perdidas", "titulo": "Jornadas no trabajadas",
             "unidad": "jornadas", "decimales": 0},
        ],
    },
    {
        "bloque": "despidos", "enlace": "despidos.html",
        "titulo": "Despidos y regulación de empleo",
        "fuente": "Regulación de Empleo y Despidos · Ministerio de Trabajo",
        "cadencia": "Mensual los expedientes de regulación; anual, los despidos.",
        "destacados": [
            {"clave": "ere_afectados",
             "titulo": "Afectados por un expediente de regulación",
             "unidad": "personas", "decimales": 0},
            {"clave": "despidos", "titulo": "Despidos en el año",
             "unidad": "despidos", "decimales": 0},
        ],
    },
    {
        "bloque": "convenios", "enlace": "convenios.html",
        "titulo": "Convenios colectivos",
        "fuente": "Convenios Colectivos · Ministerio de Trabajo",
        "cadencia": "Mensual. El ministerio publica con unos dos meses de retraso.",
        "destacados": [
            {"clave": "subida_pactada", "titulo": "Subida salarial pactada",
             "unidad": "%", "decimales": 2},
            {"clave": "trabajadores_convenio", "titulo": "Personas con convenio",
             "unidad": "personas", "decimales": 0},
        ],
    },
    {
        "bloque": "luz", "enlace": "luz.html", "titulo": "El precio de la luz",
        "fuente": "PVPC · Red Eléctrica",
        "cadencia": "Diaria. El precio de cada día se publica la tarde anterior.",
        "destacados": [
            {"clave": "pvpc_medio", "titulo": "Precio medio de la luz",
             "unidad": "c€/kWh", "decimales": 2},
            {"clave": "pvpc_brecha", "titulo": "Entre la hora cara y la barata",
             "unidad": "c€/kWh", "decimales": 2},
        ],
    },
    {
        "bloque": "materias", "enlace": "materias.html",
        "titulo": "Materias primas",
        "fuente": "Pink Sheet · Banco Mundial",
        "cadencia": "Mensual. El Banco Mundial publica el primer día hábil de "
                    "cada mes, con el mes anterior cerrado.",
        "destacados": [
            {"clave": "brent", "titulo": "Petróleo Brent",
             "unidad": "$/barril", "decimales": 2},
            {"clave": "gas_europa", "titulo": "Gas natural en Europa",
             "unidad": "$/mmbtu", "decimales": 2},
        ],
    },
    {
        "bloque": "afiliacion", "enlace": "afiliacion.html",
        "titulo": "Afiliación a la Seguridad Social",
        "fuente": "Anuario de Estadísticas · Ministerio de Trabajo",
        "cadencia": "Anual. El anuario del año sale a mediados del siguiente.",
        "destacados": [
            {"clave": "afiliados", "titulo": "Personas afiliadas",
             "unidad": "personas", "decimales": 0},
        ],
    },
    {
        "bloque": "siniestralidad", "enlace": "siniestralidad.html",
        "titulo": "Accidentes de trabajo", "fuente": "Ministerio de Trabajo",
        "cadencia": "Mensual el avance del año en curso; la serie, anual. El "
                    "ministerio publica con un par de meses de retraso.",
        "destacados": [
            {"clave": "accidentes_mortales", "titulo": "Muertes en el trabajo",
             "unidad": "personas", "decimales": 0},
            {"clave": "accidentes_jornada", "titulo": "Accidentes con baja",
             "unidad": "accidentes", "decimales": 0},
        ],
    },
    {
        "bloque": "renta", "enlace": "renta.html", "titulo": "Renta y desigualdad",
        "fuente": "Atlas de Distribución de Renta · INE",
        "cadencia": "Anual, con unos dos años de retraso.",
        "destacados": [
            {"clave": "renta_persona", "titulo": "Renta neta media por persona",
             "unidad": "euros", "decimales": 0},
        ],
    },
    {
        "bloque": "salarios", "enlace": "salarios.html",
        "titulo": "Salarios y rentas del trabajo",
        "fuente": "Atlas de renta y Encuesta de Estructura Salarial · INE",
        "cadencia": "Anual. El salario, sólo por comunidad autónoma; el reparto "
                    "de la renta, también por provincia.",
        "destacados": [
            {"clave": "renta_salario", "titulo": "Renta que viene del salario",
             "unidad": "%", "decimales": 2},
            {"clave": "salario_bruto", "titulo": "Salario medio anual",
             "unidad": "euros", "decimales": 0},
        ],
    },
    {
        "bloque": "poblacion", "enlace": "poblacion.html", "titulo": "Población",
        "fuente": "Estadística Continua de Población · INE",
        "cadencia": "Trimestral.",
        "destacados": [
            {"clave": "poblacion", "titulo": "Población", "unidad": "personas",
             "decimales": 0},
        ],
    },
    {
        "bloque": "demografia", "enlace": "demografia.html",
        "titulo": "Natalidad, mortalidad y migración",
        "fuente": "Indicadores Demográficos Básicos · INE",
        "cadencia": "Anual.",
        "destacados": [
            {"clave": "saldo_migratorio", "titulo": "Saldo migratorio", "unidad": "por mil",
             "decimales": 2},
        ],
    },
]
