// main.js — gedeelde scripts voor alle pagina's

// ── JAAR IN FOOTER ────────────────────────────────────────────
// Wordt elk jaar automatisch ingevuld
const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();

// ── DYNAMISCHE LOCATIE (LOC-balk onder de nav) ────────────────
const locEl = document.getElementById('location');
const LOC_FALLBACK = '51.2194° N, 4.4025° E — ANTWERPEN, BE';

if (locEl) {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        const lat = pos.coords.latitude.toFixed(4);
        const lng = pos.coords.longitude.toFixed(4);

        // Plaatsnaam ophalen via Nominatim
        fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`)
          .then(res => res.json())
          .then(data => {
            const a = data.address || {};
            const stad = a.city || a.town || a.village || '';
            const land = (a.country_code || '').toUpperCase();
            locEl.textContent = `${lat}° N, ${lng}° E — ${stad.toUpperCase()}, ${land}`;
          })
          .catch(() => { locEl.textContent = `${lat}° N, ${lng}° E`; });
      },
      function () { locEl.textContent = LOC_FALLBACK; }
    );
  } else {
    locEl.textContent = LOC_FALLBACK;
  }
}

// ── TEKST SCRAMBLE EFFECT OP NAV ITEMS ────────────────────────
// Letters wisselen willekeurig bij hover op nav links
const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

document.querySelectorAll('.nav-links a').forEach(link => {
  // Originele tekst één keer bewaren (zonder witruimte eromheen),
  // zodat een nieuwe hover tijdens de animatie de tekst niet verminkt
  const originalText = link.textContent.trim();
  link.textContent = originalText;
  let interval = null;

  link.addEventListener('mouseenter', () => {
    clearInterval(interval);
    let iterations = 0;

    interval = setInterval(() => {
      link.textContent = originalText
        .split('')
        .map((letter, index) => {
          if (index < iterations || letter === ' ') return letter;
          return letters[Math.floor(Math.random() * letters.length)];
        })
        .join('');

      if (iterations >= originalText.length) {
        clearInterval(interval);
        link.textContent = originalText; // zeker zijn dat tekst correct eindigt
      }

      iterations += 0.3;
    }, 40);
  });
});
