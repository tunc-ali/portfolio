#!/usr/bin/env python3
"""
build.py — genereert de statische HTML-pagina's van alitunc.net in twee talen.

GEBRUIK
    python build.py            (uitvoeren in de map van de site)

WAT HET DOET
    json/nl.json + templates/  →  *.html in de root        (Nederlands, standaard)
    json/en.json + templates/  →  en/*.html                (Engels)

    Elke pagina krijgt automatisch: <html lang>, canonical, hreflang-tags
    en de taalwisselaar in de nav die naar dezelfde pagina in de andere taal wijst.

WERKWIJZE
    - Tekst aanpassen      → json/nl.json en json/en.json (zelfde sleutels in beide)
    - Opmaak/structuur     → templates/_layout.html (nav, footer) of templates/<pagina>.html
    - Nieuwe pagina        → rij toevoegen in PAGES hieronder + templates/<id>.html
                             + "pages.<id>" (title, description) in beide json-bestanden
    - Daarna altijd `python build.py` draaien en het resultaat committen.
    De gegenereerde .html-bestanden NIET rechtstreeks bewerken: ze worden overschreven.

TEMPLATE-SYNTAX (bewust minimaal, alleen de standaardbibliotheek van Python)
    {{ pad.naar.sleutel }}                tekst, HTML wordt ge-escaped
    {{{ pad.naar.sleutel }}}              ruwe HTML (alleen voor tekst met <strong> e.d.)
    {% for x in pad.naar.lijst %} … {% endfor %}

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
                 'modules': ['js/terminal.js', 'js/lazy-3d.js']},
    'services': {'nl': 'diensten.html',  'en': 'services.html'},
    'about':    {'nl': 'over-mij.html',  'en': 'about.html'},
    'projects': {'nl': 'projecten.html', 'en': 'projects.html'},
    'contact':  {'nl': 'contact.html',   'en': 'contact.html'},
    'cv':       {'nl': 'cv.html',        'en': 'cv.html'},
}

GENERATED_NOTE = '<!-- GEGENEREERD door build.py (templates/ + json/) — niet rechtstreeks bewerken -->'


# ── Mini template-engine ──────────────────────────────────────
TOKEN = re.compile(r'(\{\{\{.*?\}\}\}|\{\{.*?\}\}|\{%.*?%\})', re.S)
FOR = re.compile(r'^for\s+(\w+)\s+in\s+([\w.]+)$')


def parse(tokens, i=0, in_loop=False):
    """Zet tokens om in een boom: ('text', s) | ('var', pad, raw) | ('for', naam, pad, kinderen)."""
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
            if stmt == 'endfor':
                if not in_loop:
                    raise SyntaxError('{% endfor %} zonder {% for %}')
                return nodes, i
            m = FOR.match(stmt)
            if not m:
                raise SyntaxError(f'Onbekende template-instructie: {tok}')
            body, i = parse(tokens, i, in_loop=True)
            nodes.append(('for', m.group(1), m.group(2), body))
        elif tok:
            nodes.append(('text', tok))
    if in_loop:
        raise SyntaxError('{% for %} zonder {% endfor %}')
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
        if node[0] == 'text':
            out.append(node[1])
        elif node[0] == 'var':
            value = str(lookup(ctx, node[1]))
            out.append(value if node[2] else html.escape(value, quote=True))
        else:
            _, name, path, body = node
            for item in lookup(ctx, path):
                out.append(evaluate(body, {**ctx, name: item}))
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


# ── URL-helpers ───────────────────────────────────────────────
def json_block(data):
    """JSON voor in een <script type="application/json"> (geen uitvoerbare code)."""
    return json.dumps(data, ensure_ascii=False).replace('</', '<\\/')


def terminal_data(t, urls):
    """Alles wat js/terminal.js nodig heeft, in de taal van de pagina."""
    return json_block({
        **t['home']['terminal']['cmd'],
        'whoami': t['home']['terminal']['whoami'],
        'skills': t['home']['terminal']['skills'],
        'projects': [c['title'] for c in t['projects']['cards']],
        'urls': {'projects': urls['projects'], 'contact': urls['contact']},
    })


def lang_dir(lang):
    return '' if lang == DEFAULT_LANG else f'{lang}/'


def abs_url(page_id, lang):
    name = PAGES[page_id][lang]
    return f'{SITE_URL}/{lang_dir(lang)}{"" if name == "index.html" else name}'


def build():
    texts = {lang: json.loads((ROOT / 'json' / f'{lang}.json').read_text(encoding='utf-8'))
             for lang in LANGS}
    check_parity(texts)

    count = 0
    for lang in LANGS:
        root = '' if lang == DEFAULT_LANG else '../'      # pad terug naar de site-root
        out_dir = ROOT / lang_dir(lang)
        out_dir.mkdir(exist_ok=True)

        for page_id, names in PAGES.items():
            ctx = {
                **texts[lang],
                'lang': lang,
                'root': root,
                'page': texts[lang]['pages'][page_id],
                # links naar de andere pagina's in dezelfde taal
                'url': {pid: n[lang] for pid, n in PAGES.items()},
                'extra_styles': names.get('styles', []),
                'extra_modules': names.get('modules', []),
                'preloads': names.get('preloads', []),
                'active': {pid: ' class="active" aria-current="page"' if pid == page_id else ''
                           for pid in PAGES},
                'cta_current': ' aria-current="page"' if page_id == 'contact' else '',
                # SEO: canonical + hreflang (absolute URL's)
                'canonical': abs_url(page_id, lang),
                'alt': {l: abs_url(page_id, l) for l in LANGS},
                # taalwisselaar: zelfde pagina in de andere taal (relatief pad)
                'switch': {l: f'{root}{lang_dir(l)}{names[l]}' for l in LANGS},
                'lang_current': {l: ' aria-current="true"' if l == lang else '' for l in LANGS},
                'generated_note': GENERATED_NOTE,
            }
            ctx['terminal_json'] = terminal_data(texts[lang], ctx['url'])
            ctx['content'] = render(f'{page_id}.html', ctx).rstrip('\n')
            page_html = render('_layout.html', ctx)
            (out_dir / names[lang]).write_text(page_html, encoding='utf-8', newline='\n')
            count += 1

    print(f'OK: {count} pagina\'s gegenereerd ({", ".join(LANGS)}).')


if __name__ == '__main__':
    build()
