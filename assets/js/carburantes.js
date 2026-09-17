/* Lo que cuesta hoy llenar el depósito, y en los tres ámbitos.
 *
 * La serie mensual que hay debajo cuenta cómo hemos llegado hasta aquí. Esto
 * de arriba contesta a la otra pregunta, la que trae a la gente a esta página:
 * cuánto vale ahora mismo, y si en Castellón sale más caro o más barato que en
 * el resto de España.
 *
 * Se alimenta de dos ficheros que el descargador escribe aparte del bloque:
 * `hoy.json`, con la media del último día y cuántas gasolineras la sostienen,
 * y `diario.json`, que es el acumulado día a día del que salen las medias
 * mensuales. El diario está aquí porque un carburante se mueve dentro del mes
 * y la media mensual se lo come.
 */
(function () {
  'use strict';

  var P = window.Panel;
  var RUTA = 'data/carburantes/';

  var CARBURANTES = [
    { clave: 'gasolina_95', titulo: 'Gasolina 95' },
    { clave: 'gasoleo_a', titulo: 'Gasóleo A' },
    { clave: 'gasolina_98', titulo: 'Gasolina 98' },
    { clave: 'gasoleo_premium', titulo: 'Gasóleo premium' },
    { clave: 'glp', titulo: 'GLP' }
  ];

  var euros = new Intl.NumberFormat('es-ES',
    { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  // «always» y no «auto»: por defecto el español no separa los millares de
  // un número de cuatro cifras, y en la misma columna quedaba «11.256» al
  // lado de «5486» como si una de las dos estuviera mal.
  var entero = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0,
                                                useGrouping: 'always' });
  var diferencia = new Intl.NumberFormat('es-ES',
    { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: 'always' });

  var hoy = null;
  var diario = null;
  var grafica = null;
  var estado = { carburante: 'gasolina_95' };

  function fechaLarga(iso) {
    var partes = String(iso || '').split('-');
    if (partes.length !== 3) return iso || '';
    var meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
                 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
    return parseInt(partes[2], 10) + ' de ' + meses[parseInt(partes[1], 10) - 1] +
      ' de ' + partes[0];
  }

  /* Una tarjeta por ámbito con los cinco precios, y al lado de cada uno cuánto
     se aparta de la media nacional. Esa comparación es la única forma de que
     «1,919 €» signifique algo. */
  function tarjeta(ambito) {
    var valores = (hoy.ambitos || {})[ambito.id] || {};
    var cuantas = (hoy.estaciones || {})[ambito.id] || {};
    var nacional = (hoy.ambitos || {}).espana || {};
    if (!Object.keys(valores).length) return null;

    var figura = document.createElement('div');
    figura.className = 'tarjeta p-4';

    var titulo = document.createElement('h3');
    titulo.className = 'font-semibold tracking-tight';
    titulo.textContent = ambito.etiqueta;
    figura.appendChild(titulo);

    var tabla = document.createElement('table');
    tabla.className = 'mt-3 w-full text-sm';
    var cuerpo = document.createElement('tbody');

    CARBURANTES.forEach(function (carburante) {
      var valor = valores[carburante.clave];
      var fila = document.createElement('tr');
      fila.className = 'border-t';
      fila.style.borderColor = P.color('--borde');

      var nombre = document.createElement('th');
      nombre.scope = 'row';
      nombre.className = 'py-2 pr-3 text-left font-normal';
      nombre.textContent = carburante.titulo;
      fila.appendChild(nombre);

      var precio = document.createElement('td');
      precio.className = 'py-2 pl-3 text-right tabular-nums whitespace-nowrap font-semibold';
      precio.textContent = valor === undefined ? '—' : euros.format(valor) + ' €';
      if (valor === undefined) precio.style.color = P.color('--tinta-tenue');
      fila.appendChild(precio);

      // Cuánto se aparta de España. En España misma, cuántas gasolineras.
      var contexto = document.createElement('td');
      contexto.className = 'py-2 pl-3 text-right text-xs whitespace-nowrap';
      contexto.style.color = P.color('--tinta-tenue');
      if (ambito.id === 'espana') {
        var n = cuantas[carburante.clave];
        contexto.textContent = n ? entero.format(n) + ' gasolineras' : '';
      } else if (valor !== undefined && nacional[carburante.clave]) {
        var puntos = (valor / nacional[carburante.clave] - 1) * 100;
        contexto.textContent = diferencia.format(puntos) + ' % vs España';
        if (Math.abs(puntos) >= 0.5) {
          contexto.style.color = P.color(puntos > 0 ? '--serie-2' : '--serie-3');
        }
      }
      fila.appendChild(contexto);
      cuerpo.appendChild(fila);
    });

    tabla.appendChild(cuerpo);
    figura.appendChild(tabla);
    return figura;
  }

  function pintaHoy() {
    var caja = document.querySelector('[data-hoy]');
    if (!caja || !hoy) return;
    caja.replaceChildren();
    P.AMBITOS.forEach(function (ambito) {
      var t = tarjeta(ambito);
      if (t) caja.appendChild(t);
    });
    var cuando = document.querySelector('[data-hoy-fecha]');
    if (cuando) cuando.textContent = 'Datos del ' + fechaLarga(hoy.fecha);
  }

  /* El día a día de los tres ámbitos. Es lo que la media mensual esconde: una
     subida de diez céntimos dentro de un mes no se ve en un solo punto. */
  function pintaDiario() {
    var lienzo = document.querySelector('[data-diario]');
    if (!lienzo || !diario) return;
    if (grafica) { grafica.destroy(); grafica = null; }

    var dias = {};
    P.AMBITOS.forEach(function (ambito) {
      Object.keys(diario[ambito.id] || {}).forEach(function (d) { dias[d] = true; });
    });
    var etiquetas = Object.keys(dias).sort();
    if (!etiquetas.length) return;

    var conjuntos = P.AMBITOS.map(function (ambito) {
      var porDia = diario[ambito.id] || {};
      return {
        label: ambito.etiqueta,
        data: etiquetas.map(function (d) {
          var v = porDia[d];
          return v && v[estado.carburante] !== undefined ? v[estado.carburante] : null;
        }),
        borderColor: P.color(ambito.variable),
        backgroundColor: 'transparent',
        borderWidth: 1.8, pointRadius: 0, tension: 0.15, spanGaps: false
      };
    }).filter(function (c) { return c.data.some(function (v) { return v !== null; }); });

    grafica = new Chart(lienzo.getContext('2d'), {
      type: 'line',
      data: { labels: etiquetas.map(fechaLarga), datasets: conjuntos },
      options: {
        animation: false,
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top',
                    labels: { color: P.color('--tinta-suave'), boxWidth: 12,
                              usePointStyle: true, pointStyle: 'line' } },
          tooltip: { callbacks: { label: function (punto) {
            return punto.dataset.label + ': ' +
              euros.format(punto.parsed.y) + ' €/l';
          } } }
        },
        scales: {
          x: { grid: { display: false },
               ticks: { color: P.color('--tinta-tenue'), maxTicksLimit: 8 } },
          // Con el símbolo detrás, porque «1,900» a secas se lee como mil
          // novecientos y no como un euro con noventa.
          y: { grid: { color: P.color('--rejilla') },
               ticks: { color: P.color('--tinta-tenue'),
                        callback: function (v) {
                          return euros.format(v) + ' €';
                        } } }
        }
      }
    });
  }

  function conectaBotones() {
    var grupo = document.querySelector('[data-grupo="carburante"]');
    if (!grupo) return;
    grupo.addEventListener('click', function (evento) {
      var boton = evento.target.closest('button[data-valor]');
      if (!boton) return;
      estado.carburante = boton.dataset.valor;
      grupo.querySelectorAll('button').forEach(function (otro) {
        otro.setAttribute('aria-pressed',
          String(otro.dataset.valor === estado.carburante));
      });
      pintaDiario();
    });
  }

  async function trae(fichero) {
    var respuesta = await fetch(RUTA + fichero, { cache: 'no-cache' });
    if (!respuesta.ok) throw new Error(respuesta.status);
    return respuesta.json();
  }

  async function arranca() {
    var seccion = document.querySelector('[data-hoy-seccion]');
    if (!seccion) return;
    try {
      hoy = await trae('hoy.json');
    } catch (_) {
      return;   // Sin el panel de hoy la página sigue: la serie está abajo.
    }
    pintaHoy();
    seccion.hidden = false;

    try {
      diario = await trae('diario.json');
    } catch (_) {
      return;
    }
    var cajaDiario = document.querySelector('[data-diario-seccion]');
    if (cajaDiario) {
      conectaBotones();
      cajaDiario.hidden = false;
      pintaDiario();
    }

    document.addEventListener('tema:cambio', function () {
      pintaHoy();
      pintaDiario();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
