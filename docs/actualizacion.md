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

Mirar todos los días cuesta entre diez y veinte minutos de máquina —gratis en
un repositorio público— y quita el problema de encima: **el dato aparece en la
web como mucho un día después** de que su organismo lo publique.

El INE limita el ritmo si se le piden muchas series seguidas, así que una
ejecución puede tardar bastante más de lo normal si se ha estado trabajando
contra su API ese mismo día. El descargador reintenta con esperas crecientes,
de modo que eso alarga el run pero no lo rompe. Si no hay nada nuevo, los descargadores escriben
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
| Cesta de la compra | IPC · INE | Mensual | a la vez que el IPC |
| Población | ECP y Cifras de Población · INE | Trimestral y anual | ~2 meses |
| Natalidad y mortalidad | Indicadores Demográficos Básicos · INE | Anual | ~1 año |
| Renta | Atlas de Distribución de Renta · INE | Anual | ~2 años |
| Salarios · reparto de la renta | Atlas · INE | Anual | ~2 años |
| Salarios · salario medio y desigualdad | Encuesta de Estructura Salarial · INE | Anual | ~1 año y medio |
| Vivienda · compraventas e hipotecas | ETDP y HPT · INE | Mensual | ~2 meses |
| Vivienda · precio de compraventa | IPV · INE | Trimestral | ~2 meses |
| Vivienda · precio del alquiler | IPVA · INE | Anual | ~1 año |
| Vivienda · ejecuciones hipotecarias | EH · INE | Anual por provincia | ~1 año |
| Vivienda · lanzamientos | CGPJ | Trimestral | ~2 meses, **y se revisan** |
| Accidentes de trabajo · avance | Ministerio de Trabajo | Mensual | ~2 meses |
| Accidentes de trabajo · serie | Ministerio de Trabajo | Anual | el año se cierra en febrero o marzo |
| Afiliación a la Seguridad Social | Anuario · Ministerio de Trabajo | Anual | el anuario sale a mediados del año siguiente |
| Precio de la luz | PVPC · Red Eléctrica | Diaria | el precio de cada día sale la tarde anterior |
| Convenios colectivos | Ministerio de Trabajo | Mensual | ~2 meses |
| Regulación de empleo | Ministerio de Trabajo | Mensual | ~2 meses |
| Despidos y su coste | Ministerio de Trabajo | Anual | ~1 año |
| Huelgas | Ministerio de Trabajo | Mensual | **~4 meses**, el mayor del panel |
| Materias primas | Pink Sheet · Banco Mundial | Mensual | el primer día hábil, con el mes anterior cerrado |
| Tipo de cambio euro/dólar | BCE | Mensual | el mes cierra en los primeros días |
| Carburantes · hoy y por provincia | MITECO | Diaria | en tiempo real, sin histórico |
| Carburantes · serie de España | Boletín petrolero · Comisión Europea | Semanal | ~1 semana |
| Municipios · paro | SEPE | Mensual | igual que el paro registrado |
| Municipios · población | Padrón · INE | Anual | ~6 meses |
| Municipios · renta | Atlas · INE | Anual | ~2 años |

### Los carburantes: lo que se pierde si no se recoge

La API del ministerio publica el precio de las once mil gasolineras **en
tiempo real y sin histórico**: da la foto del momento y nada más. Lo que no se
recoja un día no se puede recuperar nunca. Por eso `data/carburantes/diario.json`
no es un caché sino **el dato**, y por eso la serie provincial empieza el día
que el panel la empezó a medir y no antes.

La de España arranca antes -el 30 de marzo de 2026- porque ese cálculo diario ya
venía haciéndose en `preciodiariogasolina`, con esta misma fuente y este mismo
método. Se lee de allí una vez y sólo rellena días que el panel no tenga: lo que
mide el panel manda siempre sobre lo que venga de fuera.

**El plan B.** La petición que trae las once mil gasolineras de una vez son 12 MB
y el servidor corta la conexión a menudo con esa carga: en un sondeo salió a la
primera en veinte segundos y en el ensayo siguiente falló cinco veces seguidas.
Si falla dos veces, el descargador pasa a pedir **provincia por provincia**,
cincuenta y dos peticiones de 200 KB que contestan sin queja. Exige que conteste
Castellón y al menos cuarenta y cinco provincias; con menos, la media nacional
deja de serlo y no se publica.

**Las dos fuentes van desacopladas.** El histórico de la Comisión Europea y la
foto del ministerio se leen por separado y un fallo de una no tira la otra. Un
día perdido es un hueco, y los huecos se enseñan; lo que no se hace es tirar lo
que sí se tiene.

**Y no hace falta relajar el TLS.** Se probó el contexto por defecto de Python y
uno con los cifrados rebajados, y las dos veces el ministerio contestó a la
primera. Apagar la verificación del certificado, que es lo que hacen otros
scripts con este servidor, no era necesario y aquí no se hace nunca.

### La dirección del Pink Sheet se lee, no se escribe

El fichero mensual de materias primas del Banco Mundial vive en una URL que
lleva dentro un identificador de versión. Al sondear la fuente se comprobó lo
que pasa cuando esa dirección se fija en el código: **la del año anterior sigue
contestando correctamente y sirviendo un fichero congelado nueve meses atrás**.
No hay error, no hay aviso, no hay nada en rojo; simplemente se publican datos
viejos.

Por eso `descargar_materias.py` entra cada vez por
`worldbank.org/en/research/commodity-markets` y coge el enlace que la página
publique ese día. Si el enlace desaparece, el descargador falla a propósito:
más vale un run en rojo que una sección mintiendo en silencio. Es la misma
decisión que se tomó con las huelgas y la página del ministerio.

### La luz se guarda, no se vuelve a pedir

La API de Red Eléctrica no da medias: sólo sirve horas, y en rangos de como
mucho un mes. Así que el panel se baja un mes por petición, calcula él las
medias y guarda el detalle diario en `data/luz/diario.json`. **Un mes cerrado y
completo no se vuelve a pedir nunca**, porque ya está en git. La primera
ejecución gastó sesenta y nueve peticiones; las siguientes gastan una.

### El ministerio no dice que no

El Ministerio de Trabajo no devuelve un 404 cuando se le pide un fichero que
todavía no ha publicado: devuelve su portada con un 200 y tan tranquilo. Por
eso el descargador de accidentes no mira el código de respuesta sino lo que ha
llegado -un XLSX es un zip y empieza por «PK»- y va probando hacia atrás desde
el mes en curso hasta dar con el último avance publicado.

Y su certificado está bien, pero el servidor se deja el intermedio, así que
Python no puede enlazarlo con ninguna raíz de confianza. El panel hace lo
mismo que un navegador: el propio certificado lleva escrita dentro la
dirección de su emisor, se baja de ahí y se completa la cadena. Nunca se
desactiva la verificación; si el ministerio cambiara de emisor, la descarga
falla y avisa en vez de tragar lo que le sirvan.

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

**3. Y los ficheros diarios, aparte.** Los dos ficheros que acumulan días
—`carburantes/diario.json` y `luz/diario.json`— no se pueden vigilar con lo
anterior, y en carburantes eso llegó a ser un punto ciego de verdad. Su
`ultimo_periodo` lo marca la serie del boletín petrolero europeo, que es
semanal y llega siempre, de modo que el ministerio podía llevar tres semanas
sin contestar y el bloque seguiría pareciendo fresco. Y como el descargador
está escrito a propósito para seguir adelante cuando una de sus dos fuentes
falla —para que la caída de una no se lleve la otra—, el run tampoco salía en
rojo. La caída era invisible por los dos lados a la vez.

Ahora se comprueba, **por ámbito**, cuántos días hace del último recogido, con
un margen de tres días: uno suelto es normal, porque esa API se cae a ratos;
tres seguidos es que algo está roto. Por ámbito y no en conjunto porque todos
salen de la misma petición y normalmente caen juntos, pero si el ministerio
renumerase las provincias, España seguiría llegando y Castellón se quedaría
vacío en silencio. Está en `FRESCURA_DIARIA`.

Esto importa más aquí que en el resto del panel porque **el dato no se puede
recuperar**: la API del ministerio da la foto del momento y no guarda
histórico, así que un día que no se recoja está perdido para siempre. En las
demás fuentes, un fallo de tres días se arregla solo al cuarto.

**3. En cada push: `comprobaciones.yml`.** Las pruebas del motor de series y de
los cálculos propios, la validación de los datos ya publicados y la
comprobación de que el CSS commiteado coincide con el compilado.

## Cómo te enteras si algo falla

Hay dos avisos, y llegan al correo por caminos distintos.

**El de GitHub.** Cuando un workflow programado falla, GitHub manda un correo a
la cuenta del repositorio. Viene de serie; se comprueba en *Settings →
Notifications → Actions* de la cuenta (no del repositorio), donde debe estar
marcado el envío por correo. Dice poco más que «ha fallado», pero llega
siempre.

**El del propio panel.** Cuando cualquiera de las dos tareas de actualización
falla, se abre una **incidencia en el repositorio** con el paso concreto que ha
fallado, el enlace al registro y una explicación de qué significa. Al abrirse,
GitHub avisa por correo a quien sigue el repositorio, que es su dueño por
defecto. No hacen falta contraseñas ni servidores de correo: usa el token que
la propia Action ya tiene.

Si la tarea vuelve a fallar al día siguiente, **comenta en la incidencia que ya
está abierta** en lugar de abrir otra: una tarea que lleva una semana rota debe
ser una incidencia con siete comentarios, no siete incidencias. La incidencia
no se cierra sola; se cierra cuando alguien la arregla y la cierra.

### Qué se considera un fallo

- Una serie que **desaparece** o que **pierde periodos** respecto a la descarga
  anterior. Es lo que delata que un organismo ha renombrado algo y el
  descargador ha dejado de encontrarlo.
- Un valor **fuera del rango** plausible del indicador, o una **identidad
  contable** que no cuadra.
- Una fuente que se ha **quedado atrás** más de lo que le toca por su cadencia.
- Un error de red o de formato que impida terminar la descarga.

En los tres primeros casos no se publica nada: los datos del panel siguen
siendo los de la última actualización que sí funcionó. Un fallo deja el panel
como estaba, nunca a medias.

### Probar el aviso

Un aviso sin probar no es un aviso. En *Actions* hay un workflow llamado
**Probar el aviso de fallo** que falla adrede: lanzarlo abre una incidencia
como lo haría un fallo de verdad, con el paso y el enlace al registro. Se probó
así, dos veces seguidas, para comprobar también que la segunda comenta en la
incidencia abierta en vez de abrir otra.

### Qué no se considera un fallo

Que una fuente **no publique nada nuevo**. Es lo normal: la mayoría de los días
no hay dato nuevo de casi nada, la tarea termina sin tocar el repositorio y no
avisa a nadie. Un correo diario diciendo «hoy tampoco» no lo leería nadie a la
semana.

Tampoco lo es que un indicador concreto no se encuentre en una descarga suelta
mientras el resto del bloque sí: eso queda anotado en el registro del run y, si
persiste, acaba saltando como serie desaparecida en la comprobación de
cobertura.

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
