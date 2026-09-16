/* Página genérica de un bloque de datos (población, demografía, renta).
 *
 * Toda la configuración viene del índice del propio bloque: qué indicadores
 * hay, cómo se llaman, en qué unidad van y si se desglosan por sexo. Así las
 * tres páginas comparten este archivo y sólo cambian su `data-bloque`. */
(function () {
  'use strict';

  var P = window.Panel;
  var bloque = document.body.dataset.bloque;
  var RUTA = 'data/' + bloque + '/';

  var estado = {
    periodo: 'todo', sexo: 'ambos', euros: 'corrientes',
    ambitos: new Set(P.AMBITOS.map(function (a) { return a.id; }))
  };
  var indice = null;
  var datos = {};

  function ambitosActivos() {
    return P.AMBITOS.filter(function (a) { return estado.ambitos.has(a.id) && datos[a.id]; });
  }

  function periodosVisibles() {
    var todos = (datos[P.AMBITOS[0].id] || {}).periodos || [];
    if (estado.periodo === 'todo') return todos;
    var limite = parseInt(estado.periodo, 10);
    var ultimo = P.ordenPeriodo(todos[todos.length - 1])[0];
    return todos.filter(function (p) { return P.ordenPeriodo(p)[0] > ultimo - limite; });
  }

  /* Valores de un indicador para un ámbito, alineados a los periodos pedidos.
     Si el indicador no se desglosa por sexo, siempre va por «ambos». */
  function serie(ambitoId, clave, periodos) {
    var contenido = datos[ambitoId];
    if (!contenido) return periodos.map(function () { return null; });
    var porSexo = indice.indicadores[clave].por_sexo;
    var bloqueSexo = contenido.series[porSexo ? estado.sexo : 'ambos'] || {};
    var valores = bloqueSexo[clave];
    if (!valores) return periodos.map(function () { return null; });
    var posicion = new Map(contenido.periodos.map(function (p, i) { return [p, i]; }));
    return periodos.map(function (p) {
      var i = posicion.get(p);
      var v = i === undefined ? null : valores[i];
      return v === undefined ? null : v;
    });
  }

  /* Algunos indicadores tienen gemelo en euros constantes. El conmutador no
     añade gráficas: sustituye cada serie nominal por su versión deflactada. */
  function indicadoresVisibles() {
    var todos = Object.keys(indice.indicadores);
    var reales = {};
    todos.forEach(function (clave) {
      var nominal = indice.indicadores[clave].nominal;
      if (nominal) reales[nominal] = clave;
    });
    return todos.filter(function (clave) {
      return !indice.indicadores[clave].nominal;
    }).map(function (clave) {
      return estado.euros === 'constantes' && reales[clave] ? reales[clave] : clave;
    });
  }

  function hayEurosConstantes() {
    return Object.keys(indice.indicadores).some(function (k) {
      return indice.indicadores[k].nominal;
    });
  }

  /* Los desgloses se publican en personas, pero comparar 20.000 parados en
     servicios de Castellón con 1,6 millones en España no dice nada: lo que se
     compara es el peso de cada uno sobre su total. El dato guardado sigue
     siendo el absoluto; esto es sólo cómo se presenta. */
  function serieRelativa(ambitoId, clave, periodos) {
    var meta = indice.indicadores[clave];
    var valores = serie(ambitoId, clave, periodos);
    if (!meta.sobre_total) return valores;
    var totales = serie(ambitoId, meta.sobre_total, periodos);
    return valores.map(function (v, i) {
      if (v === null || !totales[i]) return null;
      return (v / totales[i]) * 100;
    });
  }

  function unidadDe(meta) {
    return meta.sobre_total ? '%' : meta.unidad;
  }

  function decimalesDe(meta) {
    return meta.sobre_total ? 1 : meta.decimales;
  }

  function ultimoConDato(valores, periodos) {
    for (var i = valores.length - 1; i >= 0; i--) {
      if (valores[i] !== null) return { valor: valores[i], periodo: periodos[i], indice: i };
    }
    return null;
  }

  /* Un bloque puede mezclar frecuencias: las compraventas son mensuales, las
     ejecuciones trimestrales y el precio del alquiler anual. El eje común de
     la página los reúne todos, así que cada gráfica se queda con los periodos
     en los que su indicador tiene dato y no con el calendario de los demás. */
  function periodosDe(clave, periodos) {
    var activos = ambitosActivos();
    var series = activos.map(function (a) { return serie(a.id, clave, periodos); });
    var propios = periodos.filter(function (_, i) {
      return series.some(function (valores) { return valores[i] !== null; });
    });
    return propios.length ? propios : periodos;
  }

  /* Dos ámbitos son comparables en una misma gráfica cuando sus magnitudes
     tienen el mismo orden: si España multiplica por diez a Castellón, la línea
     pequeña queda aplastada contra el eje y hay que separar los paneles. */
  function escalasComparables(clave, periodos) {
    var maximos = ambitosActivos().map(function (a) {
      var valores = serieRelativa(a.id, clave, periodos).filter(function (v) { return v !== null; });
      return valores.length ? Math.max.apply(null, valores.map(Math.abs)) : 0;
    }).filter(function (v) { return v > 0; });
    if (maximos.length < 2) return true;
    return Math.max.apply(null, maximos) / Math.min.apply(null, maximos) < 5;
  }

  /* ------------------------------------------------------------- resumen */

  function pintaResumen(periodos) {
    var cuerpo = document.querySelector('[data-resumen]');
    cuerpo.replaceChildren();
    var activos = ambitosActivos();

    var cabecera = document.querySelector('[data-resumen-cabecera]');
    cabecera.replaceChildren();
    var thIndicador = document.createElement('th');
    thIndicador.scope = 'col';
    thIndicador.className = 'px-4 py-2.5 font-medium text-left';
    thIndicador.textContent = 'Indicador';
    cabecera.appendChild(thIndicador);
    activos.forEach(function (a) {
      var th = document.createElement('th');
      th.scope = 'col';
      th.className = 'px-4 py-2.5 font-medium text-right';
      var marca = document.createElement('span');
      marca.setAttribute('aria-hidden', 'true');
      marca.style.cssText = 'display:inline-block;width:.6rem;height:.6rem;border-radius:2px;margin-right:.4rem;';
      marca.style.background = P.color(a.variable);
      th.appendChild(marca);
      th.appendChild(document.createTextNode(a.etiqueta));
      cabecera.appendChild(th);
    });

    indicadoresVisibles().forEach(function (clave) {
      var meta = indice.indicadores[clave];
      var fila = document.createElement('tr');
      fila.style.borderTop = '1px solid ' + P.color('--borde');

      var th = document.createElement('th');
      th.scope = 'row';
      th.className = 'px-4 py-2.5 text-left font-medium';
      th.textContent = meta.titulo;
      fila.appendChild(th);

      var algunDato = false;
      activos.forEach(function (a) {
        var td = document.createElement('td');
        td.className = 'px-4 py-2.5 text-right';
        var ultimo = ultimoConDato(serie(a.id, clave, periodos), periodos);
        if (!ultimo) {
          td.textContent = '—';
          td.style.color = P.color('--tinta-tenue');
        } else {
          algunDato = true;
          var valor = document.createElement('div');
          valor.style.cssText = 'font-weight:600;font-variant-numeric:tabular-nums;';
          valor.textContent = P.conUnidad(ultimo.valor, meta.unidad, meta.decimales);
          td.appendChild(valor);
          var cuando = document.createElement('div');
          cuando.style.cssText = 'font-size:.75rem;margin-top:.1rem;';
          cuando.style.color = P.color('--tinta-tenue');
          var peso = '';
          if (meta.sobre_total) {
            var relativo = ultimoConDato(serieRelativa(a.id, clave, periodos), periodos);
            if (relativo) peso = P.formatea(relativo.valor, 1) + ' % · ';
          }
          cuando.textContent = peso + P.etiquetaPeriodo(ultimo.periodo);
          td.appendChild(cuando);
        }
        fila.appendChild(td);
      });

      if (algunDato) cuerpo.appendChild(fila);
    });
  }

  /* ------------------------------------------------------------ gráficas */

  function tarjeta(titulo, subtitulo, nota) {
    var figura = document.createElement('figure');
    figura.className = 'tarjeta p-5 m-0';

    var pie = document.createElement('figcaption');
    var h = document.createElement('h3');
    h.className = 'font-semibold tracking-tight';
    h.textContent = titulo;
    pie.appendChild(h);
    var p = document.createElement('p');
    p.className = 'mt-0.5 text-xs';
    p.style.color = P.color('--tinta-tenue');
    p.textContent = subtitulo;
    pie.appendChild(p);
    // Lo que hay que saber para no leer mal la cifra -que el INE no publique
    // el índice por provincia, que la hipoteca media no sea el precio- va
    // pegado a la gráfica, no en una nota al pie de la página.
    if (nota) {
      var aclaracion = document.createElement('p');
      aclaracion.className = 'mt-1.5 text-xs leading-relaxed';
      aclaracion.style.color = P.color('--tinta-suave');
      aclaracion.textContent = nota;
      pie.appendChild(aclaracion);
    }
    figura.appendChild(pie);

    return figura;
  }

  function lienzo(figura, alto, etiqueta) {
    var caja = document.createElement('div');
    caja.className = 'mt-4 relative';
    caja.style.height = alto;
    var canvas = document.createElement('canvas');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', etiqueta);
    caja.appendChild(canvas);
    figura.appendChild(caja);
    return canvas;
  }

  function detallesTabla(figura, periodos, series, meta) {
    var detalles = document.createElement('details');
    detalles.className = 'mt-3 text-xs';
    var resumen = document.createElement('summary');
    resumen.className = 'cursor-pointer';
    resumen.style.color = P.color('--tinta-suave');
    resumen.textContent = 'Ver tabla de datos';
    detalles.appendChild(resumen);
    var caja = document.createElement('div');
    caja.className = 'mt-2 max-h-72 overflow-auto';
    detalles.appendChild(caja);
    figura.appendChild(detalles);
    P.pintaTabla(caja, periodos, series, meta.titulo, unidadDe(meta), decimalesDe(meta));
  }

  /* Cada indicador puede traer su propia leyenda de unidad: «por mil» no
     significa lo mismo en un saldo migratorio que en los nacidos por cada mil
     defunciones. */
  function unidadLegible(meta) {
    if (meta.sobre_total) {
      var total = indice.indicadores[meta.sobre_total];
      return 'porcentaje del total' + (total ? ' de ' + total.titulo.toLowerCase() : '');
    }
    if (meta.unidad_texto) return meta.unidad_texto;
    if (meta.unidad === '%') return 'porcentaje';
    if (meta.unidad === 'por mil') return 'por cada mil habitantes';
    if (meta.unidad === 'euros') return 'euros al año';
    return meta.unidad;
  }

  function pintaIndicadores(periodos) {
    var contenedor = document.querySelector('[data-graficas]');
    contenedor.replaceChildren();
    P.destruyeTodas();

    var activos = ambitosActivos();

    indicadoresVisibles().forEach(function (clave) {
      var meta = indice.indicadores[clave];
      var conDatos = activos.filter(function (a) {
        return serie(a.id, clave, periodos).some(function (v) { return v !== null; });
      });
      if (!conDatos.length) return;
      var propios = periodosDe(clave, periodos);

      if (escalasComparables(clave, propios)) {
        var figura = tarjeta(meta.titulo, unidadLegible(meta), meta.nota);
        var canvas = lienzo(figura, '280px', 'Evolución de ' + meta.titulo + ' por ámbito territorial');
        var series = conDatos.map(function (a) {
          return { etiqueta: a.etiqueta, color: P.color(a.variable),
                   valores: serieRelativa(a.id, clave, propios) };
        });
        var leyenda = document.createElement('div');
        leyenda.className = 'mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs';
        figura.appendChild(leyenda);
        contenedor.appendChild(figura);
        P.dibuja(canvas, clave, propios, series, unidadDe(meta), decimalesDe(meta));
        if (series.length > 1) P.pintaLeyenda(leyenda, series);
        detallesTabla(figura, propios, series, meta);
        return;
      }

      // Escalas dispares: un panel por ámbito, cada uno con su eje.
      var envoltorio = document.createElement('div');
      envoltorio.className = 'sm:col-span-2';
      var titulo = document.createElement('h3');
      titulo.className = 'text-sm font-semibold uppercase tracking-widest mb-3';
      titulo.style.color = P.color('--tinta-tenue');
      titulo.textContent = meta.titulo + ' · ' + unidadLegible(meta);
      envoltorio.appendChild(titulo);
      var rejilla = document.createElement('div');
      rejilla.className = 'grid gap-5 lg:grid-cols-' + Math.min(3, conDatos.length);
      envoltorio.appendChild(rejilla);

      conDatos.forEach(function (a) {
        var figura = tarjeta(a.etiqueta, meta.titulo + ', ' + unidadLegible(meta), meta.nota);
        var canvas = lienzo(figura, '220px', meta.titulo + ' en ' + a.etiqueta);
        var series = [{ etiqueta: a.etiqueta, color: P.color(a.variable),
                        valores: serieRelativa(a.id, clave, propios) }];
        rejilla.appendChild(figura);
        P.dibuja(canvas, clave + '-' + a.id, propios, series, unidadDe(meta), decimalesDe(meta));
        detallesTabla(figura, propios, series, meta);
      });

      contenedor.appendChild(envoltorio);
    });
  }

  function render() {
    var periodos = periodosVisibles();
    pintaResumen(periodos);
    pintaIndicadores(periodos);
  }

  /* ----------------------------------------------------------- controles */

  function conectaSegmentos() {
    document.querySelectorAll('[data-grupo]').forEach(function (grupo) {
      var clave = grupo.dataset.grupo;
      if (clave === 'ambitos') return;
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
  }

  function conectaAmbitos() {
    var contenedor = document.querySelector('[data-grupo="ambitos"]');
    P.AMBITOS.forEach(function (ambito) {
      var etiqueta = document.createElement('label');
      etiqueta.className = 'inline-flex items-center gap-2 text-sm cursor-pointer';

      var casilla = document.createElement('input');
      casilla.type = 'checkbox';
      casilla.checked = true;
      casilla.className = 'h-4 w-4 rounded';
      casilla.style.accentColor = P.color(ambito.variable);
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

      var marca = document.createElement('span');
      marca.setAttribute('aria-hidden', 'true');
      marca.style.cssText = 'display:inline-block;width:1rem;height:2px;border-radius:1px;';
      marca.style.background = P.color(ambito.variable);
      etiqueta.appendChild(marca);

      var texto = document.createElement('span');
      texto.textContent = ambito.etiqueta;
      etiqueta.appendChild(texto);

      contenedor.appendChild(etiqueta);
    });
  }

  function descarga() {
    var periodos = periodosVisibles();
    var columnas = [];
    ambitosActivos().forEach(function (a) {
      indicadoresVisibles().forEach(function (clave) {
        columnas.push({ clave: a.id + '_' + clave, valores: serie(a.id, clave, periodos) });
      });
    });
    P.descargaCsv(bloque + '-' + periodos[0] + '-' + periodos[periodos.length - 1] + '.csv',
                  periodos, columnas);
  }

  /* ------------------------------------------------------------ arranque */

  async function arranca() {
    var estadoNodo = document.querySelector('[data-estado]');
    try {
      indice = await fetch(RUTA + 'index.json', { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      });

      await Promise.all(indice.ambitos.map(async function (a) {
        var respuesta = await fetch(RUTA + a.fichero, { cache: 'no-cache' });
        if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status + ' en ' + a.fichero);
        datos[a.id] = await respuesta.json();
      }));

      estadoNodo.hidden = true;
      document.querySelector('[data-panel]').hidden = false;

      // El desglose por sexo sólo se ofrece si algún indicador lo tiene.
      var hayPorSexo = Object.keys(indice.indicadores).some(function (k) {
        return indice.indicadores[k].por_sexo;
      });
      var filtroSexo = document.querySelector('[data-filtro-sexo]');
      if (filtroSexo && !hayPorSexo) filtroSexo.hidden = true;

      var filtroEuros = document.querySelector('[data-filtro-euros]');
      if (filtroEuros && hayEurosConstantes()) filtroEuros.hidden = false;

      var fecha = new Date(indice.actualizado);
      var nodoFecha = document.querySelector('[data-actualizado]');
      if (nodoFecha) {
        nodoFecha.textContent = Number.isNaN(fecha.getTime())
          ? indice.actualizado
          : fecha.toLocaleString('es-ES', { dateStyle: 'long', timeStyle: 'short' });
      }

      conectaSegmentos();
      conectaAmbitos();
      var botonCsv = document.querySelector('[data-csv]');
      if (botonCsv) botonCsv.addEventListener('click', descarga);

      render();
      document.addEventListener('tema:cambio', render);
    } catch (error) {
      estadoNodo.textContent = 'No se han podido cargar los datos (' + error.message + '). ' +
        'Si acabas de publicar el panel, puede que la tarea de actualización todavía no haya corrido.';
      estadoNodo.style.color = P.color('--tinta');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
