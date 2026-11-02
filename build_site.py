#!/usr/bin/env python3
"""Build the diary for GitHub Pages from Pages CMS Markdown posts."""
from pathlib import Path
from datetime import date
from html import escape
from urllib.parse import quote
import re, shutil
from PIL import Image, ImageOps
from email.utils import format_datetime
from datetime import datetime, timezone
from xml.sax.saxutils import escape as xml_escape
import yaml
import markdown

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
SRC = ROOT / "content" / "posts"

def safe(s):
    return escape(str(s or ""), quote=True)

def load_posts():
    posts = []
    for path in sorted(SRC.glob("*.md")) if SRC.exists() else []:
        raw = path.read_text(encoding="utf-8")
        if not raw.startswith("---"):
            continue
        parts = raw.split("---", 2)
        if len(parts) != 3: continue
        data = yaml.safe_load(parts[1]) or {}
        if data.get("published", True) is not True: continue
        d = str(data.get("date") or "")
        slug = path.stem
        posts.append({
            "slug": slug, "title": str(data.get("title") or slug),
            "date": d, "category": str(data.get("category") or "Разработка"), "project": str(data.get("project") or "Мастерская"),
            "excerpt": str(data.get("excerpt") or ""),
            "cover": str(data.get("cover") or ""),
            "html": markdown.markdown(parts[2], extensions=["extra", "sane_lists"]),
        })
    return sorted(posts, key=lambda p: (p["date"], p["slug"]), reverse=True)


def load_projects():
    items = []
    directory = ROOT / "content" / "projects"
    if not directory.exists():
        return items
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        if not raw.startswith("---"):
            continue
        parts = raw.split("---", 2)
        if len(parts) != 3:
            continue
        data = yaml.safe_load(parts[1]) or {}
        if data.get("published", True) is not True:
            continue
        items.append({
            "slug": path.stem,
            "title": str(data.get("title") or path.stem),
            "description": str(data.get("description") or ""),
            "status": str(data.get("status") or "В разработке"),
            "cover": str(data.get("cover") or ""),
            "download": str(data.get("download") or ""),
            "html": markdown.markdown(parts[2], extensions=["extra", "sane_lists"]),
        })
    return items

def build():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copy2(ROOT / "index.html", OUT / "index.html")
    if (ROOT / "media").exists(): shutil.copytree(ROOT / "media", OUT / "media")
    if (ROOT / "assets").exists(): shutil.copytree(ROOT / "assets", OUT / "assets")
    posts = load_posts()
    index = (OUT / "index.html").read_text(encoding="utf-8")
    projects = load_projects()
    def project_for(post):
        value = post["project"].strip().casefold()
        return next((p for p in projects if value and value in (p["title"].strip().casefold(), p["slug"].strip().casefold())), None)
    if posts:
        cards = []
        for p in posts[:12]:
            link = "/posts/" + quote(p["slug"]) + "/"
            cover = f'<a href="{link}"><img loading="lazy" style="display:block;max-width:100%;max-height:360px;margin:16px 0;object-fit:cover" src="{safe(p["cover"])}" alt=""></a>' if p["cover"] else ""
            cards.append(f'<article class="post" data-category="{safe(p["category"])}"><div class="meta">{safe(p["date"])}<br>{safe(p["category"]).upper()}</div><div><div class="tag">{safe(p["project"]).upper()}</div><h3><a href="{link}">{safe(p["title"])}</a></h3><p>{safe(p["excerpt"])}</p>{cover}<a class="more" href="{link}">Читать запись →</a></div></article>')
        heading = '<div class="sectionhead"><h2>Последние публикации</h2><small>ПОСЛЕДНИЕ ЗАПИСИ</small></div>'
        section = '<section class="section" id="journal">' + heading + "".join(cards) + '</section>'
        index, count = re.subn(r'<section class="section" id="journal">.*?</section>', lambda _: section, index, flags=re.S)
        if count != 1: raise RuntimeError("Could not find journal section")
        newest = posts[0]
        latest_link = "/posts/" + quote(newest["slug"]) + "/"
        latest_cover = newest["cover"] or "/assets/side-quest-landscape.svg"
        featured = (f'<div class="feature" id="featured"><a href="{latest_link}">'
                    f'<img class="feature-art" loading="lazy" src="{safe(latest_cover)}" alt=""></a>'
                    f'<div><div class="tag">{safe(newest["category"])}</div>'
                    f'<h3><a href="{latest_link}">{safe(newest["title"])}</a></h3>'
                    f'<p>{safe(newest["excerpt"])}</p>'
                    f'<a class="more" href="{latest_link}">Читать запись →</a></div></div>')
        index, feature_count = re.subn(r'<div class="feature" id="featured">.*?</div></div>', lambda _: featured, index, count=1, flags=re.S)
        if feature_count != 1: raise RuntimeError("Could not find featured article")

    if projects:
        cards = []
        for p in projects:
            link = "/projects/" + quote(p["slug"]) + "/"
            cover = (f'<img src="{safe(p["cover"])}" alt="" loading="lazy" '
                     f'style="width:100%;aspect-ratio:16/9;object-fit:cover;border:1px solid var(--edge)">') if p["cover"] else ""
            cards.append(f'<a class="project" href="{link}" style="display:block">'
                         f'{cover}<h3>{safe(p["title"])} ↗</h3>'
                         f'<p>{safe(p["description"])}</p>'
                         f'<div class="tag">{safe(p["status"])}</div></a>')
        section = '<aside class="projects" id="projects"><h2>Мои проекты</h2>' + "".join(cards) + '<a class="projects-all" href="/projects/">Все проекты →</a></aside>'
        index, count = re.subn(r'<aside class="projects" id="projects">.*?</aside>',
                                lambda _: section, index, count=1, flags=re.S)
        if count != 1:
            raise RuntimeError("Could not locate projects sidebar")
    (OUT / "index.html").write_text(index, encoding="utf-8")
    # Article pages share the journal's masthead and footer, without hiding
    # a second copy of the homepage behind the article.
    page_head = index.split('<main class="wrap">', 1)[0]
    page_foot = index.split('<footer class="wrap foot">', 1)[1]
    for p in posts:
        folder = OUT / "posts" / p["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        meta = f'<span>{safe(p["date"])}</span><span>{safe(p["category"])}</span>'
        linked = project_for(p)
        if linked:
            meta += f'<a href="/projects/{quote(linked["slug"])}/">Проект: {safe(linked["title"])} ↗</a>'
        elif p["project"]:
            meta += f'<span>{safe(p["project"])}</span>'
        lead = f'<p class="article-lead">{safe(p["excerpt"])}</p>' if p["excerpt"] else ""
        cover = (f'<figure class="article-cover"><img src="{safe(p["cover"])}" alt="" loading="eager"></figure>'
                 if p["cover"] else "")
        project_back = (f'<a href="/projects/{quote(linked["slug"])}/">← К проекту {safe(linked["title"])}</a> · ' if linked else "")
        article = (f'<main class="wrap"><article class="article-shell">'
                   f'<a class="article-back" href="/#journal">← К журналу</a>'
                   f'<header class="article-header"><div class="article-meta">{meta}</div>'
                   f'<h1>{safe(p["title"])}</h1>{lead}</header>'
                   f'{cover}<div class="entry">{p["html"]}</div>'
                   f'<div class="article-end">{project_back}<a href="/archive/">Все публикации →</a></div>'
                   f'</article></main>')
        template = page_head + article + '<footer class="wrap foot">' + page_foot
        template = re.sub(r'<title>.*?</title>',
                          '<title>' + safe(p["title"]) + ' — Side Quest</title>',
                          template, count=1)
        folder.joinpath("index.html").write_text(template, encoding="utf-8")

    for p in projects:
        folder = OUT / "projects" / p["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        cover = (f'<figure class="article-cover"><img src="{safe(p["cover"])}" alt=""></figure>'
                 if p["cover"] else "")
        download = ""
        if p["download"].startswith(("https://", "http://")):
            download = f'<p><a class="paperlink" href="{safe(p["download"])}" rel="noopener noreferrer">Скачать или открыть проект ↗</a></p>'
        related = [post for post in posts if project_for(post) and project_for(post)["slug"] == p["slug"]]
        related_html = '<section class="project-diary"><h2>Дневник разработки</h2>'
        if related:
            for post in related:
                href = "/posts/" + quote(post["slug"]) + "/"
                related_html += (f'<article class="archive-item"><div class="meta">{safe(post["date"])}</div>'
                                 f'<div><h3><a href="{href}">{safe(post["title"])}</a></h3>'
                                 f'<p>{safe(post["excerpt"])}</p></div></article>')
        else:
            related_html += '<p class="project-diary-empty">Публикаций пока нет. Здесь появятся записи, связанные с проектом.</p>'
        related_html += '</section>'
        article = (f'<main class="wrap"><article class="article-shell">'
                   f'<a class="article-back" href="/#projects">← К проектам</a>'
                   f'<header class="article-header"><div class="article-meta">{safe(p["status"])}</div>'
                   f'<h1>{safe(p["title"])}</h1>'
                   f'<p class="article-lead">{safe(p["description"])}</p></header>'
                   f'{cover}<div class="entry">{p["html"]}{download}</div>{related_html}</article></main>')
        template = page_head + article + '<footer class="wrap foot">' + page_foot
        template = re.sub(r'<title>.*?</title>',
                          '<title>' + safe(p["title"]) + ' — Side Quest</title>',
                          template, count=1)
        folder.joinpath("index.html").write_text(template, encoding="utf-8")

    # Fully static archive, searchable on the visitor's device.
    archive_items = []
    years, categories, project_names = set(), set(), set()
    for p in posts:
        year = p["date"][:4] if len(p["date"]) >= 4 else "Без даты"
        years.add(year)
        categories.add(p["category"])
        if p["project"]:
            project_names.add(p["project"])
        archive_items.append({
            "title": p["title"], "date": p["date"], "year": year,
            "category": p["category"], "project": p["project"],
            "excerpt": p["excerpt"], "url": "/posts/" + quote(p["slug"]) + "/",
            "search": re.sub(r'<[^>]+>', ' ', p["html"]),
        })
    import json
    archive_folder = OUT / "archive"
    archive_folder.mkdir(parents=True, exist_ok=True)
    json_data = json.dumps(archive_items, ensure_ascii=False).replace("<", "\\u003c")
    archive_html = ('''<main class="wrap"><section class="archive-head"><div class="eyebrow">SIDE QUEST / КАРТОТЕКА ЭКСПЕДИЦИЙ</div>
<h1>Архив приключений.</h1><p>Все заметки, игры и открытия в одном месте. Можно искать даже по тексту публикаций.</p></section>
<div class="archive-controls"><input id="archive-search" type="search" placeholder="Поиск по публикациям…" aria-label="Поиск">
<select id="archive-category" aria-label="Раздел"><option value="">Все разделы</option></select>
<select id="archive-project" aria-label="Проект"><option value="">Все проекты</option></select>
<select id="archive-year" aria-label="Год"><option value="">Все годы</option></select></div>
<div class="archive-status" id="archive-status" role="status"></div>
<div id="archive-results"></div><noscript>Для фильтрации записей необходим JavaScript.</noscript></main>''')
    archive_script = """<script id="archive-data" type="application/json">""" + json_data + """</script>
<script>(()=> {
const records=JSON.parse(document.getElementById('archive-data').textContent);
const search=document.getElementById('archive-search'),category=document.getElementById('archive-category'),
project=document.getElementById('archive-project'),year=document.getElementById('archive-year'),
results=document.getElementById('archive-results'),status=document.getElementById('archive-status');
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function populate(select,values){for(const value of [...new Set(values)].filter(Boolean).sort().reverse()){const option=document.createElement('option');option.value=value;option.textContent=value;select.append(option)}}
populate(category,records.map(p=>p.category));populate(project,records.map(p=>p.project));populate(year,records.map(p=>p.year));
function render(){
const q=search.value.toLocaleLowerCase('ru').trim();
const filtered=records.filter(p=>(!q||[p.title,p.excerpt,p.category,p.project,p.search].join(' ').toLocaleLowerCase('ru').includes(q))&&(!category.value||p.category===category.value)&&(!project.value||p.project===project.value)&&(!year.value||p.year===year.value));
status.textContent='Найдено публикаций: '+filtered.length;
results.replaceChildren();
if(!filtered.length){const empty=document.createElement('p');empty.className='archive-empty';empty.textContent='Ничего не найдено. Попробуй другой запрос.';results.append(empty);return}
const groups=new Map();for(const p of filtered){if(!groups.has(p.year))groups.set(p.year,[]);groups.get(p.year).push(p)}
for(const [yr,items] of groups){const section=document.createElement('section');section.className='archive-year';section.innerHTML='<h2>'+escapeHTML(yr)+'</h2>';for(const p of items){const el=document.createElement('article');el.className='archive-item';el.innerHTML='<div class="meta">'+escapeHTML(p.date)+'<br>'+escapeHTML(p.category)+'</div><div><h3><a href="'+encodeURI(p.url)+'">'+escapeHTML(p.title)+'</a></h3><p>'+escapeHTML(p.excerpt)+'</p><span class="tag">'+escapeHTML(p.project)+'</span></div>';section.append(el)}results.append(section)}
}
for(const el of [search,category,project,year])el.addEventListener(el===search?'input':'change',render);
render();
})();</script>"""
    archive_page = page_head + archive_html + '<footer class="wrap foot">' + page_foot
    archive_page = archive_page.replace('</body></html>', archive_script + '</body></html>')
    archive_page = re.sub(r'<title>.*?</title>', '<title>Архив — Side Quest</title>', archive_page, count=1)
    (archive_folder / "index.html").write_text(archive_page, encoding="utf-8")
    # RSS 2.0: generated from published posts only, newest first.
    rss_items = []
    for p in posts[:30]:
        url = "https://rvanduk.github.io/posts/" + quote(p["slug"]) + "/"
        try:
            published = format_datetime(datetime.fromisoformat(p["date"]).replace(tzinfo=timezone.utc))
        except ValueError:
            published = None
        rss_items.append(
            "<item><title>" + xml_escape(p["title"]) + "</title>"
            + "<link>" + xml_escape(url) + "</link>"
            + "<guid isPermaLink=\"true\">" + xml_escape(url) + "</guid>"
            + ("<pubDate>" + published + "</pubDate>" if published else "")
            + "<description>" + xml_escape(p["excerpt"]) + "</description>"
            + "<category>" + xml_escape(p["category"]) + "</category>"
            + "</item>"
        )
    rss = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0"><channel>'
           '<title>Side Quest</title>'
           '<link>https://rvanduk.github.io/</link>'
           '<description>Игры, книги, код и неизведанное.</description>'
           '<language>ru</language>'
           '<atom:link xmlns:atom="http://www.w3.org/2005/Atom" '
           'href="https://rvanduk.github.io/rss.xml" rel="self" type="application/rss+xml"/>'
           + "".join(rss_items) + '</channel></rss>')
    (OUT / "rss.xml").write_text(rss, encoding="utf-8")

    # Full project directory is available on all screen sizes.
    catalog = OUT / "projects"
    catalog.mkdir(parents=True, exist_ok=True)
    catalog_cards = []
    for p in projects:
        link = "/projects/" + quote(p["slug"]) + "/"
        cover = (f'<img loading="lazy" src="{safe(p["cover"])}" alt="">'
                 if p["cover"] else '<img src="/assets/side-quest-landscape.svg" alt="">')
        catalog_cards.append(
            f'<a class="catalog-card" href="{link}">{cover}'
            f'<div class="tag">{safe(p["status"])}</div><h2>{safe(p["title"])}</h2>'
            f'<p>{safe(p["description"])}</p><span class="paperlink">Открыть проект →</span></a>')
    catalog_body = (
        '<main class="wrap"><section class="archive-head"><div class="eyebrow">SIDE QUEST / СВОИ МИРЫ</div>'
        '<h1>Мои проекты.</h1><p>Игры, эксперименты и истории, над которыми я работаю.</p></section>'
        '<div class="catalog-grid">' + "".join(catalog_cards) + '</div></main>')
    catalog_page = page_head + catalog_body + '<footer class="wrap foot">' + page_foot
    catalog_page = re.sub(r'<title>.*?</title>', '<title>Проекты — Side Quest</title>', catalog_page, count=1)
    (catalog / "index.html").write_text(catalog_page, encoding="utf-8")

    # Search index and share previews.
    base = "https://rvanduk.github.io"
    urls = [base + "/", base + "/archive/", base + "/projects/"]
    urls += [base + "/posts/" + quote(p["slug"]) + "/" for p in posts]
    urls += [base + "/projects/" + quote(p["slug"]) + "/" for p in projects]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>' + xml_escape(url) + '</loc></url>' for url in urls) + '</urlset>'
    (OUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\\nAllow: /\\nSitemap: " + base + "/sitemap.xml\\n", encoding="utf-8")
    for folder in [OUT / "archive", OUT / "projects"] + [OUT / "posts" / p["slug"] for p in posts] + [OUT / "projects" / p["slug"] for p in projects]:
        target = folder / "index.html"
        doc = target.read_text(encoding="utf-8")
        url = base + "/" + folder.relative_to(OUT).as_posix() + "/"
        title_match = re.search(r'<title>(.*?)</title>', doc, flags=re.S)
        title = title_match.group(1) if title_match else "Side Quest"
        meta = (f'<link rel="canonical" href="{safe(url)}">'
                f'<meta property="og:url" content="{safe(url)}">'
                f'<meta property="og:title" content="{title}">')
        doc = doc.replace("</head>", meta + "</head>", 1)
        target.write_text(doc, encoding="utf-8")
    optimized = {}
    # Re-process all previously uploaded photos on every build, not just new ones.
    for image_dir in (OUT / "media", OUT / "assets"):
        if not image_dir.exists():
            continue
        for photo in image_dir.rglob("*"):
            if photo.suffix.lower() not in (".jpg", ".jpeg", ".png") or not photo.is_file():
                continue
            try:
                with Image.open(photo) as raw:
                    pic = ImageOps.exif_transpose(raw)
                    pic.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                    if pic.mode not in ("RGB", "RGBA"):
                        pic = pic.convert("RGB")
                    target = photo.with_suffix(".webp")
                    pic.save(target, format="WEBP", quality=78, method=6)
                if target.stat().st_size < photo.stat().st_size:
                    optimized["/" + photo.relative_to(OUT).as_posix()] = "/" + target.relative_to(OUT).as_posix()
                else:
                    target.unlink()
            except OSError:
                print("Cannot compress", photo)
    for page in OUT.rglob("*.html"):
        html_source = page.read_text(encoding="utf-8")
        for old, new in optimized.items():
            html_source = html_source.replace('src="' + old + '"', 'src="' + new + '"')
            html_source = html_source.replace('url("' + old + '")', 'url("' + new + '")')
            html_source = html_source.replace("url('" + old + "')", "url('" + new + "')")
        page.write_text(html_source, encoding="utf-8")
    print("Optimized existing and new images:", len(optimized))
    print(f"Built {len(posts)} posts and {len(projects)} projects")

if __name__ == "__main__": build()
