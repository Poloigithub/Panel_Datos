/* Alterna claro/oscuro y recuerda la elección. Sin preferencia guardada manda
   el ajuste del sistema. */
(function () {
  const raiz = document.documentElement;
  const boton = document.querySelector('[data-tema]');
  if (!boton) return;

  const etiqueta = boton.querySelector('[data-tema-texto]');

  function esOscuro() {
    if (raiz.dataset.theme) return raiz.dataset.theme === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function pinta() {
    const oscuro = esOscuro();
    if (etiqueta) etiqueta.textContent = oscuro ? 'Claro' : 'Oscuro';
    boton.setAttribute('aria-label', oscuro ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro');
    document.dispatchEvent(new CustomEvent('tema:cambio', { detail: { oscuro } }));
  }

  boton.addEventListener('click', function () {
    const nuevo = esOscuro() ? 'light' : 'dark';
    raiz.dataset.theme = nuevo;
    try { localStorage.setItem('panel-tema', nuevo); } catch (_) {}
    pinta();
  });

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
    if (!raiz.dataset.theme) pinta();
  });

  pinta();
})();
