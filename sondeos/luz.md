# El precio de la luz: qué se puede bajar

Y sobre todo: con qué detalle territorial, que en este caso es
la pregunta que decide cómo se presenta la sección.

## por horas, 7 días seguidos

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2026-09-09T00:00&end_date=2026-09-16T23:59&time_trunc=hour`

- 200 (application/json), 77993 bytes
    - 2 series
        · **PVPC** (price): 192 puntos, de 2026-09-09T00:00:00.000+02:00 a 2026-09-16T23:00:00.000+02:00
          primero: 207.07 · último: 211.82
        · **Precio mercado spot** (price): 768 puntos, de 2026-09-09T00:00:00.000+02:00 a 2026-09-16T23:45:00.000+02:00
          primero: 184.01 · último: 127.66

## por horas, 31 días seguidos

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2026-08-17T00:00&end_date=2026-09-16T23:59&time_trunc=hour`

- 200 (application/json), 300190 bytes
    - 2 series
        · **PVPC** (price): 744 puntos, de 2026-08-17T00:00:00.000+02:00 a 2026-09-16T23:00:00.000+02:00
          primero: 200.65 · último: 211.82
        · **Precio mercado spot** (price): 2976 puntos, de 2026-08-17T00:00:00.000+02:00 a 2026-09-16T23:45:00.000+02:00
          primero: 205 · último: 127.66

## por horas, 92 días seguidos

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2026-06-17T00:00&end_date=2026-09-16T23:59&time_trunc=hour`

- 400 (-), 169 bytes
    - {"errors":[{"status":"400","title":"Error Interno","detail":"Los datos solicitados no est\u00e1n disponibles en este momento. Int\u00e9ntelo de nuevo m\u00e1s tarde."}]}

## por horas, un año entero

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2025-09-12T00:00&end_date=2026-09-16T23:59&time_trunc=hour`

- 400 (-), 169 bytes
    - {"errors":[{"status":"400","title":"Error Interno","detail":"Los datos solicitados no est\u00e1n disponibles en este momento. Int\u00e9ntelo de nuevo m\u00e1s tarde."}]}

## ¿desde cuándo hay PVPC? un día de 2021

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2021-06-15T00:00&end_date=2021-06-15T23:59&time_trunc=hour`

- 200 (application/json), 5111 bytes
    - 2 series
        · **PVPC** (price): 24 puntos, de 2021-06-15T00:00:00.000+02:00 a 2021-06-15T23:00:00.000+02:00
          primero: 115.76 · último: 157.45
        · **Precio mercado spot** (price): 24 puntos, de 2021-06-15T00:00:00.000+02:00 a 2021-06-15T23:00:00.000+02:00
          primero: 90 · último: 92.74

## ¿y de 2022?

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2022-06-15T00:00&end_date=2022-06-15T23:59&time_trunc=hour`

- 200 (application/json), 5153 bytes
    - 2 series
        · **PVPC** (price): 24 puntos, de 2022-06-15T00:00:00.000+02:00 a 2022-06-15T23:00:00.000+02:00
          primero: 311.85 · último: 282.86
        · **Precio mercado spot** (price): 24 puntos, de 2022-06-15T00:00:00.000+02:00 a 2022-06-15T23:00:00.000+02:00
          primero: 194.07 · último: 148

## medias diarias de un mes

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2026-08-17T00:00&end_date=2026-09-16T23:59&time_trunc=day`

- 400 (-), 169 bytes
    - {"errors":[{"status":"400","title":"Error Interno","detail":"Los datos solicitados no est\u00e1n disponibles en este momento. Int\u00e9ntelo de nuevo m\u00e1s tarde."}]}

## medias diarias de un año, acotado a la península

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2025-09-12T00:00&end_date=2026-09-16T23:59&time_trunc=day&geo_limit=peninsular&geo_ids=8741`

- 400 (-), 169 bytes
    - {"errors":[{"status":"400","title":"Error Interno","detail":"Los datos solicitados no est\u00e1n disponibles en este momento. Int\u00e9ntelo de nuevo m\u00e1s tarde."}]}

## medias mensuales de cinco años

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2021-01-01T00:00&end_date=2026-09-16T23:59&time_trunc=month&geo_limit=peninsular&geo_ids=8741`

- 400 (-), 169 bytes
    - {"errors":[{"status":"400","title":"Error Interno","detail":"Los datos solicitados no est\u00e1n disponibles en este momento. Int\u00e9ntelo de nuevo m\u00e1s tarde."}]}

## ¿hasta dónde llega el histórico? un día de 2015

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2015-06-15T00:00&end_date=2015-06-15T23:59&time_trunc=hour`

- 200 (application/json), 2282 bytes
    - 1 series
        · **Precio mercado spot** (price): 24 puntos, de 2015-06-15T00:00:00.000+02:00 a 2015-06-15T23:00:00.000+02:00
          primero: 54.49 · último: 52.78

## ¿y de 2019?

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2019-06-15T00:00&end_date=2019-06-15T23:59&time_trunc=hour`

- 200 (application/json), 2284 bytes
    - 1 series
        · **Precio mercado spot** (price): 24 puntos, de 2019-06-15T00:00:00.000+02:00 a 2019-06-15T23:00:00.000+02:00
          primero: 48.86 · último: 50.66

## hoy, que es lo que se enseñaría arriba de la página

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2026-09-17T00:00&end_date=2026-09-17T23:59&time_trunc=hour`

- 200 (application/json), 10441 bytes
    - 2 series
        · **PVPC** (price): 24 puntos, de 2026-09-17T00:00:00.000+02:00 a 2026-09-17T23:00:00.000+02:00
          primero: 185.28 · último: 247.18
        · **Precio mercado spot** (price): 96 puntos, de 2026-09-17T00:00:00.000+02:00 a 2026-09-17T23:45:00.000+02:00
          primero: 188.57 · último: 185

## precios en tiempo real, por horas de ayer

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2026-09-16T00:00&end_date=2026-09-16T23:59&time_trunc=hour`

- 200 (application/json), 10373 bytes
    - 2 series
        · **PVPC** (price): 24 puntos, de 2026-09-16T00:00:00.000+02:00 a 2026-09-16T23:00:00.000+02:00
          primero: 206.56 · último: 211.82
        · **Precio mercado spot** (price): 96 puntos, de 2026-09-16T00:00:00.000+02:00 a 2026-09-16T23:45:00.000+02:00
          primero: 182.54 · último: 127.66

## PVPC por horas de ayer

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2026-09-16T00:00&end_date=2026-09-16T23:59&time_trunc=hour&geo_limit=peninsular&geo_ids=8741`

- 200 (application/json), 2286 bytes
    - 1 series
        · **PVPC** (price): 24 puntos, de 2026-09-16T00:00:00.000+02:00 a 2026-09-16T23:00:00.000+02:00
          primero: 206.56 · último: 211.82

## media diaria de un año

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2025-09-12T00:00&end_date=2026-09-16T23:59&time_trunc=day`

- 400 (-), 169 bytes
    - {"errors":[{"status":"400","title":"Error Interno","detail":"Los datos solicitados no est\u00e1n disponibles en este momento. Int\u00e9ntelo de nuevo m\u00e1s tarde."}]}

## media mensual de un año

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2025-09-12T00:00&end_date=2026-09-16T23:59&time_trunc=month`

- 400 (-), 169 bytes
    - {"errors":[{"status":"400","title":"Error Interno","detail":"Los datos solicitados no est\u00e1n disponibles en este momento. Int\u00e9ntelo de nuevo m\u00e1s tarde."}]}

## ¿hay desglose por comunidad?

`https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2026-09-16T00:00&end_date=2026-09-16T23:59&time_trunc=day&geo_trunc=electric_system&geo_limit=ccaa&geo_ids=10`

- 400 (-), 169 bytes
    - {"errors":[{"status":"400","title":"Error Interno","detail":"Los datos solicitados no est\u00e1n disponibles en este momento. Int\u00e9ntelo de nuevo m\u00e1s tarde."}]}

## PVPC en bruto de esios, sin credencial

`https://api.esios.ree.es/archives/70/download_json?date=2026-09-16`

- 200 (application/json), 10369 bytes
    - claves: ['PVPC']
        · `PVPC`: 24 elementos, el primero `{"Dia": "16/09/2026", "Hora": "00-01", "PCB": "206,56", "CYM": "206,56", "COF2TD": "0,000105527108000000", "PMHPCB": "205,35", "PMHCYM": "205,35", "SAHPCB": "14,79", "SAHCYM": "14,79", "FOMPCB": "0,05", "FOMCYM": "0,05", "FOSPCB": "0,24", "FOSCYM": "`

