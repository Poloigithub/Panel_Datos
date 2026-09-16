/* El estado de los filtros, en la URL.
 *
 * Sin esto, una página del panel sólo se puede compartir entera: quien la abre
 * ve los filtros por defecto, no lo que estabas mirando. Con esto, la barra de
 * direcciones es siempre un enlace a la vista actual -«el paro registrado de
 * Castellón desde 2008»- y se puede pegar en cualquier sitio.
 *
 * Dos decisiones:
 *
 * - Sólo viaja lo que se ha cambiado. Una vista por defecto deja la URL limpia,
 *   y así un enlace dice exactamente qué hay de distinto en él.
 * - Se valida lo que llega. Una URL la escribe cualquiera, y un valor que no
 *   existe debe ignorarse y dejar el valor por defecto, nunca romper la página
 *   ni colarse en el estado. */
(function () {
  'use strict';

  function esConjunto(valor) {
    return valor instanceof Set;
  }

  /* Vuelca en `estado` lo que traiga la URL, ignorando lo que no encaje.
   *
   * `defectos` dice qué claves viajan y de qué tipo son; `validos` acota, por
   * clave, los valores admitidos. */
  function aplica(estado, defectos, validos) {
    var parametros = new URLSearchParams(window.location.search);
    Object.keys(defectos).forEach(function (clave) {
      if (!parametros.has(clave)) return;
      var bruto = parametros.get(clave);
      var admitidos = (validos || {})[clave] || null;

      if (esConjunto(defectos[clave])) {
        var partes = bruto.split(',').map(function (p) { return p.trim(); })
          .filter(function (p) { return p && (!admitidos || admitidos.indexOf(p) >= 0); });
        // Un conjunto vacío dejaría la página en blanco: mejor el de partida.
        if (partes.length) estado[clave] = new Set(partes);
        return;
      }
      if (!admitidos || admitidos.indexOf(bruto) >= 0) estado[clave] = bruto;
    });
    return estado;
  }

  /* Deja en la barra de direcciones la vista actual, sin tocar el historial:
     navegar por los filtros no debería llenar el botón «atrás». */
  function escribe(estado, defectos) {
    var parametros = new URLSearchParams();
    Object.keys(defectos).forEach(function (clave) {
      var valor = estado[clave];
      var defecto = defectos[clave];
      if (valor === null || valor === undefined) return;

      if (esConjunto(defecto)) {
        var actual = Array.from(valor).sort();
        var inicial = Array.from(defecto).sort();
        if (actual.join(',') !== inicial.join(',')) parametros.set(clave, actual.join(','));
        return;
      }
      if (valor !== defecto) parametros.set(clave, String(valor));
    });

    var cadena = parametros.toString();
    var url = window.location.pathname + (cadena ? '?' + cadena : '') + window.location.hash;
    try {
      window.history.replaceState(null, '', url);
    } catch (_) {
      // En file:// el navegador no deja reescribir la URL; el panel sigue
      // funcionando, simplemente sin enlace permanente.
    }
  }

  /* Botón de copiar, junto al de descargar CSV. Se crea desde aquí para que
     las nueve páginas no tengan que repetir el mismo trozo de HTML. */
  function botonCopiar(contenedor) {
    if (!contenedor) return null;
    var boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'control';
    boton.title = 'Copiar un enlace a esta vista, con los filtros puestos';
    boton.textContent = 'Copiar enlace';
    boton.addEventListener('click', function () {
      var enlace = window.location.href;
      var avisa = function (texto) {
        boton.textContent = texto;
        window.setTimeout(function () { boton.textContent = 'Copiar enlace'; }, 1800);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(enlace).then(function () {
          avisa('Enlace copiado');
        }, function () {
          avisa('Copia la barra de direcciones');
        });
      } else {
        avisa('Copia la barra de direcciones');
      }
    });
    contenedor.appendChild(boton);
    return boton;
  }

  /* Pone los controles al día con el estado, que es lo que hace falta cuando
     el estado no viene de un clic sino de la URL. */
  function sincroniza(estado) {
    document.querySelectorAll('[data-grupo]').forEach(function (grupo) {
      var clave = grupo.dataset.grupo;
      if (!(clave in estado) || estado[clave] instanceof Set) return;
      grupo.querySelectorAll('button[data-valor]').forEach(function (boton) {
        boton.setAttribute('aria-pressed', String(boton.dataset.valor === estado[clave]));
      });
    });
  }

  window.Enlace = { aplica: aplica, escribe: escribe, botonCopiar: botonCopiar,
                    sincroniza: sincroniza };
})();
