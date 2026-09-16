# Panel de datos

Panel web de acceso a series estadísticas de fuentes oficiales, publicado en
GitHub Pages. La primera sección cubre el mercado laboral (EPA del INE) en tres
ámbitos: España, la Comunitat Valenciana y la provincia de Castellón.

## Cómo funciona

```
API del INE  ──(GitHub Action)──>  data/epa/*.json  ──>  páginas estáticas
```

- **`scripts/descargar_epa.py`** consulta la API Tempus 3 del INE y escribe las
  series en `data/epa/`. No usa dependencias externas: sólo la biblioteca
  estándar de Python.
- **`.github/workflows/actualizar-datos.yml`** ejecuta ese script en las fechas
  en que el INE publica la EPA y commitea el resultado si ha cambiado algo. El
  histórico de revisiones de cada cifra queda en el historial de git.
- **`.github/workflows/publicar.yml`** compila la hoja de estilos y publica el
  sitio en GitHub Pages.

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

Las dos se ejecutan en cada push, y la validación también después de cada
descarga: si algo no cuadra, no se publica nada. Comprueba las identidades
contables (activos = ocupados + parados y compañía), que cada valor caiga en
un rango plausible y que **ninguna serie pierda periodos** respecto a la
descarga anterior, que es lo que delata que el INE ha renombrado una serie y
el descargador ha dejado de encontrarla.

`data/cobertura.json` guarda cuántos periodos tiene cada serie y es la
referencia de esa última comprobación, así que se versiona con el resto.

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
| `index.html` | Portada del panel, con los enlaces a cada sección |
| `mercado-laboral.html` | Sección de mercado laboral (EPA) |
| `assets/js/mercado-laboral.js` | Filtros, gráficas y tablas de esa sección |
| `assets/js/tema.js` | Alternancia de tema claro/oscuro |
| `src/tailwind.css` | Fuente de la hoja de estilos (tokens y componentes) |
| `config/series-epa.json` | Procedencia de cada serie: de qué códigos del INE sale |
| `scripts/descargar_epa.py` | Descargador de la EPA |
| `scripts/ine_api.py` | Cliente mínimo de la API del INE |
| `scripts/ine_series.py` | Motor de resolución y fusión de series |
| `scripts/descargar_sociodemografia.py` | Descargador de población, demografía y renta |
| `scripts/validar_datos.py` | Validación de los datos antes de publicarlos |
| `tests/` | Pruebas del motor de series |
| `docs/hoja-de-ruta.md` | Plan de ampliación del panel |
| `data/epa/` | Series descargadas, en JSON |

## Fuente de los datos

Instituto Nacional de Estadística, Encuesta de Población Activa (EPA), a través
de su API pública (`servicios.ine.es/wstempus`). Los valores absolutos van en
miles de personas y las tasas en porcentaje, tal y como los publica el INE.
