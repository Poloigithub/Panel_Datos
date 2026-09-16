/* Mapa coroplético de los municipios de la provincia.
 *
 * Se dibuja como SVG, sin librería de cartografía: para un territorio del
 * tamaño de una provincia basta con una proyección equirectangular corregida
 * por la latitud media, y así el panel sigue sin dependencias externas.
 *
 * Reglas que comparte con el resto de gráficas del panel: un solo tono para
 * una escala de magnitud, leyenda siempre visible y una tabla equivalente,
 * porque un mapa nunca puede ser la única forma de leer el dato. */
(function () {
  'use strict';

  var P = window.Panel;

  /* Rampa de un solo tono. En claro va de suave a intenso; en oscuro, al
     revés, porque sobre fondo oscuro lo que destaca es lo luminoso. */
  var RAMPA_CLARA = ['#cde2fb', '#9ec5f4', '#5598e7', '#2a78d6', '#184f95'];
  var RAMPA_OSCURA = ['#104281', '#1c5cab', '#2a78d6', '#5598e7', '#9ec5f4'];

  function esOscuro() {
    var raiz = document.documentElement;
    if (raiz.dataset.theme) return raiz.dataset.theme === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function rampa() {
    return esOscuro() ? RAMPA_OSCURA : RAMPA_CLARA;
  }

  /* Cortes por cuantiles: con datos muy asimétricos -una capital y decenas de
     pueblos- una escala lineal pintaría todo del mismo color. */
  function cortes(valores, clases) {
    var ordenados = valores.filter(function (v) { return v !== null && !isNaN(v); })
                           .sort(function (a, b) { return a - b; });
    if (!ordenados.length) return [];
    var limites = [];
    for (var i = 1; i < clases; i++) {
      limites.push(ordenados[Math.floor((ordenados.length * i) / clases)]);
    }
    return limites;
  }

  function claseDe(valor, limites) {
    if (valor === null || valor === undefined || isNaN(valor)) return -1;
    for (var i = 0; i < limites.length; i++) {
      if (valor < limites[i]) return i;
    }
    return limites.length;
  }

  /* Extensión de todas las geometrías, para encuadrar el mapa. */
  function encuadre(geojson) {
    var minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
    geojson.features.forEach(function (elemento) {
      recorreAnillos(elemento.geometry, function (punto) {
        if (punto[0] < minLon) minLon = punto[0];
        if (punto[0] > maxLon) maxLon = punto[0];
        if (punto[1] < minLat) minLat = punto[1];
        if (punto[1] > maxLat) maxLat = punto[1];
      });
    });
    return { minLon: minLon, maxLon: maxLon, minLat: minLat, maxLat: maxLat };
  }

  function recorreAnillos(geometria, visita) {
    if (!geometria) return;
    var coordenadas = geometria.coordinates || [];
    if (geometria.type === 'Polygon') {
      coordenadas.forEach(function (anillo) { anillo.forEach(visita); });
    } else if (geometria.type === 'MultiPolygon') {
      coordenadas.forEach(function (poligono) {
        poligono.forEach(function (anillo) { anillo.forEach(visita); });
      });
    }
  }

  function proyector(caja, ancho, alto, margen) {
    // Un grado de longitud mide menos que uno de latitud según se sube: sin
    // esta corrección la provincia saldría estirada a lo ancho.
    var latMedia = ((caja.minLat + caja.maxLat) / 2) * Math.PI / 180;
    var escalaLon = Math.cos(latMedia);
    var anchoGrados = (caja.maxLon - caja.minLon) * escalaLon;
    var altoGrados = caja.maxLat - caja.minLat;
    var escala = Math.min((ancho - margen * 2) / anchoGrados, (alto - margen * 2) / altoGrados);
    var desplazaX = (ancho - anchoGrados * escala) / 2;
    var desplazaY = (alto - altoGrados * escala) / 2;

    return function (punto) {
      var x = (punto[0] - caja.minLon) * escalaLon * escala + desplazaX;
      var y = (caja.maxLat - punto[1]) * escala + desplazaY;
      return [x, y];
    };
  }

  function trazado(geometria, proyecta) {
    var partes = [];
    function anillo(puntos) {
      var d = '';
      puntos.forEach(function (punto, i) {
        var p = proyecta(punto);
        d += (i === 0 ? 'M' : 'L') + p[0].toFixed(1) + ',' + p[1].toFixed(1);
      });
      partes.push(d + 'Z');
    }
    var coordenadas = geometria.coordinates || [];
    if (geometria.type === 'Polygon') {
      coordenadas.forEach(anillo);
    } else if (geometria.type === 'MultiPolygon') {
      coordenadas.forEach(function (poligono) { poligono.forEach(anillo); });
    }
    return partes.join('');
  }

  function tooltip() {
    var nodo = document.getElementById('tooltip-mapa');
    if (nodo) return nodo;
    nodo = document.createElement('div');
    nodo.id = 'tooltip-mapa';
    nodo.setAttribute('role', 'tooltip');
    nodo.style.cssText = [
      'position:fixed', 'pointer-events:none', 'opacity:0', 'z-index:50',
      'transition:opacity .1s ease', 'border-radius:.6rem', 'padding:.5rem .7rem',
      'font-size:.8rem', 'line-height:1.35', 'box-shadow:0 6px 24px rgba(0,0,0,.14)'
    ].join(';');
    document.body.appendChild(nodo);
    return nodo;
  }

  function muestraTooltip(evento, nombre, texto) {
    var nodo = tooltip();
    nodo.style.background = P.color('--superficie');
    nodo.style.border = '1px solid ' + P.color('--borde');
    nodo.style.color = P.color('--tinta');
    nodo.replaceChildren();

    var titulo = document.createElement('div');
    titulo.style.cssText = 'font-weight:600;';
    titulo.textContent = nombre;           // nombre externo: como texto, nunca HTML
    nodo.appendChild(titulo);

    var valor = document.createElement('div');
    valor.style.color = P.color('--tinta-suave');
    valor.style.fontVariantNumeric = 'tabular-nums';
    valor.textContent = texto;
    nodo.appendChild(valor);

    nodo.style.opacity = '1';
    var ancho = nodo.offsetWidth || 140;
    nodo.style.left = Math.min(evento.clientX + 14, window.innerWidth - ancho - 8) + 'px';
    nodo.style.top = Math.max(8, evento.clientY - 10) + 'px';
  }

  function ocultaTooltip() {
    var nodo = document.getElementById('tooltip-mapa');
    if (nodo) nodo.style.opacity = '0';
  }

  /* opciones: { valores: {codigo: numero}, etiqueta: fn(codigo) -> texto,
                 titulo: string, alSeleccionar: fn(codigo) } */
  function dibuja(contenedor, geojson, opciones) {
    contenedor.replaceChildren();
    var ancho = 640, alto = 460;
    var caja = encuadre(geojson);
    var proyecta = proyector(caja, ancho, alto, 8);
    var limites = cortes(Object.keys(opciones.valores).map(function (c) {
      return opciones.valores[c];
    }), 5);
    var colores = rampa();

    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 ' + ancho + ' ' + alto);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', opciones.titulo);
    svg.style.cssText = 'width:100%;height:auto;display:block;';

    geojson.features.forEach(function (elemento) {
      var codigo = elemento.properties.codigo;
      var valor = opciones.valores[codigo];
      var clase = claseDe(valor, limites);

      var camino = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      camino.setAttribute('d', trazado(elemento.geometry, proyecta));
      camino.setAttribute('fill', clase < 0 ? P.color('--superficie-2') : colores[clase]);
      camino.setAttribute('stroke', P.color('--superficie'));
      camino.setAttribute('stroke-width', '0.6');
      camino.style.cursor = 'pointer';
      camino.setAttribute('tabindex', '0');

      var nombre = elemento.properties.nombre;
      var texto = opciones.etiqueta(codigo);
      camino.setAttribute('aria-label', nombre + ': ' + texto);

      function resalta(evento) {
        camino.setAttribute('stroke', P.color('--tinta'));
        camino.setAttribute('stroke-width', '1.6');
        muestraTooltip(evento.clientX !== undefined ? evento
                       : camino.getBoundingClientRect(), nombre, texto);
      }
      function apaga() {
        camino.setAttribute('stroke', P.color('--superficie'));
        camino.setAttribute('stroke-width', '0.6');
        ocultaTooltip();
      }
      camino.addEventListener('pointermove', resalta);
      camino.addEventListener('pointerleave', apaga);
      camino.addEventListener('focus', function () {
        var caja2 = camino.getBoundingClientRect();
        resalta({ clientX: caja2.left + caja2.width / 2, clientY: caja2.top });
      });
      camino.addEventListener('blur', apaga);
      if (opciones.alSeleccionar) {
        camino.addEventListener('click', function () { opciones.alSeleccionar(codigo); });
        camino.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            opciones.alSeleccionar(codigo);
          }
        });
      }

      svg.appendChild(camino);
    });

    contenedor.appendChild(svg);
    contenedor.appendChild(leyenda(limites, colores, opciones));
  }

  function leyenda(limites, colores, opciones) {
    var caja = document.createElement('div');
    caja.className = 'mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs';

    colores.forEach(function (color, i) {
      var item = document.createElement('span');
      item.style.cssText = 'display:inline-flex;align-items:center;gap:.35rem;';

      var muestra = document.createElement('span');
      muestra.setAttribute('aria-hidden', 'true');
      muestra.style.cssText = 'display:inline-block;width:1.1rem;height:.7rem;border-radius:2px;';
      muestra.style.background = color;
      item.appendChild(muestra);

      var texto = document.createElement('span');
      texto.style.color = P.color('--tinta-suave');
      var desde = i === 0 ? null : limites[i - 1];
      var hasta = i < limites.length ? limites[i] : null;
      texto.textContent = opciones.rango(desde, hasta);
      item.appendChild(texto);

      caja.appendChild(item);
    });

    return caja;
  }

  window.Panel.dibujaMapa = dibuja;
})();
