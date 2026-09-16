# Hoja de ruta

Plan para ampliar el panel. El orden no es caprichoso: cada fase se apoya en
la anterior, y la fase 0 va primera porque todo lo demás multiplica la
superficie de datos que puede romperse en silencio.

Cada fase termina con datos descargados, verificados y publicados. Si una fase
se queda a medias, el panel sigue funcionando: ninguna depende de que la
siguiente exista.

---

## Fase 0 · Cimientos: que los datos rotos hagan ruido

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

**Coste**: una sesión corta. **Riesgo**: ninguno; no toca datos publicados.

---

## Fase 1 · IPC provincial y renta real

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

**Coste**: una sesión. **Riesgo a vigilar**: el IPC cambia de base (2021=100)
y hay series enlazadas; hay que comprobar que se toma la enlazada y no un
tramo suelto. La validación de continuidad de la fase 0 lo detectaría.

---

## Fase 2 · Paro registrado y afiliación

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

**Hecho cuando** el paro registrado provincial cuadra con la nota de prensa
mensual del SEPE y la serie municipal carga sin penalizar la página.

**Coste**: dos sesiones, la más cara del plan. **Riesgo alto**: los ficheros
del SEPE cambian de formato entre años; hay que normalizar a un contrato
propio y no depender de la posición de las columnas. Conviene fijar el
contrato de datos antes de escribir el parser.

---

## Fase 3 · Municipios y mapa

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

**Hecho cuando** se puede ver la renta media de cada municipio en un mapa y
abrir la ficha de cualquiera de ellos.

**Coste**: dos sesiones. **Riesgo**: el peso de las geometrías; hay que
simplificarlas y medir la carga en móvil.

---

## Fase 4 · Vivienda

**Qué hay disponible**, que no es lo mismo que lo que uno querría:

- **Transacciones inmobiliarias** e **hipotecas** (INE): provinciales. ✔
- **Precio del alquiler** (sistema estatal de referencia, MIVAU): municipal y
  anual. ✔
- **Índice de precios de vivienda** (INE): solo autonómico. ✘ para Castellón.

**Qué se hace.** Sección **Vivienda** con lo provincial y municipal, diciendo
en la propia página que el precio de compraventa solo existe por comunidad
autónoma. Cruce con la renta: esfuerzo de acceso a la vivienda, alquiler medio
sobre renta media por hogar.

**Coste**: una sesión, más si el portal del MIVAU no da los datos en un
formato estable.

---

## Fase 5 · Salarios y poder adquisitivo

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

## Fase 6 · El panel como producto

Cosas que no son datos nuevos pero multiplican lo que ya hay:

- **Enlaces permanentes**: que el estado de los filtros viaje en la URL, para
  poder compartir «la tasa de paro de Castellón desde 2008» con un enlace.
- **Portada con titulares**: los últimos datos en cifras, no solo tarjetas de
  sección.
- **Buscador de indicadores**, cuando haya suficientes para que haga falta.
- **Página de novedades**: qué dato cambió y cuándo, generada desde el
  historial de git, que ya guarda cada revisión.
- **Descarga completa** del conjunto de datos en un solo archivo.

**Coste**: se puede picotear; cada punto es independiente.

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
