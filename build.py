#!/usr/bin/env python3
"""
build.py — genereert de statische HTML-pagina's van alitunc.net in twee talen.

GEBRUIK
    python build.py            (uitvoeren in de map van de site)

WAT HET DOET
    json/nl.json + templates/  →  *.html in de root        (Nederlands, standaard)
    json/en.json + templates/  →  en/*.html                (Engels)
    notes/nl/*.md, notes/en/*.md  →  lab-notes/ en en/lab-notes/   (zie LAB NOTES)

    Elke pagina krijgt automatisch: <html lang>, canonical, hreflang-tags
    en de taalwisselaar in de nav die naar dezelfde pagina in de andere taal wijst.

WERKWIJZE
    - Tekst aanpassen      → json/nl.json en json/en.json (zelfde sleutels in beide)
    - Opmaak/structuur     → templates/_layout.html (nav, footer) of templates/<pagina>.html
    - Nieuwe pagina        → rij toevoegen in PAGES hieronder + templates/<id>.html
                             + "pages.<id>" (title, description) in beide json-bestanden
    - Daarna altijd `python build.py` draaien en het resultaat committen.
    De gegenereerde .html-bestanden NIET rechtstreeks bewerken: ze worden overschreven.

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
    Een artikel dat maar in één taal bestaat, krijgt geen taalwisselaar-link
    naar het artikel maar naar de lijst in de andere taal.

TEMPLATE-SYNTAX (bewust minimaal, alleen de standaardbibliotheek van Python)
    {{ pad.naar.sleutel }}                tekst, HTML wordt ge-escaped
    {{{ pad.naar.sleutel }}}              ruwe HTML (alleen voor tekst met <strong> e.d.)
    {% for x in pad.naar.lijst %} … {% endfor %}
    {% if pad.naar.sleutel %} … {% endif %}     (leeg/ontbrekend = niet tonen)

Een ontbrekende sleutel of een verschil tussen nl.json en en.json stopt de build
met een duidelijke foutmelding.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
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

GENERATED_NOTE = '<!-- GEGENEREERD door build.py (templates/ + json/) — niet rechtstreeks bewerken -->'


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


def render(template_name, ctx):
    src = (ROOT / 'templates' / template_name).read_text(encoding='utf-8')
    nodes, _ = parse(TOKEN.split(src))
    try:
        return evaluate(nodes, ctx)
    except KeyError as e:
        sys.exit(f'FOUT: sleutel {e} ontbreekt (template {template_name}, taal {ctx["lang"]})')


# ── Controle: beide talen moeten dezelfde structuur hebben ────
def shape(value, prefix=''):
    """Alle sleutelpaden van een json-structuur (lijsten met index)."""
    if isinstance(value, dict):
        return {p for k, v in value.items() for p in shape(v, f'{prefix}{k}.')}
    if isinstance(value, list):
        return {p for n, v in enumerate(value) for p in shape(v, f'{prefix}{n}.')}
    return {prefix.rstrip('.')}


def check_parity(texts):
    base = shape(texts[DEFAULT_LANG])
    ok = True
    for lang in LANGS:
        missing = sorted(base - shape(texts[lang]))
        extra = sorted(shape(texts[lang]) - base)
        for key in missing:
            print(f'FOUT: json/{lang}.json mist sleutel: {key}')
        for key in extra:
            print(f'FOUT: json/{lang}.json heeft extra sleutel: {key}')
        ok = ok and not missing and not extra
    if not ok:
        sys.exit('Build gestopt: nl.json en en.json moeten dezelfde sleutels hebben.')


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


def load_notes(lang):
    """Leest notes/<taal>/*.md → lijst van dicts, nieuwste eerst."""
    notes = []
    folder = ROOT / 'notes' / lang
    for path in sorted(folder.glob('*.md')) if folder.is_dir() else []:
        raw = path.read_text(encoding='utf-8').replace('\r\n', '\n')
        m = re.match(r'^---\n(.*?)\n---\n?(.*)$', raw, re.S)
        if not m:
            sys.exit(f'FOUT: {path.relative_to(ROOT)} mist het blok met title/date/description bovenaan (--- … ---)')
        meta = dict((k.strip(), v.strip()) for k, v in
                    (ln.split(':', 1) for ln in m.group(1).split('\n') if ':' in ln))
        for key in ('title', 'date', 'description'):
            if not meta.get(key):
                sys.exit(f'FOUT: {path.relative_to(ROOT)} mist "{key}:" bovenaan')
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', meta['date']):
            sys.exit(f'FOUT: {path.relative_to(ROOT)}: date moet JJJJ-MM-DD zijn')
        slug = re.sub(r'[^a-z0-9-]', '-', path.stem.lower()).strip('-')
        notes.append({**meta, 'slug': slug, 'file': f'{slug}.html', 'body': md_to_html(m.group(2))})
    return sorted(notes, key=lambda n: n['date'], reverse=True)


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


def write_page(texts, lang, rel_path, template, alt_paths, extra, page_opts=None, active=None, hreflangs=LANGS):
    """Rendert één pagina.
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
    ctx['terminal_json'] = terminal_data(texts[lang], ctx['url'])
    ctx['content'] = render(template, ctx).rstrip('\n')
    out = ROOT / lang_dir(lang) / rel_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render('_layout.html', ctx), encoding='utf-8', newline='\n')


def build():
    texts = {lang: json.loads((ROOT / 'json' / f'{lang}.json').read_text(encoding='utf-8'))
             for lang in LANGS}
    check_parity(texts)

    notes = {lang: load_notes(lang) for lang in LANGS}
    count = 0

    for lang in LANGS:
        common = {'has_notes': bool(notes[lang])}       # nav-link alleen als er artikels zijn

        # Gewone pagina's
        for page_id, names in PAGES.items():
            write_page(texts, lang, names[lang], f'{page_id}.html',
                       alt_paths={l: names[l] for l in LANGS},
                       extra={**common, 'page': texts[lang]['pages'][page_id]},
                       page_opts=names, active=page_id)
            count += 1

        # Lab notes: lijst + één pagina per artikel
        if notes[lang]:
            index_alts = {l: f'{NOTES_DIR}/index.html' if notes[l] else PAGES['home'][l] for l in LANGS}
            write_page(texts, lang, f'{NOTES_DIR}/index.html', 'notes-index.html',
                       alt_paths=index_alts, hreflangs=[l for l in LANGS if notes[l]],
                       extra={**common, 'notes_list': notes[lang],
                              'page': {'title': f'{texts[lang]["notes"]["title"]} — Ali Tunç',
                                       'description': texts[lang]['notes']['intro']}},
                       active='notes')
            count += 1
            for note in notes[lang]:
                # Vertaling = zelfde bestandsnaam in de andere taal; anders naar de lijst
                alts = {}
                for l in LANGS:
                    if any(n['slug'] == note['slug'] for n in notes[l]):
                        alts[l] = f'{NOTES_DIR}/{note["file"]}'
                    elif notes[l]:
                        alts[l] = f'{NOTES_DIR}/index.html'
                    else:
                        alts[l] = PAGES['home'][l]
                translated = [l for l in LANGS if any(n['slug'] == note['slug'] for n in notes[l])]
                write_page(texts, lang, f'{NOTES_DIR}/{note["file"]}', 'note.html',
                           alt_paths=alts, hreflangs=translated,
                           extra={**common, 'note': note,
                                  'page': {'title': f'{note["title"]} — Ali Tunç',
                                           'description': note['description']}},
                           active='notes')
                count += 1

    print(f'OK: {count} pagina\'s gegenereerd ({", ".join(LANGS)}).')


if __name__ == '__main__':
    build()
