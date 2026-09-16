# Sondeo de fuentes salariales

La pregunta es una: ¿hay salario con dato propio de Castellón?

## Operaciones del INE que hablan de salarios

7 operaciones:
- `ICLA` · Índice de Coste Laboral Armonizado
- `EAES:Q` · Encuesta Cuatrienal de Estructura Salarial
- `EACL` · Encuesta Anual de Coste Laboral
- `EAES` · Encuesta Anual de Estructura Salarial
- `ETCL` · Encuesta Trimestral de Coste Laboral (ETCL)
- `ADRH` · Atlas de distribución de renta de los hogares
- `EAES:Q` · Encuesta Cuatrienal de Estructural Salarial

### Índice de Coste Laboral Armonizado
- código `ICLA`
- variables territoriales: 349 Total Nacional
- **no llega a provincia**
- **España**: 2054 series, 1982 combinaciones
    - ['actividades administrativas y servicios auxiliares', 'coste laboral total por hora', 'indice', 'total nacional'] → `ICLA2330`
    - ['actividades administrativas y servicios auxiliares', 'coste laboral total por hora', 'ponderacion', 'total nacional'] → `ICLA2978`
    - ['actividades administrativas y servicios auxiliares', 'coste laboral total por hora', 'total nacional', 'variacion anual'] → `ICLA2406`
    - ['actividades administrativas y servicios auxiliares', 'coste salarial total por hora', 'indice', 'total nacional'] → `ICLA2329`
    - ['actividades administrativas y servicios auxiliares', 'coste salarial total por hora', 'ponderacion', 'total nacional'] → `ICLA2977`
    - ['actividades administrativas y servicios auxiliares', 'coste salarial total por hora', 'total nacional', 'variacion anual'] → `ICLA2405`
    - ['actividades administrativas y servicios auxiliares', 'coste total por hora excluidas pagas extras y atrasos', 'indice', 'total nacional'] → `ICLA2327`
    - ['actividades administrativas y servicios auxiliares', 'coste total por hora excluidas pagas extras y atrasos', 'ponderacion', 'total nacional'] → `ICLA2975`
    - ['actividades administrativas y servicios auxiliares', 'coste total por hora excluidas pagas extras y atrasos', 'total nacional', 'variacion anual'] → `ICLA2403`
    - ['actividades administrativas y servicios auxiliares', 'indice', 'otros costes por hora', 'total nacional'] → `ICLA2328`
    - ['actividades administrativas y servicios auxiliares', 'otros costes por hora', 'ponderacion', 'total nacional'] → `ICLA2976`
    - ['actividades administrativas y servicios auxiliares', 'otros costes por hora', 'total nacional', 'variacion anual'] → `ICLA2404`
    - ['actividades financieras y de seguros', 'coste laboral total por hora', 'indice', 'total nacional'] → `ICLA2342`
    - ['actividades financieras y de seguros', 'coste laboral total por hora', 'ponderacion', 'total nacional'] → `ICLA2990`
    - ['actividades financieras y de seguros', 'coste laboral total por hora', 'total nacional', 'variacion anual'] → `ICLA2418`
    - ['actividades financieras y de seguros', 'coste salarial total por hora', 'indice', 'total nacional'] → `ICLA2341`
- **Comunitat Valenciana**: 0 series, 0 combinaciones

### Encuesta Cuatrienal de Estructura Salarial
- código `EAES:Q`
- variables territoriales: 70 Comunidades y Ciudades Autónomas, 349 Total Nacional
- **no llega a provincia**
- **España**: 10000 series, 9694 combinaciones
    - ['brecha salarial entre mujeres y hombres', 'dato base', 'total nacional'] → `EAES2686`
    - ['coeficiente de variacion', 'jornada a tiempo parcial', 'total nacional'] → `EAES93245`
    - ['coeficiente de variacion', 'total', 'total nacional'] → `EAES93247`
    - ['d5/d1 (la mediana (3) dividida por la 1a decila de la ganancia por hora)', 'dato base', 'total nacional'] → `EAES2691`
    - ['d9/d1 (9a decila dividida por la 1a decila de la ganancia por hora)', 'dato base', 'total nacional'] → `EAES2690`
    - ['d9/d5 (9a decila (2) dividida por la mediana de la ganancia por hora)', 'dato base', 'total nacional'] → `EAES2692`
    - ['dato base', 'indice de gini', 'total nacional'] → `EAES2689`
    - ['dato base', 'proporcion (%) de mujeres en el total de asalariados con ganancia baja', 'total nacional'] → `EAES2687`
    - ['actividades administrativas y servicios auxiliares', 'coeficiente de variacion', 'mujeres', 'total nacional'] → `EAES93018`
    - ['actividades financieras y de seguros', 'ambos sexos', 'coeficiente de variacion', 'total nacional'] → `EAES93028`
    - ['actividades inmobiliarias', 'ambos sexos', 'coeficiente de variacion', 'total nacional'] → `EAES93025`
    - ['actividades inmobiliarias', 'coeficiente de variacion', 'hombres', 'total nacional'] → `EAES93023`
    - ['actividades sanitarias y de servicios sociales', 'ambos sexos', 'coeficiente de variacion', 'total nacional'] → `EAES93010`
    - ['administracion publica y defensa; seguridad social obligatoria', 'coeficiente de variacion', 'mujeres', 'total nacional'] → `EAES93015`
    - ['ambos sexos', 'coeficiente de variacion', 'conductores y operadores de maquinaria movil', 'total nacional'] → `EAES93124`
    - ['ambos sexos', 'coeficiente de variacion', 'construccion', 'total nacional'] → `EAES93043`
- **Comunitat Valenciana**: 4092 series, 3494 combinaciones
    - ['ambos sexos', 'coeficiente de variacion', 'comunitat valenciana'] → `EAES2492`
    - ['coeficiente de variacion', 'comunitat valenciana', 'hombres'] → `EAES2456`
    - ['coeficiente de variacion', 'comunitat valenciana', 'indefinido'] → `EAES93273`
    - ['coeficiente de variacion', 'comunitat valenciana', 'jornada a tiempo completo'] → `EAES93216`
    - ['coeficiente de variacion', 'comunitat valenciana', 'jornada a tiempo parcial'] → `EAES93215`
    - ['coeficiente de variacion', 'comunitat valenciana', 'mujeres'] → `EAES2474`
    - ['coeficiente de variacion', 'comunitat valenciana', 'temporal'] → `EAES93272`
    - ['coeficiente de variacion', 'comunitat valenciana', 'total'] → `EAES93217`
    - ['ambos sexos', 'coeficiente de variacion', 'comunitat valenciana', 'todas las secciones'] → `EAES93085`
    - ['ambos sexos', 'complementos salariales', 'componente del salario bruto mensual', 'comunitat valenciana'] → `EAES33563`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'pagos extraordinarios'] → `EAES33851`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'salario bruto'] → `EAES33852`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'salario ordinario'] → `EAES33849`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'valoracion en especie'] → `EAES33850`
    - ['ambos sexos', 'componente del salario bruto mensual', 'comunitat valenciana', 'contribuciones a la seguridad social a cargo del trabajador'] → `EAES33557`
    - ['ambos sexos', 'componente del salario bruto mensual', 'comunitat valenciana', 'pagas extraordinarias'] → `EAES33559`

### Encuesta Anual de Coste Laboral
- código `EACL`
- variables territoriales: 70 Comunidades y Ciudades Autónomas, 349 Total Nacional
- **no llega a provincia**
- **España**: 3768 series, 3668 combinaciones
    - ['porcentaje de centros de trabajo', 'sin modificaciones o no sujetos a convenio', 'total nacional'] → `EACL14832`
    - ['porcentaje de centros de trabajo', 'solo regimen salarial', 'total nacional'] → `EACL14833`
    - ['porcentaje de centros de trabajo', 'total', 'total nacional'] → `EACL14835`
    - ['porcentaje de centros de trabajo', 'total modificaciones', 'total nacional'] → `EACL14834`
    - ['porcentaje de trabajadores', 'sin modificaciones o no sujetos a convenio', 'total nacional'] → `EACL14904`
    - ['porcentaje de trabajadores', 'solo regimen salarial', 'total nacional'] → `EACL14905`
    - ['porcentaje de trabajadores', 'total', 'total nacional'] → `EACL14907`
    - ['porcentaje de trabajadores', 'total modificaciones', 'total nacional'] → `EACL14906`
    - ['actividades administrativas de oficina y otras actividades auxiliares a las empresas', 'coste por percepciones no salariales', 'errores de muestreo', 'total nacional'] → `EACL14944`
    - ['actividades administrativas de oficina y otras actividades auxiliares a las empresas', 'coste total bruto', 'porcentaje sobre el coste total bruto', 'total nacional'] → `EACL1927`
    - ['actividades administrativas de oficina y otras actividades auxiliares a las empresas', 'coste total bruto', 'total nacional', 'valor absoluto'] → `EACL1003`
    - ['actividades administrativas de oficina y otras actividades auxiliares a las empresas', 'coste total neto', 'errores de muestreo', 'total nacional'] → `EACL14946`
    - ['actividades administrativas de oficina y otras actividades auxiliares a las empresas', 'coste total neto', 'porcentaje sobre el coste total bruto', 'total nacional'] → `EACL1916`
    - ['actividades administrativas de oficina y otras actividades auxiliares a las empresas', 'coste total neto', 'total nacional', 'valor absoluto'] → `EACL992`
    - ['actividades administrativas de oficina y otras actividades auxiliares a las empresas', 'cotizaciones obligatorias', 'porcentaje sobre el coste total bruto', 'total nacional'] → `EACL1925`
    - ['actividades administrativas de oficina y otras actividades auxiliares a las empresas', 'cotizaciones obligatorias', 'total nacional', 'valor absoluto'] → `EACL1001`
- **Comunitat Valenciana**: 493 series, 493 combinaciones
    - ['comunitat valenciana', 'coste por percepciones no salariales', 'errores de muestreo'] → `EACL15152`
    - ['comunitat valenciana', 'coste total neto', 'errores de muestreo'] → `EACL15186`
    - ['comunitat valenciana', 'errores de muestreo', 'sueldos y salarios'] → `EACL15169`
    - ['comunitat valenciana', 'porcentaje de centros de trabajo', 'sin modificaciones o no sujetos a convenio'] → `EACL14792`
    - ['comunitat valenciana', 'porcentaje de centros de trabajo', 'solo regimen salarial'] → `EACL14793`
    - ['comunitat valenciana', 'porcentaje de centros de trabajo', 'total'] → `EACL14795`
    - ['comunitat valenciana', 'porcentaje de centros de trabajo', 'total modificaciones'] → `EACL14794`
    - ['comunitat valenciana', 'porcentaje de trabajadores', 'sin modificaciones o no sujetos a convenio'] → `EACL14864`
    - ['comunitat valenciana', 'porcentaje de trabajadores', 'solo regimen salarial'] → `EACL14865`
    - ['comunitat valenciana', 'porcentaje de trabajadores', 'total'] → `EACL14867`
    - ['comunitat valenciana', 'porcentaje de trabajadores', 'total modificaciones'] → `EACL14866`
    - ['comunitat valenciana', 'construccion', 'coste total bruto', 'porcentaje sobre el coste total bruto'] → `EACL5026`
    - ['comunitat valenciana', 'construccion', 'coste total bruto', 'valor absoluto'] → `EACL4210`
    - ['comunitat valenciana', 'construccion', 'coste total neto', 'porcentaje sobre el coste total bruto'] → `EACL4278`
    - ['comunitat valenciana', 'construccion', 'coste total neto', 'valor absoluto'] → `EACL3462`
    - ['comunitat valenciana', 'construccion', 'cotizaciones obligatorias', 'porcentaje sobre el coste total bruto'] → `EACL4890`

### Encuesta Anual de Estructura Salarial
- código `EAES`
- variables territoriales: 70 Comunidades y Ciudades Autónomas, 349 Total Nacional
- **no llega a provincia**
- **España**: 10000 series, 9694 combinaciones
    - ['brecha salarial entre mujeres y hombres', 'dato base', 'total nacional'] → `EAES2686`
    - ['coeficiente de variacion', 'jornada a tiempo parcial', 'total nacional'] → `EAES93245`
    - ['coeficiente de variacion', 'total', 'total nacional'] → `EAES93247`
    - ['d5/d1 (la mediana (3) dividida por la 1a decila de la ganancia por hora)', 'dato base', 'total nacional'] → `EAES2691`
    - ['d9/d1 (9a decila dividida por la 1a decila de la ganancia por hora)', 'dato base', 'total nacional'] → `EAES2690`
    - ['d9/d5 (9a decila (2) dividida por la mediana de la ganancia por hora)', 'dato base', 'total nacional'] → `EAES2692`
    - ['dato base', 'indice de gini', 'total nacional'] → `EAES2689`
    - ['dato base', 'proporcion (%) de mujeres en el total de asalariados con ganancia baja', 'total nacional'] → `EAES2687`
    - ['actividades administrativas y servicios auxiliares', 'coeficiente de variacion', 'mujeres', 'total nacional'] → `EAES93018`
    - ['actividades financieras y de seguros', 'ambos sexos', 'coeficiente de variacion', 'total nacional'] → `EAES93028`
    - ['actividades inmobiliarias', 'ambos sexos', 'coeficiente de variacion', 'total nacional'] → `EAES93025`
    - ['actividades inmobiliarias', 'coeficiente de variacion', 'hombres', 'total nacional'] → `EAES93023`
    - ['actividades sanitarias y de servicios sociales', 'ambos sexos', 'coeficiente de variacion', 'total nacional'] → `EAES93010`
    - ['administracion publica y defensa; seguridad social obligatoria', 'coeficiente de variacion', 'mujeres', 'total nacional'] → `EAES93015`
    - ['ambos sexos', 'coeficiente de variacion', 'conductores y operadores de maquinaria movil', 'total nacional'] → `EAES93124`
    - ['ambos sexos', 'coeficiente de variacion', 'construccion', 'total nacional'] → `EAES93043`
- **Comunitat Valenciana**: 4092 series, 3494 combinaciones
    - ['ambos sexos', 'coeficiente de variacion', 'comunitat valenciana'] → `EAES2492`
    - ['coeficiente de variacion', 'comunitat valenciana', 'hombres'] → `EAES2456`
    - ['coeficiente de variacion', 'comunitat valenciana', 'indefinido'] → `EAES93273`
    - ['coeficiente de variacion', 'comunitat valenciana', 'jornada a tiempo completo'] → `EAES93216`
    - ['coeficiente de variacion', 'comunitat valenciana', 'jornada a tiempo parcial'] → `EAES93215`
    - ['coeficiente de variacion', 'comunitat valenciana', 'mujeres'] → `EAES2474`
    - ['coeficiente de variacion', 'comunitat valenciana', 'temporal'] → `EAES93272`
    - ['coeficiente de variacion', 'comunitat valenciana', 'total'] → `EAES93217`
    - ['ambos sexos', 'coeficiente de variacion', 'comunitat valenciana', 'todas las secciones'] → `EAES93085`
    - ['ambos sexos', 'complementos salariales', 'componente del salario bruto mensual', 'comunitat valenciana'] → `EAES33563`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'pagos extraordinarios'] → `EAES33851`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'salario bruto'] → `EAES33852`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'salario ordinario'] → `EAES33849`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'valoracion en especie'] → `EAES33850`
    - ['ambos sexos', 'componente del salario bruto mensual', 'comunitat valenciana', 'contribuciones a la seguridad social a cargo del trabajador'] → `EAES33557`
    - ['ambos sexos', 'componente del salario bruto mensual', 'comunitat valenciana', 'pagas extraordinarias'] → `EAES33559`

### Encuesta Trimestral de Coste Laboral (ETCL)
- código `ETCL`
- variables territoriales: 70 Comunidades y Ciudades Autónomas, 349 Total Nacional
- **no llega a provincia**
- **España**: 7479 series, 6377 combinaciones
    - ['actividades administrativas y servicios auxiliares', 'total', 'total nacional'] → `ETCL2986`
    - ['actividades financieras y de seguros', 'total', 'total nacional'] → `ETCL2998`
    - ['actividades inmobiliarias', 'total', 'total nacional'] → `ETCL2994`
    - ['actividades sanitarias y de servicios sociales', 'total', 'total nacional'] → `ETCL2974`
    - ['administracion publica y defensa; seguridad social obligatoria', 'total', 'total nacional'] → `ETCL2982`
    - ['comercio al por mayor y al por menor; reparacion de vehiculos de motor y motocicletas', 'total', 'total nacional'] → `ETCL3014`
    - ['construccion', 'total', 'total nacional'] → `ETCL3018`
    - ['educacion', 'total', 'total nacional'] → `ETCL2978`
    - ['hosteleria', 'total', 'total nacional'] → `ETCL3006`
    - ['industria', 'total', 'total nacional'] → `ETCL2958`
    - ['industria manufacturera', 'total', 'total nacional'] → `ETCL3030`
    - ['industrias extractivas', 'total', 'total nacional'] → `ETCL3034`
    - ['informacion y comunicaciones', 'total', 'total nacional'] → `ETCL3002`
    - ['otros servicios', 'total', 'total nacional'] → `ETCL2966`
    - ['servicios', 'total', 'total nacional'] → `ETCL2950`
    - ['total', 'total nacional', 'transporte y almacenamiento'] → `ETCL3010`
- **Comunitat Valenciana**: 330 series, 264 combinaciones
    - ['comunitat valenciana', 'construccion y servicios (excepto actividades de los hogares como empleadores y de organizaciones y organismos extraterritoriales)', 'industria', 'total'] → `ETCL5512`
    - ['comunitat valenciana', 'construccion', 'coste laboral total', 'costes laborales', 'euros'] → `ETCL3861`
    - ['comunitat valenciana', 'construccion', 'coste laboral total por hora', 'costes laborales', 'euros'] → `ETCL4401`
    - ['comunitat valenciana', 'construccion', 'coste por cotizaciones obligatorias', 'costes laborales', 'euros'] → `ETCL3856`
    - ['comunitat valenciana', 'construccion', 'coste por percepciones no salariales', 'costes laborales', 'euros'] → `ETCL3857`
    - ['comunitat valenciana', 'construccion', 'coste salarial ordinario', 'costes laborales', 'euros'] → `ETCL3859`
    - ['comunitat valenciana', 'construccion', 'coste salarial ordinario por hora', 'costes laborales', 'euros'] → `ETCL13169`
    - ['comunitat valenciana', 'construccion', 'coste salarial total', 'costes laborales', 'euros'] → `ETCL12917`
    - ['comunitat valenciana', 'construccion', 'coste salarial total por hora', 'costes laborales', 'euros'] → `ETCL13187`
    - ['comunitat valenciana', 'construccion', 'costes laborales', 'euros', 'otros costes'] → `ETCL3858`
    - ['comunitat valenciana', 'construccion', 'costes laborales', 'euros', 'otros costes por hora'] → `ETCL13151`
    - ['comunitat valenciana', 'construccion y servicios (excepto actividades de los hogares como empleadores y de organizaciones y organismos extraterritoriales)', 'faltan demandantes con los requisitos deseados', 'industria', 'total'] → `ETCL5511`
    - ['comunitat valenciana', 'construccion y servicios (excepto actividades de los hogares como empleadores y de organizaciones y organismos extraterritoriales)', 'industria', 'no han considerado idoneas las condiciones de trabajo', 'total'] → `ETCL5510`
    - ['comunitat valenciana', 'construccion y servicios (excepto actividades de los hogares como empleadores y de organizaciones y organismos extraterritoriales)', 'industria', 'otros', 'total'] → `ETCL5509`
    - ['comunitat valenciana', 'construccion y servicios (excepto actividades de los hogares como empleadores y de organizaciones y organismos extraterritoriales)', 'industria', 'porcentaje', 'total'] → `ETCL5580`
    - ['comunitat valenciana', 'construccion y servicios (excepto actividades de los hogares como empleadores y de organizaciones y organismos extraterritoriales)', 'industria', 'puestos de trabajo vacantes en un ccc', 'total'] → `ETCL5471`

### Atlas de distribución de renta de los hogares
- código `ADRH`
- variables territoriales: 19 Municipios, 70 Comunidades y Ciudades Autónomas, 115 Provincias, 349 Total Nacional
- **España**: 188 series, 188 combinaciones
    - ['dato base', 'distribucion de la renta p80/p20', 'total nacional'] → `ADRH9974943`
    - ['dato base', 'edad media de la poblacion', 'total nacional'] → `ADRH10030164`
    - ['dato base', 'fuente de ingreso: otras prestaciones', 'total nacional'] → `ADRH9974797`
    - ['dato base', 'fuente de ingreso: otros ingresos', 'total nacional'] → `ADRH9974796`
    - ['dato base', 'fuente de ingreso: pensiones', 'total nacional'] → `ADRH9974799`
    - ['dato base', 'fuente de ingreso: prestaciones por desempleo', 'total nacional'] → `ADRH9974798`
    - ['dato base', 'fuente de ingreso: salario', 'total nacional'] → `ADRH9974800`
    - ['dato base', 'indice de gini', 'total nacional'] → `ADRH9974944`
    - ['dato base', 'media de la renta por unidad de consumo', 'total nacional'] → `ADRH9974438`
    - ['dato base', 'mediana de la renta por unidad de consumo', 'total nacional'] → `ADRH9974437`
    - ['dato base', 'poblacion', 'total nacional'] → `ADRH10030081`
    - ['dato base', 'porcentaje de hogares unipersonales', 'total nacional'] → `ADRH10029916`
    - ['dato base', 'porcentaje de poblacion de 65 y mas anos', 'total nacional'] → `ADRH10029917`
    - ['dato base', 'porcentaje de poblacion espanola', 'total nacional'] → `ADRH10029915`
    - ['dato base', 'porcentaje de poblacion menor de 18 anos', 'total nacional'] → `ADRH10029918`
    - ['dato base', 'renta bruta media por hogar', 'total nacional'] → `ADRH9974434`
- **Comunitat Valenciana**: 188 series, 188 combinaciones
    - ['comunitat valenciana', 'dato base', 'distribucion de la renta p80/p20'] → `ADRH9974923`
    - ['comunitat valenciana', 'dato base', 'edad media de la poblacion'] → `ADRH10030154`
    - ['comunitat valenciana', 'dato base', 'fuente de ingreso: otras prestaciones'] → `ADRH9974747`
    - ['comunitat valenciana', 'dato base', 'fuente de ingreso: otros ingresos'] → `ADRH9974746`
    - ['comunitat valenciana', 'dato base', 'fuente de ingreso: pensiones'] → `ADRH9974749`
    - ['comunitat valenciana', 'dato base', 'fuente de ingreso: prestaciones por desempleo'] → `ADRH9974748`
    - ['comunitat valenciana', 'dato base', 'fuente de ingreso: salario'] → `ADRH9974750`
    - ['comunitat valenciana', 'dato base', 'indice de gini'] → `ADRH9974924`
    - ['comunitat valenciana', 'dato base', 'media de la renta por unidad de consumo'] → `ADRH9974368`
    - ['comunitat valenciana', 'dato base', 'mediana de la renta por unidad de consumo'] → `ADRH9974367`
    - ['comunitat valenciana', 'dato base', 'poblacion'] → `ADRH10030061`
    - ['comunitat valenciana', 'dato base', 'porcentaje de hogares unipersonales'] → `ADRH10029876`
    - ['comunitat valenciana', 'dato base', 'porcentaje de poblacion de 65 y mas anos'] → `ADRH10029877`
    - ['comunitat valenciana', 'dato base', 'porcentaje de poblacion espanola'] → `ADRH10029875`
    - ['comunitat valenciana', 'dato base', 'porcentaje de poblacion menor de 18 anos'] → `ADRH10029878`
    - ['comunitat valenciana', 'dato base', 'renta bruta media por hogar'] → `ADRH9974364`
- **Castellón**: 188 series, 188 combinaciones
    - ['castellon/castello', 'dato base', 'distribucion de la renta p80/p20'] → `ADRH9974833`
    - ['castellon/castello', 'dato base', 'edad media de la poblacion'] → `ADRH10030109`
    - ['castellon/castello', 'dato base', 'fuente de ingreso: otras prestaciones'] → `ADRH9974522`
    - ['castellon/castello', 'dato base', 'fuente de ingreso: otros ingresos'] → `ADRH9974521`
    - ['castellon/castello', 'dato base', 'fuente de ingreso: pensiones'] → `ADRH9974524`
    - ['castellon/castello', 'dato base', 'fuente de ingreso: prestaciones por desempleo'] → `ADRH9974523`
    - ['castellon/castello', 'dato base', 'fuente de ingreso: salario'] → `ADRH9974525`
    - ['castellon/castello', 'dato base', 'indice de gini'] → `ADRH9974834`
    - ['castellon/castello', 'dato base', 'media de la renta por unidad de consumo'] → `ADRH9974126`
    - ['castellon/castello', 'dato base', 'mediana de la renta por unidad de consumo'] → `ADRH9974125`
    - ['castellon/castello', 'dato base', 'poblacion'] → `ADRH10029971`
    - ['castellon/castello', 'dato base', 'porcentaje de hogares unipersonales'] → `ADRH10029696`
    - ['castellon/castello', 'dato base', 'porcentaje de poblacion de 65 y mas anos'] → `ADRH10029697`
    - ['castellon/castello', 'dato base', 'porcentaje de poblacion espanola'] → `ADRH10029695`
    - ['castellon/castello', 'dato base', 'porcentaje de poblacion menor de 18 anos'] → `ADRH10029698`
    - ['castellon/castello', 'dato base', 'renta bruta media por hogar'] → `ADRH9974122`

### Encuesta Cuatrienal de Estructural Salarial
- código `EAES:Q`
- variables territoriales: 70 Comunidades y Ciudades Autónomas, 349 Total Nacional
- **no llega a provincia**
- **España**: 10000 series, 9694 combinaciones
    - ['brecha salarial entre mujeres y hombres', 'dato base', 'total nacional'] → `EAES2686`
    - ['coeficiente de variacion', 'jornada a tiempo parcial', 'total nacional'] → `EAES93245`
    - ['coeficiente de variacion', 'total', 'total nacional'] → `EAES93247`
    - ['d5/d1 (la mediana (3) dividida por la 1a decila de la ganancia por hora)', 'dato base', 'total nacional'] → `EAES2691`
    - ['d9/d1 (9a decila dividida por la 1a decila de la ganancia por hora)', 'dato base', 'total nacional'] → `EAES2690`
    - ['d9/d5 (9a decila (2) dividida por la mediana de la ganancia por hora)', 'dato base', 'total nacional'] → `EAES2692`
    - ['dato base', 'indice de gini', 'total nacional'] → `EAES2689`
    - ['dato base', 'proporcion (%) de mujeres en el total de asalariados con ganancia baja', 'total nacional'] → `EAES2687`
    - ['actividades administrativas y servicios auxiliares', 'coeficiente de variacion', 'mujeres', 'total nacional'] → `EAES93018`
    - ['actividades financieras y de seguros', 'ambos sexos', 'coeficiente de variacion', 'total nacional'] → `EAES93028`
    - ['actividades inmobiliarias', 'ambos sexos', 'coeficiente de variacion', 'total nacional'] → `EAES93025`
    - ['actividades inmobiliarias', 'coeficiente de variacion', 'hombres', 'total nacional'] → `EAES93023`
    - ['actividades sanitarias y de servicios sociales', 'ambos sexos', 'coeficiente de variacion', 'total nacional'] → `EAES93010`
    - ['administracion publica y defensa; seguridad social obligatoria', 'coeficiente de variacion', 'mujeres', 'total nacional'] → `EAES93015`
    - ['ambos sexos', 'coeficiente de variacion', 'conductores y operadores de maquinaria movil', 'total nacional'] → `EAES93124`
    - ['ambos sexos', 'coeficiente de variacion', 'construccion', 'total nacional'] → `EAES93043`
- **Comunitat Valenciana**: 4092 series, 3494 combinaciones
    - ['ambos sexos', 'coeficiente de variacion', 'comunitat valenciana'] → `EAES2492`
    - ['coeficiente de variacion', 'comunitat valenciana', 'hombres'] → `EAES2456`
    - ['coeficiente de variacion', 'comunitat valenciana', 'indefinido'] → `EAES93273`
    - ['coeficiente de variacion', 'comunitat valenciana', 'jornada a tiempo completo'] → `EAES93216`
    - ['coeficiente de variacion', 'comunitat valenciana', 'jornada a tiempo parcial'] → `EAES93215`
    - ['coeficiente de variacion', 'comunitat valenciana', 'mujeres'] → `EAES2474`
    - ['coeficiente de variacion', 'comunitat valenciana', 'temporal'] → `EAES93272`
    - ['coeficiente de variacion', 'comunitat valenciana', 'total'] → `EAES93217`
    - ['ambos sexos', 'coeficiente de variacion', 'comunitat valenciana', 'todas las secciones'] → `EAES93085`
    - ['ambos sexos', 'complementos salariales', 'componente del salario bruto mensual', 'comunitat valenciana'] → `EAES33563`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'pagos extraordinarios'] → `EAES33851`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'salario bruto'] → `EAES33852`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'salario ordinario'] → `EAES33849`
    - ['ambos sexos', 'componente del salario bruto anual', 'comunitat valenciana', 'valoracion en especie'] → `EAES33850`
    - ['ambos sexos', 'componente del salario bruto mensual', 'comunitat valenciana', 'contribuciones a la seguridad social a cargo del trabajador'] → `EAES33557`
    - ['ambos sexos', 'componente del salario bruto mensual', 'comunitat valenciana', 'pagas extraordinarias'] → `EAES33559`

## Agencia Tributaria

### Estadísticas AEAT
- `404` · - · https://sede.agenciatributaria.gob.es/Sede/datos-abiertos/catalogo-informacion-publica.html
- Not Found

### Mercado de trabajo y pensiones
- `404` · - · https://sede.agenciatributaria.gob.es/Sede/datos-abiertos/catalogo-informacion-publica/estadisticas-tributarias/mercado-trabajo-pensiones-fuentes-tributarias.html
- Not Found

### Portal estadístico AEAT
- `200` · text/html · https://sede.agenciatributaria.gob.es/Sede/estadisticas.html
- 0 ficheros descargables
- 1 enlaces que mencionan salarios
    - **Ventas, Empleo y Salarios en las declaraciones tributarias** → https://sede.agenciatributaria.gob.es/Sede/datosabiertos/catalogo/hacienda/Informes_Ventas_Empleos_y_Salarios_en_las_declaraciones_tributarias.shtml

## Catálogo de datos.gob.es

### «mercado de trabajo y pensiones» → 200
- **Mercado de Trabajo y Pensiones en las Fuentes Tributarias**
    - https://sede.agenciatributaria.gob.es/Sede/estadisticas/estadisticas-impuesto/mercado-trabajo-pensiones-fuentes-tributarias/metodologia.html
    - https://sede.agenciatributaria.gob.es/AEAT/Contenidos_Comunes/La_Agencia_Tributaria/Estadisticas/Publicaciones/sites/mercado/2023/home.html
    - https://sede.agenciatributaria.gob.es/Sede/datosabiertos/catalogo/hacienda/Mercado_de_Trabajo_y_Pensiones_en_las_Fuentes_Tributarias.shtml
- **Mercado de trabajo y pensiones en las fuentes tributarias**
    - https://www.icane.es/data/api/fuentes-tributarias-salarios-percibidos-versus-pagados.json
    - https://www.icane.es/data/api/fuentes-tributarias-grupos-poblacion-naturaleza-retribuciones.csv
    - https://www.icane.es/data/api/fuentes-tributarias-perceptor-salarios-genero-actividad-cnae93.csv

### «salarios» → 200
- **Los salarios en Andalucía**
    - https://www.juntadeandalucia.es/institutodeestadisticaycartografia/dega/los-salarios-en-andalucia
- **Asalariados, percepciones salariales y salarios por tramos de salario y sexo**
    - https://abertos.xunta.gal/catalogo/economia-empresa-emprego/-/dataset/0198/asalariados-percepcions-salariais-salarios/101/acceso-aos-datos.csv
- **Ventas, Empleo y Salarios en las Grandes Empresas (informes mensuales)**
    - https://sede.agenciatributaria.gob.es/static_files/AEAT/Estudios/Estadisticas/Informes_Estadisticos/Informe_VESGE/Metodologia.pdf
    - https://sede.agenciatributaria.gob.es/static_files/AEAT/Estudios/Estadisticas/Informes_Estadisticos/Informes_VESGE/InformesHtml/Informe_web.html
    - https://sede.agenciatributaria.gob.es/Sede/estadisticas/ventas-empleos-salarios-declaraciones-tributarias/ventas-empleo-salarios-grandes-empresas/calendario.html
- **Ventas, empleos y salarios en grandes empresas y pymes (trimestral)**
    - https://sede.agenciatributaria.gob.es/Sede/datosabiertos/catalogo/hacienda/Informe_Ventas_Empleo_y_Salarios_en_Grandes_Empresas_y_Pymes.shtml
- **Agenda 2030 ODS -  Proporción del PIB generada por el trabajo, que comprende los salarios y las transferencias de protección social (Identificador API: 233:2426)**
    - https://www.ine.es/consul/excelCesta.do?tipofichero=xlsc&serie=CNE2426
    - https://www.ine.es/dyngs/ODS/es/indicador.htm?id=5070
    - https://www.ine.es/consul/excelCesta.do?tipofichero=2&serie=CNE2426
- **Asalariados con salarios bajos por ámbito geográfico (Identificador API: 69587)**
    - https://www.ine.es/jaxiT3/files/t/csv_bd/69587.csv
    - https://www.ine.es/jaxiT3/files/t/px/69587.px
    - https://www.ine.es/jaxiT3/files/t/csv_bdsc/69587.csv

### «estructura salarial» → 200
- **Encuesta de estructura salarial**
    - https://nastat.navarra.es/es/tablas_powerbi/-/tag/encuesta-estructura-salarial
- **Estadística municipal de estructura salarial**
    - https://nastat.navarra.es/es/tablas_powerbi/-/tag/estadistica-municipal-estructura-salarial
- **Encuesta Cuatrienal de Estructura Salarial (2022). Trabajadores. Derechos de acceso restringidos.**
    - https://es-datalab.es/
- **Esquema de conceptos de medida de Encuesta Anual de Estructura Salarial (ISTAC: CSM_E30189A)**
    - https://datos.canarias.es/api/estadisticas/structural-resources/v1.0/conceptschemes/ISTAC/CSM_E30189A/01.000/concepts.csv?fields=+description
    - https://datos.canarias.es/api/estadisticas/structural-resources/v1.0/conceptschemes/ISTAC/CSM_E30189A/01.000/concepts.json?fields=+description
    - https://datos.canarias.es/api/estadisticas/structural-resources/v1.0/conceptschemes/ISTAC/CSM_E30189A/01.000/concepts.xlsx?fields=+description
- **Encuesta anual de estructura salarial**
    - https://www.icane.es/data/api/eaes-ganancia-hora-trabajo-genero-tipo-contrato.sdmx
    - https://www.icane.es/data/api/eaes-ganancia-hora-trabajo-genero-actividad-cnae93.google-json
    - https://www.icane.es/data/api/eaes-ganancia-media-anual-trabajador-genero-actividad-cnae09.sdmx
- **Encuesta de estructura salarial**
    - https://idescat.cat/pub/?id=ees

### «coste laboral» → 200
- **Coste laboral mensual por trabajador. España y comunidades autónomas por trimestres. (Base 2016)**
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000001/1.21.jsonstat
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000001/1.21.xlsx
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000001/1.21.xml
- **Coste laboral mensual por trabajador según sector económico. España y comunidades autónomas por trimestres**
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000003/1.21.xlsx
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000003/1.21.json
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000003/1.21.csv
- **Coste laboral por hora efectiva por trabajador. España y comunidades autónomas por trimestres. (Base 2016)**
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000002/1.21.csv
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000002/1.21.json
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000002/1.21.tsv
- **Coste laboral por hora efectiva y extraordinaria por trabajador según sector económico. España y comunidades autónomas por trimestres**
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000004/1.21.json
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000004/1.21.tsv
    - https://datos.canarias.es/api/estadisticas/statistical-resources/v1.0/datasets/ISTAC/E30187A_000004/1.21.xml
- **Coste laboral en Castilla-La Mancha**
    - https://datosabiertos.castillalamancha.es/sites/datosabiertos.castillalamancha.es/files/eacl%20por%20sectores%20y%20componente%20del%20costeODS.ods
    - https://datosabiertos.castillalamancha.es/sites/datosabiertos.castillalamancha.es/files/eacl%20por%20tama%C3%B1o%20establecimiento%20%20y%20componente%20del%20coste.csv
    - https://datosabiertos.castillalamancha.es/sites/datosabiertos.castillalamancha.es/files/por%20tama%C3%B1o.json
- **Encuesta anual de coste laboral**
    - https://nastat.navarra.es/es/tablas_powerbi/-/tag/encuesta-anual-coste-laboral

