/* Panel de mercado laboral (EPA).
 *
 * Lee las series ya descargadas del INE en data/epa/ y las pinta. Todo el
 * estado vive en `estado`; cualquier cambio de filtro llama a `render()`.
 */
(function () {
  'use strict';

  const RUTA_DATOS = 'data/epa/';

  /* Color por entidad, nunca por posición: si filtras un ámbito, los demás
     conservan el suyo. */
  const AMBITOS = [
    { id: 'espana', etiqueta: 'España', variable: '--serie-1' },
    { id: 'comunitat-valenciana', etiqueta: 'C. Valenciana', variable: '--serie-2' },
    { id: 'castellon', etiqueta: 'Castellón', variable: '--serie-3' }
  ];

  const MAGNITUDES = {
    ocupados: { titulo: 'Ocupados', unidad: 'miles de personas', decimales: 1 },
    parados: { titulo: 'Parados', unidad: 'miles de personas', decimales: 1 },
    tasa_actividad: { titulo: 'Tasa de actividad', unidad: '%', decimales: 2 },
    tasa_paro: { titulo: 'Tasa de paro', unidad: '%', decimales: 2 }
  };

  const estado = {
    periodo: 'todo',
    sexo: 'ambos',
    modo: 'absoluto',
    ambitos: new Set(AMBITOS.map((a) => a.id))
  };

  let datos = null;          // { indice, ambitos: { id: contenido } }
  const graficas = new Map(); // clave -> instancia de Chart

  /* ---------------------------------------------------------------- utilidades */

  // useGrouping 'always' para que 2.329 no se quede sin separador junto a 25.248,2.
  const numero = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1, useGrouping: 'always' });
  const numero2 = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function formatea(valor, magnitud) {
    if (valor === null || valor === undefined || Number.isNaN(valor)) return '—';
    return MAGNITUDES[magnitud].decimales === 2 ? numero2.format(valor) : numero.format(valor);
  }

  function formateaConUnidad(valor, magnitud) {
    if (valor === null || valor === undefined || Number.isNaN(valor)) return 'sin dato';
    const texto = formatea(valor, magnitud);
    return MAGNITUDES[magnitud].unidad === '%' ? texto + ' %' : texto;
  }

  function color(variable) {
    return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
  }

  function etiquetaAmbito(id) {
    const a = AMBITOS.find((x) => x.id === id);
    return a ? a.etiqueta : id;
  }

  function etiquetaPeriodo(periodo) {
    // "2026T2" -> "2T 2026"
    const m = /^(\d{4})T(\d)$/.exec(periodo || '');
    return m ? m[2] + 'T ' + m[1] : periodo;
  }

  /* Ámbitos seleccionados, siempre en el orden canónico. */
  function ambitosActivos() {
    return AMBITOS.filter((a) => estado.ambitos.has(a.id) && datos.ambitos[a.id]);
  }

  /* Los periodos que se muestran: unión de los de todos los ámbitos cargados,
     recortada por el filtro temporal. */
  function periodosVisibles() {
    const todos = datos.ambitos[AMBITOS[0].id].periodos.slice();
    if (estado.periodo === 'todo') return todos;
    const trimestres = parseInt(estado.periodo, 10) * 4;
    return todos.slice(Math.max(0, todos.length - trimestres));
  }

  /* Valores de una magnitud para un ámbito, alineados a `periodos`. */
  function serie(ambitoId, magnitud, periodos) {
    const contenido = datos.ambitos[ambitoId];
    if (!contenido) return periodos.map(() => null);
    const bloque = contenido.series[estado.sexo];
    if (!bloque || !bloque[magnitud]) return periodos.map(() => null);
    const indicePorPeriodo = new Map(contenido.periodos.map((p, i) => [p, i]));
    return periodos.map((p) => {
      const i = indicePorPeriodo.get(p);
      if (i === undefined) return null;
      const v = bloque[magnitud][i];
      return v === null || v === undefined ? null : v;
    });
  }

  function indexa(valores) {
    const base = valores.find((v) => v !== null && v !== 0);
    if (base === undefined) return valores.map(() => null);
    return valores.map((v) => (v === null ? null : (v / base) * 100));
  }

  /* --------------------------------------------------------------- tooltip HTML */

  function contenedorTooltip() {
    let nodo = document.getElementById('tooltip-grafica');
    if (nodo) return nodo;
    nodo = document.createElement('div');
    nodo.id = 'tooltip-grafica';
    nodo.setAttribute('role', 'tooltip');
    nodo.style.cssText = [
      'position:fixed', 'pointer-events:none', 'opacity:0', 'z-index:50',
      'transition:opacity .12s ease', 'border-radius:.6rem', 'padding:.55rem .7rem',
      'font-size:.75rem', 'line-height:1.35', 'box-shadow:0 6px 24px rgba(0,0,0,.14)',
      'min-width:9rem'
    ].join(';');
    document.body.appendChild(nodo);
    return nodo;
  }

  /* Los nombres de serie vienen de un JSON externo: se insertan como texto,
     nunca como HTML. */
  function pintaTooltip(contexto) {
    const nodo = contenedorTooltip();
    const modelo = contexto.tooltip;

    if (modelo.opacity === 0) {
      nodo.style.opacity = '0';
      return;
    }

    nodo.style.background = color('--superficie');
    nodo.style.border = '1px solid ' + color('--borde');
    nodo.style.color = color('--tinta');

    nodo.replaceChildren();

    const cabecera = document.createElement('div');
    cabecera.style.cssText = 'font-weight:600;margin-bottom:.35rem;';
    cabecera.style.color = color('--tinta-suave');
    cabecera.textContent = etiquetaPeriodo(modelo.title[0] || '');
    nodo.appendChild(cabecera);

    (modelo.dataPoints || []).forEach(function (punto) {
      const fila = document.createElement('div');
      fila.style.cssText = 'display:flex;align-items:baseline;gap:.45rem;white-space:nowrap;';

      const clave = document.createElement('span');
      clave.setAttribute('aria-hidden', 'true');
      clave.style.cssText = 'display:inline-block;width:.85rem;height:2px;border-radius:1px;flex:none;';
      clave.style.background = punto.dataset.borderColor;
      fila.appendChild(clave);

      // El valor manda; el nombre de la serie acompaña.
      const valor = document.createElement('strong');
      valor.style.cssText = 'font-variant-numeric:tabular-nums;font-weight:600;';
      const magnitud = punto.dataset.magnitud;
      valor.textContent = estado.modo === 'indice' && magnitud !== 'tasa_paro' && magnitud !== 'tasa_actividad'
        ? numero.format(punto.parsed.y)
        : formateaConUnidad(punto.parsed.y, magnitud);
      fila.appendChild(valor);

      const nombre = document.createElement('span');
      nombre.style.color = color('--tinta-tenue');
      nombre.textContent = punto.dataset.label;
      fila.appendChild(nombre);

      nodo.appendChild(fila);
    });

    const caja = contexto.chart.canvas.getBoundingClientRect();
    nodo.style.opacity = '1';
    const x = caja.left + modelo.caretX + 14;
    const y = caja.top + modelo.caretY - 10;
    const ancho = nodo.offsetWidth || 160;
    nodo.style.left = Math.min(x, window.innerWidth - ancho - 8) + 'px';
    nodo.style.top = Math.max(8, y) + 'px';
  }

  /* Hairline vertical que ancla la lectura al trimestre. */
  const plugInCrosshair = {
    id: 'crosshair',
    afterDatasetsDraw: function (chart) {
      const activos = chart.tooltip && chart.tooltip.getActiveElements
        ? chart.tooltip.getActiveElements()
        : [];
      if (!activos.length) return;
      const ctx = chart.ctx;
      const x = activos[0].element.x;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(x, chart.chartArea.top);
      ctx.lineTo(x, chart.chartArea.bottom);
      ctx.lineWidth = 1;
      ctx.strokeStyle = color('--tinta-tenue');
      ctx.globalAlpha = 0.55;
      ctx.stroke();
      ctx.restore();
    }
  };

  /* ---------------------------------------------------------------- gráficas */

  function opciones(periodos, magnitud, opcionesExtra) {
    const extra = opcionesExtra || {};
    const paso = Math.max(1, Math.ceil(periodos.length / 4 / 8));

    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: 'index', intersect: false },
      layout: { padding: { top: 4, right: 6 } },
      elements: {
        line: { borderWidth: 2, tension: 0 },
        point: { radius: 0, hoverRadius: 4, hoverBorderWidth: 2 }
      },
      scales: {
        x: {
          grid: { display: false },
          border: { color: color('--rejilla') },
          ticks: {
            color: color('--tinta-tenue'),
            font: { size: 11 },
            maxRotation: 0,
            autoSkip: false,
            callback: function (_valor, indice) {
              const p = periodos[indice];
              if (!p || !p.endsWith('T1')) return '';
              const anyo = parseInt(p.slice(0, 4), 10);
              return anyo % paso === 0 ? String(anyo) : '';
            }
          }
        },
        y: {
          beginAtZero: extra.desdeCero !== false,
          grid: { color: color('--rejilla'), drawTicks: false },
          border: { display: false },
          ticks: {
            color: color('--tinta-tenue'),
            font: { size: 11 },
            padding: 8,
            callback: function (valor) { return numero.format(valor); }
          }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: false,
          external: pintaTooltip,
          callbacks: {}
        }
      }
    };
  }

  function dibuja(canvas, clave, periodos, series, magnitud, opcionesExtra) {
    const anterior = graficas.get(clave);
    if (anterior) anterior.destroy();

    const grafica = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: periodos,
        datasets: series.map(function (s) {
          return {
            label: s.etiqueta,
            data: s.valores,
            borderColor: s.color,
            backgroundColor: s.color,
            magnitud: magnitud,
            spanGaps: false
          };
        })
      },
      options: opciones(periodos, magnitud, opcionesExtra),
      plugins: [plugInCrosshair]
    });

    graficas.set(clave, grafica);
    return grafica;
  }

  /* ---------------------------------------------------------------- leyendas */

  function pintaLeyenda(contenedor, series) {
    contenedor.replaceChildren();
    series.forEach(function (s) {
      const item = document.createElement('span');
      item.style.cssText = 'display:inline-flex;align-items:center;gap:.4rem;';

      const marca = document.createElement('span');
      marca.setAttribute('aria-hidden', 'true');
      marca.style.cssText = 'display:inline-block;width:1rem;height:2px;border-radius:1px;';
      marca.style.background = s.color;
      item.appendChild(marca);

      const texto = document.createElement('span');
      texto.style.color = color('--tinta-suave');
      texto.textContent = s.etiqueta;
      item.appendChild(texto);

      contenedor.appendChild(item);
    });
  }

  /* ------------------------------------------------------------ tabla equivalente */

  function pintaTabla(contenedor, periodos, series, magnitud) {
    contenedor.replaceChildren();

    const tabla = document.createElement('table');
    tabla.className = 'w-full text-xs';
    tabla.style.borderCollapse = 'collapse';

    const caption = document.createElement('caption');
    caption.className = 'sr-only';
    caption.textContent = MAGNITUDES[magnitud].titulo + ' por trimestre y ámbito, en ' + MAGNITUDES[magnitud].unidad;
    tabla.appendChild(caption);

    const thead = document.createElement('thead');
    const filaCabecera = document.createElement('tr');
    ['Trimestre'].concat(series.map(function (s) { return s.etiqueta; })).forEach(function (texto, i) {
      const th = document.createElement('th');
      th.scope = 'col';
      th.textContent = texto;
      th.style.cssText = 'padding:.3rem .5rem;text-align:' + (i === 0 ? 'left' : 'right') +
        ';position:sticky;top:0;font-weight:600;';
      th.style.background = color('--superficie');
      th.style.color = color('--tinta-tenue');
      filaCabecera.appendChild(th);
    });
    thead.appendChild(filaCabecera);
    tabla.appendChild(thead);

    const tbody = document.createElement('tbody');
    for (let i = periodos.length - 1; i >= 0; i--) {
      const fila = document.createElement('tr');
      const th = document.createElement('th');
      th.scope = 'row';
      th.textContent = etiquetaPeriodo(periodos[i]);
      th.style.cssText = 'padding:.3rem .5rem;text-align:left;font-weight:400;';
      th.style.color = color('--tinta-suave');
      fila.appendChild(th);
      series.forEach(function (s) {
        const td = document.createElement('td');
        td.textContent = formatea(s.valores[i], magnitud);
        td.style.cssText = 'padding:.3rem .5rem;text-align:right;font-variant-numeric:tabular-nums;';
        fila.appendChild(td);
      });
      tbody.appendChild(fila);
    }
    tabla.appendChild(tbody);
    contenedor.appendChild(tabla);
  }

  /* ---------------------------------------------------------------- resumen */

  function variacion(valores) {
    // Interanual: último dato frente al mismo trimestre del año anterior.
    const n = valores.length;
    if (n < 5) return null;
    const actual = valores[n - 1];
    const previo = valores[n - 5];
    if (actual === null || previo === null) return null;
    return { absoluta: actual - previo, relativa: previo === 0 ? null : ((actual - previo) / previo) * 100 };
  }

  function celdaValor(fila, valores, magnitud) {
    const td = document.createElement('td');
    td.style.cssText = 'padding:.6rem 1rem;text-align:right;';

    const principal = document.createElement('div');
    principal.style.cssText = 'font-weight:600;font-variant-numeric:tabular-nums;';
    principal.textContent = formateaConUnidad(valores[valores.length - 1], magnitud);
    td.appendChild(principal);

    const cambio = variacion(valores);
    const detalle = document.createElement('div');
    detalle.style.cssText = 'font-size:.75rem;margin-top:.1rem;';
    detalle.style.color = color('--tinta-tenue');
    if (!cambio) {
      detalle.textContent = '—';
    } else if (MAGNITUDES[magnitud].unidad === '%') {
      const signo = cambio.absoluta > 0 ? '+' : cambio.absoluta < 0 ? '−' : '';
      detalle.textContent = signo + numero2.format(Math.abs(cambio.absoluta)) + ' p.p. interanual';
    } else {
      const signo = cambio.relativa > 0 ? '+' : cambio.relativa < 0 ? '−' : '';
      detalle.textContent = signo + numero.format(Math.abs(cambio.relativa)) + ' % interanual';
    }
    td.appendChild(detalle);

    fila.appendChild(td);
  }

  function pintaResumen(periodos) {
    const cuerpo = document.querySelector('[data-resumen]');
    cuerpo.replaceChildren();

    document.querySelector('[data-ultimo-periodo]').textContent =
      etiquetaPeriodo(periodos[periodos.length - 1]);

    ambitosActivos().forEach(function (ambito) {
      const fila = document.createElement('tr');
      fila.style.borderTop = '1px solid ' + color('--borde');

      const th = document.createElement('th');
      th.scope = 'row';
      th.style.cssText = 'padding:.6rem 1rem;text-align:left;font-weight:500;';
      const marca = document.createElement('span');
      marca.setAttribute('aria-hidden', 'true');
      marca.style.cssText = 'display:inline-block;width:.6rem;height:.6rem;border-radius:2px;margin-right:.45rem;';
      marca.style.background = color(ambito.variable);
      th.appendChild(marca);
      th.appendChild(document.createTextNode(ambito.etiqueta));
      fila.appendChild(th);

      ['ocupados', 'parados', 'tasa_actividad', 'tasa_paro'].forEach(function (magnitud) {
        celdaValor(fila, serie(ambito.id, magnitud, periodos), magnitud);
      });

      cuerpo.appendChild(fila);
    });
  }

  /* ------------------------------------------------------- paneles de absolutos */

  function tarjetaPanel(titulo, subtitulo, idCanvas) {
    const figura = document.createElement('figure');
    figura.className = 'tarjeta p-4 m-0';

    const pie = document.createElement('figcaption');
    const h = document.createElement('h4');
    h.className = 'text-sm font-semibold';
    h.textContent = titulo;
    pie.appendChild(h);
    const p = document.createElement('p');
    p.className = 'mt-0.5 text-xs';
    p.style.color = color('--tinta-tenue');
    p.textContent = subtitulo;
    pie.appendChild(p);
    figura.appendChild(pie);

    const caja = document.createElement('div');
    caja.className = 'mt-3 relative';
    caja.style.height = '210px';
    const canvas = document.createElement('canvas');
    canvas.id = idCanvas;
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', titulo + ', ' + subtitulo);
    caja.appendChild(canvas);
    figura.appendChild(caja);

    return { figura: figura, canvas: canvas };
  }

  function pintaAbsolutos(magnitud, periodos) {
    const contenedor = document.querySelector('[data-paneles="' + magnitud + '"]');
    contenedor.replaceChildren();

    const activos = ambitosActivos();

    if (estado.modo === 'indice') {
      contenedor.className = 'grid gap-5';
      const series = activos.map(function (a) {
        return {
          etiqueta: a.etiqueta,
          color: color(a.variable),
          valores: indexa(serie(a.id, magnitud, periodos))
        };
      });
      const base = etiquetaPeriodo(periodos[0]);
      const panel = tarjetaPanel(
        MAGNITUDES[magnitud].titulo + ', evolución comparada',
        'Índice: ' + base + ' = 100'
      , 'canvas-' + magnitud + '-indice');
      contenedor.appendChild(panel.figura);

      const leyenda = document.createElement('div');
      leyenda.className = 'mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs';
      panel.figura.appendChild(leyenda);
      pintaLeyenda(leyenda, series);

      const detalles = document.createElement('details');
      detalles.className = 'mt-3 text-xs';
      const resumenDet = document.createElement('summary');
      resumenDet.className = 'cursor-pointer';
      resumenDet.style.color = color('--tinta-suave');
      resumenDet.textContent = 'Ver tabla de datos';
      detalles.appendChild(resumenDet);
      const cajaTabla = document.createElement('div');
      cajaTabla.className = 'mt-2 max-h-72 overflow-auto';
      detalles.appendChild(cajaTabla);
      panel.figura.appendChild(detalles);
      pintaTabla(cajaTabla, periodos, series, magnitud);

      dibuja(panel.canvas, magnitud + '-indice', periodos, series, magnitud, { desdeCero: false });
      return;
    }

    contenedor.className = 'grid gap-5 lg:grid-cols-' + Math.min(3, Math.max(1, activos.length));

    activos.forEach(function (ambito) {
      const valores = serie(ambito.id, magnitud, periodos);
      const panel = tarjetaPanel(
        ambito.etiqueta,
        MAGNITUDES[magnitud].titulo + ', miles de personas',
        'canvas-' + magnitud + '-' + ambito.id
      );
      contenedor.appendChild(panel.figura);

      const serieUnica = [{ etiqueta: ambito.etiqueta, color: color(ambito.variable), valores: valores }];

      const detalles = document.createElement('details');
      detalles.className = 'mt-3 text-xs';
      const resumenDet = document.createElement('summary');
      resumenDet.className = 'cursor-pointer';
      resumenDet.style.color = color('--tinta-suave');
      resumenDet.textContent = 'Ver tabla de datos';
      detalles.appendChild(resumenDet);
      const cajaTabla = document.createElement('div');
      cajaTabla.className = 'mt-2 max-h-72 overflow-auto';
      detalles.appendChild(cajaTabla);
      panel.figura.appendChild(detalles);
      pintaTabla(cajaTabla, periodos, serieUnica, magnitud);

      dibuja(panel.canvas, magnitud + '-' + ambito.id, periodos, serieUnica, magnitud);
    });
  }

  /* ---------------------------------------------------------------- render */

  function render() {
    const periodos = periodosVisibles();
    const activos = ambitosActivos();

    pintaResumen(periodos);

    ['tasa_paro', 'tasa_actividad'].forEach(function (magnitud) {
      const canvas = document.querySelector('[data-grafica="' + magnitud + '"]');
      const series = activos.map(function (a) {
        return { etiqueta: a.etiqueta, color: color(a.variable), valores: serie(a.id, magnitud, periodos) };
      });
      dibuja(canvas, magnitud, periodos, series, magnitud, { desdeCero: magnitud === 'tasa_paro' });
      pintaLeyenda(document.querySelector('[data-leyenda="' + magnitud + '"]'), series);
      pintaTabla(document.querySelector('[data-tabla="' + magnitud + '"]'), periodos, series, magnitud);
    });

    pintaAbsolutos('ocupados', periodos);
    pintaAbsolutos('parados', periodos);
  }

  /* ---------------------------------------------------------------- controles */

  function conectaSegmentos() {
    document.querySelectorAll('[data-grupo]').forEach(function (grupo) {
      const clave = grupo.dataset.grupo;
      if (clave === 'ambitos') return;
      grupo.addEventListener('click', function (evento) {
        const boton = evento.target.closest('button[data-valor]');
        if (!boton) return;
        grupo.querySelectorAll('button').forEach(function (b) {
          b.setAttribute('aria-pressed', String(b === boton));
        });
        estado[clave] = boton.dataset.valor;
        render();
      });
    });
  }

  function conectaAmbitos() {
    const contenedor = document.querySelector('[data-grupo="ambitos"]');
    AMBITOS.forEach(function (ambito) {
      const etiqueta = document.createElement('label');
      etiqueta.className = 'inline-flex items-center gap-2 text-sm cursor-pointer';

      const casilla = document.createElement('input');
      casilla.type = 'checkbox';
      casilla.checked = true;
      casilla.className = 'h-4 w-4 rounded';
      casilla.style.accentColor = color(ambito.variable);
      casilla.addEventListener('change', function () {
        if (casilla.checked) {
          estado.ambitos.add(ambito.id);
        } else if (estado.ambitos.size > 1) {
          estado.ambitos.delete(ambito.id);
        } else {
          casilla.checked = true; // nunca dejamos la vista vacía
          return;
        }
        render();
      });
      etiqueta.appendChild(casilla);

      const marca = document.createElement('span');
      marca.setAttribute('aria-hidden', 'true');
      marca.style.cssText = 'display:inline-block;width:1rem;height:2px;border-radius:1px;';
      marca.style.background = color(ambito.variable);
      etiqueta.appendChild(marca);

      const texto = document.createElement('span');
      texto.textContent = ambito.etiqueta;
      etiqueta.appendChild(texto);

      contenedor.appendChild(etiqueta);
    });
  }

  function descargaCsv() {
    const periodos = periodosVisibles();
    const activos = ambitosActivos();
    const magnitudes = Object.keys(MAGNITUDES);

    const cabecera = ['trimestre'];
    const columnas = [];
    activos.forEach(function (a) {
      magnitudes.forEach(function (m) {
        cabecera.push(a.id + '_' + m);
        columnas.push(serie(a.id, m, periodos));
      });
    });

    const filas = [cabecera.join(',')];
    periodos.forEach(function (p, i) {
      const fila = [p];
      columnas.forEach(function (valores) {
        const v = valores[i];
        fila.push(v === null || v === undefined ? '' : String(v));
      });
      filas.push(fila.join(','));
    });

    const blob = new Blob(['﻿' + filas.join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = 'epa-' + estado.sexo + '-' + periodos[0] + '-' + periodos[periodos.length - 1] + '.csv';
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    URL.revokeObjectURL(url);
  }

  /* ---------------------------------------------------------------- procedencia */

  function pintaProcedencia() {
    const fecha = new Date(datos.indice.actualizado);
    document.querySelector('[data-actualizado]').textContent =
      Number.isNaN(fecha.getTime())
        ? datos.indice.actualizado
        : fecha.toLocaleString('es-ES', { dateStyle: 'long', timeStyle: 'short' });

    const lista = document.querySelector('[data-fuentes]');
    lista.replaceChildren();

    const vistas = new Set();
    AMBITOS.forEach(function (ambito) {
      const contenido = datos.ambitos[ambito.id];
      if (!contenido) return;
      (contenido.fuentes || []).forEach(function (fuente) {
        if (vistas.has(fuente.tabla)) return;
        vistas.add(fuente.tabla);
        const li = document.createElement('li');
        const enlace = document.createElement('a');
        enlace.className = 'enlace-sutil';
        enlace.href = fuente.url;
        enlace.rel = 'noopener';
        enlace.textContent = 'INE, tabla ' + fuente.tabla + ': ' + fuente.nombre;
        li.appendChild(enlace);
        lista.appendChild(li);
      });
    });
  }

  /* ---------------------------------------------------------------- arranque */

  function fallo(mensaje) {
    const estadoNodo = document.querySelector('[data-estado]');
    estadoNodo.textContent = mensaje;
    estadoNodo.style.color = color('--tinta');
  }

  async function arranca() {
    try {
      const indice = await fetch(RUTA_DATOS + 'index.json', { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });

      const cargados = {};
      await Promise.all(indice.ambitos.map(async function (a) {
        const respuesta = await fetch(RUTA_DATOS + a.fichero, { cache: 'no-cache' });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status + ' en ' + a.fichero);
        cargados[a.id] = await respuesta.json();
      }));

      datos = { indice: indice, ambitos: cargados };

      document.querySelector('[data-estado]').hidden = true;
      document.querySelector('[data-panel]').hidden = false;

      conectaSegmentos();
      conectaAmbitos();
      document.querySelector('[data-csv]').addEventListener('click', descargaCsv);
      pintaProcedencia();
      render();

      // El tema oscuro tiene sus propios pasos de color: hay que repintar.
      document.addEventListener('tema:cambio', function () { render(); });
    } catch (error) {
      fallo('No se han podido cargar los datos (' + error.message + '). ' +
            'Si acabas de publicar el panel, puede que la tarea de actualización todavía no haya corrido.');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
