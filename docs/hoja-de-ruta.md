# Hoja de ruta

Plan para ampliar el panel. El orden no es caprichoso: cada fase se apoya en
la anterior, y la fase 0 va primera porque todo lo demás multiplica la
superficie de datos que puede romperse en silencio.

Cada fase termina con datos descargados, verificados y publicados. Si una fase
se queda a medias, el panel sigue funcionando: ninguna depende de que la
siguiente exista.

---

## Fase 0 · Cimientos: que los datos rotos hagan ruido ✅ hecha

**Por qué primero.** El panel ya publicó una vez «esperanza de vida: 3,01
años» porque una búsqueda acabó en la serie de mortalidad infantil. Se detectó
mirando valores a mano. Con cuatro secciones el repaso manual todavía es
viable; con ocho, no. Y hay un fallo peor que el dato absurdo: si el INE
renombra una serie, el indicador desaparece sin que nadie se entere.

**Qué se hace.**

1. `scripts/validar_datos.py`, que recorre todo `data/` y comprueba:
   - **Identidades contables** donde existan (activos = ocupados + parados;
     tasa de paro = parados / activos; tasa de empleo = tasa de actividad ×
     (1 − tasa de paro)), con la tolerancia del redondeo del INE.
   - **Rangos plausibles** por indicador, los mismos que ya declara el
     descargador.
   - **Cobertura**: ningún indicador puede perder periodos respecto a la
     descarga anterior. Esto es lo que detecta un renombrado en el INE.
   - **Continuidad**: saltos bruscos entre periodos consecutivos que delaten
     un cambio de serie encadenado por error.
2. El workflow de actualización ejecuta la validación **antes** de commitear.
   Si falla, no se publica nada y el run queda en rojo.
3. Tests del motor (`scripts/ine_series.py`) con `unittest` de la biblioteca
   estándar, sin dependencias nuevas: parseo de las tres formas de periodo,
   fusión de series equivalentes, rechazo de las que no solapan, y selección
   por cobertura.
4. `data/cobertura.json`: qué indicador existe para qué ámbito y desde cuándo.
   Alimenta la validación y sirve para enseñar los huecos en la web.

**Hecho cuando** el workflow falla si se rompe un indicador, y los tests pasan
en local sin instalar nada.

**Resultado.** `scripts/validar_datos.py` y 26 pruebas en `tests/`. Se comprobó
que detecta los cuatro fallos que le tocan corrompiendo los datos a propósito:
valor fuera de rango, identidad rota, serie desaparecida y serie encogida. En
la fase 1 paró la publicación tres veces, todas con razón.

---

## Fase 1 · IPC provincial y renta real ✅ hecha

**Por qué.** Es lo que más rinde por lo que cuesta: el IPC del INE es
**provincial y mensual**, así que Castellón tiene dato propio, y el motor
actual sirve tal cual.

Pero el valor no está en la inflación sola, sino en cruzarla con lo que ya
hay. La sección de renta enseña hoy una línea que sube desde 2015 sin decir
que buena parte de esa subida se la comió la inflación de 2021-2023. Con el
IPC se puede mostrar la renta en **euros constantes**, que es la pregunta
real: no cuánto ingresas, sino cuánto te da de sí.

**Qué se hace.**

1. Descargar la operación IPC para los tres ámbitos: índice general y los
   grupos principales (alimentos, vivienda, transporte…), mensual.
2. Sección nueva **Precios**, con la página genérica que ya existe:
   índice general, variación interanual y grupos.
3. Indicador derivado **renta en euros constantes**: deflactar la renta del
   Atlas con la media anual del IPC, con año base elegible.
4. En la sección de renta, un conmutador *euros corrientes / euros
   constantes*, igual que el de *absolutos / índice* del mercado laboral.

**Hecho cuando** la renta se puede leer en euros constantes y el cálculo está
documentado en la propia página.

**Resultado.** Sección *Precios* con índice general, inflación interanual y
los grupos de alimentos y transporte, mensual desde 2002 y con dato propio de
provincia. La renta del Atlas se deflacta con la media anual del IPC y la
sección de renta tiene conmutador entre euros corrientes y constantes.

El riesgo que estaba anotado se materializó: el índice de España llegó con
valores de 8,18 porque el INE conserva el índice en bases antiguas. El
validador lo paró tres veces seguidas y hicieron falta tres arreglos —filtrar
candidatas por rango durante la búsqueda, comprobar el rango en toda la serie
y no sólo en su cola, y acotar el bloque al enlace de la base vigente— hasta
que salió limpio. Sin la fase 0, eso se habría publicado.

**Lo que no entró**: el grupo de vivienda y energía del IPC, que sólo aparece
en un ámbito de tres y con serie corta.

---

## Fase 2 · Paro registrado y contratación ✅ hecha

**Por qué.** Rompe de golpe los dos límites del panel actual: es **mensual**
en vez de trimestral y llega a **municipio**. Poder ver el paro registrado en
Vila-real, Borriana u Onda, y no solo el agregado provincial, cambia lo que se
puede contar.

**Qué se hace.**

1. Cliente nuevo para SEPE (paro registrado, contratos) y Seguridad Social
   (afiliación). No es la API del INE: son ficheros mensuales publicados en
   datos.gob.es y en los portales de los organismos, en CSV y XLS.
2. **Primero provincial**, que es lo que encaja con el panel actual y permite
   validar el cliente contra cifras conocidas. **Después municipal**, que es
   donde está el valor pero también el volumen.
3. Sección **Paro registrado y afiliación**: serie mensual, desglose por sexo,
   edad y sector, y comparación con el paro de la EPA (miden cosas distintas y
   la página debe decirlo).

**Resultado.** Dos secciones nuevas, mensuales desde 2006 (238 meses):

- **Paro registrado**, con desglose por sexo, tramo de edad y sector.
- **Contratación**, con el reparto entre indefinidos, temporales y convertidos.

Los ficheros del SEPE resultaron mucho mejores de lo previsto: un CSV por año
y estadística con todos los municipios de España, y la misma forma en los dos,
así que los lee el mismo código parametrizado. Las cifras cuadran con las
oficiales: máximo histórico en febrero de 2013 (5.040.222 parados) y pico de
la pandemia en abril de 2020 (3.831.203). Los 135 municipios de Castellón
suman exactamente el total provincial.

**La afiliación se queda fuera**: no se publica por municipio en datos
abiertos; sus conjuntos llegan a provincia y actividad. En su lugar entró la
contratación, que sí es municipal y da la temporalidad que la EPA no ofrece
para Castellón.

**Dos decisiones que marcaron el resultado.** El secreto estadístico del SEPE
(los valores menores de cinco se publican como «<5») impide sumar los
desgloses: no son ceros, así que se descartan y quedan contados, y una
comprobación vigila que la diferencia con el total no pase del 5 %. Y los
desgloses se presentan como peso sobre el total en vez de en valores
absolutos: comparar 20.000 parados en servicios de Castellón con 1,6 millones
en España no dice nada, y así la página pasó de 27 paneles repetidos a 11
gráficas legibles.

**Queda pendiente** la parte municipal en la web: el dato ya está publicado
(`municipios-castellon.json`, 135 municipios × 238 meses), pero su
visualización es el mapa de la fase 3.

---

## Fase 3 · Municipios y mapa ✅ hecha

**Por qué.** Es lo que hace que un panel se mire en vez de consultarse, y los
datos ya están al alcance: el Padrón y el Atlas de renta llegan a municipio
—el Atlas incluso a sección censal— y la variable de municipios está en las
mismas operaciones que ya se usan.

**Qué se hace.**

1. Ampliar el descargador del INE con la variable *Municipios* para padrón y
   renta, limitada a los municipios de la provincia de Castellón.
2. Geometrías municipales en GeoJSON, simplificadas para que pesen poco, y
   servidas desde el propio repositorio como el resto.
3. Componente de mapa coroplético. Sin librería pesada: SVG propio o
   `d3-geo`, decidido midiendo. Reglas que ya sigue el panel: escala
   secuencial de un solo tono, leyenda siempre visible y tabla equivalente,
   porque un mapa nunca puede ser la única forma de leer el dato.
4. **Ficha por municipio**: una página por municipio con sus indicadores.

**Resultado.** Página de municipios con mapa coroplético de los 135 términos
de la provincia, ranking ordenado y ficha de cada uno con su serie mensual
completa. Tres indicadores: variación del paro en un año, paro por cada cien
habitantes y paro registrado.

Las geometrías salen de GISCO (Eurostat), con los códigos del INE: encajan
exactamente con los 135 municipios del SEPE. Simplificadas con Douglas-Peucker
quedan en 126 KB y 3.037 vértices, así que el riesgo del peso no llegó a
materializarse. El mapa va sin librería de cartografía: una proyección
equirectangular corregida por la latitud media basta para una provincia.

**Lo que costó.** Dos cosas, ninguna prevista en el plan:

1. *La población municipal no aparecía.* El INE la publica, pero la magnitud
   no se llama «Población» sino «Total habitantes», y el nombre del municipio
   se parte en varios segmentos cuando lleva artículo pospuesto («Pobla de
   Benifassà, la»). Hizo falta que el descargador enseñara los segmentos
   reales para verlo. Hasta resolverlo, el mapa salió a flote con la variación
   interanual, que no necesita denominador.
2. *El ruido de los municipios pequeños.* Comparando meses sueltos, Catí
   pasaba de 10 a 17 parados y encabezaba el mapa con un +70 % que no
   significa nada. Comparando medias de doce meses los extremos bajan a ±34 %
   y el mapa enseña la tendencia en vez del azar.

**El cabo suelto, ya cerrado.** La renta por municipio del Atlas entró después,
junto con la fase 4: el mapa tiene un cuarto indicador -renta neta media por
persona- y la ficha de cada municipio muestra además la renta por hogar. Como
el Atlas es anual y llega con dos años de retraso frente al paro mensual, el
mapa enseña el último año publicado hasta el mes elegido y lo rotula con ese
año, no con el mes.

---

## Fase 4 · Vivienda ✅ hecha

**Qué hay disponible**, que no es lo mismo que lo que uno querría. El sondeo
previo (`sondeos/vivienda.md`) lo dejó claro antes de escribir nada:

- **Compraventas** (ETDP), **hipotecas** (HPT) y **ejecuciones hipotecarias**
  (EH), del INE: provinciales. ✔
- **Índice de precios de vivienda en alquiler** (IPVA, INE): anual y
  provincial. ✔ No estaba en el plan; apareció en el sondeo.
- **Índice de precios de vivienda** (IPV, INE): solo autonómico. ✘ para
  Castellón, y la página lo dice en la propia gráfica.
- **Precio del alquiler** (sistema estatal de referencia, MIVAU): ✘. Responde
  403 a cualquier descarga automática, así que no entra. El alquiler se sigue
  por el índice del INE, que dice cuánto sube, no cuánto cuesta.
- **Lanzamientos practicados** (CGPJ): trimestrales y provinciales. ✔ Entraron
  después, a petición: son los desahucios ya ejecutados y los únicos que
  separan los que vienen de una ejecución hipotecaria de los derivados de la
  Ley de Arrendamientos Urbanos, es decir, alquileres impagados. Esa
  distinción no existe en la estadística del INE, que sólo cuenta ejecuciones
  hipotecarias, y el contraste es lo que hacía falta ver: en el primer
  trimestre de 2026 el 65 % de los lanzamientos de España fueron por alquiler,
  mientras que en Castellón la mitad de los 24 fueron por hipoteca.

**Resultado.** Sección **Vivienda** con once indicadores y dos cálculos
propios: la hipoteca media -importe entre número de hipotecas- y los años de
renta del hogar que suma, que es el cruce con el Atlas de renta que pedía el
plan, hecho con las dos cifras en euros que sí existen por provincia. En junio
de 2026 la hipoteca media es de 178.365 € en España, 145.251 € en la Comunitat
y 114.556 € en Castellón; en 2023 equivalían a 3,7 · 3,13 · 2,51 años de renta
neta del hogar.

**Lo que costó.** Cuatro cosas, tres del mismo género -el INE nombra las series
con más precisión de la que uno supone- y una del CGPJ.

1. *Las hipotecas mensuales llevan «mensual» en el nombre*, y sin esa palabra
   ninguna de las búsquedas las encontraba. El descargador enseñó los
   conjuntos de segmentos reales y se vio de un vistazo.
2. *Las ejecuciones vienen por trimestres para España y la Comunitat pero sólo
   por años para Castellón.* Comparar un trimestre con un año no significa
   nada, así que se bajan todas al año.
3. *El bloque mezcla frecuencias* -mensual, trimestral y anual en la misma
   página-, de modo que cada gráfica se pinta sobre el calendario de su propio
   indicador en vez de sobre el común del bloque.

4. *El CGPJ no publica API sino hojas de cálculo*, con el trimestre en el
   nombre del fichero -que cambia cada vez-, el nombre de la provincia en la
   segunda columna y, debajo de la tabla, un segundo cuadro de variaciones con
   las mismas provincias repetidas. Hizo falta escribir un lector de XLSX con
   la biblioteca estándar, porque el panel no usa dependencias, y volcar las
   hojas tal cual para ver su formato en vez de suponerlo.

De paso, la maquinaria de bloques salió del descargador sociodemográfico a
`scripts/bloques_ine.py`, que es lo que usan ahora los dos. La comprobación de
que el cambio no alteraba nada fue rehacer los cuatro bloques ya publicados a
partir de sus propios datos: ficheros idénticos.

---

## Fase 5 · Salarios y poder adquisitivo

**Sondeada antes de empezar** (`sondeos/salarios.md`), y la respuesta obliga a
reescribirla: de las seis operaciones salariales del INE -índice de coste
laboral armonizado, encuesta cuatrienal y anual de estructura salarial,
encuesta anual y trimestral de coste laboral-, **ninguna tiene la variable de
provincias**. Castellón se quedaría sin cifra en su propia página, que es justo
lo que el panel no hace.

Lo que sí hay, y no estaba en el plan:

- El **Atlas de renta** publica la distribución por fuente de ingreso -salario,
  pensiones, prestaciones por desempleo, otras prestaciones, otros ingresos-
  **por provincia y por municipio**. No es el salario medio, pero sí dice qué
  parte de la renta de un territorio viene del trabajo, y baja hasta el
  municipio.
- La **Agencia Tributaria** publica «Mercado de Trabajo y Pensiones en las
  Fuentes Tributarias», que sí trae salario medio por provincia. Está en el
  catálogo de datos.gob.es con una dirección por año
  (`.../sites/mercado/2023/home.html`), así que falta un sondeo más para ver si
  las tablas se pueden leer sin manos.

Con eso, la fase 5 pasa de «una página donde Castellón no aparece» a otra cosa.

### Lo planeado originalmente


**Qué hay.** La Encuesta de Estructura Salarial y la Encuesta Trimestral de
Coste Laboral son **autonómicas**: no hay salario medio provincial. La sección
tiene que decirlo desde el principio en vez de dar a entender un detalle que
no existe.

**Qué se hace.** Salario medio, brecha salarial de género y distribución por
deciles para España y la Comunitat Valenciana. Y, apoyándose en la fase 1,
**salario real**: la serie deflactada por el IPC, que es la única forma de ver
si los salarios ganan o pierden frente a los precios.

**Depende de**: fase 1.

**Coste**: una sesión.

---

## Fase 6 · El panel como producto · en marcha

Cosas que no son datos nuevos pero multiplican lo que ya hay:

- ✅ **Enlaces permanentes**: el estado de los filtros viaja en la URL y hay un
  botón para copiarla, así que «la tasa de paro de Castellón desde 2008» se
  puede compartir con un enlace. Sólo viaja lo que se ha cambiado y lo que
  llega se valida, porque una URL la escribe cualquiera.
- ✅ **Portada con titulares**: las ocho secciones enseñan su última cifra en
  los tres ámbitos, con la variación en un año y la cadencia de su fuente. Los
  compone el propio script de actualización en `data/portada.json`.
- ✅ **Fuentes y calendario**: página con lo que publica cada organismo, cada
  cuánto, y las advertencias que hasta ahora vivían sueltas por el panel.
- ✅ **Aviso si una fuente se apaga**: comprobación de frescura al final de la
  tarea diaria.
- **Buscador de indicadores**, cuando haya suficientes para que haga falta.
- **Página de novedades**: qué dato cambió y cuándo, generada desde el
  historial de git, que ya guarda cada revisión.
- **Descarga completa** del conjunto de datos en un solo archivo.

**Y el calendario cambió con esto.** Antes la tarea miraba en unas pocas fechas
al año, calcadas del calendario de la EPA. Ahora mira **todos los días**: nueve
organismos publican cada uno por su lado y perseguir sus calendarios por
separado es mantener nueve calendarios y equivocarse cuando uno cambie. Mirar a
diario cuesta un cuarto de hora de máquina y garantiza que un dato aparezca
como mucho un día después de publicarse; si no hay nada nuevo, el run termina
sin tocar el repositorio. Lo municipal, que tarda diez minutos por descarga y
viene de fuentes anuales, se revisa una vez al mes.

---

## Orden y dependencias

```
Fase 0 ─┬─> Fase 1 ─┬─> Fase 5
        │           └─> (renta real en Fase 1)
        ├─> Fase 2
        ├─> Fase 3 ──> ficha municipal
        └─> Fase 4
```

La 0 va antes que todo. La 1 antes que la 5. Las demás son independientes
entre sí y se pueden reordenar según interese.

## Criterios que se mantienen

Lo que ya está decidido y no se renegocia en cada fase:

- **Trazabilidad**: cada cifra viene de una API oficial y su procedencia queda
  anotada en `config/`. Nada de datos escritos a mano.
- **Los huecos se ven**: si el INE no publica algo, la serie aparece cortada.
  Nunca se interpola para que quede bonito.
- **Antes descartar que publicar mal**: un indicador que no se puede
  identificar con certeza se queda fuera, y la página explica por qué.
- **Sin dependencias en el navegador**: HTML estático, Chart.js servido desde
  el repositorio, cero CDN.
- **Los datos viven en git**: cada actualización es un commit, así que el
  histórico de revisiones de cualquier cifra es consultable.
