# Brent y materias primas: qué fuente aguanta un panel

Yahoo no tiene API pública: lo que se usa es un endpoint interno
de su web. Aquí se prueba junto a tres fuentes que sí son
oficiales, para poder decidir con datos delante.

## Yahoo Finance · Brent por meses

`https://query1.finance.yahoo.com/v8/finance/chart/BZ=F?range=5y&interval=1mo`

- 200 (application/json), 6851 bytes
    - claves: ['chart']
        · {"chart": {"result": [{"meta": {"currency": "USD", "symbol": "BZ=F", "exchangeName": "NYM", "fullExchangeName": "NY Mercantile", "instrumentType": "FUTURE", "firstTradeDate": 1185768000, "regularMarketTime": 1789655472, "hasPrePostMarketData": false, "gmtoffset": -14400, "timezone": "EDT", "exchangeTimezoneName": "America/New_York", "regularMarketPrice": 103.1, "regularMarketChangePercent": -2.58, "fulldayPrice": 103.1, "fulldayChange": -2.73, "fulldayChangePercent": -2.58, "fiftyTwoWeekHigh": 126.1, "fiftyTwoWeekLow": 58.72, "regularMarketDayHigh": 106.0, "regularMarketDayLow": 101.55, "regul

## Banco Mundial · Pink Sheet mensual

`https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx`

- 200 (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet), 778415 bytes
    - hoja de cálculo con 5 hojas: «AFOSHEET», «Monthly Prices», «Monthly Indices», «Description», «Index Weights»
    - «AFOSHEET», 0 filas:
    - «Monthly Prices», 798 filas:
        · World Bank Commodity Price Data (The Pink Sheet)
        · monthly prices in nominal US dollars, 1960 to present
        · (monthly series are available only in nominal US dollars)
        · Updated on January 06, 2025
        ·  | Crude oil, average | Crude oil, Brent | Crude oil, Dubai | Crude oil, WTI | Coal, Australian | Coal, South African ** | Natural gas, US | Natural gas, Europe | Liquefied natural gas, Japan | Natural gas index | Cocoa
        ·  | ($/bbl) | ($/bbl) | ($/bbl) | ($/bbl) | ($/mt) | ($/mt) | ($/mmbtu) | ($/mmbtu) | ($/mmbtu) | (2010=100) | ($/kg)
        · 1960M01 | 1.63000011444 | 1.63000011444 | 1.63000011444 | … | … | … | 0.14 | 0.40477399635 | … | … | 0.634
        · 1960M02 | 1.63000011444 | 1.63000011444 | 1.63000011444 | … | … | … | 0.14 | 0.40477399635 | … | … | 0.608
        · última fila: 2025M12 | 60.88 | 62.72 | 61.98 | 57.94 | 107.67 | 90.88 | 4.2514

## Ministerio · carburantes de Castellón

`https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/FiltroProvincia/12`

- 0 (-), 62 bytes
    - URLError: <urlopen error [Errno 104] Connection reset by peer>

## BCE · dólar por euro

`https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A?format=csvdata&startPeriod=2020-01`

- 200 (text/csv), 17321 bytes
    - texto:
        · KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE,OBS_STATUS,OBS_CONF,OBS_PRE_BREAK,OBS_COM,TIME_FORMAT,BREAKS,COLLECTION,COMPILING_ORG,DISS_ORG,DOM_SER_IDS,PUBL_ECB,PUBL_MU,P
        · EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2020-01,1.1100363636364,A,F,,,P1M,,A,,,,,,,99Q1=100,,,4,,4F0,,US dollar/Euro ECB reference exchange rate,"ECB reference exchange rate, US dollar/Euro, 2.15 pm (C.
        · EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2020-02,1.0905,A,F,,,P1M,,A,,,,,,,99Q1=100,,,4,,4F0,,US dollar/Euro ECB reference exchange rate,"ECB reference exchange rate, US dollar/Euro, 2.15 pm (C.E.T.)",US
        · EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2020-03,1.1063409090909,A,F,,,P1M,,A,,,,,,,99Q1=100,,,4,,4F0,,US dollar/Euro ECB reference exchange rate,"ECB reference exchange rate, US dollar/Euro, 2.15 pm (C.
        · EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2020-04,1.08619,A,F,,,P1M,,A,,,,,,,99Q1=100,,,4,,4F0,,US dollar/Euro ECB reference exchange rate,"ECB reference exchange rate, US dollar/Euro, 2.15 pm (C.E.T.)",U
        · EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2020-05,1.090185,A,F,,,P1M,,A,,,,,,,99Q1=100,,,4,,4F0,,US dollar/Euro ECB reference exchange rate,"ECB reference exchange rate, US dollar/Euro, 2.15 pm (C.E.T.)",

