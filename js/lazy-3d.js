// lazy-3d.js — laadt de 3D-scènes pas wanneer ze bijna in beeld komen.
//
// Elk element met data-scene="topology" of data-scene="globe" krijgt zijn
// module (en daarmee three.js, ±145 kB gzip) pas wanneer het in beeld komt.
// Geen WebGL of een fout bij het laden → class "no-webgl": de CSS toont dan
// de HTML-fallback (lijst met dezelfde informatie).

const loaders = {
  topology: () => import('./topology.js'),
  globe: () => import('./globe.js'),
};

function hasWebGL() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch {
    return false;
  }
}

const targets = document.querySelectorAll('[data-scene]');

if (!hasWebGL() || !('IntersectionObserver' in window)) {
  targets.forEach(el => el.classList.add('no-webgl'));
} else {
  const io = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      const el = entry.target;
      io.unobserve(el);
      loaders[el.dataset.scene]()
        .then(mod => mod.init(el))
        .then(() => el.classList.add('is-3d'))
        .catch((err) => {
          console.warn('3D-scène niet geladen:', err);
          el.classList.add('no-webgl');
        });
    }
  });

  // Pas beginnen na het laden van de pagina, zodat three.js de eerste weergave
  // (hero-foto, lettertypes) niet in de weg zit.
  const start = () => targets.forEach(el => { if (loaders[el.dataset.scene]) io.observe(el); });
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, { once: true });
}
