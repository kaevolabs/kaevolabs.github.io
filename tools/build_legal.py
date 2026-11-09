"""
Kaevo Labs sitesi (kaevolabs.github.io): bir uygulamanın yasal metinlerini Markdown'dan HTML'e çevirir ve
ana sayfayı sitedeki BÜTÜN uygulamalardan yeniden kurar.

Her uygulama deposunda bir klasör (ör. docs/legal) şunları tutar:
  app.json                       {"slug", "name", "name_tr", "tagline", "docs": ["privacy", "terms"]}
  privacy-en.md, privacy-tr.md   (docs listesindeki her belge için iki dil)
Çıktı:
  /<slug>/<doc>/      İngilizce     /<slug>/<doc>/tr/   Türkçe
  /<slug>/app.json    ana sayfanın bu uygulamayı tanıması için (elle düzenlenmez)
  /                   ana sayfa: sitede app.json'u olan her uygulama, sırası app.json'daki "order"
Kullanım:  python tools/build_legal.py <uygulamanın yasal klasörü> [site klasörü]
Site klasörü verilmezse bu dosyanın bir üstü. Sonra site deposunda commit + push (GitHub Pages yayınlar).
"""
import html
import json
import sys
from pathlib import Path

import markdown

CONTACT = 'kaevolabs@gmail.com'
LANGS = {'en': 'English', 'tr': 'Türkçe'}
DOC_TITLES = {'privacy': {'en': 'Privacy Policy', 'tr': 'Gizlilik Politikası'},
              'terms': {'en': 'Terms of Use', 'tr': 'Kullanım Şartları'}}
UI = {
    'en': {'contact': 'Contact'},
    'tr': {'contact': 'İletişim'},
}

CSS = """
:root {
  --bg: #f7f5f0; --paper: #fffdf8; --ink: #1f2326; --muted: #5e676d; --line: #e4dfd4;
  --accent: #0b6e7a; --accent-ink: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #0f1416; --paper: #151c1f; --ink: #e8e6e1; --muted: #9aa5ab; --line: #26302f;
          --accent: #4fb8c4; --accent-ink: #0f1416; }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 17px/1.65 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
a { color: var(--accent); }
.wrap { max-width: 760px; margin: 0 auto; padding: 0 20px; }
header { border-bottom: 1px solid var(--line); background: var(--paper); }
header .wrap { display: flex; align-items: center; justify-content: space-between; gap: 12px;
  min-height: 60px; flex-wrap: wrap; }
.brand { font-weight: 700; letter-spacing: 0.02em; color: var(--ink); text-decoration: none; }
.brand span { color: var(--accent); }
.langs { display: flex; gap: 6px; }
.langs a { padding: 4px 10px; border: 1px solid var(--line); border-radius: 999px; text-decoration: none;
  color: var(--muted); font-size: 14px; }
.langs a[aria-current] { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
main { padding: 36px 0 56px; }
main h1 { font-size: 30px; line-height: 1.2; margin: 0 0 6px; }
main h2 { font-size: 21px; margin: 36px 0 8px; padding-top: 14px; border-top: 1px solid var(--line); }
main h3 { font-size: 17px; margin: 24px 0 6px; }
main p, main li { color: var(--ink); }
main table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 15px; display: block;
  overflow-x: auto; }
main th, main td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
main th { color: var(--muted); font-weight: 600; }
main code { font-size: 0.92em; }
.meta { color: var(--muted); }
.apps { list-style: none; padding: 0; }
.apps li { background: var(--paper); border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px;
  margin: 12px 0; }
.apps strong { font-size: 19px; }
footer { border-top: 1px solid var(--line); color: var(--muted); font-size: 14px; padding: 22px 0 40px; }
"""


def page(lang: str, title: str, body: str, langs_nav: str = '') -> str:
    t = UI[lang]
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(title)} · Kaevo Labs">
<style>{CSS}</style>
</head>
<body>
<header><div class="wrap">
  <a class="brand" href="/">Kaevo<span>Labs</span></a>
  {langs_nav}
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">© 2026 Kaevo Labs · {t['contact']}: <a href="mailto:{CONTACT}">{CONTACT}</a></div></footer>
</body>
</html>
"""


def write(out: Path, rel: str, content: str) -> None:
    path = out / rel / 'index.html' if rel else out / 'index.html'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')
    print('  ', path.relative_to(out))


def doc_url(slug: str, doc: str, lang: str) -> str:
    return f'/{slug}/{doc}/' + ('' if lang == 'en' else f'{lang}/')


def build_app(src: Path, out: Path) -> dict:
    app = json.loads((src / 'app.json').read_text(encoding='utf-8'))
    for doc in app['docs']:
        for lang in LANGS:
            text = (src / f'{doc}-{lang}.md').read_text(encoding='utf-8')
            body = markdown.markdown(text, extensions=['tables'])
            nav = '<nav class="langs">' + ''.join(
                f'<a href="{doc_url(app["slug"], doc, code)}"{" aria-current=page" if code == lang else ""}>{name}</a>'
                for code, name in LANGS.items()
            ) + '</nav>'
            name = app['name'] if lang == 'en' else app['name_tr']
            write(out, doc_url(app['slug'], doc, lang).strip('/'),
                  page(lang, f"{name} — {DOC_TITLES[doc][lang]}", body, nav))
    meta = out / app['slug'] / 'app.json'
    meta.write_text(json.dumps(app, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return app


def build_home(out: Path) -> None:
    apps = [json.loads(p.read_text(encoding='utf-8')) for p in out.glob('*/app.json')]
    apps.sort(key=lambda a: (a.get('order', 99), a['name']))
    items = []
    for app in apps:
        links = ' · '.join(
            f'<a href="{doc_url(app["slug"], doc, lang)}">{DOC_TITLES[doc][lang]}{"" if lang == "en" else " (TR)"}</a>'
            for doc in app['docs'] for lang in LANGS
        )
        items.append(f"""  <li><strong>{html.escape(app['name'])}</strong> <span class="meta">({html.escape(app['name_tr'])})</span><br>
  {html.escape(app['tagline'])}<br>{links}</li>""")
    home = '<h1>Kaevo Labs</h1>\n<p class="meta">Independent apps and games by Mehmet Kaya.</p>\n' \
           '<ul class="apps">\n' + '\n'.join(items) + '\n</ul>'
    write(out, '', page('en', 'Kaevo Labs', home))
    (out / '404.html').write_text(
        page('en', 'Not found · Kaevo Labs', '<h1>Page not found</h1><p><a href="/">Kaevo Labs</a></p>'),
        encoding='utf-8', newline='\n')


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent
    out.mkdir(parents=True, exist_ok=True)
    (out / '.nojekyll').write_text('', encoding='utf-8')
    print('site:', out)
    app = build_app(src, out)
    print('uygulama:', app['slug'])
    build_home(out)


if __name__ == '__main__':
    main()
