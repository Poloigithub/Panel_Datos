# Panel de datos

Panel web de acceso a series estadísticas de fuentes oficiales, publicado en
GitHub Pages. Siempre en tres ámbitos -España, la Comunitat Valenciana y la
provincia de Castellón- y, cuando la fuente llega, por municipio.

Secciones: mercado laboral (EPA), población, natalidad y mortalidad, precios,
renta, salarios, la cesta de la compra, accidentes de trabajo, vivienda,
paro registrado y contratación (SEPE), y el mapa municipal de la provincia.

## Cómo funciona

```
APIs y ficheros oficiales ──(GitHub Action diaria)──> data/*.json ──> páginas estáticas
```

- Los **descargadores** de `scripts/` consultan cada fuente y escriben las
  series en `data/`. No usan dependencias externas: sólo la biblioteca estándar
  de Python, incluido el lector de XLSX que hace falta para el CGPJ.
- **`.github/workflows/actualizar-datos.yml`** los ejecuta **todos los días a
  las 5:30 UTC**, valida lo descargado y commitea sólo si alguna cifra ha
  cambiado. Así un dato aparece en la web como mucho un día después de que su
  organismo lo publique, y si no hay nada nuevo no queda ni rastro.
- **`.github/workflows/actualizar-municipios.yml`** hace lo propio con los
  datos municipales una vez al mes: tardan diez minutos por descarga y sus
  fuentes son anuales.
- **`.github/workflows/publicar.yml`** compila la hoja de estilos y publica el
  sitio en GitHub Pages en cuanto hay un commit.

El calendario completo —qué publica cada organismo, cada cuánto, con qué
retraso y qué límites tiene— está en **[`docs/actualizacion.md`](docs/actualizacion.md)**
y, para quien lea la web, en la página *Fuentes y calendario*.

Las páginas son HTML estático: leen los JSON con `fetch` y pintan las gráficas
con Chart.js, que se sirve desde el propio repositorio (`assets/vendor/`) para
no depender de un CDN.

## Puesta en marcha

1. En **Settings → Pages**, elige como origen **GitHub Actions**. El workflow
   intenta activarlo solo, pero el token de Actions no siempre tiene permiso
   para hacerlo, así que puede hacer falta este paso a mano una única vez.
2. Vuelve a lanzar *Publicar en GitHub Pages* desde la pestaña Actions. El
   sitio queda en `https://<usuario>.github.io/Panel_Datos/`.
3. A partir de ahí se publica solo en cada push a la rama por defecto del
   repositorio (ojo: sólo esa rama publica; si cambias cuál es la principal,
   acuérdate de fusionar en ella).

Los datos ya están descargados y versionados, así que el panel funciona desde
el primer despliegue. Para forzar una actualización, lanza *Actualizar datos
del INE*.

## Comprobaciones

```bash
python3 -m unittest discover -s tests   # pruebas del motor de series
python3 scripts/validar_datos.py        # validación de los datos publicados
```

```bash
python3 scripts/validar_datos.py --frescura   # ¿sigue llegando lo que se descarga?
```

Las dos primeras se ejecutan en cada push, y la validación también después de
cada descarga: si algo no cuadra, no se publica nada. Comprueba las identidades
contables (activos = ocupados + parados y compañía), que cada valor caiga en
un rango plausible y que **ninguna serie pierda periodos** respecto a la
descarga anterior, que es lo que delata que el INE ha renombrado una serie y
el descargador ha dejado de encontrarla.

`data/cobertura.json` guarda cuántos periodos tiene cada serie y es la
referencia de esa última comprobación, así que se versiona con el resto.

Al **retirar un indicador a propósito**, hay que quitar sus entradas de ese
fichero en el mismo commit; si no, la validación lo dará por desaparecido y
parará la publicación, que es justo lo que debe hacer cuando la desaparición
no es intencionada.

Si algo de esto falla, la tarea abre una **incidencia en el repositorio** con
el paso que ha fallado y el enlace al registro (`scripts/avisar_fallo.py`), y
GitHub avisa por correo a quien sigue el repositorio. Si vuelve a fallar,
comenta en la misma incidencia en vez de abrir otra. El detalle de qué cuenta
como fallo y qué no está en [`docs/actualizacion.md`](docs/actualizacion.md).

La comprobación de **frescura** es distinta y va aparte, al final de la tarea
de actualización: mira que el último dato de cada fuente esté dentro del plazo
que le toca por su cadencia. Detecta lo que la cobertura no puede detectar —que
una fuente deje de publicar, o que el descargador deje de encontrarla— sin
impedir que se publique lo que sí ha llegado. Los márgenes están en `FRESCURA`,
dentro de `scripts/validar_datos.py`.

## Desarrollo en local

```bash
npm install
npm run build:css     # compila assets/css/app.css con Tailwind
npm run serve         # sirve el sitio en http://localhost:8080
```

`assets/css/app.css` está versionado para que el sitio funcione sin pasar por
el build; si tocas clases de Tailwind en el HTML o el JS, recompílalo.

Para actualizar los datos en local:

```bash
python3 scripts/descargar_epa.py
```

## Estructura

| Ruta | Qué es |
|---|---|
| `index.html` | Portada: titulares de cada sección y enlaces |
| `fuentes.html` | Fuentes, calendario de publicación y advertencias |
| `assets/js/portada.js` | Titulares de la portada, desde `data/portada.json` |
| `assets/js/enlace.js` | El estado de los filtros, en la URL |
| `scripts/generar_portada.py` | Compone los titulares tras cada descarga |
| `mercado-laboral.html` | Sección de mercado laboral (EPA) |
| `assets/js/mercado-laboral.js` | Filtros, gráficas y tablas de esa sección |
| `assets/js/tema.js` | Alternancia de tema claro/oscuro |
| `src/tailwind.css` | Fuente de la hoja de estilos (tokens y componentes) |
| `config/series-epa.json` | Procedencia de cada serie: de qué códigos del INE sale |
| `scripts/descargar_epa.py` | Descargador de la EPA |
| `scripts/ine_api.py` | Cliente mínimo de la API del INE |
| `scripts/ine_series.py` | Motor de resolución y fusión de series |
| `scripts/bloques_ine.py` | Motor de bloques: de la declaración de indicadores a su JSON |
| `scripts/descargar_sociodemografia.py` | Población, demografía, precios y renta |
| `scripts/descargar_vivienda.py` | Compraventas, hipotecas, ejecuciones y precios de vivienda |
| `scripts/descargar_salarios.py` | Salario, brecha y de dónde viene la renta |
| `scripts/descargar_cesta.py` | El IPC producto a producto |
| `scripts/descargar_siniestralidad.py` | Accidentes de trabajo del Ministerio de Trabajo |
| `scripts/red_ministerio.py` | Completa la cadena de certificados que el ministerio no manda |
| `scripts/generar_catalogo.py` | Catálogo de indicadores y descarga completa |
| `scripts/generar_cambios.py` | Qué se ha añadido y qué se ha actualizado, desde el historial de git |
| `scripts/cgpj_lanzamientos.py` | Lanzamientos del CGPJ: por hipoteca, por alquiler y otros |
| `scripts/xlsx.py` | Lector de XLSX con la biblioteca estándar |
| `scripts/descargar_paro.py` | Paro registrado y contratación del SEPE |
| `scripts/descargar_municipios.py` | Población de los municipios de Castellón |
| `scripts/descargar_renta_municipal.py` | Renta municipal del Atlas del INE |
| `scripts/descargar_geometrias.py` | Contornos municipales de GISCO, simplificados |
| `scripts/validar_datos.py` | Validación de los datos antes de publicarlos |
| `scripts/avisar_fallo.py` | Abre una incidencia cuando la actualización falla |
| `assets/js/bloque.js` | Página genérica de un bloque, gobernada por su índice |
| `assets/js/mapa.js` | Mapa coroplético, sin librería de cartografía |
| `tests/` | Pruebas del motor de series y de los cálculos propios |
| `docs/hoja-de-ruta.md` | Plan de ampliación del panel |
| `docs/actualizacion.md` | Calendario de las fuentes y qué pasa si algo falla |
| `sondeos/` | Volcados de los sondeos de fuentes, previos a cada descargador |
| `data/` | Series descargadas, en JSON, una carpeta por bloque |

## Añadir una fuente nueva

El entorno de desarrollo no tiene salida hacia el INE ni hacia el SEPE, así que
el trabajo con una fuente nueva pasa por dos workflows manuales:

1. **Sondear una fuente** (`sondear.yml`) ejecuta un script de sondeo y
   commitea su volcado en `sondeos/`. Sirve para saber qué publica la fuente,
   con qué detalle territorial y cómo se llaman sus series antes de escribir
   nada.
2. **Ensayar un descargador** (`ensayo.yml`) ejecuta un descargador y commitea
   lo que baje *antes* de validarlo, dejando su salida en `sondeos/`. Es lo
   que permite ver por qué no ha encontrado una serie. La actualización de
   verdad hace lo contrario: valida primero y sólo commitea si todo cuadra.

## Fuente de los datos

Instituto Nacional de Estadística (EPA, IPC, Atlas de renta, indicadores
demográficos, vivienda) a través de su API pública
(`servicios.ine.es/wstempus`); Servicio Público de Empleo Estatal (paro
registrado y contratos) desde sus ficheros abiertos; Consejo General del Poder
Judicial (lanzamientos practicados) desde sus hojas de cálculo; y
Eurostat/GISCO para los contornos municipales. Los valores absolutos de la EPA van en miles de
personas y las tasas en porcentaje, tal y como los publica el INE.
