/* La cesta de la compra: cuánto ha subido cada producto.
 *
 * La pregunta de esta página no es «cómo va la inflación» sino «qué ha subido
 * más», y eso se lee en un ranking, no en doce líneas de colores dentro de una
 * misma gráfica: doce series obligarían a doce tonos que nadie distingue y que
 * además romperían la paleta del panel.
 *
 * Todo se calcula dividiendo el índice de hoy entre el de la fecha con la que
 * se compara, que es exactamente comparar dos precios. No se resta 100: la base
 * del índice es la que el INE tenga vigente -ahora 2025- y cambia cada pocos
 * años, así que dar por hecho que 2021 vale 100 daría cifras falsas. */
(function () {
  'use strict';

  var P = window.Panel;
  var RUTA = 'data/cesta/';

  var estado = { ambito: 'espana', desde: '2021' };
  var DEFECTOS = { ambito: 'espana', desde: '2021' };
  var VALIDOS = {
    ambito: ['espana', 'comunitat-valenciana', 'castellon'],
    desde: ['2021', '2019', '1']
  };

  var indice = null;
  var datos = {};

  // Un decimal siempre: «+84 %» al lado de «+60,1 %» parece otra precisión.
  var porcentaje = new Intl.NumberFormat('es-ES', {
    minimumFractionDigits: 1, maximumFractionDigits: 1, useGrouping: 'always'
  });

  function contenido() {
    return datos[estado.ambito];
  }

  function serie(clave) {
    var actual = contenido();
    if (!actual) return [];
    var valores = (actual.series.ambos || {})[clave];
    if (!valores) return [];
    return actual.periodos.map(function (periodo, i) {
      return { periodo: periodo, valor: valores[i] };
    }).filter(function (p) { return p.valor !== null && p.valor !== undefined; });
  }

  /* El punto con el que se compara. Un valor de cuatro cifras es un año
     concreto; uno pequeño, cuántos años atrás. Se busca el mismo mes de aquel
     año, no el primero que haya, para no comparar agosto con enero: la fruta y
     la verdura tienen temporada y eso movería la cifra sin que suba nada. */
  function referencia(puntos) {
    if (!puntos.length) return null;
    var ultimo = puntos[puntos.length - 1];
    var anyoUltimo = P.ordenPeriodo(ultimo.periodo)[0];
    var pedido = parseInt(estado.desde, 10);
    var objetivo = pedido > 1000 ? pedido : anyoUltimo - pedido;
    var mismoMes = ultimo.periodo.replace(/^\d{4}/, String(objetivo));

    var exacto = puntos.filter(function (p) { return p.periodo === mismoMes; })[0];
    if (exacto) return exacto;
    // Sin ese mes exacto, el último punto de aquel año o el más antiguo que haya.
    var delAnyo = puntos.filter(function (p) {
      return P.ordenPeriodo(p.periodo)[0] === objetivo;
    });
    if (delAnyo.length) return delAnyo[delAnyo.length - 1];
    return P.ordenPeriodo(puntos[0].periodo)[0] > objetivo ? null : puntos[0];
  }

  function subida(clave) {
    var puntos = serie(clave);
    if (!puntos.length) return null;
    var ultimo = puntos[puntos.length - 1];
    var base = referencia(puntos);
    if (!base || !base.valor) return null;
    var variacion = (ultimo.valor / base.valor - 1) * 100;
    return {
      clave: clave,
      titulo: (indice.indicadores[clave] || {}).titulo || clave,
      nota: (indice.indicadores[clave] || {}).nota,
      variacion: variacion,
      ultimo: ultimo,
      base: base,
      puntos: puntos
    };
  }

  function subidas() {
    return Object.keys(indice.indicadores)
      .map(subida)
      .filter(Boolean)
      .sort(function (a, b) { return b.variacion - a.variacion; });
  }

  function colorAmbito() {
    var variables = { espana: '--serie-1', 'comunitat-valenciana': '--serie-2',
                      castellon: '--serie-3' };
    return P.color(variables[estado.ambito] || '--serie-1');
  }

  function textoDesde(fila) {
    return 'desde ' + P.etiquetaPeriodo(fila.base.periodo);
  }

  /* ---------------------------------------------------------------- ranking */

  function pintaRanking(filas) {
    var cuerpo = document.querySelector('[data-ranking]');
    cuerpo.replaceChildren();
    var tope = Math.max.apply(null, filas.map(function (f) {
      return Math.abs(f.variacion);
    }).concat([1]));

    filas.forEach(function (fila) {
      var tr = document.createElement('tr');
      tr.style.borderTop = '1px solid ' + P.color('--borde');

      var nombre = document.createElement('th');
      nombre.scope = 'row';
      nombre.className = 'px-3 py-2 text-left font-normal';
      nombre.textContent = fila.titulo;
      tr.appendChild(nombre);

      // La barra dice de un vistazo lo que la cifra dice con precisión.
      var barra = document.createElement('td');
      barra.className = 'px-3 py-2 w-1/2';
      var carril = document.createElement('div');
      carril.style.cssText = 'height:.55rem;border-radius:999px;position:relative;';
      carril.style.background = P.color('--superficie-2');
      var relleno = document.createElement('div');
      relleno.style.cssText = 'height:100%;border-radius:999px;';
      relleno.style.width = (Math.abs(fila.variacion) / tope * 100).toFixed(1) + '%';
      relleno.style.background = fila.variacion >= 0 ? colorAmbito() : P.color('--tinta-tenue');
      carril.appendChild(relleno);
      barra.appendChild(carril);
      tr.appendChild(barra);

      var valor = document.createElement('td');
      valor.className = 'px-3 py-2 text-right font-semibold whitespace-nowrap';
      valor.style.fontVariantNumeric = 'tabular-nums';
      valor.textContent = (fila.variacion >= 0 ? '+' : '−') +
        porcentaje.format(Math.abs(fila.variacion)) + ' %';
      tr.appendChild(valor);

      var cuando = document.createElement('td');
      cuando.className = 'px-3 py-2 text-right text-xs whitespace-nowrap';
      cuando.style.color = P.color('--tinta-tenue');
      cuando.textContent = textoDesde(fila);
      tr.appendChild(cuando);

      cuerpo.appendChild(tr);
    });
  }

  /* ------------------------------------------------------------- evoluciones */

  function pintaSeries(filas) {
    var contenedor = document.querySelector('[data-series]');
    contenedor.replaceChildren();
    P.destruyeTodas();

    filas.forEach(function (fila) {
      var figura = document.createElement('figure');
      figura.className = 'tarjeta p-4 m-0';

      var pie = document.createElement('figcaption');
      var titulo = document.createElement('h3');
      titulo.className = 'text-sm font-semibold tracking-tight';
      titulo.textContent = fila.titulo;
      pie.appendChild(titulo);
      var cifra = document.createElement('p');
      cifra.className = 'text-xs';
      cifra.style.color = P.color('--tinta-tenue');
      cifra.textContent = P.formatea(fila.ultimo.valor, 1) + ' · ' +
        P.etiquetaPeriodo(fila.ultimo.periodo);
      pie.appendChild(cifra);
      figura.appendChild(pie);

      var caja = document.createElement('div');
      caja.className = 'mt-3 relative';
      caja.style.height = '150px';
      var lienzo = document.createElement('canvas');
      lienzo.setAttribute('role', 'img');
      lienzo.setAttribute('aria-label', 'Evolución del índice de ' + fila.titulo);
      caja.appendChild(lienzo);
      figura.appendChild(caja);
      contenedor.appendChild(figura);

      var periodos = fila.puntos.map(function (p) { return p.periodo; });
      var series = [{
        etiqueta: fila.titulo, color: colorAmbito(),
        valores: fila.puntos.map(function (p) { return p.valor; })
      }];
      P.dibuja(lienzo, 'cesta-' + fila.clave, periodos, series, 'índice', 1);

      var detalles = document.createElement('details');
      detalles.className = 'mt-2 text-xs';
      var resumen = document.createElement('summary');
      resumen.className = 'cursor-pointer';
      resumen.style.color = P.color('--tinta-suave');
      resumen.textContent = 'Ver tabla de datos';
      detalles.appendChild(resumen);
      var tabla = document.createElement('div');
      tabla.className = 'mt-2 max-h-72 overflow-auto';
      detalles.appendChild(tabla);
      figura.appendChild(detalles);
      P.pintaTabla(tabla, periodos, series, 'Índice de ' + fila.titulo, 'índice', 1);
    });
  }

  function render() {
    var filas = subidas();
    pintaRanking(filas);
    pintaSeries(filas);

    var titular = document.querySelector('[data-titular]');
    if (titular && filas.length) {
      var primera = filas[0];
      titular.textContent = primera.titulo + ', lo que más ha subido: ' +
        (primera.variacion >= 0 ? '+' : '−') +
        porcentaje.format(Math.abs(primera.variacion)) + ' % ' + textoDesde(primera) +
        ' (último dato, ' + P.etiquetaPeriodo(primera.ultimo.periodo) + ').';
    }

    var aviso = document.querySelector('[data-aviso-ambito]');
    if (aviso) {
      aviso.hidden = estado.ambito !== 'castellon';
    }
    window.Enlace.escribe(estado, DEFECTOS);
  }

  function conectaControles() {
    document.querySelectorAll('[data-grupo]').forEach(function (grupo) {
      var clave = grupo.dataset.grupo;
      grupo.addEventListener('click', function (evento) {
        var boton = evento.target.closest('button[data-valor]');
        if (!boton) return;
        grupo.querySelectorAll('button').forEach(function (b) {
          b.setAttribute('aria-pressed', String(b === boton));
        });
        estado[clave] = boton.dataset.valor;
        render();
      });
    });
    var csv = document.querySelector('[data-csv]');
    if (csv) {
      csv.addEventListener('click', function () {
        var filas = subidas();
        var periodos = (contenido() || {}).periodos || [];
        var columnas = filas.map(function (f) {
          var porPeriodo = {};
          f.puntos.forEach(function (p) { porPeriodo[p.periodo] = p.valor; });
          return { clave: f.clave,
                   valores: periodos.map(function (p) {
                     var v = porPeriodo[p];
                     return v === undefined ? null : v;
                   }) };
        });
        P.descargaCsv('cesta-' + estado.ambito + '.csv', periodos, columnas);
      });
      window.Enlace.botonCopiar(csv.parentNode);
    }
  }

  async function carga(ruta) {
    var respuesta = await fetch(ruta, { cache: 'no-cache' });
    if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
    return respuesta.json();
  }

  async function arranca() {
    var aviso = document.querySelector('[data-estado]');
    try {
      indice = await carga(RUTA + 'index.json');
      await Promise.all(indice.ambitos.map(async function (a) {
        datos[a.id] = await carga(RUTA + a.fichero);
      }));

      window.Enlace.aplica(estado, DEFECTOS, VALIDOS);
      aviso.hidden = true;
      document.querySelector('[data-panel]').hidden = false;

      var fecha = new Date(indice.actualizado);
      var nodo = document.querySelector('[data-actualizado]');
      if (nodo) {
        nodo.textContent = Number.isNaN(fecha.getTime())
          ? indice.actualizado
          : fecha.toLocaleString('es-ES', { dateStyle: 'long', timeStyle: 'short' });
      }

      conectaControles();
      window.Enlace.sincroniza(estado);
      render();
      document.addEventListener('tema:cambio', render);
    } catch (error) {
      aviso.textContent = 'No se han podido cargar los datos (' + error.message + ').';
      aviso.style.color = P.color('--tinta');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
