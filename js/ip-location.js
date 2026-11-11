// ip-location.js — locatie + IP van de bezoeker in de LOC-balk onder de nav
//
// - Op basis van het IP-adres: geen toestemmingsvenster van de browser.
// - Het IP wordt alleen aan de bezoeker zelf getoond; er wordt niets
//   naar een eigen server gestuurd of gelogd. Het resultaat blijft enkel
//   in sessionStorage van de bezoeker (verdwijnt bij sluiten van de tab),
//   zodat niet elke pagina opnieuw een lookup doet.
// - Bij een fout: stille fallback (tekst uit data-fallback, IP verborgen).

(() => {
  const locEl  = document.getElementById('location');
  const ipEl   = document.getElementById('visitor-ip');
  const ipWrap = ipEl ? ipEl.closest('.nav-ip') : null;
  if (!locEl) return;

  const CACHE_KEY = 'visitorGeo';
  const TIMEOUT_MS = 4000;

  // Publieke lookup-diensten (HTTPS + CORS, geen API-key). Tweede = reserve.
  const providers = [
    {
      url: 'https://ipwho.is/?fields=ip,success,city,country_code,latitude,longitude',
      map: d => d.success === false ? null
        : { ip: d.ip, city: d.city, cc: d.country_code, lat: d.latitude, lon: d.longitude },
    },
    {
      url: 'https://ipapi.co/json/',
      map: d => d.error ? null
        : { ip: d.ip, city: d.city, cc: d.country_code, lat: d.latitude, lon: d.longitude },
    },
  ];

  // Alleen tekens die in een IPv4/IPv6-adres voorkomen
  const isIp = v => typeof v === 'string' && v.length <= 45 && /^[0-9a-fA-F:.]+$/.test(v);

  function formatCoords(lat, lon) {
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return '';
    const ns = lat >= 0 ? 'N' : 'S';
    const ew = lon >= 0 ? 'E' : 'W';
    return `${Math.abs(lat).toFixed(4)}° ${ns}, ${Math.abs(lon).toFixed(4)}° ${ew}`;
  }

  function render(geo) {
    const coords = formatCoords(Number(geo.lat), Number(geo.lon));
    const place = [geo.city, geo.cc]
      .filter(v => typeof v === 'string' && v.trim())
      .map(v => v.trim().slice(0, 40).toUpperCase())
      .join(', ');
    const text = [coords, place].filter(Boolean).join(' — ');
    if (!text) return false;

    locEl.textContent = text;            // textContent: nooit HTML uit de API
    if (ipEl && ipWrap && isIp(geo.ip)) {
      ipEl.textContent = geo.ip;
      ipWrap.hidden = false;
    }
    return true;
  }

  function renderFallback() {
    locEl.textContent = locEl.dataset.fallback || '—';
    if (ipWrap) ipWrap.hidden = true;
  }

  async function lookup(provider) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    try {
      const res = await fetch(provider.url, {
        signal: ctrl.signal,
        credentials: 'omit',
        referrerPolicy: 'no-referrer',
      });
      if (!res.ok) return null;
      return provider.map(await res.json());
    } catch {
      return null;
    } finally {
      clearTimeout(timer);
    }
  }

  async function init() {
    // 1) Eerder resultaat uit deze sessie
    try {
      const cached = JSON.parse(sessionStorage.getItem(CACHE_KEY));
      if (cached && render(cached)) return;
    } catch { /* sessionStorage niet beschikbaar of ongeldig → gewoon ophalen */ }

    // 2) Diensten één voor één proberen
    for (const provider of providers) {
      const geo = await lookup(provider);
      if (geo && render(geo)) {
        try { sessionStorage.setItem(CACHE_KEY, JSON.stringify(geo)); } catch { /* negeren */ }
        return;
      }
    }

    // 3) Niets gelukt → stil terugvallen
    renderFallback();
  }

  init();
})();
