/* Buscador de indicadores y registro de novedades.
 *
 * Con setenta y tantos indicadores repartidos en nueve secciones, la pregunta
 * «¿tenéis el dato de X?» ya no se responde mirando la portada. Las dos páginas
 * leen ficheros que compone la propia tarea de actualización, así que lo que
 * sale aquí es exactamente lo que hay publicado, no una lista escrita a mano
 * que se quede vieja. */
(function () {
  'use strict';

  function color(variable) {
    return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
  }

  /* Sin acentos y en minúsculas: quien busca «brecha salarial» no debería
     tener que acordarse de las tildes. */
  function normaliza(texto) {
    return (texto || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  function etiquetaPeriodo(periodo) {
    var meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
                 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    var m = /^(\d{4})(?:([TSM])(\d{1,2}))?$/.exec(periodo || '');
    if (!m) return periodo || '';
    if (!m[2]) return m[1];
    if (m[2] === 'M') return meses[parseInt(m[3], 10) - 1] + ' ' + m[1];
    return parseInt(m[3], 10) + (m[2] === 'T' ? 'T ' : 'S ') + m[1];
  }

  var AMBITOS = {
    espana: { etiqueta: 'España', variable: '--serie-1' },
    'comunitat-valenciana': { etiqueta: 'C. Valenciana', variable: '--serie-2' },
    castellon: { etiqueta: 'Castellón', variable: '--serie-3' }
  };

  function marcaAmbito(id) {
    var ambito = AMBITOS[id];
    var caja = document.createElement('span');
    caja.className = 'inline-flex items-center gap-1 text-xs';
    caja.style.color = color('--tinta-tenue');
    var marca = document.createElement('span');
    marca.setAttribute('aria-hidden', 'true');
    marca.style.cssText = 'display:inline-block;width:.5rem;height:.5rem;border-radius:2px;';
    marca.style.background = color(ambito ? ambito.variable : '--serie-1');
    caja.appendChild(marca);
    caja.appendChild(document.createTextNode(ambito ? ambito.etiqueta : id));
    return caja;
  }

  function ficha(indicador) {
    var caja = document.createElement('li');
    caja.className = 'tarjeta p-4';

    var titulo = document.createElement('h3');
    titulo.className = 'font-semibold tracking-tight';
    var enlace = document.createElement('a');
    enlace.className = 'enlace-sutil';
    enlace.href = indicador.enlace || './';
    enlace.textContent = indicador.titulo;
    titulo.appendChild(enlace);
    caja.appendChild(titulo);

    var seccion = document.createElement('p');
    seccion.className = 'mt-0.5 text-xs';
    seccion.style.color = color('--tinta-tenue');
    seccion.textContent = indicador.seccion + (indicador.fuente ? ' · ' + indicador.fuente : '');
    caja.appendChild(seccion);

    if (indicador.unidad_texto || indicador.unidad) {
      var unidad = document.createElement('p');
      unidad.className = 'mt-2 text-sm';
      unidad.style.color = color('--tinta-suave');
      unidad.textContent = indicador.unidad_texto || indicador.unidad;
      caja.appendChild(unidad);
    }

    var pie = document.createElement('div');
    pie.className = 'mt-3 flex flex-wrap items-center gap-x-3 gap-y-1';
    indicador.ambitos.forEach(function (id) { pie.appendChild(marcaAmbito(id)); });
    var rango = document.createElement('span');
    rango.className = 'text-xs';
    rango.style.color = color('--tinta-tenue');
    rango.textContent = etiquetaPeriodo(indicador.desde) + ' – ' + etiquetaPeriodo(indicador.hasta);
    pie.appendChild(rango);
    if (indicador.por_sexo) {
      var sexo = document.createElement('span');
      sexo.className = 'text-xs';
      sexo.style.color = color('--tinta-tenue');
      sexo.textContent = 'con desglose por sexo';
      pie.appendChild(sexo);
    }
    caja.appendChild(pie);

    // Las advertencias del indicador viajan con él: si un dato no existe por
    // provincia, quien lo encuentre aquí tiene que enterarse aquí.
    if (indicador.nota) {
      var nota = document.createElement('p');
      nota.className = 'mt-2 text-xs leading-relaxed';
      nota.style.color = color('--tinta-suave');
      nota.textContent = indicador.nota;
      caja.appendChild(nota);
    }
    return caja;
  }

  function arrancaBuscador(catalogo) {
    var lista = document.querySelector('[data-resultados]');
    var caja = document.querySelector('[data-busqueda]');
    var cuenta = document.querySelector('[data-cuenta]');
    var soloProvincia = document.querySelector('[data-solo-provincia]');
    if (!lista) return;

    var indicadores = catalogo.indicadores.map(function (i) {
      return Object.assign({}, i, {
        buscable: normaliza([i.titulo, i.seccion, i.unidad, i.unidad_texto,
                             i.nota, i.clave].join(' '))
      });
    });

    function pinta() {
      var texto = normaliza(caja ? caja.value : '').trim();
      var palabras = texto ? texto.split(/\s+/) : [];
      var visibles = indicadores.filter(function (i) {
        if (soloProvincia && soloProvincia.checked && i.ambitos.indexOf('castellon') < 0) {
          return false;
        }
        return palabras.every(function (p) { return i.buscable.indexOf(p) >= 0; });
      });

      lista.replaceChildren();
      visibles.forEach(function (i) { lista.appendChild(ficha(i)); });
      if (cuenta) {
        cuenta.textContent = visibles.length === indicadores.length
          ? indicadores.length + ' indicadores publicados'
          : visibles.length + ' de ' + indicadores.length + ' indicadores';
      }
      if (!visibles.length) {
        var vacio = document.createElement('li');
        vacio.className = 'text-sm sm:col-span-2';
        vacio.style.color = color('--tinta-suave');
        vacio.textContent = 'Nada con «' + (caja ? caja.value : '') + '». ' +
          'Puede que la fuente no lo publique con ese detalle; en Fuentes y ' +
          'calendario está lo que hay y lo que no.';
        lista.appendChild(vacio);
      }
    }

    if (caja) caja.addEventListener('input', pinta);
    if (soloProvincia) soloProvincia.addEventListener('change', pinta);
    document.addEventListener('tema:cambio', pinta);
    pinta();
  }

  function arrancaNovedades(datos) {
    var lista = document.querySelector('[data-novedades]');
    if (!lista) return;
    lista.replaceChildren();

    datos.novedades.forEach(function (novedad) {
      var fila = document.createElement('li');
      fila.className = 'tarjeta p-4';

      var cabecera = document.createElement('div');
      cabecera.className = 'flex flex-wrap items-baseline justify-between gap-2';
      var asunto = document.createElement('p');
      asunto.className = 'font-medium';
      asunto.textContent = novedad.asunto.replace(/ \[skip ci\]$/, '');
      cabecera.appendChild(asunto);
      var fecha = document.createElement('a');
      fecha.className = 'enlace-sutil text-xs whitespace-nowrap';
      fecha.href = datos.repositorio + '/commit/' + novedad.commit;
      fecha.rel = 'noopener';
      fecha.textContent = new Date(novedad.fecha).toLocaleDateString('es-ES', {
        day: 'numeric', month: 'long', year: 'numeric'
      });
      cabecera.appendChild(fecha);
      fila.appendChild(cabecera);

      var secciones = document.createElement('p');
      secciones.className = 'mt-1 text-xs';
      secciones.style.color = color('--tinta-tenue');
      secciones.textContent = novedad.secciones.map(function (s) {
        return s.titulo;
      }).join(' · ');
      fila.appendChild(secciones);

      lista.appendChild(fila);
    });
  }

  async function carga(ruta) {
    var respuesta = await fetch(ruta, { cache: 'no-cache' });
    if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
    return respuesta.json();
  }

  async function arranca() {
    var aviso = document.querySelector('[data-estado]');
    try {
      if (document.querySelector('[data-resultados]')) {
        arrancaBuscador(await carga('data/indicadores.json'));
      }
      if (document.querySelector('[data-novedades]')) {
        arrancaNovedades(await carga('data/novedades.json'));
      }
      if (aviso) aviso.hidden = true;
    } catch (error) {
      if (aviso) aviso.textContent = 'No se ha podido cargar (' + error.message + ').';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
