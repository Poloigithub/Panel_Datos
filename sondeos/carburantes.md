# Carburantes: cuánto detalle hay, y desde cuándo

## Todas las estaciones de España, de un viaje

`https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/`

- 0 (-), 62 bytes, intento 4, 31.5 s
    · b'URLError: <urlopen error [Errno 104] Connection reset by peer>'

## Listado de provincias, para saber cuáles son la Comunitat

- 0 (-), 62 bytes

## Boletín petrolero de la Comisión Europea (histórico)

### página

`https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en`

- 200 (text/html; charset=UTF-8), 103,325 bytes, intento 1
- hojas de cálculo enlazadas: 4
    · /document/download/264c2d0f-f161-4ea3-a777-78faae59bea0_en?filename=Weekly%20Oil%20Bulletin%20Weekly%20prices%20with%20Taxes%20-%202024-02-19.xlsx
    · /document/download/78311f92-68f8-4b82-b5cf-1293beeaae77_en?filename=Weekly%20Oil%20Bulletin%20Weekly%20prices%20without%20taxes%20-%202024-02-19.xlsx
    · /document/download/ccdc6e96-6792-40cb-b0b4-b6609f1e30d0_en?filename=Oil_Bulletin_Duties_and_taxes.xlsx
    · /document/download/906e60ca-8b6a-44e7-8589-652854d2fd3f_en?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx

### fichero

`https://energy.ec.europa.eu/document/download/Oil_Bulletin_Prices_History.xlsx`

- 404 (-), 600 bytes, intento 1
    · b'<!DOCTYPE html>\n<html lang="en" dir="ltr" prefix="og: https://ogp.me/ns#">\n  <head>\n    <meta charset="utf-8" />\n<meta property="og:determiner" content="auto" />\n<meta property="og:site_name" content='

## Lo que ya está calculado en `preciodiariogasolina`

`https://raw.githubusercontent.com/Poloigithub/preciodiariogasolina/main/precios_carburantes.csv`

- 200 (text/plain; charset=utf-8), 8,190 bytes
- 173 días, de 2026-03-30 a 2026-09-17
- columnas: ['Fecha', 'Gasolina 95', 'Gasolina 98', 'Diésel', 'Diésel Premium', 'GLP']
- primera: {"Fecha": "2026-03-30", "Gasolina 95": "1.5467", "Gasolina 98": "1.6854", "Diésel": "1.7767", "Diésel Premium": "1.8631", "GLP": "0.9247"}
- última:  {"Fecha": "2026-09-17", "Gasolina 95": "1.9173", "Gasolina 98": "2.0717", "Diésel": "1.9120", "Diésel Premium": "2.0032", "GLP": "1.0975"}
- días que faltan entre el primero y el último: -1

