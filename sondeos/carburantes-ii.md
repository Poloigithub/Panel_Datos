# Carburantes, segundo sondeo

## ¿Es el TLS? Mismas direcciones, dos contextos

### Contexto: por defecto

- **provincias**: 200, 4,099 bytes, intento 1, 0.6 s
- **Castellón**: 200, 212,622 bytes, intento 1, 1.4 s
- **toda España**: 200, 12,195,678 bytes, intento 1, 22.6 s

### Contexto: cifrados viejos, verificación intacta

- **provincias**: 200, 4,099 bytes, intento 1, 0.5 s
- **Castellón**: 200, 212,622 bytes, intento 1, 1.0 s
- **toda España**: 200, 12,195,678 bytes, intento 1, 22.2 s

## Qué trae cada estación (con «por defecto»)

- fecha declarada: '17/09/2026 17:06:18'
- 11,471 estaciones
- campos de la primera:
    · C.P.: '02250'
    · Dirección: 'AVENIDA CASTILLA LA MANCHA, 26'
    · Horario: 'L-D: 07:00-22:00'
    · Latitud: '39,211417'
    · Localidad: 'ABENGIBRE'
    · Longitud (WGS84): '-1,539167'
    · Margen: 'D'
    · Municipio: 'Abengibre'
    · Precio Adblue: ''
    · Precio Amoniaco: ''
    · Precio Biodiesel: ''
    · Precio Bioetanol: ''
    · Precio Biogas Natural Comprimido: ''
    · Precio Biogas Natural Licuado: ''
    · Precio Diésel Renovable: ''
    · Precio Gas Natural Comprimido: ''
    · Precio Gas Natural Licuado: ''
    · Precio Gases licuados del petróleo: ''
    · Precio Gasoleo A: '1,879'
    · Precio Gasoleo B: '1,669'
    · Precio Gasoleo Premium: ''
    · Precio Gasolina 95 E10: ''
    · Precio Gasolina 95 E25: ''
    · Precio Gasolina 95 E5: '1,849'
    · Precio Gasolina 95 E5 Premium: ''
    · Precio Gasolina 95 E85: ''
    · Precio Gasolina 98 E10: ''
    · Precio Gasolina 98 E5: ''
    · Precio Gasolina Renovable: ''
    · Precio Hidrogeno: ''
    · Precio Metanol: ''
    · Provincia: 'ALBACETE'
    · Remisión: 'dm'
    · Rótulo: 'Nº 10.935'
    · Tipo Venta: 'P'
    · % BioEtanol: '0,0'
    · % Éster metílico: '0,0'
    · IDEESS: '4375'
    · IDMunicipio: '52'
    · IDProvincia: '02'
    · IDCCAA: '07'

- campos de provincia: ['Provincia', 'IDProvincia']
    · Provincia: 52 valores distintos
      primeros: {'ALBACETE': 153, 'ALICANTE': 480, 'ALMERÍA': 227, 'ARABA/ÁLAVA': 73}
    · IDProvincia: 52 valores distintos
      primeros: {'01': 73, '02': 153, '03': 480, '04': 227}
    · publican «Precio Gasolina 95 E5»: 10,909 de 11,471
    · publican «Precio Gasoleo A»: 11,256 de 11,471
    · publican «Precio Gasolina 98 E5»: 5,486 de 11,471
    · publican «Precio Gasoleo Premium»: 5,890 de 11,471
    · publican «Precio Gases licuados del petróleo»: 997 de 11,471

## El histórico del boletín petrolero europeo

- enlaces con «history»: 1
    · https://energy.ec.europa.eu/document/download/906e60ca-8b6a-44e7-8589-652854d2fd3f_en?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx

- descarga: 200, 4,467,723 bytes
- 7 hojas: ['Prices with taxes', 'Prices wo taxes', 'Consumption', 'VAT', 'Excise duties', 'Excise duties - components', 'Other Indirect Taxes']
- «Prices with taxes», 1107 filas:
    · Consumer prices of petroleum | CTR | EU_price_with_tax_euro95 | EU_price_with_tax_diesel | EU_price_with_tax_heating_oi | EU_price_with_tax_fuel_oil_1 | EU_price_with_tax_fuel_oil_2 | EU_price_with_tax_LPG | CTR
    ·  |  | Euro-super 95  (I) | Gas oil automobile Automotiv |  Gas oil de chauffage Heatin |  Fuel oil - Schweres Heizöl  |  Fuel oil -Schweres Heizöl ( | GPL pour moteur LPG motor fu | 
    · Date |  | 1000 l | 1000 l | 1000 l | t | t | 1000 l | 
    · 46279 | EU_ | 2063.3575051911107 | 2158.7361941679264 | 1711.5895290393926 | 688.2514090295678 | 578.4701170179737 | 854.2469750765367 | EUR_
    · 46272 | EU_ | 2043.0281411269013 | 2108.412782332712 | 1595.7566892899863 | 668.1812524734459 | 570.5353961193824 | 850.5967027405358 | EUR_
    · 46265 | EU_ | 1949.9923900848278 | 2039.1469620832606 | 1472.9454249041821 | 701.9314585124384 | 530.9607341530043 | 845.6997586736653 | EUR_
    · 46258 | EU_ | 1941.8563648897593 | 2063.3660614777104 | 1475.4712472734063 | 690.4217088991296 | 576.3154347030134 | 850.5527010955583 | EUR_
    · 46251 | EU_ | 1923.6200449931841 | 2033.1381469525866 | 1458.7022912064526 | 681.8358752457556 | 534.5447853998979 | 851.9769334798319 | EUR_
    · 46244 | EU_ | 1910.685187264571 | 2012.673791462358 | 1416.150440074126 | 705.548008223777 | 507.38862819611103 | 849.5215413887611 | EUR_
    · 46237 | EU_ | 1952.5695273651602 | 2043.9216435120368 | 1444.050212926433 | 703.0036927479368 | 540.5538892195578 | 847.8148788877376 | EUR_
    filas que nombran a España: 0 (primeras [])
- «Prices wo taxes», 1107 filas:
    · Consumer prices of petroleum | CTR | EU_price_wo_tax_euro95 | EU_price_wo_tax_diesel | EU_price_wo_tax_heating_oil | EU_price_wo_tax_fuel_oil_1 | EU_price_wo_tax_fuel_oil_2 | EU_price_wo_tax_LPG | CTR
    ·  |  | Euro-super 95  (I) | Gas oil automobile Automotiv |  Gas oil de chauffage Heatin |  Fuel oil - Schweres Heizöl  |  Fuel oil -Schweres Heizöl ( | GPL pour moteur LPG motor fu | 
    · Date |  | 1000 l | 1000 l | 1000 l | t | t | 1000 l | 
    · 46279 | EU_ | 1087.8339389411249 | 1315.310779959775 | 1233.927775533604 | 632.7737981101224 | 585.1849688057893 | 543.9787440400562 | EUR_
    · 46272 | EU_ | 1070.44779118352 | 1272.2492698384508 | 1136.9992358915156 | 612.5059987552636 | 576.8240152299211 | 541.4132995760621 | EUR_
    · 46265 | EU_ | 1016.0380731798393 | 1218.6848885984218 | 1034.1106966578009 | 646.1700389846347 | 535.7682250574816 | 537.743523241699 | EUR_
    · 46258 | EU_ | 1009.0562737436744 | 1239.3886334419276 | 1035.5068340566406 | 634.6094537147175 | 582.8206501573814 | 541.6235127447238 | EUR_
    · 46251 | EU_ | 993.6951318123761 | 1211.9336900611695 | 1021.9229802778729 | 625.8877593763684 | 539.412005364045 | 542.7686314841881 | EUR_
    · 46244 | EU_ | 965.499118820232 | 1175.926033395668 | 986.6872831727552 | 649.5386420864382 | 511.1684847920979 | 540.8558976219606 | EUR_
    · 46237 | EU_ | 1003.3020051263884 | 1206.1539377330453 | 1008.8723917944786 | 647.027313794616 | 545.6447774339942 | 539.4161382535003 | EUR_
    filas que nombran a España: 0 (primeras [])
- «Consumption», 46 filas:
    · Consumption in 1,000 t or kt | CTR | EU_consumption_euro95 | EU_consumption_diesel | EU_consumption_heEUing_oil | EU_consumption_fuel_oil_1 | EU_consumption_fuel_oil_2 | EU_consumption_LPG | CTR
    · Year |  | Euro-super 95  (I) | Gas oil automobile Automotiv |  Gas oil de chauffage Heatin |  Fuel oil - Schweres Heizöl  |  Fuel oil -Schweres Heizöl ( | GPL pour moteur LPG motor fu | 
    · 2024 | EU_ | 57651.40527694906 | 188265.71134300312 | 26764.483153714882 | 4837.2064809791345 | 6266.066031008148 | 10088.43274805985 | EUR_
    · 2023 | EU_ | 57336.431000000004 | 189539.53099999993 | 28333.318999999992 | 4555.951000000001 | 6504.074 | 5026.1539999999995 | EUR_
    · 2022 | EU_ | 54220.93700000001 | 195282.71700000003 | 30131.76000000001 | 12043.692 | 10493.876 | 7145.617 | EUR_
    · 2021 | EU_ | 51660.047000000006 | 190873.27899999998 | 29679.085 | 4058.8349999999996 | 6889.594000000001 | 4438.947000000002 | EUR_
    · 2020 | EU_ | 48106.35699999998 | 177154.89 | 35101.83199999999 | 3999.1720000000005 | 1851.897 | 4781.878000000001 | EUR_
    · 2019 | EU_ | 68624.378 | 227196.12399999998 | 35127.952000000005 | 4308.258000000002 | 2704.3399999999992 | 5606.718000000001 | EUR_
    · 2018 | EU_ | 68217.017 | 227696.05 | 33907.403 | 4498.677 | 53.4 | 5354.156 | EUR_
    · 2017 | EU_ | 68563.13300000002 | 226964.22599999997 | 36369.797 | 4817.928000000001 | 269.3 | 5333.746999999999 | EUR_
    filas que nombran a España: 0 (primeras [])

