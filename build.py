#!/usr/bin/env python3
"""
build.py — controleert de bronbestanden en bouwt alitunc.net in dist/.

GEBRUIK
    python build.py            controleren + bouwen naar dist/
    python build.py --list     idem, en daarna de inhoud van dist/ tonen
    Lokaal bekijken:  python -m http.server 8000 -d dist

WAT HET DOET
    1. CONTROLE  Alle bronnen worden eerst gecontroleerd. Bij één of meer fouten
                 toont build.py ze allemaal en stopt het met exit code 1, zonder
                 dist/ aan te raken. Op Netlify mislukt de deploy dan en blijft
                 de vorige versie online.
    2. BOUWEN    json/nl.json + templates/  →  dist/*.html          (Nederlands)
                 json/en.json + templates/  →  dist/en/*.html       (Engels)
                 notes/nl/*.md, notes/en/*.md → dist/lab-notes/, dist/en/lab-notes/
                 + de bestanden uit STATIC (whitelist) worden naar dist/ gekopieerd.
                 Er wordt eerst in .dist-tmp/ gebouwd; pas als alles gelukt is,
                 vervangt die map dist/.

    Elke pagina krijgt automatisch: <html lang>, canonical, hreflang-tags
    en de taalwisselaar in de nav die naar dezelfde pagina in de andere taal wijst.

    dist/ staat niet in git. Netlify voert `python3 build.py` zelf uit
    (zie netlify.toml); de GitHub Action doet hetzelfde als controle.

WERKWIJZE
    - Tekst aanpassen      → json/nl.json en json/en.json (zelfde sleutels in beide)
    - Opmaak/structuur     → templates/_layout.html (nav, footer) of templates/<pagina>.html
    - Nieuwe pagina        → rij toevoegen in PAGES hieronder + templates/<id>.html
                             + "pages.<id>" (title, description) in beide json-bestanden
    - Nieuw statisch bestand of nieuwe map voor de site → toevoegen aan STATIC.
      Wat niet in STATIC staat, komt niet online (bv. notes/, templates/, build.py).

CONTROLES (elke fout stopt de build)
    json/nl.json, json/en.json
      - geldige JSON (met regel/kolom bij een fout)
      - exact dezelfde sleutels, lijstlengtes en types in beide talen
      - geen lege tekst, behalve in velden met een naam uit OPTIONAL_EMPTY;
        zo'n veld moet dan in beide talen leeg of in beide talen ingevuld zijn
      - pages.<id>.title en .description voor elke pagina in PAGES
      - HTML in tekst: alleen <strong>, <em>, <br>, <code> zonder attributen
      - home.topology.nodes: elke id moet bestaan in json/topology.json
    json/topology.json, json/globe.json, json/news.json
      - geldige JSON en de velden die de scripts op de site verwachten
    notes/<taal>/*.md (lab notes)
      - bestandsnaam = slug: alleen a-z, 0-9 en koppeltekens (bv. vlan-hopping.md)
      - kopblok (--- … ---) met precies title, date, description, niet leeg;
        geen onbekende of dubbele sleutels; date is een echte datum JJJJ-MM-DD
      - tekst onder het kopblok mag niet leeg zijn
      - elk artikel bestaat in BEIDE talen met dezelfde bestandsnaam
    images/uploads/
      - alleen .jpg .jpeg .png .webp .avif, max. 5 MB, en de inhoud moet
        echt dat formaat zijn (geen hernoemde SVG/HTML)
      - geen EXIF/XMP/IPTC-metadata (GPS-locatie, camera, …)
    algemeen
      - geen symbolische links in wat naar dist/ gaat
      - elke template-sleutel moet bestaan

LAB NOTES (artikels)
    Eén Markdown-bestand per artikel en per taal, met dezelfde bestandsnaam:
        notes/nl/vlan-hopping.md      notes/en/vlan-hopping.md
    Bovenaan elk bestand:
        ---
        title: VLAN hopping in het lab
        date: 2026-12-01
        description: Eén zin voor de lijst en voor zoekmachines.
        ---
    Daaronder gewone Markdown: ## en ### koppen, alinea's, lijsten (- of 1.),
    > citaten, ```codeblokken```, `code`, **vet**, *cursief* en [links](https://…).
    Zolang er geen artikels zijn, maakt build.py geen lab-notes-pagina's en staat
    er geen link in de nav. Met het eerste artikel verschijnen beide vanzelf.

TEMPLATE-SYNTAX (bewust minimaal, alleen de standaardbibliotheek van Python)
    {{ pad.naar.sleutel }}                tekst, HTML wordt ge-escaped
    {{{ pad.naar.sleutel }}}              ruwe HTML (alleen voor tekst met <strong> e.d.)
    {% for x in pad.naar.lijst %} … {% endfor %}
    {% if pad.naar.sleutel %} … {% endif %}     (leeg/ontbrekend = niet tonen)
"""
import datetime
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'
TMP = ROOT / '.dist-tmp'
SITE_URL = 'https://alitunc.net'
DEFAULT_LANG = 'nl'                 # staat in de root; andere talen in /<taal>/
LANGS = ('nl', 'en')
NOTES_DIR = 'lab-notes'             # uitvoermap voor artikels (bron: notes/<taal>/*.md)

# pagina-id → bestandsnaam per taal
# Optioneel per pagina: 'styles' (extra css), 'modules' (extra ES-modules) en
# 'preloads' (afbeeldingen om vroeg te laden), paden vanaf de root.
PAGES = {
    'home':     {'nl': 'index.html',     'en': 'index.html',
                 'styles': ['css/scenes.css'],
                 # hero-foto vroeg laten ophalen (staat in de CSS, dus anders laat ontdekt)
                 'preloads': [
                     {'href': 'images/network_with_military_green.webp', 'media': '(min-width: 901px)'},
                     {'href': 'images/network_with_military_green-960.webp', 'media': '(max-width: 900px)'},
                 ],
                 'modules': ['js/terminal.js', 'js/lazy-3d.js', 'js/news.js']},
    'services': {'nl': 'expertise.html', 'en': 'expertise.html'},
    'about':    {'nl': 'over-mij.html',  'en': 'about.html'},
    'projects': {'nl': 'projecten.html', 'en': 'projects.html'},
    'contact':  {'nl': 'contact.html',   'en': 'contact.html'},
    'cv':       {'nl': 'cv.html',        'en': 'cv.html'},
}

# WHITELIST: alleen deze bestanden/mappen gaan naar dist/ (paden vanaf de root).
# True = verplicht (ontbreekt → fout), False = optioneel (wordt gekopieerd als het bestaat).
STATIC = {
    'css':                       True,
    'js':                        True,
    'images':                    True,
    'vendor/three.bundle.min.js': True,
    'vendor/LICENSE-three.txt':  True,
    'vendor/fonts':              True,
    'vendor/sveltia-cms':        True,    # CMS-script voor /admin (zie vendor/README.md)
    'json/topology.json':        True,
    'json/globe.json':           True,
    'json/news.json':            True,
    'admin':                     False,   # CMS (volgt in stap 4)
    'robots.txt':                False,
    '404.html':                  False,
    'favicon.ico':               False,
    '.well-known':               False,   # bv. .well-known/security.txt
}
# Nooit kopiëren, ook niet binnen een map uit STATIC
IGNORED_NAMES = {'Thumbs.db', 'desktop.ini', '.DS_Store', '.gitkeep'}

# Tekstvelden die leeg mogen zijn (naam van het laatste deel van het sleutelpad)
OPTIONAL_EMPTY = {'note', 'result'}
# HTML die in json-tekst mag staan (zonder attributen)
ALLOWED_TAGS = {'strong', 'em', 'br', 'code'}

UPLOADS = 'images/uploads'
UPLOAD_MAX_BYTES = 5 * 1024 * 1024
UPLOAD_TYPES = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png', '.webp': 'webp', '.avif': 'avif'}

NOTE_KEYS = ('title', 'date', 'description')
SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

GENERATED_NOTE = '<!-- GEGENEREERD door build.py (templates/ + json/) — niet rechtstreeks bewerken -->'


# ── Foutverzameling ───────────────────────────────────────────
class Errors(list):
    def add(self, msg):
        self.append(msg)


class BuildError(Exception):
    pass


def rel(path):
    return path.relative_to(ROOT).as_posix()


# ── Mini template-engine ──────────────────────────────────────
TOKEN = re.compile(r'(\{\{\{.*?\}\}\}|\{\{.*?\}\}|\{%.*?%\})', re.S)
FOR = re.compile(r'^for\s+(\w+)\s+in\s+([\w.]+)$')
IF = re.compile(r'^if\s+([\w.]+)$')


def parse(tokens, i=0, closing=None):
    """Zet tokens om in een boom:
    ('text', s) | ('var', pad, raw) | ('for', naam, pad, kinderen) | ('if', pad, kinderen)."""
    nodes = []
    while i < len(tokens):
        tok = tokens[i]
        i += 1
        if tok.startswith('{{{'):
            nodes.append(('var', tok[3:-3].strip(), True))
        elif tok.startswith('{{'):
            nodes.append(('var', tok[2:-2].strip(), False))
        elif tok.startswith('{%'):
            stmt = tok[2:-2].strip()
            if stmt in ('endfor', 'endif'):
                if stmt != closing:
                    raise SyntaxError(f'Onverwachte {{% {stmt} %}}')
                return nodes, i
            m_for, m_if = FOR.match(stmt), IF.match(stmt)
            if m_for:
                body, i = parse(tokens, i, 'endfor')
                nodes.append(('for', m_for.group(1), m_for.group(2), body))
            elif m_if:
                body, i = parse(tokens, i, 'endif')
                nodes.append(('if', m_if.group(1), body))
            else:
                raise SyntaxError(f'Onbekende template-instructie: {tok}')
        elif tok:
            nodes.append(('text', tok))
    if closing:
        raise SyntaxError(f'{{% {closing} %}} ontbreekt')
    return nodes, i


def lookup(ctx, path):
    cur = ctx
    for part in path.split('.'):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(path)
    return cur


def evaluate(nodes, ctx):
    out = []
    for node in nodes:
        kind = node[0]
        if kind == 'text':
            out.append(node[1])
        elif kind == 'var':
            value = str(lookup(ctx, node[1]))
            out.append(value if node[2] else html.escape(value, quote=True))
        elif kind == 'for':
            _, name, path, body = node
            for item in lookup(ctx, path):
                out.append(evaluate(body, {**ctx, name: item}))
        else:                                   # if: leeg of ontbrekend = overslaan
            try:
                value = lookup(ctx, node[1])
            except KeyError:
                value = None
            if value:
                out.append(evaluate(node[2], ctx))
    return ''.join(out)


_TEMPLATES = {}


def render(template_name, ctx):
    if template_name not in _TEMPLATES:
        path = ROOT / 'templates' / template_name
        if not path.is_file():
            raise BuildError(f'templates/{template_name} bestaat niet')
        try:
            _TEMPLATES[template_name] = parse(TOKEN.split(path.read_text(encoding='utf-8')))[0]
        except SyntaxError as e:
            raise BuildError(f'templates/{template_name}: {e}')
    try:
        return evaluate(_TEMPLATES[template_name], ctx)
    except KeyError as e:
        raise BuildError(f'sleutel {e} ontbreekt (template {template_name}, taal {ctx["lang"]})')


# ── JSON laden en controleren ─────────────────────────────────
def load_json(path, errors):
    if not path.is_file():
        errors.add(f'{rel(path)} ontbreekt')
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except UnicodeDecodeError:
        errors.add(f'{rel(path)}: geen geldige UTF-8')
    except json.JSONDecodeError as e:
        errors.add(f'{rel(path)}: ongeldige JSON op regel {e.lineno}, kolom {e.colno}: {e.msg}')
    return None


def leaves(value, prefix=''):
    """(sleutelpad, waarde) voor elk blad; lijsten met index."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield from leaves(v, f'{prefix}{k}.')
    elif isinstance(value, list):
        if not value:
            yield prefix.rstrip('.'), value
        for n, v in enumerate(value):
            yield from leaves(v, f'{prefix}{n}.')
    else:
        yield prefix.rstrip('.'), value


TAG = re.compile(r'<\s*(/?)\s*([a-zA-Z][\w-]*)([^>]*)>')


def check_texts(texts, errors):
    flat = {lang: dict(leaves(texts[lang])) for lang in LANGS}
    base = flat[DEFAULT_LANG]

    # 1. zelfde sleutels en types in beide talen
    for lang in LANGS:
        if lang == DEFAULT_LANG:
            continue
        for key in sorted(base.keys() - flat[lang].keys()):
            errors.add(f'json/{lang}.json mist sleutel: {key}')
        for key in sorted(flat[lang].keys() - base.keys()):
            errors.add(f'json/{lang}.json heeft extra sleutel: {key}')
        for key in sorted(base.keys() & flat[lang].keys()):
            a, b = base[key], flat[lang][key]
            if type(a) is not type(b):
                errors.add(f'{key}: type verschilt (nl: {type(a).__name__}, {lang}: {type(b).__name__})')

    for lang in LANGS:
        src = f'json/{lang}.json'
        for key, value in flat[lang].items():
            last = key.rsplit('.', 1)[-1]
            # 2. lege waarden
            if value in ('', None, [], {}):
                if last not in OPTIONAL_EMPTY:
                    errors.add(f'{src}: {key} is leeg (verplicht veld)')
            elif not isinstance(value, (str, int, float, bool)):
                errors.add(f'{src}: {key} heeft een ongeldig type')
            # 3. toegestane HTML
            if isinstance(value, str):
                for m in TAG.finditer(value):
                    if m.group(2).lower() not in ALLOWED_TAGS or m.group(3).strip(' /'):
                        errors.add(f'{src}: {key} bevat niet-toegestane HTML: {m.group(0)}')
                if re.search(r'<!--|<!\[|javascript:', value, re.I):
                    errors.add(f'{src}: {key} bevat niet-toegestane inhoud')

    # 4. optionele velden: leeg in beide talen of ingevuld in beide
    for key in sorted(base):
        if key.rsplit('.', 1)[-1] in OPTIONAL_EMPTY:
            filled = {lang: bool(flat[lang].get(key)) for lang in LANGS if key in flat[lang]}
            if len(set(filled.values())) > 1:
                detail = ', '.join(f'{l}: {"ingevuld" if f else "leeg"}' for l, f in filled.items())
                errors.add(f'{key}: in de ene taal ingevuld, in de andere leeg ({detail})')

    # 5. pagina-metadata (leeg wordt hierboven al gemeld; hier alleen: ontbreekt)
    for lang in LANGS:
        for pid in PAGES:
            for field in ('title', 'description'):
                if f'pages.{pid}.{field}' not in flat[lang]:
                    errors.add(f'json/{lang}.json: pages.{pid}.{field} ontbreekt')


def check_runtime_json(texts, errors):
    """De json-bestanden die js/ op de site zelf inleest."""
    topo = load_json(ROOT / 'json' / 'topology.json', errors)
    if topo is not None:
        nodes = topo.get('nodes') if isinstance(topo, dict) else None
        if not isinstance(nodes, list) or not nodes:
            errors.add('json/topology.json: "nodes" moet een niet-lege lijst zijn')
            nodes = []
        ids = set()
        for i, n in enumerate(nodes):
            if not (isinstance(n, dict) and isinstance(n.get('id'), str) and n['id']):
                errors.add(f'json/topology.json: nodes.{i} heeft geen id')
                continue
            if n['id'] in ids:
                errors.add(f'json/topology.json: dubbele id "{n["id"]}"')
            ids.add(n['id'])
            pos = n.get('pos')
            if not (isinstance(pos, list) and len(pos) == 3 and all(isinstance(p, (int, float)) for p in pos)):
                errors.add(f'json/topology.json: nodes.{i} ({n["id"]}): pos moet [x, y, z] zijn')
        for i, link in enumerate(topo.get('links', []) if isinstance(topo, dict) else []):
            ends = list(link.values()) if isinstance(link, dict) else link if isinstance(link, list) else []
            for end in ends:
                if isinstance(end, str) and end not in ids:
                    errors.add(f'json/topology.json: links.{i} verwijst naar onbekende node "{end}"')
        for lang in LANGS:
            try:
                text_nodes = texts[lang]['home']['topology']['nodes']
            except (KeyError, TypeError):
                continue
            for i, n in enumerate(text_nodes):
                if isinstance(n, dict) and n.get('id') not in ids:
                    errors.add(f'json/{lang}.json: home.topology.nodes.{i}: id "{n.get("id")}" '
                               f'bestaat niet in json/topology.json')

    globe = load_json(ROOT / 'json' / 'globe.json', errors)
    if globe is not None:
        for key in ('cities', 'arcs', 'dots'):
            if not isinstance(globe, dict) or not isinstance(globe.get(key), list):
                errors.add(f'json/globe.json: "{key}" moet een lijst zijn')

    news = load_json(ROOT / 'json' / 'news.json', errors)
    if news is not None:
        items = news.get('items') if isinstance(news, dict) else None
        if not isinstance(items, list):
            errors.add('json/news.json: "items" moet een lijst zijn')
            items = []
        for i, item in enumerate(items):
            for field in ('source', 'url', 'title'):
                if not (isinstance(item, dict) and isinstance(item.get(field), str) and item[field].strip()):
                    errors.add(f'json/news.json: items.{i}.{field} ontbreekt of is leeg')
            if isinstance(item, dict) and isinstance(item.get('url'), str) \
                    and not item['url'].startswith('https://'):
                errors.add(f'json/news.json: items.{i}.url moet met https:// beginnen')


# ── Mini-Markdown voor lab notes ──────────────────────────────
SAFE_URL = re.compile(r'^(https?://|mailto:|/|\./|\.\./|#)')


def md_inline(text):
    """Inline-opmaak. Alles wordt eerst ge-escaped: ruwe HTML in een artikel blijft tekst."""
    codes = []

    def stash(m):
        codes.append(f'<code>{html.escape(m.group(1))}</code>')
        return f'\x00{len(codes) - 1}\x00'

    text = re.sub(r'`([^`]+)`', stash, text)
    text = html.escape(text, quote=False)

    def link(m):
        url = html.unescape(m.group(2)).strip()
        if not SAFE_URL.match(url):
            return m.group(0)
        ext = ' rel="noopener noreferrer"' if url.startswith('http') else ''
        return f'<a href="{html.escape(url, quote=True)}"{ext}>{m.group(1)}</a>'

    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])', r'<em>\1</em>', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: codes[int(m.group(1))], text)


def md_to_html(src):
    out, para, items, list_tag, quote = [], [], [], None, []

    def flush():
        nonlocal para, items, list_tag, quote
        if para:
            out.append(f'<p>{md_inline(" ".join(para))}</p>')
        if items:
            lis = ''.join(f'<li>{md_inline(i)}</li>' for i in items)
            out.append(f'<{list_tag}>{lis}</{list_tag}>')
        if quote:
            out.append(f'<blockquote><p>{md_inline(" ".join(quote))}</p></blockquote>')
        para, items, list_tag, quote = [], [], None, []

    lines = src.replace('\r\n', '\n').split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.startswith('```'):
            flush()
            lang = re.sub(r'[^\w-]', '', line[3:].strip())
            code = []
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i])
                i += 1
            i += 1
            cls = f' class="language-{lang}"' if lang else ''
            out.append(f'<pre><code{cls}>{html.escape(chr(10).join(code))}</code></pre>')
            continue
        m_head = re.match(r'^(#{1,3})\s+(.*)$', line)
        m_ul = re.match(r'^\s*[-*]\s+(.*)$', line)
        m_ol = re.match(r'^\s*\d+[.)]\s+(.*)$', line)
        if not line.strip():
            flush()
        elif m_head:
            flush()
            level = 3 if len(m_head.group(1)) == 3 else 2    # h1 is de titel van de pagina
            out.append(f'<h{level}>{md_inline(m_head.group(2))}</h{level}>')
        elif m_ul or m_ol:
            tag = 'ul' if m_ul else 'ol'
            if para or quote or (list_tag and list_tag != tag):
                flush()
            list_tag = tag
            items.append((m_ul or m_ol).group(1))
        elif line.startswith('>'):
            if para or items:
                flush()
            quote.append(line.lstrip('> ').strip())
        elif items and line.startswith(('  ', '\t')):
            items[-1] += ' ' + line.strip()                 # vervolgregel van een lijstitem
        else:
            if items or quote:
                flush()
            para.append(line.strip())
    flush()
    return '\n'.join(out)


# ── Lab notes laden en controleren ────────────────────────────
def load_notes(lang, errors):
    """Leest notes/<taal>/*.md → lijst van dicts, nieuwste eerst."""
    notes = []
    folder = ROOT / 'notes' / lang
    if not folder.is_dir():
        return notes
    for path in sorted(folder.iterdir()):
        name = rel(path)
        if path.name in IGNORED_NAMES:
            continue
        if path.is_symlink() or not path.is_file() or path.suffix != '.md':
            errors.add(f'{name}: alleen .md-bestanden horen in notes/{lang}/')
            continue
        if not SLUG.match(path.stem):
            errors.add(f'{name}: bestandsnaam moet een slug zijn (a-z, 0-9, koppeltekens), bv. vlan-hopping.md')
            continue
        try:
            raw = path.read_text(encoding='utf-8').replace('\r\n', '\n').lstrip('﻿')
        except UnicodeDecodeError:
            errors.add(f'{name}: geen geldige UTF-8')
            continue
        m = re.match(r'^---\n(.*?)\n---[ \t]*(?:\n(.*))?$', raw, re.S)
        if not m:
            errors.add(f'{name}: kopblok ontbreekt of is niet afgesloten (--- … --- bovenaan)')
            continue
        meta, bad = {}, False
        for n, line in enumerate(m.group(1).split('\n'), start=2):
            if not line.strip():
                continue
            if ':' not in line:
                errors.add(f'{name}, regel {n}: verwacht "sleutel: waarde", gevonden: {line.strip()!r}')
                bad = True
                continue
            key, value = (s.strip() for s in line.split(':', 1))
            if key not in NOTE_KEYS:
                errors.add(f'{name}, regel {n}: onbekende sleutel "{key}" (toegestaan: {", ".join(NOTE_KEYS)})')
                bad = True
            elif key in meta:
                errors.add(f'{name}, regel {n}: sleutel "{key}" staat er twee keer')
                bad = True
            else:
                meta[key] = value.strip('"\'') if len(value) > 1 and value[0] == value[-1] in '"\'' else value
        for key in NOTE_KEYS:
            if not meta.get(key):
                errors.add(f'{name}: "{key}:" ontbreekt of is leeg in het kopblok')
                bad = True
        if meta.get('date'):
            try:
                datetime.date.fromisoformat(meta['date'])
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', meta['date']):
                    raise ValueError
            except ValueError:
                errors.add(f'{name}: date "{meta["date"]}" is geen geldige datum (JJJJ-MM-DD)')
                bad = True
        body = (m.group(2) or '').strip()
        if not body:
            errors.add(f'{name}: de tekst onder het kopblok is leeg')
            bad = True
        if bad:
            continue
        slug = path.stem
        notes.append({**meta, 'slug': slug, 'file': f'{slug}.html', 'body': md_to_html(body)})
    return sorted(notes, key=lambda n: (n['date'], n['slug']), reverse=True)


def check_notes_parity(notes, errors):
    slugs = {lang: {n['slug'] for n in notes[lang]} for lang in LANGS}
    for lang in LANGS:
        for other in LANGS:
            if other == lang:
                continue
            for slug in sorted(slugs[lang] - slugs[other]):
                errors.add(f'notes/{lang}/{slug}.md heeft geen vertaling: notes/{other}/{slug}.md ontbreekt')


# ── Uploads en statische bestanden ────────────────────────────
def sniff(data):
    if data[:3] == b'\xff\xd8\xff':
        return 'jpeg'
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    if data[4:8] == b'ftyp' and data[8:12] in (b'avif', b'avis'):
        return 'avif'
    return None


def find_metadata(data, kind):
    """Zoekt EXIF/XMP/IPTC-blokken (o.a. GPS, camera). Geeft een lijst namen terug; leeg = schoon.
    Alleen de standaardbibliotheek: de containerstructuur van elk formaat wordt doorlopen."""
    found = []
    if kind == 'jpeg':
        i = 2
        while i + 4 <= len(data) and data[i] == 0xFF:
            marker = data[i + 1]
            if marker == 0xFF:                       # opvulbyte
                i += 1
                continue
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            if marker in (0xDA, 0xD9):               # begin beelddata / einde: geen metadata meer
                break
            length = int.from_bytes(data[i + 2:i + 4], 'big')
            body = data[i + 4:i + 2 + length]
            if marker == 0xE1 and body.startswith(b'Exif\x00'):
                found.append('EXIF')
            elif marker == 0xE1 and body.startswith((b'http://ns.adobe.com/xap/1.0/', b'http://ns.adobe.com/xmp/')):
                found.append('XMP')
            elif marker == 0xED:
                found.append('IPTC/Photoshop')
            i += 2 + length
    elif kind == 'png':
        i = 8
        while i + 8 <= len(data):
            length = int.from_bytes(data[i:i + 4], 'big')
            ctype = data[i + 4:i + 8]
            body = data[i + 8:i + 8 + length]
            if ctype == b'eXIf':
                found.append('EXIF')
            elif ctype in (b'iTXt', b'tEXt', b'zTXt') and body.startswith((b'XML:com.adobe.xmp', b'Raw profile type exif')):
                found.append('XMP' if body.startswith(b'XML') else 'EXIF')
            if ctype == b'IEND':
                break
            i += 12 + length
    elif kind == 'webp':
        i = 12
        while i + 8 <= len(data):
            ctype = data[i:i + 4]
            length = int.from_bytes(data[i + 4:i + 8], 'little')
            if ctype == b'EXIF':
                found.append('EXIF')
            elif ctype == b'XMP ':
                found.append('XMP')
            i += 8 + length + (length & 1)
    elif kind == 'avif':
        # Metadata staat als item in de 'meta'-box: item_type 'Exif' of 'mime' (XMP) in een 'infe'-box
        for m in re.finditer(rb'infe', data[:65536]):
            window = data[m.end():m.end() + 24]
            if b'Exif' in window:
                found.append('EXIF')
            elif b'mime' in window and b'rdf+xml' in data[m.end():m.end() + 64]:
                found.append('XMP')
    return sorted(set(found))


def check_uploads(errors):
    folder = ROOT / UPLOADS
    if not folder.exists():
        return
    for path in sorted(folder.rglob('*')):
        name = rel(path)
        if path.name in IGNORED_NAMES or path.is_dir() and not path.is_symlink():
            continue
        if path.is_symlink():
            errors.add(f'{name}: symbolische links zijn niet toegestaan')
            continue
        ext = path.suffix.lower()
        if ext not in UPLOAD_TYPES:
            errors.add(f'{name}: bestandstype niet toegestaan (alleen {", ".join(sorted(UPLOAD_TYPES))})')
            continue
        size = path.stat().st_size
        if size > UPLOAD_MAX_BYTES:
            errors.add(f'{name}: {size / 1048576:.1f} MB, maximum is {UPLOAD_MAX_BYTES // 1048576} MB')
            continue
        data = path.read_bytes()
        kind = sniff(data[:16])
        if kind != UPLOAD_TYPES[ext]:
            errors.add(f'{name}: inhoud is geen echte {ext[1:].upper()}-afbeelding')
            continue
        meta = find_metadata(data, kind)
        if meta:
            errors.add(f'{name}: bevat metadata ({", ".join(meta)}), mogelijk met GPS-locatie of '
                       f'cameragegevens. Verwijder die eerst (bv. opnieuw opslaan als webp via het CMS).')


def static_files(errors):
    """Alle bestanden uit STATIC als (bron, doel-pad in dist)."""
    files = []
    for entry, required in STATIC.items():
        src = ROOT / entry
        if src.is_symlink():
            errors.add(f'{entry}: symbolische links zijn niet toegestaan')
            continue
        if not src.exists():
            if required:
                errors.add(f'{entry} ontbreekt (verplicht in STATIC)')
            continue
        if src.is_file():
            files.append((src, entry))
            continue
        for path in sorted(src.rglob('*')):
            parts = path.relative_to(ROOT).parts
            if any(p in IGNORED_NAMES for p in parts):
                continue
            if path.is_symlink():
                errors.add(f'{rel(path)}: symbolische links zijn niet toegestaan')
            elif path.is_file():
                files.append((path, rel(path)))
    return files


# ── URL-helpers ───────────────────────────────────────────────
def lang_dir(lang):
    return '' if lang == DEFAULT_LANG else f'{lang}/'


def json_block(data):
    """JSON voor in een <script type="application/json"> (geen uitvoerbare code)."""
    return json.dumps(data, ensure_ascii=False).replace('</', '<\\/')


def terminal_data(t, urls):
    """Alles wat js/terminal.js nodig heeft, in de taal van de pagina."""
    return json_block({
        **t['home']['terminal']['cmd'],
        'whoami': t['home']['terminal']['whoami'],
        'skills': t['home']['terminal']['skills'],
        'projects': [c['title'] for group in t['projects']['groups'] for c in group['cards']],
        'urls': {'projects': urls['projects'], 'contact': urls['contact']},
    })


# ── Pagina's renderen (in het geheugen) ───────────────────────
def render_page(texts, lang, rel_path, template, alt_paths, extra, page_opts=None, active=None, hreflangs=LANGS):
    """Rendert één pagina en geeft (pad in dist, html) terug.
       rel_path   : pad binnen de taalmap (bv. 'cv.html' of 'lab-notes/x.html')
       alt_paths  : {taal: pad binnen díe taalmap} voor de taalwisselaar
       hreflangs  : talen waarvoor alt_paths een echte vertaling is (hreflang-tags)
    """
    page_opts = page_opts or {}
    depth = rel_path.count('/')
    base = '../' * depth                                   # terug naar de taalmap
    root = base + ('' if lang == DEFAULT_LANG else '../')   # terug naar de site-root

    def absolute(l, path):
        path = re.sub(r'(^|/)index\.html$', r'\1', path)
        return f'{SITE_URL}/{lang_dir(l)}{path}'

    ctx = {
        **texts[lang],
        'lang': lang,
        'root': root,
        'base': base,
        # links naar de andere pagina's in dezelfde taal
        'url': {pid: n[lang] for pid, n in PAGES.items()},
        'notes_url': f'{NOTES_DIR}/index.html',
        'active': {pid: ' class="active" aria-current="page"' if pid == active else ''
                   for pid in list(PAGES) + ['notes']},
        'cta_current': ' aria-current="page"' if active == 'contact' else '',
        'extra_styles': page_opts.get('styles', []),
        'extra_modules': page_opts.get('modules', []),
        'preloads': page_opts.get('preloads', []),
        # SEO: canonical + hreflang (absolute URL's)
        'canonical': absolute(lang, rel_path),
        'alts': [{'lang': l, 'href': absolute(l, alt_paths[l])} for l in hreflangs],
        'x_default': absolute(DEFAULT_LANG, alt_paths[DEFAULT_LANG]) if DEFAULT_LANG in hreflangs else '',
        # taalwisselaar: zelfde pagina in de andere taal (relatief pad)
        'switch': {l: f'{root}{lang_dir(l)}{p}' for l, p in alt_paths.items()},
        'lang_current': {l: ' aria-current="true"' if l == lang else '' for l in LANGS},
        'generated_note': GENERATED_NOTE,
        **extra,
    }
    try:
        ctx['terminal_json'] = terminal_data(texts[lang], ctx['url'])
    except (KeyError, TypeError) as e:
        raise BuildError(f'json/{lang}.json: gegevens voor de terminal ontbreken ({e})')
    ctx['content'] = render(template, ctx).rstrip('\n')
    return f'{lang_dir(lang)}{rel_path}', render('_layout.html', ctx)


def render_site(texts, notes, errors):
    pages = {}

    def add(*args, **kwargs):
        try:
            path, out = render_page(*args, **kwargs)
            pages[path] = out
        except BuildError as e:
            errors.add(str(e))

    for lang in LANGS:
        common = {'has_notes': bool(notes[lang])}       # nav-link alleen als er artikels zijn

        # Gewone pagina's
        for page_id, names in PAGES.items():
            add(texts, lang, names[lang], f'{page_id}.html',
                alt_paths={l: names[l] for l in LANGS},
                extra={**common, 'page': texts[lang]['pages'][page_id]},
                page_opts=names, active=page_id)

        # Lab notes: lijst + één pagina per artikel (elk artikel bestaat in alle talen)
        if notes[lang]:
            add(texts, lang, f'{NOTES_DIR}/index.html', 'notes-index.html',
                alt_paths={l: f'{NOTES_DIR}/index.html' for l in LANGS},
                extra={**common, 'notes_list': notes[lang],
                       'page': {'title': f'{texts[lang]["notes"]["title"]} — Ali Tunç',
                                'description': texts[lang]['notes']['intro']}},
                active='notes')
            for note in notes[lang]:
                add(texts, lang, f'{NOTES_DIR}/{note["file"]}', 'note.html',
                    alt_paths={l: f'{NOTES_DIR}/{note["file"]}' for l in LANGS},
                    extra={**common, 'note': note,
                           'page': {'title': f'{note["title"]} — Ali Tunç',
                                    'description': note['description']}},
                    active='notes')
    return pages


# ── Schrijven naar dist/ ──────────────────────────────────────
def write_dist(pages, files):
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir()
    for path, content in pages.items():
        out = TMP / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding='utf-8', newline='\n')
    for src, dest in files:
        out = TMP / dest
        if out.exists():
            raise BuildError(f'{dest}: botst met een gegenereerde pagina')
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
    if DIST.exists():
        shutil.rmtree(DIST)
    TMP.rename(DIST)


def build(list_output=False):
    errors = Errors()

    # 1. Controle
    texts = {lang: load_json(ROOT / 'json' / f'{lang}.json', errors) for lang in LANGS}
    texts_ok = all(isinstance(t, dict) for t in texts.values())
    if texts_ok:
        check_texts(texts, errors)
        check_runtime_json(texts, errors)
    notes = {lang: load_notes(lang, errors) for lang in LANGS}
    check_notes_parity(notes, errors)
    check_uploads(errors)
    files = static_files(errors)

    # 2. Renderen (alleen als de teksten bruikbaar zijn; template-fouten worden ook verzameld)
    pages = render_site(texts, notes, errors) if texts_ok and not errors else {}

    if errors:
        print(f'BUILD MISLUKT — {len(errors)} fout(en):', file=sys.stderr)
        for e in errors:
            print(f'  FOUT: {e}', file=sys.stderr)
        print('dist/ is niet aangepast.', file=sys.stderr)
        sys.exit(1)

    # 3. Schrijven
    try:
        write_dist(pages, files)
    except (BuildError, OSError) as e:
        shutil.rmtree(TMP, ignore_errors=True)
        print(f'BUILD MISLUKT bij het schrijven: {e}', file=sys.stderr)
        print('Tip: staat dist/ nog open in een server of verkenner? Sluit die en probeer opnieuw.',
              file=sys.stderr)
        sys.exit(1)

    out_files = sorted(p for p in DIST.rglob('*') if p.is_file())
    size = sum(p.stat().st_size for p in out_files)
    print(f'OK: {len(pages)} pagina\'s ({", ".join(LANGS)}) + {len(files)} statische bestanden '
          f'→ dist/ ({len(out_files)} bestanden, {size / 1024:.0f} KB)')
    if list_output:
        for p in out_files:
            print(f'  {p.relative_to(DIST).as_posix():60} {p.stat().st_size:>9}')


if __name__ == '__main__':
    args = sys.argv[1:]
    if any(a not in ('--list',) for a in args):
        sys.exit('Gebruik: python build.py [--list]')
    build(list_output='--list' in args)
