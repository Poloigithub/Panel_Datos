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
  var salarios = null;   // el bloque de salarios, para el cruce
  var convenios = null;  // y el de convenios, que llega mucho más lejos
  var salarioIndice = null;

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

  /* --------------------------------------------------- la comida y el salario */

  /* Media de los meses de cada año. Con menos de diez meses el año no cuenta:
     comparar un año entero con los ocho primeros meses del siguiente movería
     la cifra sin que hubiera subido nada. */
  function mediaAnual(puntos) {
    var porAnyo = {};
    puntos.forEach(function (p) {
      var anyo = p.periodo.slice(0, 4);
      (porAnyo[anyo] = porAnyo[anyo] || []).push(p.valor);
    });
    var medias = {};
    Object.keys(porAnyo).forEach(function (anyo) {
      if (porAnyo[anyo].length >= 10) {
        medias[anyo] = porAnyo[anyo].reduce(function (a, b) { return a + b; }, 0) /
          porAnyo[anyo].length;
      }
    });
    return medias;
  }

  function serieSalario() {
    if (!salarios || !salarios[estado.ambito]) return {};
    var contenido = salarios[estado.ambito];
    var valores = (contenido.series.ambos || {}).salario_bruto;
    if (!valores) return {};
    var anual = {};
    contenido.periodos.forEach(function (periodo, i) {
      if (valores[i] !== null && valores[i] !== undefined && /^\d{4}$/.test(periodo)) {
        anual[periodo] = valores[i];
      }
    });
    return anual;
  }

  /* Lo pactado en convenio, encadenado año a año.
   *
   * Los convenios no dan un nivel sino una subida: «este año se ha pactado un
   * 3,04 %». Para poder ponerlo junto a un índice de precios hay que encadenar
   * las subidas, que es lo que hace de verdad un salario de convenio: cada año
   * sube sobre lo que ya había.
   *
   * De cada año se coge su último mes publicado, porque la cifra es acumulada
   * dentro del año y el último mes es el año entero -o lo que va de él, en el
   * año en curso-.
   */
  function seriePactado() {
    if (!convenios || !convenios[estado.ambito]) return {};
    var contenido = convenios[estado.ambito];
    var valores = (contenido.series.ambos || {}).subida_pactada;
    if (!valores) return {};

    var ultimoDelAnyo = {};
    contenido.periodos.forEach(function (periodo, i) {
      if (valores[i] === null || valores[i] === undefined) return;
      var anyo = periodo.slice(0, 4);
      if (!ultimoDelAnyo[anyo] || periodo > ultimoDelAnyo[anyo].periodo) {
        ultimoDelAnyo[anyo] = { periodo: periodo, subida: valores[i] };
      }
    });

    var anyos = Object.keys(ultimoDelAnyo).sort();
    var indice = {};
    var acumulado = 100;
    anyos.forEach(function (anyo, i) {
      // El primer año es la base: su subida ya se dio antes de empezar a mirar.
      if (i > 0) acumulado *= 1 + ultimoDelAnyo[anyo].subida / 100;
      indice[anyo] = acumulado;
    });
    return indice;
  }

  /* Los tres en el mismo lenguaje: cuánto vale hoy lo que en el año de partida
     valía 100. Es la única forma honesta de comparar un índice de precios con
     unos euros al año. */
  function cruce() {
    var comida = mediaAnual(serie('alimentos'));
    var salario = serieSalario();
    var pactado = seriePactado();
    var comunes = Object.keys(comida).filter(function (a) { return salario[a]; }).sort();
    // De Castellón no hay salario, pero sí lo pactado en convenio. Antes aquí
    // no se enseñaba nada; ahora se enseña lo que hay, que es media respuesta y
    // media respuesta es mucho más que ninguna.
    var soloPactado = false;
    if (comunes.length < 2) {
      comunes = Object.keys(comida).filter(function (a) { return pactado[a]; }).sort();
      soloPactado = true;
      if (comunes.length < 2) return null;
    }

    var pedido = parseInt(estado.desde, 10);
    var ultimo = comunes[comunes.length - 1];
    var partida = pedido > 1000 ? String(pedido) : String(parseInt(ultimo, 10) - pedido);
    if (comunes.indexOf(partida) < 0) partida = comunes[0];

    // Lo pactado llega dos años más lejos que la encuesta salarial, así que el
    // eje se estira hasta donde llegue: es justo lo que aporta este dato.
    var hasta = Object.keys(comida).filter(function (a) {
      return a >= partida && (salario[a] || pactado[a]);
    }).sort();

    var datos = {
      anyos: hasta,
      partida: partida,
      ultimo: ultimo,
      comida: comida,
      salario: salario,
      pactado: pactado,
      soloPactado: soloPactado,
      subidaComida: (comida[ultimo] / comida[partida] - 1) * 100,
      subidaSalario: soloPactado ? null
        : (salario[ultimo] / salario[partida] - 1) * 100
    };

    // Y la lectura fresca: qué se está pactando ahora y qué ha hecho la comida
    // en ese mismo tramo, hasta donde llegan los dos.
    var ultimoPactado = hasta.filter(function (a) { return pactado[a]; }).pop();
    if (ultimoPactado && pactado[partida] && ultimoPactado !== partida) {
      datos.ultimoPactado = ultimoPactado;
      datos.subidaPactada = (pactado[ultimoPactado] / pactado[partida] - 1) * 100;
      datos.comidaHastaPactado = (comida[ultimoPactado] / comida[partida] - 1) * 100;
    }
    return datos;
  }

  function pintaCruce() {
    var caja = document.querySelector('[data-cruce]');
    var seccion = document.querySelector('[data-cruce-seccion]');
    if (!caja || !seccion) return;
    caja.replaceChildren();

    var datosCruce = cruce();
    var aviso = document.querySelector('[data-cruce-aviso]');
    if (!datosCruce) {
      seccion.hidden = false;
      if (aviso) {
        aviso.hidden = false;
        aviso.textContent = 'Faltan años en común entre los precios y lo que ' +
          'se cobra para poder comparar.';
      }
      return;
    }
    if (aviso) aviso.hidden = true;
    seccion.hidden = false;

    var frase = document.createElement('p');
    frase.className = 'text-lg font-semibold tracking-tight';
    if (datosCruce.soloPactado) {
      var hueco = datosCruce.comidaHastaPactado - datosCruce.subidaPactada;
      frase.textContent = 'Entre ' + datosCruce.partida + ' y ' +
        datosCruce.ultimoPactado + ', la comida subió un ' +
        porcentaje.format(datosCruce.comidaHastaPactado) +
        ' % y lo pactado en convenio un ' +
        porcentaje.format(datosCruce.subidaPactada) + ' %: ' +
        (hueco >= 0 ? 'la comida se llevó ' : 'el convenio ganó ') +
        porcentaje.format(Math.abs(hueco)) + ' puntos.';
      caja.appendChild(frase);
      var apunte = document.createElement('p');
      apunte.className = 'mt-2 text-sm leading-relaxed';
      apunte.style.color = P.color('--tinta-suave');
      apunte.textContent = 'De Castellón no hay salario medio -el INE no lo ' +
        'publica por provincia-, así que aquí la comparación se hace con lo ' +
        'que se firma en convenio, que sí tiene dato provincial. No es lo ' +
        'mismo: el convenio es el suelo, no lo que cada cual acaba cobrando.';
      caja.appendChild(apunte);
      pintaGrafica(caja, datosCruce);
      return;
    }
    var diferencia = datosCruce.subidaComida - datosCruce.subidaSalario;
    frase.textContent = 'Entre ' + datosCruce.partida + ' y ' + datosCruce.ultimo +
      ', la comida subió un ' + porcentaje.format(datosCruce.subidaComida) +
      ' % y el salario bruto medio un ' + porcentaje.format(datosCruce.subidaSalario) +
      ' %: ' + (diferencia >= 0 ? 'la comida se llevó ' : 'el salario ganó ') +
      porcentaje.format(Math.abs(diferencia)) + ' puntos ' +
      (diferencia >= 0 ? 'de ventaja.' : 'de margen.');
    caja.appendChild(frase);

    if (datosCruce.ultimoPactado) {
      var fresca = document.createElement('p');
      fresca.className = 'mt-2 text-sm leading-relaxed';
      fresca.style.color = P.color('--tinta-suave');
      var margen = datosCruce.comidaHastaPactado - datosCruce.subidaPactada;
      fresca.textContent = 'Y con el dato que llega antes: lo pactado en ' +
        'convenio acumula un ' + porcentaje.format(datosCruce.subidaPactada) +
        ' % desde ' + datosCruce.partida + ' hasta ' + datosCruce.ultimoPactado +
        ', mientras la comida subía un ' +
        porcentaje.format(datosCruce.comidaHastaPactado) + ' %. ' +
        (margen >= 0
          ? 'La comida sigue por delante, ' + porcentaje.format(margen) +
            ' puntos.'
          : 'Ahí lo pactado va por delante, ' +
            porcentaje.format(Math.abs(margen)) + ' puntos.');
      caja.appendChild(fresca);
    }

    pintaGrafica(caja, datosCruce);
  }

  function pintaGrafica(caja, datosCruce) {
    var figura = document.createElement('figure');
    figura.className = 'tarjeta p-5 m-0 mt-4';
    var pie = document.createElement('figcaption');
    var titulo = document.createElement('h3');
    titulo.className = 'font-semibold tracking-tight';
    titulo.textContent = 'Comida y salario, con ' + datosCruce.partida + ' = 100';
    pie.appendChild(titulo);
    var nota = document.createElement('p');
    nota.className = 'mt-0.5 text-xs';
    nota.style.color = P.color('--tinta-tenue');
    nota.textContent = 'Índice de alimentos, salario bruto medio anual y ' +
      'subida pactada en convenio encadenada, los tres a 100 en el año de ' +
      'partida';
    pie.appendChild(nota);
    figura.appendChild(pie);

    var lienzoCaja = document.createElement('div');
    lienzoCaja.className = 'mt-4 relative';
    lienzoCaja.style.height = '300px';
    var lienzo = document.createElement('canvas');
    lienzo.setAttribute('role', 'img');
    lienzo.setAttribute('aria-label',
      'Comparación entre la subida de los alimentos y la del salario');
    lienzoCaja.appendChild(lienzo);
    figura.appendChild(lienzoCaja);

    var leyenda = document.createElement('div');
    leyenda.className = 'mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs';
    figura.appendChild(leyenda);
    caja.appendChild(figura);

    var series = [
      { etiqueta: 'Comida', color: P.color('--serie-1'),
        valores: datosCruce.anyos.map(function (a) {
          return datosCruce.comida[a] / datosCruce.comida[datosCruce.partida] * 100;
        }) },
      { etiqueta: 'Salario bruto medio', color: P.color('--serie-2'),
        valores: datosCruce.anyos.map(function (a) {
          return datosCruce.salario[a]
            ? datosCruce.salario[a] / datosCruce.salario[datosCruce.partida] * 100
            : null;
        }) }
    ];
    if (datosCruce.pactado && datosCruce.pactado[datosCruce.partida]) {
      series.push({
        etiqueta: 'Pactado en convenio', color: P.color('--serie-3'),
        valores: datosCruce.anyos.map(function (a) {
          return datosCruce.pactado[a]
            ? datosCruce.pactado[a] / datosCruce.pactado[datosCruce.partida] * 100
            : null;
        })
      });
    }
    P.dibuja(lienzo, 'cruce', datosCruce.anyos, series, 'índice', 1);
    P.pintaLeyenda(leyenda, series);

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
    P.pintaTabla(tabla, datosCruce.anyos, series,
                 'Comida y salario con ' + datosCruce.partida + ' = 100', 'índice', 1);
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
    // El cruce va después de las evoluciones porque pintarlas destruye todas
    // las gráficas vivas, y la del cruce es una de ellas.
    pintaSeries(filas);
    pintaCruce();

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

      // Lo pactado en convenio llega dos años más lejos que la encuesta
      // salarial, que es precisamente lo que aporta.
      try {
        var indiceConvenios = await carga('data/convenios/index.json');
        convenios = {};
        for (const a of indiceConvenios.ambitos) {
          convenios[a.id] = await carga('data/convenios/' + a.fichero);
        }
      } catch (_) {
        convenios = null;
      }

      // El cruce con el salario es un extra: si no está, la página sigue.
      try {
        var indiceSalarios = await carga('data/salarios/index.json');
        salarios = {};
        await Promise.all(indiceSalarios.ambitos.map(async function (a) {
          salarios[a.id] = await carga('data/salarios/' + a.fichero);
        }));
      } catch (_) {
        salarios = null;
      }

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
