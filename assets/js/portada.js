/* Titulares de la portada: lo último de cada sección, sin entrar en ella.
 *
 * Lee `data/portada.json`, que compone el propio script de actualización. Se
 * genera allí y no aquí para que la portada no tenga que descargarse los datos
 * de las ocho secciones para enseñar ocho cifras. */
(function () {
  'use strict';

  var numero = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 2 });

  function formatea(valor, decimales) {
    if (valor === null || valor === undefined) return '—';
    return new Intl.NumberFormat('es-ES', {
      minimumFractionDigits: decimales, maximumFractionDigits: decimales
    }).format(valor);
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

  /* La variación en un año se lee distinta según la unidad: un porcentaje
     varía en puntos, y un recuento, en tanto por ciento. Mezclarlo sería
     decir que el paro «subió un 10 %» cuando subió diez puntos. */
  function variacion(destacado, ambito) {
    var ahora = destacado.valores[ambito];
    var antes = (destacado.hace_un_anyo || {})[ambito];
    if (ahora === null || ahora === undefined || !antes) return null;
    if (destacado.unidad === '%' || destacado.unidad === 'por mil') {
      var puntos = ahora - antes;
      return { valor: puntos, texto: (puntos >= 0 ? '+' : '−') +
               formatea(Math.abs(puntos), 2) + ' pts' };
    }
    var relativa = ((ahora - antes) / Math.abs(antes)) * 100;
    return { valor: relativa, texto: (relativa >= 0 ? '+' : '−') +
             numero.format(Math.abs(relativa)) + ' %' };
  }

  function colorAmbito(id) {
    var estilo = getComputedStyle(document.documentElement);
    var variables = { espana: '--serie-1', 'comunitat-valenciana': '--serie-2',
                      castellon: '--serie-3' };
    return estilo.getPropertyValue(variables[id] || '--serie-1').trim();
  }

  function color(variable) {
    return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
  }

  function cifra(ambito, destacado) {
    var caja = document.createElement('div');

    var etiqueta = document.createElement('div');
    etiqueta.className = 'flex items-center gap-1.5 text-xs';
    etiqueta.style.color = color('--tinta-tenue');
    var marca = document.createElement('span');
    marca.setAttribute('aria-hidden', 'true');
    marca.style.cssText = 'display:inline-block;width:.55rem;height:.55rem;border-radius:2px;';
    marca.style.background = colorAmbito(ambito.id);
    etiqueta.appendChild(marca);
    etiqueta.appendChild(document.createTextNode(ambito.etiqueta));
    caja.appendChild(etiqueta);

    var valor = document.createElement('div');
    valor.className = 'mt-0.5 text-lg font-semibold tracking-tight';
    valor.style.fontVariantNumeric = 'tabular-nums';
    var bruto = destacado.valores[ambito.id];
    valor.textContent = formatea(bruto, destacado.decimales) +
      (destacado.unidad === '%' ? ' %' : '');
    caja.appendChild(valor);

    // Si el indicador es parte de un total, el porcentaje dice más que la
    // cifra: 8.314 contratos indefinidos son el 46 % de los del mes.
    var sobre = (destacado.sobre_valores || {})[ambito.id];
    if (sobre && bruto !== null && bruto !== undefined) {
      var parte = document.createElement('div');
      parte.className = 'text-xs';
      parte.style.color = color('--tinta-suave');
      parte.textContent = numero.format((bruto / sobre) * 100) + ' % del total';
      caja.appendChild(parte);
    }

    var cambio = variacion(destacado, ambito.id);
    if (cambio) {
      var delta = document.createElement('div');
      delta.className = 'text-xs';
      delta.style.color = color('--tinta-tenue');
      delta.textContent = cambio.texto + ' en un año';
      caja.appendChild(delta);
    }
    return caja;
  }

  function tarjeta(seccion, ambitos) {
    var caja = document.createElement('article');
    caja.className = 'tarjeta p-5';

    var cabecera = document.createElement('div');
    cabecera.className = 'flex items-baseline justify-between gap-3';
    var titulo = document.createElement('h3');
    titulo.className = 'font-semibold tracking-tight';
    var enlace = document.createElement('a');
    enlace.href = seccion.enlace;
    enlace.className = 'enlace-sutil';
    enlace.textContent = seccion.titulo;
    titulo.appendChild(enlace);
    cabecera.appendChild(titulo);
    var periodo = document.createElement('span');
    periodo.className = 'text-xs whitespace-nowrap';
    periodo.style.color = color('--tinta-tenue');
    periodo.textContent = etiquetaPeriodo(seccion.ultimo_periodo);
    cabecera.appendChild(periodo);
    caja.appendChild(cabecera);

    seccion.destacados.forEach(function (destacado) {
      var bloque = document.createElement('div');
      bloque.className = 'mt-3';
      var nombre = document.createElement('div');
      nombre.className = 'text-xs font-medium uppercase tracking-widest';
      nombre.style.color = color('--tinta-suave');
      nombre.textContent = destacado.titulo + ' · ' + etiquetaPeriodo(destacado.periodo);
      bloque.appendChild(nombre);

      var rejilla = document.createElement('div');
      rejilla.className = 'mt-1.5 grid grid-cols-3 gap-3';
      ambitos.forEach(function (ambito) {
        rejilla.appendChild(cifra(ambito, destacado));
      });
      bloque.appendChild(rejilla);
      caja.appendChild(bloque);
    });

    var pie = document.createElement('p');
    pie.className = 'mt-4 text-xs leading-relaxed';
    pie.style.color = color('--tinta-tenue');
    pie.textContent = seccion.fuente + ' · ' + seccion.cadencia;
    caja.appendChild(pie);

    return caja;
  }

  function pinta(portada) {
    var contenedor = document.querySelector('[data-titulares]');
    if (!contenedor) return;
    contenedor.replaceChildren();
    portada.secciones.forEach(function (seccion) {
      contenedor.appendChild(tarjeta(seccion, portada.ambitos));
    });

    var fecha = new Date(portada.actualizado);
    var nodo = document.querySelector('[data-portada-actualizada]');
    if (nodo) {
      nodo.textContent = Number.isNaN(fecha.getTime())
        ? portada.actualizado
        : fecha.toLocaleString('es-ES', { dateStyle: 'long', timeStyle: 'short' });
    }
    var aviso = document.querySelector('[data-titulares-estado]');
    if (aviso) aviso.hidden = true;
  }

  async function arranca() {
    var aviso = document.querySelector('[data-titulares-estado]');
    try {
      var respuesta = await fetch('data/portada.json', { cache: 'no-cache' });
      if (!respuesta.ok) throw new Error('HTTP ' + respuesta.status);
      var portada = await respuesta.json();
      pinta(portada);
      // Los colores de las marcas cambian con el tema.
      document.addEventListener('tema:cambio', function () { pinta(portada); });
    } catch (error) {
      if (aviso) {
        aviso.textContent = 'Todavía no hay titulares que enseñar (' + error.message +
          '). Las secciones de abajo siguen funcionando.';
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', arranca);
  } else {
    arranca();
  }
})();
