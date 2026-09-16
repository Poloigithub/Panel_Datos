# Cómo y cada cuánto se actualiza el panel

Este documento responde a una pregunta concreta: **si el INE publica hoy el
IPC, ¿cuándo aparece en la web?** La respuesta corta es *mañana por la mañana*.
La larga es el resto del documento.

## El ciclo

```
05:30 UTC, todos los días
   │
   ├─ descargar_epa.py                 EPA del INE
   ├─ descargar_sociodemografia.py     población, demografía, precios, renta
   ├─ descargar_vivienda.py            compraventas, hipotecas, precios, lanzamientos
   ├─ descargar_paro.py                paro registrado y contratos del SEPE
   ├─ generar_portada.py               titulares de la portada
   │
   ├─ validar_datos.py ───── ¿algo no cuadra? ──> el run se para, no se publica nada
   │
   ├─ commit + push  (sólo si alguna cifra ha cambiado)
   │        └──> «Publicar en GitHub Pages» despliega el sitio
   │
   └─ validar_datos.py --frescura ──> ¿alguna fuente se ha quedado atrás?
```

Y una vez al mes, el día 5 a las 04:00 UTC, lo municipal:
`descargar_municipios.py` y `descargar_renta_municipal.py`.

## Por qué se mira todos los días

Cada organismo publica cuando le toca, y no hay dos que coincidan: el SEPE
saca el paro registrado en los primeros días de cada mes, el INE el IPC hacia
la mitad, la EPA a finales de enero, abril, julio y octubre, y el CGPJ los
lanzamientos por trimestres. Perseguir cada calendario con su propio `cron`
significa mantener nueve calendarios y equivocarse cuando uno cambie.

Mirar todos los días cuesta unos diez minutos de máquina y quita el problema
de encima: **el dato aparece en la web como mucho un día después** de que su
organismo lo publique. Si no hay nada nuevo, los descargadores escriben
exactamente lo mismo que ya estaba, `git diff` no encuentra cambios y el run
termina sin tocar el repositorio. No hay commits de relleno.

Mirar a diario no hace que un dato anual cambie a diario. La renta del Atlas
seguirá siendo la de 2023 hasta que el INE publique la de 2024, con o sin
tarea diaria.

## Qué publica cada fuente y cada cuánto

| Sección | Fuente | Cadencia real | Retraso habitual |
|---|---|---|---|
| Mercado laboral | EPA · INE | Trimestral | ~1 mes tras cerrar el trimestre |
| Paro registrado | SEPE | Mensual | 2.º día hábil del mes siguiente |
| Contratación | SEPE | Mensual | igual que el paro registrado |
| Precios | IPC · INE | Mensual | ~13 del mes siguiente |
| Población | ECP y Cifras de Población · INE | Trimestral y anual | ~2 meses |
| Natalidad y mortalidad | Indicadores Demográficos Básicos · INE | Anual | ~1 año |
| Renta | Atlas de Distribución de Renta · INE | Anual | ~2 años |
| Vivienda · compraventas e hipotecas | ETDP y HPT · INE | Mensual | ~2 meses |
| Vivienda · precio de compraventa | IPV · INE | Trimestral | ~2 meses |
| Vivienda · precio del alquiler | IPVA · INE | Anual | ~1 año |
| Vivienda · ejecuciones hipotecarias | EH · INE | Anual por provincia | ~1 año |
| Vivienda · lanzamientos | CGPJ | Trimestral | ~2 meses, **y se revisan** |
| Municipios · paro | SEPE | Mensual | igual que el paro registrado |
| Municipios · población | Padrón · INE | Anual | ~6 meses |
| Municipios · renta | Atlas · INE | Anual | ~2 años |

### Los lanzamientos se revisan

Los trimestres recientes del CGPJ llegan **incompletos** y se corrigen al alza
en ediciones posteriores. No es una sospecha: sumando los cuatro trimestres de
cada año y comparándolos con el total anual que el propio CGPJ publica por
partido judicial, 2023 y 2024 cuadran al dato (26.659 y 27.563) pero 2025 se
queda en 24.540 frente a 27.483, un 11 % corto.

Por eso el descargador compara los dos ficheros en cada ejecución, marca los
años que no cuadran y lo dice en la tarjeta de cada indicador. Y por eso los
lanzamientos no salen en los titulares de la portada: un «−72 % en un año»
sería, en buena parte, el retraso de los juzgados en informar.

## Qué pasa si algo va mal

Hay tres redes distintas, y cada una está puesta donde puede hacer algo.

**1. Antes de publicar: `validar_datos.py`.** Se ejecuta después de descargar y
antes de commitear. Comprueba que cada fichero diga lo que dice su índice, que
se cumplan las identidades contables (activos = ocupados + parados,
lanzamientos = hipoteca + alquiler + otros, y compañía), que cada valor caiga
en un rango plausible y que ninguna serie haya perdido periodos respecto a la
descarga anterior. Si algo falla, **el run se para y no se publica nada**: se
queda la versión anterior, que es correcta, en vez de publicar una nueva que no
lo es.

**2. Después de publicar: `validar_datos.py --frescura`.** La comprobación
anterior detecta que una serie *pierda* periodos, no que deje de *ganarlos*.
Sin esto, una fuente puede morirse en silencio; de hecho el descargador de
lanzamientos está escrito para que, si un día no encuentra el fichero del CGPJ,
publique el bloque sin ellos en vez de tumbar toda la vivienda. Eso es lo que
se quiere, pero hay que enterarse. Así que al final del run se comprueba que el
último dato de cada bloque esté dentro del margen que le toca por su cadencia,
y si no lo está el run sale en rojo. Va al final y aparte a propósito: que una
fuente se haya quedado atrás no debe impedir publicar lo que sí ha llegado.

Los márgenes son generosos —cuentan desde el final del periodo e incluyen el
retraso normal del organismo— porque lo que tienen que detectar no es que una
fuente vaya lenta, sino que ha dejado de llegar. Están en `FRESCURA`, dentro de
`scripts/validar_datos.py`.

**3. En cada push: `comprobaciones.yml`.** Las pruebas del motor de series y de
los cálculos propios, la validación de los datos ya publicados y la
comprobación de que el CSS commiteado coincide con el compilado.

## Dónde queda el histórico

Cada actualización es un commit, así que el histórico de revisiones de
cualquier cifra es consultable: `git log -p data/epa/castellon.json` enseña
cuándo cambió cada valor y qué valor tenía antes. Eso incluye las revisiones
que hacen los propios organismos, que son frecuentes y suelen pasar
desapercibidas.

## Publicación del sitio

`publicar.yml` despliega en GitHub Pages en cada push a la rama por defecto del
repositorio, así que el sitio se actualiza solo en cuanto la tarea de datos
commitea. Compila la hoja de estilos con Tailwind antes de subir, de modo que
el CSS servido siempre corresponde al HTML publicado.

## Ejecutar a mano

Todo se puede lanzar desde la pestaña *Actions* del repositorio:

- **Actualizar datos**: fuerza una revisión inmediata de todo lo diario.
- **Actualizar datos municipales**: lo mensual.
- **Sondear una fuente** y **Ensayar un descargador**: para trabajar con una
  fuente nueva; el primero vuelca lo que encuentra en `sondeos/` y el segundo
  ejecuta un descargador dejando su salida allí.

En local, cualquier descargador funciona suelto —no hay dependencias más allá
de la biblioteca estándar de Python— siempre que la máquina tenga salida a
internet hacia el organismo correspondiente.
