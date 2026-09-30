(function () {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/sw.js?v=13').catch(function () {
      // La app sigue funcionando aunque el navegador no permita PWA.
    });
  });
})();
