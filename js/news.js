// news.js — security-nieuws op de homepagina
//
// Leest json/news.json en toont de items als kaarten. Nu staat daar
// voorbeelddata in ("sample": true → melding "voorbeeldweergave").
// Later komt hier de URL van de Netlify Function die de RSS-feeds ophaalt;
// het formaat blijft hetzelfde: { items: [{ source, title, url, date? }] }.
// Lukt het laden niet, dan blijven alleen de bronlinks onder de lijst staan.

const NEWS_URL = new URL('../json/news.json', import.meta.url);
const MAX_ITEMS = 6;

const list = document.querySelector('.news-list');
const sampleNote = document.querySelector('.news-sample');

function card(item) {
  // Alleen https-links, en tekst altijd via textContent (nooit HTML uit de feed)
  let url;
  try { url = new URL(item.url); } catch { return null; }
  if (url.protocol !== 'https:' || typeof item.title !== 'string') return null;

  const li = document.createElement('li');
  const a = document.createElement('a');
  a.className = 'news-card';
  a.href = url.href;
  a.rel = 'noopener noreferrer';

  const source = document.createElement('span');
  source.className = 'news-source';
  source.textContent = String(item.source || url.hostname).slice(0, 40);

  const title = document.createElement('span');
  title.className = 'news-title';
  title.textContent = item.title.slice(0, 200);

  a.append(source, title);
  li.append(a);
  return li;
}

if (list) {
  fetch(NEWS_URL)
    .then(res => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
    .then((data) => {
      const cards = (Array.isArray(data.items) ? data.items : []).slice(0, MAX_ITEMS).map(card).filter(Boolean);
      if (!cards.length) throw new Error('geen items');
      list.replaceChildren(...cards);
      if (data.sample && sampleNote) sampleNote.hidden = false;
    })
    .catch(() => { list.hidden = true; });     // bronlinks eronder blijven zichtbaar
}
