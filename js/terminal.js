// terminal.js — interactieve terminal op de homepagina
//
// Alle uitvoerteksten komen uit json/nl.json / en.json: build.py zet ze als
// <script type="application/json" id="terminal-data"> in de pagina.
// Er wordt niets uitgevoerd of verstuurd: elk commando drukt vaste tekst af.
// Zonder JS blijft de statische terminal (whoami + skills.conf) staan.

const root = document.getElementById('terminal');
const dataEl = document.getElementById('terminal-data');

if (root && dataEl) {
  const T = JSON.parse(dataEl.textContent);
  const log = root.querySelector('.t-log');
  const form = root.querySelector('.t-form');
  const input = root.querySelector('.t-input');
  const chips = document.querySelector('.t-chips');
  const MAX_LINES = 200;
  const history = [];
  let historyPos = 0;

  // ── Uitvoer (altijd via textContent, nooit HTML uit invoer) ──
  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function print(text, cls = 't-w') {
    const row = el('div');
    row.append(el('span', 't-o', '→'), ' ', el('span', cls, text));
    log.append(row);
  }
  function printPair(key, value) {
    const row = el('div');
    row.append(el('span', 't-o', '→'), ' ', el('span', 't-k', key), ' ', el('span', 't-w', value));
    log.append(row);
  }
  function printLink(text, href) {
    const row = el('div');
    const a = el('a', 't-link', text);
    a.href = href;
    row.append(a);
    log.append(row);
  }
  function printPrompt(cmd) {
    const row = el('div');
    row.append(
      el('span', 't-u', 'ali'), el('span', 't-d', '@'), el('span', 't-u', 'infra'), ' ',
      el('span', 't-d', ':'), el('span', 't-p', '~'), ' ', el('span', 't-d', '$ '), el('span', 't-c', cmd),
    );
    log.append(row);
  }
  const fill = (text, vars) => text.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');

  // ── Commando's ──────────────────────────────────────────────
  const currentLang = document.documentElement.lang || 'nl';

  const commands = {
    help() {
      print(T.help_title, 't-c');
      T.help.forEach(h => printPair(h.c, h.d));
    },
    whoami() { print(T.whoami); },
    skills() { T.skills.forEach(s => printPair(s.key, s.value)); },
    projects() {
      T.projects.forEach((title, i) => printPair(`#${String(i + 1).padStart(3, '0')}`, title));
      printLink(T.projects_link, T.urls.projects);
    },
    contact() {
      print(T.contact_text);
      printLink(T.contact_link, T.urls.contact);
    },
    lang(args) {
      const wanted = (args[0] || '').toLowerCase();
      if (!wanted) {
        print(fill(T.lang_current, { lang: currentLang }));
        print(T.lang_usage);
      } else if (wanted === currentLang) {
        print(T.lang_same);
      } else {
        const link = document.querySelector(`.nav-lang a[lang="${CSS.escape(wanted)}"]`);
        if (!link) { print(T.lang_usage, 't-e'); return; }
        print(fill(T.lang_switch, { lang: wanted }));
        setTimeout(() => { window.location.href = link.href; }, 500);
      }
    },
    clear() { log.replaceChildren(); },

    // Easter eggs — onschuldig: vaste tekst, er gebeurt niets
    sudo() { print(T.sudo, 't-e'); },
    nmap(args) {
      const target = args.filter(a => !a.startsWith('-')).pop() || 'alitunc.net';
      const host = target.toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, '');
      if (host !== 'alitunc.net' && host !== 'www.alitunc.net') {
        print(fill(T.nmap_scope, { target: target.slice(0, 60) }), 't-e');
        return;
      }
      T.nmap.forEach(line => print(line));
    },
  };

  function run(raw) {
    const line = raw.trim().slice(0, 80);
    printPrompt(line);
    if (line) {
      const [name, ...args] = line.split(/\s+/);
      const cmd = commands[name.toLowerCase()];
      if (cmd && Object.hasOwn(commands, name.toLowerCase())) cmd(args);
      else print(fill(T.not_found, { cmd: name.slice(0, 30) }), 't-e');
      history.push(line);
      if (history.length > 50) history.shift();
    }
    historyPos = history.length;
    if (line.toLowerCase() !== 'clear') log.append(el('br'));
    while (log.childElementCount > MAX_LINES) log.firstElementChild.remove();
    root.scrollTop = root.scrollHeight;
  }

  // ── Invoer ──────────────────────────────────────────────────
  root.querySelector('.t-static').hidden = true;
  form.hidden = false;
  if (chips) chips.hidden = false;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    run(input.value);
    input.value = '';
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowUp' && historyPos > 0) {
      historyPos--; input.value = history[historyPos]; e.preventDefault();
    } else if (e.key === 'ArrowDown') {
      historyPos = Math.min(history.length, historyPos + 1);
      input.value = history[historyPos] || ''; e.preventDefault();
    } else if (e.key === 'l' && e.ctrlKey) {
      commands.clear(); e.preventDefault();
    }
  });

  // Klik ergens in de terminal → focus op de invoer (niet bij tekst selecteren of links)
  root.addEventListener('click', (e) => {
    if (e.target.closest('a') || String(window.getSelection())) return;
    input.focus({ preventScroll: true });
  });

  // Knoppen onder de terminal (handig op touch)
  chips?.querySelectorAll('.t-chip').forEach(btn => {
    btn.addEventListener('click', () => run(btn.dataset.cmd));
  });
}
