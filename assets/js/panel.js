/* Piezas comunes a todas las secciones del panel: colores por ámbito, formato
 * de cifras, gráficas de línea con crosshair y tooltip, leyendas y tablas.
 *
 * Se expone como window.Panel para que cada página lo use sin necesidad de un
 * empaquetador: el sitio es HTML estático servido tal cual. */
(function () {
  'use strict';

  /* Color por entidad, nunca por posición: si filtras un ámbito, los demás
     conservan el suyo. Los tres tonos son los únicos de la paleta que
     mantienen separación suficiente bajo daltonismo con todos los pares en
     juego. */
  var AMBITOS = [
    { id: 'espana', etiqueta: 'España', variable: '--serie-1' },
    { id: 'comunitat-valenciana', etiqueta: 'C. Valenciana', variable: '--serie-2' },
    { id: 'castellon', etiqueta: 'Castellón', variable: '--serie-3' }
  ];

  var enteros = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0, useGrouping: 'always' });
  var unDecimal = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 1, useGrouping: 'always' });
  var dosDecimales = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function formatea(valor, decimales) {
    if (valor === null || valor === undefined || Number.isNaN(valor)) return '—';
    if (decimales === 0) return enteros.format(valor);
    if (decimales === 2) return dosDecimales.format(valor);
    return unDecimal.format(valor);
  }

  function conUnidad(valor, unidad, decimales) {
    if (valor === null || valor === undefined || Number.isNaN(valor)) return 'sin dato';
    var texto = formatea(valor, decimales);
    if (unidad === '%') return texto + ' %';
    if (unidad === 'euros') return texto + ' €';
    if (unidad === 'años') return texto + ' años';
    if (unidad === 'por mil') return texto + ' ‰';
    return texto;
  }

  function color(variable) {
    return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
  }

  /* '2026T2' -> '2T 2026'; '2024S1' -> '1S 2024'; '2023' -> '2023'. */
  function etiquetaPeriodo(periodo) {
    var m = /^(\d{4})([TSM])(\d{1,2})$/.exec(periodo || '');
    if (!m) return periodo;
    return m[3] + m[2] + ' ' + m[1];
  }

  function ordenPeriodo(periodo) {
    var m = /^(\d{4})(?:[TSM](\d{1,2}))?$/.exec(periodo || '');
    if (!m) return [0, 0];
    return [parseInt(m[1], 10), m[2] ? parseInt(m[2], 10) : 0];
  }

  /* ------------------------------------------------------------- tooltip */

  function contenedorTooltip() {
    var nodo = document.getElementById('tooltip-grafica');
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
    var nodo = contenedorTooltip();
    var modelo = contexto.tooltip;

    if (modelo.opacity === 0) {
      nodo.style.opacity = '0';
      return;
    }

    nodo.style.background = color('--superficie');
    nodo.style.border = '1px solid ' + color('--borde');
    nodo.style.color = color('--tinta');
    nodo.replaceChildren();

    var cabecera = document.createElement('div');
    cabecera.style.cssText = 'font-weight:600;margin-bottom:.35rem;';
    cabecera.style.color = color('--tinta-suave');
    cabecera.textContent = etiquetaPeriodo((modelo.title || [])[0] || '');
    nodo.appendChild(cabecera);

    (modelo.dataPoints || []).forEach(function (punto) {
      var fila = document.createElement('div');
      fila.style.cssText = 'display:flex;align-items:baseline;gap:.45rem;white-space:nowrap;';

      var clave = document.createElement('span');
      clave.setAttribute('aria-hidden', 'true');
      clave.style.cssText = 'display:inline-block;width:.85rem;height:2px;border-radius:1px;flex:none;';
      clave.style.background = punto.dataset.borderColor;
      fila.appendChild(clave);

      // El valor manda; el nombre de la serie acompaña.
      var valor = document.createElement('strong');
      valor.style.cssText = 'font-variant-numeric:tabular-nums;font-weight:600;';
      valor.textContent = conUnidad(punto.parsed.y, punto.dataset.unidad, punto.dataset.decimales);
      fila.appendChild(valor);

      var nombre = document.createElement('span');
      nombre.style.color = color('--tinta-tenue');
      nombre.textContent = punto.dataset.label;
      fila.appendChild(nombre);

      nodo.appendChild(fila);
    });

    var caja = contexto.chart.canvas.getBoundingClientRect();
    nodo.style.opacity = '1';
    var x = caja.left + modelo.caretX + 14;
    var y = caja.top + modelo.caretY - 10;
    var ancho = nodo.offsetWidth || 160;
    nodo.style.left = Math.min(x, window.innerWidth - ancho - 8) + 'px';
    nodo.style.top = Math.max(8, y) + 'px';
  }

  /* Hairline vertical que ancla la lectura al periodo. */
  var crosshair = {
    id: 'crosshair',
    afterDatasetsDraw: function (chart) {
      var activos = chart.tooltip && chart.tooltip.getActiveElements
        ? chart.tooltip.getActiveElements() : [];
      if (!activos.length) return;
      var ctx = chart.ctx;
      var x = activos[0].element.x;
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

  /* ------------------------------------------------------------- gráficas */

  var graficas = new Map();

  function opciones(periodos, unidad, decimales, extra) {
    extra = extra || {};
    var anyos = periodos.length ? ordenPeriodo(periodos[periodos.length - 1])[0] - ordenPeriodo(periodos[0])[0] : 1;
    var paso = Math.max(1, Math.ceil((anyos + 1) / 8));

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
            color: color('--tinta-tenue'), font: { size: 11 },
            maxRotation: 0, autoSkip: false,
            callback: function (_v, indice) {
              var p = periodos[indice];
              if (!p) return '';
              var partes = ordenPeriodo(p);
              // En series con subperiodo sólo se rotula el primero del año.
              if (/[TSM]/.test(p) && partes[1] !== 1) return '';
              return partes[0] % paso === 0 ? String(partes[0]) : '';
            }
          }
        },
        y: {
          beginAtZero: extra.desdeCero === true,
          grid: { color: color('--rejilla'), drawTicks: false },
          border: { display: false },
          ticks: {
            color: color('--tinta-tenue'), font: { size: 11 }, padding: 8,
            callback: function (valor) { return formatea(valor, decimales === 0 ? 0 : 1); }
          }
        }
      },
      plugins: { legend: { display: false }, tooltip: { enabled: false, external: pintaTooltip } }
    };
  }

  function dibuja(canvas, clave, periodos, series, unidad, decimales, extra) {
    var anterior = graficas.get(clave);
    if (anterior) anterior.destroy();

    var grafica = new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: periodos,
        datasets: series.map(function (s) {
          return {
            label: s.etiqueta,
            data: s.valores,
            borderColor: s.color,
            backgroundColor: s.color,
            unidad: unidad,
            decimales: decimales,
            spanGaps: false
          };
        })
      },
      options: opciones(periodos, unidad, decimales, extra),
      plugins: [crosshair]
    });

    graficas.set(clave, grafica);
    return grafica;
  }

  function destruyeTodas() {
    graficas.forEach(function (g) { g.destroy(); });
    graficas.clear();
  }

  /* ------------------------------------------------- leyendas y tablas */

  function pintaLeyenda(contenedor, series) {
    contenedor.replaceChildren();
    series.forEach(function (s) {
      var item = document.createElement('span');
      item.style.cssText = 'display:inline-flex;align-items:center;gap:.4rem;';

      var marca = document.createElement('span');
      marca.setAttribute('aria-hidden', 'true');
      marca.style.cssText = 'display:inline-block;width:1rem;height:2px;border-radius:1px;';
      marca.style.background = s.color;
      item.appendChild(marca);

      var texto = document.createElement('span');
      texto.style.color = color('--tinta-suave');
      texto.textContent = s.etiqueta;
      item.appendChild(texto);

      contenedor.appendChild(item);
    });
  }

  function pintaTabla(contenedor, periodos, series, titulo, unidad, decimales) {
    contenedor.replaceChildren();

    var tabla = document.createElement('table');
    tabla.className = 'w-full text-xs';
    tabla.style.borderCollapse = 'collapse';

    var caption = document.createElement('caption');
    caption.className = 'sr-only';
    caption.textContent = titulo + ', por periodo y ámbito, en ' + unidad;
    tabla.appendChild(caption);

    var thead = document.createElement('thead');
    var filaCabecera = document.createElement('tr');
    ['Periodo'].concat(series.map(function (s) { return s.etiqueta; })).forEach(function (texto, i) {
      var th = document.createElement('th');
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

    var tbody = document.createElement('tbody');
    for (var i = periodos.length - 1; i >= 0; i--) {
      var fila = document.createElement('tr');
      var th = document.createElement('th');
      th.scope = 'row';
      th.textContent = etiquetaPeriodo(periodos[i]);
      th.style.cssText = 'padding:.3rem .5rem;text-align:left;font-weight:400;';
      th.style.color = color('--tinta-suave');
      fila.appendChild(th);
      series.forEach(function (s) {
        var td = document.createElement('td');
        td.textContent = formatea(s.valores[i], decimales);
        td.style.cssText = 'padding:.3rem .5rem;text-align:right;font-variant-numeric:tabular-nums;';
        fila.appendChild(td);
      });
      tbody.appendChild(fila);
    }
    tabla.appendChild(tbody);
    contenedor.appendChild(tabla);
  }

  /* ------------------------------------------------------------ descargas */

  function descargaCsv(nombre, periodos, columnas) {
    var cabecera = ['periodo'].concat(columnas.map(function (c) { return c.clave; }));
    var filas = [cabecera.join(',')];
    periodos.forEach(function (p, i) {
      var fila = [p];
      columnas.forEach(function (c) {
        var v = c.valores[i];
        fila.push(v === null || v === undefined ? '' : String(v));
      });
      filas.push(fila.join(','));
    });

    var blob = new Blob(['﻿' + filas.join('\n')], { type: 'text/csv;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = nombre;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    URL.revokeObjectURL(url);
  }

  window.Panel = {
    AMBITOS: AMBITOS,
    formatea: formatea,
    conUnidad: conUnidad,
    color: color,
    etiquetaPeriodo: etiquetaPeriodo,
    ordenPeriodo: ordenPeriodo,
    dibuja: dibuja,
    destruyeTodas: destruyeTodas,
    pintaLeyenda: pintaLeyenda,
    pintaTabla: pintaTabla,
    descargaCsv: descargaCsv
  };
})();
