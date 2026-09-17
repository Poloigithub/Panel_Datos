/* El día de hoy, hora a hora, que es a lo que se entra en esta página.
 *
 * La serie mensual la pinta `bloque.js` como en cualquier otra sección. Esto
 * añade lo de arriba: las veinticuatro horas del último día publicado, con la
 * más barata y la más cara señaladas, porque la pregunta que trae aquí a la
 * gente no es «cuánto costó la luz en marzo» sino «a qué hora pongo la
 * lavadora».
 */
(function () {
  'use strict';

  var P = window.Panel;
  var RUTA = 'data/luz/hoy.json';

  var precio = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 2,
                                                maximumFractionDigits: 2 });

  function reloj(hora) {
    return String(hora).padStart(2, '0') + ':00';
  }

  function tramo(hora) {
    return reloj(hora) + ' a ' + reloj((hora + 1) % 24);
  }

  function pintaFrase(nodo, datos) {
    var r = datos.resumen;
    nodo.textContent = 'La luz está hoy a ' + precio.format(r.media) +
      ' c€/kWh de media. La hora más barata es de ' + tramo(r.hora_minima) +
      ', a ' + precio.format(r.minimo) + ', y la más cara de ' +
      tramo(r.hora_maxima) + ', a ' + precio.format(r.maximo) + ': ' +
      (r.minimo > 0 ? precio.format(r.maximo / r.minimo) + ' veces más.'
                    : 'incomparablemente más.');
  }

  /* Barras y no línea: son veinticuatro tramos, no una evolución continua, y
     lo que hay que poder hacer de un vistazo es comparar dos horas sueltas. */
  function pintaHoras(caja, datos) {
    var figura = document.createElement('figure');
    figura.className = 'tarjeta p-5 m-0';

    var pie = document.createElement('figcaption');
    var titulo = document.createElement('h3');
    titulo.className = 'font-semibold tracking-tight';
    titulo.textContent = 'Precio de cada hora del día';
    pie.appendChild(titulo);
    var nota = document.createElement('p');
    nota.className = 'mt-0.5 text-xs';
    nota.style.color = P.color('--tinta-tenue');
    nota.textContent = 'En céntimos de euro por kilovatio hora. La hora más ' +
      'barata y la más cara van marcadas.';
    pie.appendChild(nota);
    figura.appendChild(pie);

    var lienzoCaja = document.createElement('div');
    lienzoCaja.className = 'mt-4 relative';
    lienzoCaja.style.height = '320px';
    var lienzo = document.createElement('canvas');
    lienzo.setAttribute('role', 'img');
    lienzo.setAttribute('aria-label', 'Precio de la luz en cada hora del día');
    lienzoCaja.appendChild(lienzo);
    figura.appendChild(lienzoCaja);
    caja.appendChild(figura);

    var etiquetas = datos.horas.map(function (h) { return reloj(h.hora); });
    var valores = datos.horas.map(function (h) { return h.valor; });
    var barata = datos.resumen.hora_minima;
    var cara = datos.resumen.hora_maxima;
    var colores = datos.horas.map(function (h) {
      if (h.hora === barata) return P.color('--serie-3');
      if (h.hora === cara) return P.color('--serie-2');
      return P.color('--serie-1');
    });

    new Chart(lienzo.getContext('2d'), {
      type: 'bar',
      data: { labels: etiquetas,
              datasets: [{ data: valores, backgroundColor: colores,
                           borderWidth: 0, borderRadius: 3 }] },
      options: {
        // Sin animación, como el resto del panel: la gráfica tiene que estar
        // dibujada en cuanto aparece, no crecer desde cero.
        animation: false,
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: function (puntos) {
                return tramo(datos.horas[puntos[0].dataIndex].hora);
              },
              label: function (punto) {
                return precio.format(punto.parsed.y) + ' c€/kWh';
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false },
               ticks: { color: P.color('--tinta-tenue'), maxRotation: 0,
                        autoSkipPadding: 12 } },
          y: { beginAtZero: true,
               grid: { color: P.color('--rejilla') },
               ticks: { color: P.color('--tinta-tenue'),
                        callback: function (v) { return precio.format(v); } },
               title: { display: true, text: 'c€/kWh',
                        color: P.color('--tinta-tenue') } }
        }
      }
    });

    var detalles = document.createElement('details');
    detalles.className = 'mt-3 text-xs';
    var resumen = document.createElement('summary');
    resumen.className = 'cursor-pointer';
    resumen.style.color = P.color('--tinta-suave');
    resumen.textContent = 'Ver tabla de datos';
    detalles.appendChild(resumen);
    var tabla = document.createElement('div');
    tabla.className = 'mt-2 max-h-72 overflow-auto';
    detalles.appendChild(tabla);
    figura.appendChild(detalles);
    P.pintaTabla(tabla, etiquetas,
                 [{ etiqueta: 'Precio', color: P.color('--serie-1'),
                    valores: valores }],
                 'Precio de la luz por horas', 'c€/kWh', 2);
  }

  async function arranca() {
    var seccion = document.querySelector('[data-hoy-seccion]');
    var caja = document.querySelector('[data-hoy]');
    if (!seccion || !caja) return;

    var datos;
    try {
      var respuesta = await fetch(RUTA, { cache: 'no-cache' });
      if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
      datos = await respuesta.json();
    } catch (_) {
      // Sin el detalle del día la página sigue: la serie mensual está entera.
      return;
    }
    if (!datos.horas || !datos.horas.length) return;

    function pinta() {
      caja.replaceChildren();
      pintaFrase(document.querySelector('[data-hoy-frase]'), datos);
      var fecha = document.querySelector('[data-hoy-fecha]');
      if (fecha) {
        fecha.textContent = new Date(datos.dia + 'T12:00:00')
          .toLocaleDateString('es-ES',
            { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
      }
      pintaHoras(caja, datos);
      seccion.hidden = false;
    }

    pinta();
    document.addEventListener('tema:cambio', pinta);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
