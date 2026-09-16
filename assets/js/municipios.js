/* Mapa y fichas de los municipios de la provincia de Castellón.
 *
 * Junta cuatro fuentes: los contornos de GISCO, el paro registrado del SEPE, y
 * del INE la población y la renta del Atlas, que es la única estadística que
 * baja de la provincia. El indicador que más dice es el derivado del paro y la
 * población -paro por cada cien habitantes-, porque es el único que permite
 * comparar un pueblo de doscientos vecinos con la capital. */
(function () {
  'use strict';

  var P = window.Panel;

  var estado = { indicador: 'variacion', periodo: null, municipio: null };
  var geo = null, paro = null, poblacion = null, renta = null;

  var INDICADORES = {
    variacion: {
      titulo: 'Variación del paro en un año',
      unidad: '%',
      decimales: 1,
      tipo: 'divergente',
      explicacion: 'Media de los últimos doce meses frente a los doce anteriores. ' +
                   'Azul, baja; rojo, sube. Se comparan medias anuales y no meses ' +
                   'sueltos porque en pueblos pequeños unos pocos parados más darían ' +
                   'saltos enormes que no significan nada.'
    },
    tasa: {
      titulo: 'Paro por cada 100 habitantes',
      unidad: '%',
      decimales: 1,
      explicacion: 'Personas apuntadas al paro por cada cien habitantes. No es la tasa ' +
                   'de paro -el denominador es la población total, no la activa- pero ' +
                   'sí permite comparar municipios de distinto tamaño.'
    },
    paro: {
      unidad: 'personas',
      decimales: 0,
      explicacion: 'Personas apuntadas en las oficinas de empleo. En valores absolutos, ' +
                   'el mapa señala sobre todo dónde vive más gente.'
    },
    renta: {
      titulo: 'Renta neta media por persona',
      unidad: 'euros',
      decimales: 0,
      anual: true,
      explicacion: 'Renta neta media por persona del Atlas de Distribución de Renta del ' +
                   'INE, única fuente que baja de la provincia. Es anual y va con un ' +
                   'par de años de retraso respecto al paro, así que se muestra el ' +
                   'último año publicado hasta el mes elegido. Los pueblos más pequeños ' +
                   'comparten un valor de grupo: quince de ellos, todos por debajo de ' +
                   'los 110 habitantes, repiten exactamente la misma cifra.'
    },
  };

  /* La población es anual y el paro mensual: para un mes dado se toma el dato
     del mismo año, o el más reciente que exista. */
  function poblacionDe(codigo, periodo) {
    if (!poblacion) return null;
    var municipio = poblacion.municipios[codigo];
    if (!municipio) return null;
    var objetivo = parseInt((periodo || '').slice(0, 4), 10);
    var mejor = null, mejorAnyo = -Infinity, ultimo = null;
    poblacion.periodos.forEach(function (p, i) {
      var valor = municipio.poblacion[i];
      if (valor === null || valor === undefined) return;
      ultimo = valor;
      var anyo = parseInt(p.slice(0, 4), 10);
      if (anyo <= objetivo && anyo > mejorAnyo) {
        mejor = valor;
        mejorAnyo = anyo;
      }
    });
    return mejor !== null ? mejor : ultimo;
  }

  /* La renta es anual y llega con retraso: para un mes dado se coge el último
     año publicado que no sea posterior. Devuelve también de qué año es, porque
     rotular con el mes elegido una cifra de hace dos años sería mentir. */
  function rentaDe(codigo, periodo, clave) {
    if (!renta) return null;
    var municipio = renta.municipios[codigo];
    if (!municipio || !municipio[clave || 'renta_persona']) return null;
    var valores = municipio[clave || 'renta_persona'];
    var objetivo = parseInt((periodo || '').slice(0, 4), 10);
    var mejor = null, mejorAnyo = -Infinity;
    renta.periodos.forEach(function (p, i) {
      var valor = valores[i];
      if (valor === null || valor === undefined) return;
      var anyo = parseInt(p.slice(0, 4), 10);
      if (anyo <= objetivo && anyo > mejorAnyo) {
        mejor = { valor: valor, anyo: p };
        mejorAnyo = anyo;
      }
    });
    return mejor;
  }

  /* Mismo mes del año anterior: '2026M07' -> '2025M07'. */
  function haceUnAnyo(periodo) {
    var m = /^(\d{4})M(\d{2})$/.exec(periodo || '');
    return m ? (parseInt(m[1], 10) - 1) + 'M' + m[2] : null;
  }

  /* Media de los doce meses que terminan en `periodo`.
     Comparar meses sueltos en pueblos de pocos cientos de habitantes es ruido:
     siete parados más en Catí son un 70 % que no dice nada. La media anual
     quita de en medio la estacionalidad y el azar de los números pequeños. */
  function mediaAnual(codigo, periodo) {
    var municipio = paro.municipios[codigo];
    if (!municipio) return null;
    var fin = paro.periodos.indexOf(periodo);
    if (fin < 11) return null;
    var suma = 0, cuantos = 0;
    for (var i = fin - 11; i <= fin; i++) {
      var valor = municipio.paro_total[i];
      if (valor === null || valor === undefined) continue;
      suma += valor;
      cuantos++;
    }
    return cuantos >= 10 ? suma / cuantos : null;
  }

  function anyoDe(periodo) {
    return parseInt((periodo || '').slice(0, 4), 10);
  }

  function paroDe(codigo, periodo) {
    var municipio = paro.municipios[codigo];
    if (!municipio) return null;
    var i = paro.periodos.indexOf(periodo);
    if (i < 0) return null;
    var valor = municipio.paro_total[i];
    return valor === undefined ? null : valor;
  }

  function valorDe(codigo, periodo) {
    if (estado.indicador === 'paro') return paroDe(codigo, periodo);
    if (estado.indicador === 'renta') {
      var dato = rentaDe(codigo, periodo);
      return dato ? dato.valor : null;
    }
    if (estado.indicador === 'tasa') {
      var parados = paroDe(codigo, periodo);
      var habitantes = poblacionDe(codigo, periodo);
      if (parados === null || !habitantes) return null;
      return (parados / habitantes) * 100;
    }
    var ahora = mediaAnual(codigo, periodo);
    var antes = mediaAnual(codigo, haceUnAnyo(periodo));
    if (ahora === null || !antes) return null;
    return ((ahora - antes) / antes) * 100;
  }

  /* Los códigos a pintar salen de la fuente del indicador: la renta y el paro
     no tienen por qué cubrir exactamente los mismos municipios. */
  function codigosDelIndicador() {
    if (estado.indicador === 'renta' && renta) return Object.keys(renta.municipios);
    return Object.keys(paro.municipios);
  }

  function valoresActuales() {
    var mapa = {};
    codigosDelIndicador().forEach(function (codigo) {
      var valor = valorDe(codigo, estado.periodo);
      if (valor !== null) mapa[codigo] = valor;
    });
    return mapa;
  }

  function nombreDe(codigo) {
    return (paro.municipios[codigo] || {}).nombre ||
           ((poblacion && poblacion.municipios[codigo]) || {}).nombre ||
           ((renta && renta.municipios[codigo]) || {}).nombre || codigo;
  }

  /* El periodo al que corresponde de verdad lo que se está pintando. */
  function periodoDelIndicador() {
    if (estado.indicador !== 'renta') return P.etiquetaPeriodo(estado.periodo);
    var alguno = codigosDelIndicador()
      .map(function (codigo) { return rentaDe(codigo, estado.periodo); })
      .filter(Boolean)[0];
    return alguno ? alguno.anyo : 'sin dato';
  }

  function textoDe(codigo) {
    var meta = INDICADORES[estado.indicador];
    var valor = valorDe(codigo, estado.periodo);
    if (valor === null) return 'sin dato';
    var texto = P.conUnidad(valor, meta.unidad, meta.decimales);
    if (estado.indicador === 'renta') {
      var dato = rentaDe(codigo, estado.periodo);
      return texto + (dato ? ' · ' + dato.anyo : '');
    }
    if (estado.indicador !== 'paro') {
      var parados = paroDe(codigo, estado.periodo);
      if (parados !== null) texto += ' · ' + P.formatea(parados, 0) + ' parados';
    }
    return texto;
  }

  /* ---------------------------------------------------------------- mapa */

  function pintaMapa() {
    var meta = INDICADORES[estado.indicador];
    P.dibujaMapa(document.querySelector('[data-mapa]'), geo, {
      valores: valoresActuales(),
      etiqueta: textoDe,
      titulo: meta.titulo + ' por municipio, ' + periodoDelIndicador(),
      tipo: meta.tipo,
      rango: function (desde, hasta) {
        var f = function (v) { return P.formatea(v, meta.decimales); };
        if (desde === null) return 'menos de ' + f(hasta);
        if (hasta === null) return f(desde) + ' o más';
        return f(desde) + ' – ' + f(hasta);
      },
      alSeleccionar: function (codigo) {
        estado.municipio = codigo;
        pintaFicha();
        document.querySelector('[data-ficha]').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });

    document.querySelector('[data-explicacion]').textContent = meta.explicacion;
  }

  /* -------------------------------------------------------------- ranking */

  function pintaRanking() {
    var meta = INDICADORES[estado.indicador];
    var cuerpo = document.querySelector('[data-ranking]');
    cuerpo.replaceChildren();

    var filas = codigosDelIndicador().map(function (codigo) {
      return { codigo: codigo, nombre: nombreDe(codigo), valor: valorDe(codigo, estado.periodo) };
    }).filter(function (f) { return f.valor !== null; })
      .sort(function (a, b) { return b.valor - a.valor; });

    filas.forEach(function (fila, posicion) {
      var tr = document.createElement('tr');
      tr.style.borderTop = '1px solid ' + P.color('--borde');

      var orden = document.createElement('td');
      orden.className = 'px-3 py-1.5 text-right';
      orden.style.color = P.color('--tinta-tenue');
      orden.textContent = String(posicion + 1);
      tr.appendChild(orden);

      var nombre = document.createElement('th');
      nombre.scope = 'row';
      nombre.className = 'px-3 py-1.5 text-left font-normal';
      var boton = document.createElement('button');
      boton.type = 'button';
      boton.className = 'enlace-sutil';
      boton.textContent = fila.nombre;
      boton.addEventListener('click', function () {
        estado.municipio = fila.codigo;
        pintaFicha();
      });
      nombre.appendChild(boton);
      tr.appendChild(nombre);

      var valor = document.createElement('td');
      valor.className = 'px-3 py-1.5 text-right whitespace-nowrap';
      valor.style.fontVariantNumeric = 'tabular-nums';
      valor.textContent = P.conUnidad(fila.valor, meta.unidad, meta.decimales);
      tr.appendChild(valor);

      var tamanyo = document.createElement('td');
      tamanyo.className = 'px-3 py-1.5 text-right text-xs';
      tamanyo.style.color = P.color('--tinta-tenue');
      tamanyo.style.fontVariantNumeric = 'tabular-nums';
      var parados = paroDe(fila.codigo, estado.periodo);
      tamanyo.textContent = parados === null ? '' : P.formatea(parados, 0);
      tr.appendChild(tamanyo);

      cuerpo.appendChild(tr);
    });
  }

  /* ---------------------------------------------------------------- ficha */

  function pintaFicha() {
    var caja = document.querySelector('[data-ficha]');
    caja.hidden = false;
    var codigo = estado.municipio;
    if (!codigo) {
      caja.hidden = true;
      return;
    }

    document.querySelector('[data-ficha-nombre]').textContent = nombreDe(codigo);

    var resumen = document.querySelector('[data-ficha-datos]');
    resumen.replaceChildren();
    var media = mediaAnual(codigo, estado.periodo);
    var mediaPrevia = mediaAnual(codigo, haceUnAnyo(estado.periodo));
    var parados = paroDe(codigo, estado.periodo);
    var habitantes = poblacionDe(codigo, estado.periodo);
    var porPersona = rentaDe(codigo, estado.periodo, 'renta_persona');
    var porHogar = rentaDe(codigo, estado.periodo, 'renta_hogar');
    [['Paro registrado', parados, 'personas', 0],
     ['Habitantes', habitantes, 'personas', 0],
     ['Paro por 100 hab.', parados !== null && habitantes ? (parados / habitantes) * 100 : null, '%', 1],
     ['Media de 12 meses', media, 'personas', 0],
     ['Variación en un año',
      media !== null && mediaPrevia ? ((media - mediaPrevia) / mediaPrevia) * 100 : null, '%', 1],
     // La renta lleva el año en la etiqueta: no es del mes que se está viendo.
     ['Renta por persona' + (porPersona ? ' (' + porPersona.anyo + ')' : ''),
      porPersona ? porPersona.valor : null, 'euros', 0],
     ['Renta por hogar' + (porHogar ? ' (' + porHogar.anyo + ')' : ''),
      porHogar ? porHogar.valor : null, 'euros', 0]
    ].forEach(function (dato) {
      var item = document.createElement('div');
      var etiqueta = document.createElement('div');
      etiqueta.className = 'text-xs';
      etiqueta.style.color = P.color('--tinta-tenue');
      etiqueta.textContent = dato[0];
      item.appendChild(etiqueta);
      var valor = document.createElement('div');
      valor.className = 'text-lg font-semibold';
      valor.style.fontVariantNumeric = 'tabular-nums';
      valor.textContent = P.conUnidad(dato[1], dato[2], dato[3]);
      item.appendChild(valor);
      resumen.appendChild(item);
    });

    var serie = {
      etiqueta: nombreDe(codigo),
      color: P.color('--serie-3'),
      valores: paro.periodos.map(function (p) { return paroDe(codigo, p); })
    };
    P.dibuja(document.querySelector('[data-ficha-grafica]'), 'ficha',
             paro.periodos, [serie], 'personas', 0);
    P.pintaTabla(document.querySelector('[data-ficha-tabla]'), paro.periodos, [serie],
                 'Paro registrado en ' + nombreDe(codigo), 'personas', 0);
  }

  /* ----------------------------------------------------------- controles */

  function conectaControles() {
    document.querySelector('[data-grupo="indicador"]').addEventListener('click', function (evento) {
      var boton = evento.target.closest('button[data-valor]');
      if (!boton) return;
      this.querySelectorAll('button').forEach(function (b) {
        b.setAttribute('aria-pressed', String(b === boton));
      });
      estado.indicador = boton.dataset.valor;
      render();
    });

    var selector = document.querySelector('[data-periodo]');
    paro.periodos.slice().reverse().forEach(function (periodo) {
      var opcion = document.createElement('option');
      opcion.value = periodo;
      opcion.textContent = P.etiquetaPeriodo(periodo);
      selector.appendChild(opcion);
    });
    selector.value = estado.periodo;
    selector.addEventListener('change', function () {
      estado.periodo = selector.value;
      render();
    });
  }

  function render() {
    pintaMapa();
    pintaRanking();
    if (estado.municipio) pintaFicha();
    // El rótulo del mapa lleva el periodo del dato, no el del selector: la
    // renta es de hace dos años aunque se esté mirando el mes de este verano.
    document.querySelector('[data-mes-actual]').textContent = periodoDelIndicador();
  }

  async function carga(ruta) {
    var respuesta = await fetch(ruta, { cache: 'no-cache' });
    if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status + ' en ' + ruta);
    return respuesta.json();
  }

  async function arranca() {
    var estadoNodo = document.querySelector('[data-estado]');
    try {
      geo = await carga('data/geo/municipios-castellon.geojson');
      paro = await carga('data/paro-registrado/municipios-castellon.json');
      try {
        poblacion = await carga('data/municipios/poblacion-castellon.json');
      } catch (_) {
        // Sin población no hay tasa, pero el resto del mapa sigue sirviendo.
        poblacion = null;
        var boton = document.querySelector('button[data-valor="tasa"]');
        if (boton) boton.disabled = true;
      }
      try {
        renta = await carga('data/municipios/renta-castellon.json');
      } catch (_) {
        renta = null;
        var botonRenta = document.querySelector('button[data-valor="renta"]');
        if (botonRenta) botonRenta.disabled = true;
      }

      estado.periodo = paro.periodos[paro.periodos.length - 1];
      estadoNodo.hidden = true;
      document.querySelector('[data-panel]').hidden = false;

      conectaControles();
      render();
      document.addEventListener('tema:cambio', render);
    } catch (error) {
      estadoNodo.textContent = 'No se han podido cargar los datos (' + error.message + ').';
      estadoNodo.style.color = P.color('--tinta');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
