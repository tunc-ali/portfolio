// main.js — gedeelde scripts voor alle pagina's

// ── JAAR IN FOOTER ────────────────────────────────────────────
// Wordt elk jaar automatisch ingevuld
const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();

// ── MOBIEL MENU (hamburger) ───────────────────────────────────
const navToggle = document.querySelector('.nav-toggle');
const navMenu = document.getElementById('nav-menu');

if (navToggle && navMenu) {
  const setOpen = open => {
    navMenu.classList.toggle('open', open);
    navToggle.setAttribute('aria-expanded', String(open));
  };

  navToggle.addEventListener('click', () => setOpen(!navMenu.classList.contains('open')));

  // Sluiten met Escape of bij klik buiten het menu
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && navMenu.classList.contains('open')) {
      setOpen(false);
      navToggle.focus();
    }
  });
  document.addEventListener('click', e => {
    if (!navMenu.contains(e.target) && !navToggle.contains(e.target)) setOpen(false);
  });
}

// ── E-MAIL LINK (anti-spam) ───────────────────────────────────
// Het adres staat nergens als geheel in de HTML; het wordt pas
// samengesteld wanneer een bezoeker op de knop klikt.
document.querySelectorAll('.js-mail').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const user = ['a', 'tunc1'].join('.');
    const host = ['yahoo', 'com'].join('.');
    window.location.href = 'mai' + 'lto:' + user + '@' + host;
  });
});

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
