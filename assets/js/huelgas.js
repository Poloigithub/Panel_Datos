/* El total de cada año, que es lo que deja ver la tendencia.
 *
 * La serie mensual de huelgas es muy dentada -un mes con una huelga grande
 * dispara el gráfico y el siguiente vuelve a cero- y de un vistazo no se sabe
 * si el conflicto sube o baja. Sumando el año se ve.
 *
 * Los totales se calculan aquí y no en el descargador a propósito: son la suma
 * de unos datos que ya están descargados, y guardarlos otra vez sería tener la
 * misma cifra en dos sitios pudiendo contradecirse.
 */
(function () {
  'use strict';

  var P = window.Panel;
  var RUTA = 'data/huelgas/';

  var entero = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0,
                                                useGrouping: 'always' });

  var MAGNITUDES = [
    { clave: 'participantes', titulo: 'Personas que secundaron una huelga' },
    { clave: 'jornadas_perdidas', titulo: 'Jornadas no trabajadas' },
    { clave: 'huelgas', titulo: 'Huelgas' }
  ];

  var datos = {};
  var estado = { magnitud: 'participantes' };

  /* Un año cuenta como completo cuando están sus doce meses. Los demás se
     pintan igual, porque un año a medias también informa, pero se marcan:
     comparar cinco meses con doce sin avisar es mentir con una barra. */
  function porAnyo(ambito, clave) {
    var contenido = datos[ambito];
    if (!contenido) return [];
    var valores = (contenido.series.ambos || {})[clave];
    if (!valores) return [];

    var suma = {};
    contenido.periodos.forEach(function (periodo, i) {
      if (valores[i] === null || valores[i] === undefined) return;
      var anyo = periodo.slice(0, 4);
      if (!suma[anyo]) suma[anyo] = { total: 0, meses: 0 };
      suma[anyo].total += valores[i];
      suma[anyo].meses += 1;
    });

    return Object.keys(suma).sort().map(function (anyo) {
      return { anyo: anyo, total: suma[anyo].total,
               meses: suma[anyo].meses, completo: suma[anyo].meses === 12 };
    });
  }

  function tarjeta(ambito, magnitud) {
    var filas = porAnyo(ambito.id, magnitud.clave);
    if (!filas.length) return null;

    var figura = document.createElement('figure');
    figura.className = 'tarjeta p-4 m-0';

    var pie = document.createElement('figcaption');
    var titulo = document.createElement('h3');
    titulo.className = 'font-semibold tracking-tight';
    titulo.textContent = ambito.etiqueta;
    pie.appendChild(titulo);
    var nota = document.createElement('p');
    nota.className = 'mt-0.5 text-xs';
    nota.style.color = P.color('--tinta-tenue');
    nota.textContent = magnitud.titulo + ', suma de cada año';
    pie.appendChild(nota);
    figura.appendChild(pie);

    var lienzoCaja = document.createElement('div');
    lienzoCaja.className = 'mt-4 relative';
    lienzoCaja.style.height = '240px';
    var lienzo = document.createElement('canvas');
    lienzo.setAttribute('role', 'img');
    lienzo.setAttribute('aria-label',
      magnitud.titulo + ' por año en ' + ambito.etiqueta);
    lienzoCaja.appendChild(lienzo);
    figura.appendChild(lienzoCaja);

    // Los años incompletos van en un tono apagado, y su etiqueta lo dice.
    var color = P.color(ambito.variable);
    new Chart(lienzo.getContext('2d'), {
      type: 'bar',
      data: {
        labels: filas.map(function (f) { return f.anyo; }),
        datasets: [{
          data: filas.map(function (f) { return f.total; }),
          backgroundColor: filas.map(function (f) {
            return f.completo ? color : P.color('--tinta-tenue');
          }),
          borderWidth: 0, borderRadius: 3
        }]
      },
      options: {
        animation: false,
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (punto) {
                var fila = filas[punto.dataIndex];
                return entero.format(punto.parsed.y) +
                  (fila.completo ? '' : ' · sólo ' + fila.meses +
                    (fila.meses === 1 ? ' mes publicado' : ' meses publicados'));
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false },
               ticks: { color: P.color('--tinta-tenue') } },
          y: { beginAtZero: true,
               grid: { color: P.color('--rejilla') },
               ticks: { color: P.color('--tinta-tenue'),
                        callback: function (v) { return entero.format(v); } } }
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
    P.pintaTabla(tabla, filas.map(function (f) {
      return f.completo ? f.anyo : f.anyo + ' (' + f.meses + ' meses)';
    }), [{ etiqueta: magnitud.titulo, color: color,
           valores: filas.map(function (f) { return f.total; }) }],
      magnitud.titulo + ' por año en ' + ambito.etiqueta, '', 0);

    return figura;
  }

  function pinta() {
    var caja = document.querySelector('[data-anual]');
    if (!caja) return;
    caja.replaceChildren();
    var magnitud = MAGNITUDES.find(function (m) {
      return m.clave === estado.magnitud;
    }) || MAGNITUDES[0];

    P.AMBITOS.forEach(function (ambito) {
      var figura = tarjeta(ambito, magnitud);
      if (figura) caja.appendChild(figura);
    });
  }

  function conectaBotones() {
    var grupo = document.querySelector('[data-grupo="magnitud"]');
    if (!grupo) return;
    grupo.addEventListener('click', function (evento) {
      var boton = evento.target.closest('button[data-valor]');
      if (!boton) return;
      estado.magnitud = boton.dataset.valor;
      grupo.querySelectorAll('button').forEach(function (otro) {
        otro.setAttribute('aria-pressed',
          String(otro.dataset.valor === estado.magnitud));
      });
      pinta();
    });
  }

  async function arranca() {
    var seccion = document.querySelector('[data-anual-seccion]');
    if (!seccion) return;
    try {
      var indice = await fetch(RUTA + 'index.json', { cache: 'no-cache' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
      for (const a of indice.ambitos) {
        var respuesta = await fetch(RUTA + a.fichero, { cache: 'no-cache' });
        if (!respuesta.ok) throw new Error(respuesta.status);
        datos[a.id] = await respuesta.json();
      }
    } catch (_) {
      // Sin los totales la página sigue: la serie mensual está entera.
      return;
    }

    conectaBotones();
    pinta();
    seccion.hidden = false;
    document.addEventListener('tema:cambio', pinta);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
