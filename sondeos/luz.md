# El precio de la luz: qué se puede bajar

Y sobre todo: con qué detalle territorial, que en este caso es
la pregunta que decide cómo se presenta la sección.

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
    - 0 series

