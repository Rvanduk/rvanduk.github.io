#!/usr/bin/env python3
"""Build the diary for GitHub Pages from Pages CMS Markdown posts."""
from pathlib import Path
from datetime import date
from html import escape
from urllib.parse import quote
import re, shutil
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

def build():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copy2(ROOT / "index.html", OUT / "index.html")
    if (ROOT / "media").exists(): shutil.copytree(ROOT / "media", OUT / "media")
    if (ROOT / "assets").exists(): shutil.copytree(ROOT / "assets", OUT / "assets")
    posts = load_posts()
    index = (OUT / "index.html").read_text(encoding="utf-8")
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
    (OUT / "index.html").write_text(index, encoding="utf-8")
    for p in posts:
        folder = OUT / "posts" / p["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        content = f'<article class="hero" style="padding-top:55px"><div class="eyebrow">{safe(p["category"])} · {safe(p["project"])} / {safe(p["date"])}</div><h1 style="font-size:clamp(36px,6vw,65px)">{safe(p["title"])}</h1><p class="lead">{safe(p["excerpt"])}</p>'
        if p["cover"]: content += f'<img src="{safe(p["cover"])}" alt="" style="margin-top:30px;max-width:100%;height:auto">'
        content += '<div class="entry" style="margin-top:40px;font-size:19px;line-height:1.85;overflow-wrap:anywhere">' + p["html"] + '</div><p style="margin-top:45px"><a href="/#journal">← Все записи</a></p></article>'
        # Reuse the same global styles and header/footer.
        template = index.replace('<main class="wrap">', '<main class="wrap">' + content + '<div style="display:none">', 1)
        template = template.replace('</main><footer', '</div></main><footer', 1)
        template = re.sub(r'<title>.*?</title>', '<title>' + safe(p["title"]) + ' — Side Quest</title>', template, count=1)
        folder.joinpath("index.html").write_text(template, encoding="utf-8")
    print(f"Built {len(posts)} published post(s)")

if __name__ == "__main__": build()
