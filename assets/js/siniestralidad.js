/* El avance del año en curso, que es la cifra que la gente viene a buscar.
 *
 * La serie anual la pinta `bloque.js` como en cualquier otra sección; esto sólo
 * añade lo de arriba: cuántos accidentes y cuántas muertes van en lo que va de
 * año en cada ámbito, y si son más o menos que por estas fechas el año pasado.
 *
 * La comparación es siempre contra el MISMO PERIODO del año anterior. Los
 * ficheros del ministerio son acumulados desde enero, así que medir siete meses
 * contra doce diría que los accidentes se han hundido un cuarenta por ciento
 * todos los años por marzo.
 */
(function () {
  'use strict';

  var P = window.Panel;
  var RUTA = 'data/siniestralidad/avance.json';

  var entero = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0,
                                                useGrouping: 'always' });
  var porcentaje = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 1,
                                                    maximumFractionDigits: 1 });

  function variacion(actual, anterior) {
    if (!anterior || actual === undefined || actual === null) return null;
    return (actual / anterior - 1) * 100;
  }

  /* El panel no pinta las subidas de rojo ni las bajadas de verde en ningún
     sitio, y aquí tampoco: el color no dice si algo va bien o mal, lo dicen
     las palabras. Un «más» o un «menos» delante es más claro que un matiz de
     color que además se lee mal en según qué pantalla. */
  function pintaVariacion(nodo, valor, sufijo) {
    if (valor === null) {
      nodo.textContent = 'sin comparación con el año anterior';
      return;
    }
    if (Math.abs(valor) < 0.05) {
      nodo.textContent = 'los mismos ' + sufijo;
      return;
    }
    nodo.textContent = porcentaje.format(Math.abs(valor)) + ' % ' +
      (valor > 0 ? 'más ' : 'menos ') + sufijo;
  }

  function tarjeta(nombre, datos) {
    var caja = document.createElement('article');
    caja.className = 'tarjeta p-4';

    var titulo = document.createElement('h3');
    titulo.className = 'text-xs font-semibold uppercase tracking-widest';
    titulo.style.color = P.color('--tinta-tenue');
    titulo.textContent = nombre;
    caja.appendChild(titulo);

    var cifra = document.createElement('p');
    cifra.className = 'mt-2 text-3xl font-bold tracking-tight tabular-nums';
    cifra.textContent = entero.format(datos.actual.accidentes_jornada);
    caja.appendChild(cifra);

    var pie = document.createElement('p');
    pie.className = 'text-sm';
    pie.style.color = P.color('--tinta-suave');
    pie.textContent = 'accidentes con baja en el trabajo';
    caja.appendChild(pie);

    var cambio = document.createElement('p');
    cambio.className = 'mt-1 text-sm font-medium tabular-nums';
    cambio.style.color = P.color('--tinta-suave');
    pintaVariacion(cambio, variacion(datos.actual.accidentes_jornada,
                                     datos.anterior.accidentes_jornada),
                   'que el año pasado por estas fechas');
    caja.appendChild(cambio);

    var muertes = document.createElement('p');
    muertes.className = 'mt-3 pt-3 text-sm';
    muertes.style.borderTop = '1px solid ' + P.color('--borde');
    muertes.style.color = P.color('--tinta-suave');
    var cuantas = datos.actual.accidentes_mortales;
    muertes.innerHTML = '';
    var fuerte = document.createElement('strong');
    fuerte.style.color = P.color('--tinta');
    fuerte.textContent = entero.format(cuantas);
    muertes.appendChild(fuerte);
    muertes.appendChild(document.createTextNode(
      cuantas === 1 ? ' persona ha muerto en el puesto de trabajo'
                    : ' personas han muerto en el puesto de trabajo'));
    caja.appendChild(muertes);

    var itinere = document.createElement('p');
    itinere.className = 'mt-1 text-xs';
    itinere.style.color = P.color('--tinta-tenue');
    itinere.textContent = 'y ' + entero.format(datos.actual.mortales_itinere) +
      ' yendo o volviendo, de ' + entero.format(datos.actual.accidentes_itinere) +
      ' accidentes in itinere';
    caja.appendChild(itinere);

    return caja;
  }

  async function arranca() {
    var seccion = document.querySelector('[data-avance-seccion]');
    var caja = document.querySelector('[data-avance]');
    if (!seccion || !caja) return;

    var avance;
    try {
      var respuesta = await fetch(RUTA, { cache: 'no-cache' });
      if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
      avance = await respuesta.json();
    } catch (_) {
      // Sin avance la página sigue siendo útil: la serie anual está entera.
      return;
    }

    function pinta() {
      caja.replaceChildren();
      P.AMBITOS.forEach(function (ambito) {
        var datos = avance.ambitos[ambito.id];
        if (datos && datos.actual && datos.actual.accidentes_jornada !== undefined) {
          caja.appendChild(tarjeta(ambito.etiqueta, datos));
        }
      });
      var pie = document.querySelector('[data-avance-pie]');
      if (pie) {
        pie.textContent = (avance.periodo_texto || 'Avance de ' + avance.anyo) +
          ', frente al mismo periodo de ' + avance.anyo_anterior + '.';
      }
      seccion.hidden = false;
    }

    pinta();
    // Los colores se leen del tema, así que hay que repintar si el tema cambia.
    document.addEventListener('tema:cambio', pinta);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
