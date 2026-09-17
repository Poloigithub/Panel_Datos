/* El tablero de materias primas y el paso a euros.
 *
 * Dos cosas que la serie mensual sola no cuenta:
 *
 * - **Cuánto ha cambiado.** Un gráfico de sesenta años enseña la forma, pero
 *   no responde a «¿el café está más caro que hace un año?». El tablero pone
 *   el último precio de cada materia con su variación a un año y a cinco.
 *
 * - **Cuánto de la subida es la materia y cuánto es el dólar.** Todo esto
 *   cotiza en dólares y aquí se paga en euros. Un barril que sube un 10 % con
 *   un dólar que se debilita un 10 % no ha subido nada para quien compra desde
 *   Europa. Por eso el conmutador de moneda: los datos se guardan tal y como
 *   los publica el Banco Mundial, y la división por el tipo de cambio oficial
 *   del BCE se hace aquí, a la vista.
 */
(function () {
  'use strict';

  var P = window.Panel;
  var RUTA = 'data/materias/';
  var AMBITO = 'espana';        // no hay otro: el Brent no tiene provincia
  var CAMBIO = 'euro_dolar';

  /* El orden es el del tablero, agrupado por lo que son. */
  var GRUPOS = [
    { titulo: 'Energía', claves: ['brent', 'gas_europa', 'carbon'] },
    { titulo: 'Lo que acaba en la cesta de la compra',
      claves: ['trigo', 'maiz', 'aceite_girasol', 'azucar', 'cafe', 'cacao',
               'naranja'] },
    { titulo: 'Campo, metal e industria',
      claves: ['urea', 'cobre', 'aluminio', 'oro'] }
  ];

  var porcentaje = new Intl.NumberFormat('es-ES',
    { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: 'always' });

  var contenido = null;
  var indice = null;
  var estado = { moneda: 'dolares' };
  /* Este gráfico no pasa por P.dibuja, así que no está en el registro que
     P.destruyeTodas vacía: hay que guardarlo y destruirlo a mano antes de
     repintarlo, o al cambiar de tema quedan dos Chart sobre el mismo lienzo. */
  var grafica = null;

  function serie(clave) {
    return (contenido.series.ambos || {})[clave] || [];
  }

  /* El precio en la moneda elegida. En euros es dividir por los dólares que
     vale un euro, y si ese mes no tiene tipo de cambio -antes de 1999 no hay
     euro- el resultado es un hueco, no un apaño. */
  function valorEn(clave, i) {
    var bruto = serie(clave)[i];
    if (bruto === null || bruto === undefined) return null;
    if (estado.moneda === 'dolares') return bruto;
    var cambio = serie(CAMBIO)[i];
    if (!cambio) return null;
    return bruto / cambio;
  }

  function ultimoConDato(clave) {
    var valores = serie(clave);
    for (var i = valores.length - 1; i >= 0; i--) {
      if (valorEn(clave, i) !== null) return i;
    }
    return -1;
  }

  function variacion(clave, desde, hasta) {
    var antes = valorEn(clave, desde);
    var ahora = valorEn(clave, hasta);
    if (antes === null || ahora === null || antes === 0) return null;
    return (ahora / antes - 1) * 100;
  }

  function unidadDe(clave) {
    var ficha = (indice.indicadores || {})[clave] || {};
    var unidad = ficha.unidad || '';
    if (estado.moneda === 'euros') unidad = unidad.replace('$', '€');
    return unidad;
  }

  function tituloDe(clave) {
    return ((indice.indicadores || {})[clave] || {}).titulo || clave;
  }

  function decimalesDe(clave) {
    var ficha = (indice.indicadores || {})[clave] || {};
    return ficha.decimales === undefined ? 2 : ficha.decimales;
  }

  function celdaVariacion(valor) {
    var celda = document.createElement('td');
    celda.className = 'py-2 pl-3 text-right tabular-nums whitespace-nowrap';
    if (valor === null) {
      celda.textContent = '—';
      celda.style.color = P.color('--tinta-tenue');
      return celda;
    }
    celda.textContent = porcentaje.format(valor) + ' %';
    // Sube o baja, sin juzgar si eso es bueno: que el pan suba y que el oro
    // suba no son la misma noticia.
    celda.style.color = P.color(valor >= 0 ? '--serie-1' : '--serie-2');
    return celda;
  }

  function filaDe(clave) {
    var hasta = ultimoConDato(clave);
    if (hasta < 0) return null;
    var periodos = contenido.periodos;

    var fila = document.createElement('tr');
    fila.className = 'border-t';
    fila.style.borderColor = P.color('--borde');

    var nombre = document.createElement('th');
    nombre.scope = 'row';
    nombre.className = 'py-2 pr-3 text-left font-medium';
    nombre.textContent = tituloDe(clave);
    fila.appendChild(nombre);

    var precio = document.createElement('td');
    precio.className = 'py-2 pl-3 text-right tabular-nums whitespace-nowrap font-semibold';
    precio.textContent = P.formatea(valorEn(clave, hasta), decimalesDe(clave));
    fila.appendChild(precio);

    var unidad = document.createElement('td');
    unidad.className = 'py-2 pl-2 text-left text-xs whitespace-nowrap';
    unidad.style.color = P.color('--tinta-tenue');
    unidad.textContent = unidadDe(clave);
    fila.appendChild(unidad);

    fila.appendChild(celdaVariacion(variacion(clave, hasta - 12, hasta)));
    fila.appendChild(celdaVariacion(variacion(clave, hasta - 60, hasta)));

    var cuando = document.createElement('td');
    cuando.className = 'py-2 pl-3 text-right text-xs whitespace-nowrap';
    cuando.style.color = P.color('--tinta-tenue');
    cuando.textContent = P.etiquetaPeriodo(periodos[hasta]);
    fila.appendChild(cuando);

    return fila;
  }

  function pintaTablero() {
    var caja = document.querySelector('[data-tablero]');
    if (!caja) return;
    caja.replaceChildren();

    GRUPOS.forEach(function (grupo) {
      var filas = grupo.claves.map(filaDe).filter(Boolean);
      if (!filas.length) return;

      var tabla = document.createElement('table');
      tabla.className = 'w-full text-sm';

      var leyenda = document.createElement('caption');
      leyenda.className = 'text-left text-xs font-semibold uppercase tracking-widest pb-2';
      leyenda.style.color = P.color('--tinta-tenue');
      leyenda.textContent = grupo.titulo;
      tabla.appendChild(leyenda);

      var cabecera = document.createElement('thead');
      var filaCabecera = document.createElement('tr');
      filaCabecera.className = 'text-xs';
      filaCabecera.style.color = P.color('--tinta-tenue');
      [['', 'left'], ['Último precio', 'right'], ['', 'left'],
       ['Un año', 'right'], ['Cinco años', 'right'], ['Mes', 'right']]
        .forEach(function (par) {
          var celda = document.createElement('th');
          celda.scope = 'col';
          celda.className = 'pb-1 font-medium text-' + par[1];
          celda.textContent = par[0];
          filaCabecera.appendChild(celda);
        });
      cabecera.appendChild(filaCabecera);
      tabla.appendChild(cabecera);

      var cuerpo = document.createElement('tbody');
      filas.forEach(function (fila) { cuerpo.appendChild(fila); });
      tabla.appendChild(cuerpo);

      var tarjeta = document.createElement('div');
      tarjeta.className = 'tarjeta p-4 overflow-x-auto';
      tarjeta.appendChild(tabla);
      caja.appendChild(tarjeta);
    });
  }

  /* El Brent en las dos monedas a la vez, que es la forma de ver de un vistazo
     cuánto de lo que pasa es el petróleo y cuánto es el dólar. */
  function pintaBrent() {
    var lienzo = document.querySelector('[data-brent]');
    if (!lienzo) return;
    if (grafica) { grafica.destroy(); grafica = null; }
    var periodos = contenido.periodos;
    var dolares = serie('brent');
    var cambio = serie(CAMBIO);

    // Desde que existe el euro: antes no hay con qué comparar.
    var desde = periodos.indexOf('1999M01');
    if (desde < 0) desde = 0;

    var etiquetas = periodos.slice(desde).map(P.etiquetaPeriodo);
    var enDolares = dolares.slice(desde);
    var enEuros = enDolares.map(function (valor, i) {
      var tipo = cambio[desde + i];
      return (valor === null || valor === undefined || !tipo) ? null : valor / tipo;
    });

    grafica = new Chart(lienzo.getContext('2d'), {
      type: 'line',
      data: {
        labels: etiquetas,
        datasets: [
          { label: 'Dólares por barril', data: enDolares,
            borderColor: P.color('--serie-1'), backgroundColor: 'transparent',
            borderWidth: 1.6, pointRadius: 0, tension: 0.1 },
          { label: 'Euros por barril', data: enEuros,
            borderColor: P.color('--serie-2'), backgroundColor: 'transparent',
            borderWidth: 1.6, pointRadius: 0, tension: 0.1 }
        ]
      },
      options: {
        animation: false,
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: true, position: 'top',
                    labels: { color: P.color('--tinta-suave'), boxWidth: 12,
                              usePointStyle: true, pointStyle: 'line' } },
          tooltip: {
            callbacks: {
              label: function (punto) {
                return punto.dataset.label + ': ' +
                  P.formatea(punto.parsed.y, 2);
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false },
               ticks: { color: P.color('--tinta-tenue'), maxTicksLimit: 10 } },
          y: { beginAtZero: true,
               grid: { color: P.color('--rejilla') },
               ticks: { color: P.color('--tinta-tenue') } }
        }
      }
    });
  }

  function conectaMoneda() {
    var grupo = document.querySelector('[data-grupo="moneda"]');
    if (!grupo) return;
    grupo.addEventListener('click', function (evento) {
      var boton = evento.target.closest('button[data-valor]');
      if (!boton) return;
      estado.moneda = boton.dataset.valor;
      grupo.querySelectorAll('button').forEach(function (otro) {
        otro.setAttribute('aria-pressed',
          String(otro.dataset.valor === estado.moneda));
      });
      pintaTablero();
    });
  }

  async function arranca() {
    var seccion = document.querySelector('[data-tablero-seccion]');
    if (!seccion) return;
    try {
      indice = await fetch(RUTA + 'index.json', { cache: 'no-cache' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
      contenido = await fetch(RUTA + AMBITO + '.json', { cache: 'no-cache' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    } catch (_) {
      // Sin el tablero la página sigue: las series completas están abajo.
      return;
    }

    conectaMoneda();
    pintaTablero();
    seccion.hidden = false;

    var caja = document.querySelector('[data-brent-seccion]');
    if (caja) {
      caja.hidden = false;
      pintaBrent();
    }

    document.addEventListener('tema:cambio', function () {
      pintaTablero();
      pintaBrent();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
