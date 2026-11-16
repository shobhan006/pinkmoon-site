#!/usr/bin/env python3
"""Build one static page per view of the site, plus sitemap.xml and 404.html.

The site is a single app (index.html). Search engines need a real URL for each view, with its own
title, description, heading and structured data in the HTML they receive. This script copies index.html
into a folder per view (about/, work/justmates/, justmates/episode-3/ ...) and swaps the page-level tags.
The SEO copy lives in index.html itself (the <script id="seo-data"> block), so the app and these pages
always agree.

Run from the repo root:  python3 tools/build_seo.py
A GitHub Action runs it on every push that changes index.html.
"""
import json, os, re, subprocess, html, shutil, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://pinkmoonhouse.com"
MEDIA = "https://media.pinkmoonhouse.com"
os.chdir(ROOT)

src = open("index.html", encoding="utf-8").read()
SEO = json.loads(re.search(r'<script type="application/json" id="seo-data">(.*?)</script>', src, re.S).group(1))
DUR = json.load(open("tools/video-durations.json"))

# what the app knows: series and their episode counts, IP pages and the films they play
SERIES = {}
for key, name, typ, count in re.findall(r'\n\s*(\w+): \{name:"([^"]+)", type:"([^"]+)", count:(\d+)', src):
    SERIES[key] = {"name": name, "type": typ, "count": int(count)}
SPATH = {"justmates": "justmates", "meninpink": "men-in-pink"}
IPS = re.findall(r'\{slug:"([a-z0-9-]+)", cat:"([^"]+)", logline:"([^"]+)".*?hero:"([^"]+)", thumb:"([^"]+)", watch:"([^"]+)"', src, re.S)
IP_SLUGS = [i[0] for i in IPS]
FILM_FILES = {"introducing-pinkmoon": "films/pinkmoon-loop.mp4", "wakeup": "films/wakeup-trailer.mp4",
              "jadeblue": "films/jadeblue-wedding-story.mp4", "tecno-mobile": "films/tecno-spark-go.mp4"}


def esc(s):
    return html.escape(html.unescape(s), quote=True)


def iso_dur(sec):
    sec = int(round(sec))
    return f"PT{sec // 60}M{sec % 60}S" if sec >= 60 else f"PT{sec}S"


def added(path):
    """Date a file first went into the repo, used as the video's upload date."""
    try:
        out = subprocess.run(["git", "log", "--diff-filter=A", "--follow", "--format=%aI", "--", path],
                             capture_output=True, text=True).stdout.split()
        return out[-1] if out else None
    except Exception:
        return None


TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).replace(microsecond=0).isoformat()
ORG = {"@type": "Organization", "@id": SITE + "/#org", "name": "PINKMOON", "url": SITE + "/"}


def crumbs(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + p} for i, (n, p) in enumerate(items)]}


def video_obj(name, desc, page, thumb, dur, content, embed_note=None, date=None):
    v = {"@type": "VideoObject", "name": name, "description": desc, "thumbnailUrl": [SITE + "/" + thumb],
         "uploadDate": date or TODAY, "contentUrl": content, "embedUrl": SITE + page, "url": SITE + page,
         "publisher": ORG}
    if dur:
        v["duration"] = iso_dur(dur)
    return v


pages = []  # (path, meta, jsonld list, og_image, video for sitemap)

# plain pages
for key, path, crumb in [("about", "/about/", "About"), ("archive", "/featured/", "Featured"), ("services", "/services/", "Services"),
                         ("team", "/team/", "Team"), ("contact", "/contact/", "Contact")]:
    ld = [crumbs([("PINKMOON", "/"), (crumb, path)])]
    if key == "team":
        ld.append({"@type": "Organization", "@id": SITE + "/#org", "name": "PINKMOON", "url": SITE + "/",
                   "founder": [{"@type": "Person", "name": "Kanishak Rajpal", "jobTitle": "Founder & Creative Director", "worksFor": {"@id": SITE + "/#org"}},
                               {"@type": "Person", "name": "Shobhan Sharma", "jobTitle": "Co-Founder & Filmmaker", "worksFor": {"@id": SITE + "/#org"}}]})
    if key == "contact":
        ld.append({"@type": "ContactPage", "url": SITE + path, "about": {"@id": SITE + "/#org"}})
    pages.append((path, SEO["pages"][key], ld, "img/landing-poster.jpg", None))

# IP pages
for slug, cat, logline, hero, thumb, watch in IPS:
    path = f"/work/{slug}/"
    meta = SEO["pages"]["ip-" + slug]
    ld = [crumbs([("PINKMOON", "/"), ("Featured", "/featured/"), (meta["h1"].split(",")[0], path)])]
    skey = next((k for k in SERIES if SPATH.get(k, k) == slug or k == slug), None)
    if skey:
        S = SERIES[skey]
        ld.append({"@type": "TVSeries", "name": S["name"], "description": html.unescape(logline), "url": SITE + path,
                   "image": SITE + "/" + hero, "numberOfEpisodes": S["count"], "productionCompany": {"@id": SITE + "/#org"},
                   "genre": "Comedy" if skey == "justmates" else "Drama"})
    else:
        ld.append({"@type": "CreativeWork", "name": meta["h1"], "description": html.unescape(logline), "url": SITE + path,
                   "image": SITE + "/" + hero, "creator": {"@id": SITE + "/#org"}})
    pages.append((path, meta, ld, hero, None))

# film watch pages
for i, (slug, cat, logline, hero, thumb, watch) in enumerate(IPS):
    if slug not in SEO["films"]:
        continue
    path = f"/watch/{slug}/"
    meta = SEO["films"][slug]
    f = FILM_FILES[slug]
    v = video_obj(meta["h1"].replace("Watch ", ""), meta["description"], path, thumb, DUR.get(slug), SITE + "/" + f, date=added(f))
    ld = [crumbs([("PINKMOON", "/"), ("Featured", "/featured/"), (meta["h1"], path)]), v]
    pages.append((path, meta, ld, thumb, v))

# series lists and every episode
for skey, S in SERIES.items():
    sp = "/" + SPATH.get(skey, skey) + "/"
    ld = [crumbs([("PINKMOON", "/"), ("Featured", "/featured/"), (S["name"], sp)]),
          {"@type": "TVSeries", "name": S["name"], "url": SITE + sp, "numberOfEpisodes": S["count"],
           "productionCompany": {"@id": SITE + "/#org"},
           "episode": [{"@type": "TVEpisode", "episodeNumber": n, "name": f"{S['name']} Episode {n}",
                        "url": f"{SITE}{sp}episode-{n}/"} for n in range(1, S["count"] + 1)]}]
    first_thumb = f"img/ep/{skey}-1.jpg"
    pages.append((sp, SEO["pages"][skey], ld, first_thumb if os.path.exists(first_thumb) else "img/landing-poster.jpg", None))
    for n in range(1, S["count"] + 1):
        path = f"{sp}episode-{n}/"
        title = f"{S['name']} Episode {n} | Watch Online | PINKMOON"
        desc = SEO["series"][skey]["episode"].replace("{n}", str(n))
        meta = {"title": title, "description": desc, "h1": f"{S['name']} Episode {n}"}
        thumb = f"img/ep/{skey}-{n}.jpg"
        if not os.path.exists(thumb):
            prev = f"films/{skey}-ep{n}.mp4"
            if os.path.exists(prev) and shutil.which("ffmpeg"):
                os.makedirs("img/ep", exist_ok=True)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "4", "-i", prev, "-frames:v", "1", "-vf", "scale=-2:960", "-q:v", "4", thumb])
        if not os.path.exists(thumb):
            thumb = "img/landing-poster.jpg"
        full = f"films/{skey}-ep{n}-full.mp4"
        content = SITE + "/" + full if os.path.exists(full) else f"{MEDIA}/{skey}/ep{n}/master.m3u8"
        dur = DUR.get(skey, {}).get(str(n)) if isinstance(DUR.get(skey), dict) else DUR.get(f"{skey}-{n}")
        v = video_obj(f"{S['name']} Episode {n}", desc, path, thumb, dur, content, date=added(f"films/{skey}-ep{n}.mp4"))
        ep = {"@type": "TVEpisode", "name": f"{S['name']} Episode {n}", "episodeNumber": n, "url": SITE + path,
              "partOfSeries": {"@type": "TVSeries", "name": S["name"], "url": SITE + sp}, "video": v}
        ld = [crumbs([("PINKMOON", "/"), (S["name"], sp), (f"Episode {n}", path)]), ep]
        pages.append((path, meta, ld, thumb, v))


def render(path, meta, ld, og_image, noindex=False):
    h = src
    url = SITE + path
    t = meta["title"]
    h = re.sub(r"<title>.*?</title>", f"<title>{t}</title>", h, count=1, flags=re.S)
    h = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(meta["description"])}">', h, count=1)
    h = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">', h, count=1)
    h = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">', h, count=1)
    h = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{t}">', h, count=1)
    h = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{esc(meta["description"])}">', h, count=1)
    h = re.sub(r'<meta property="og:image" content="[^"]*">', f'<meta property="og:image" content="{SITE}/{og_image}">', h, count=1)
    h = re.sub(r'<h1 id="seo-h1" class="sr">.*?</h1>', f'<h1 id="seo-h1" class="sr">{esc(meta.get("h1") or t.split(" | ")[0])}</h1>', h, count=1, flags=re.S)
    if noindex:
        h = h.replace('<base href="/">', '<base href="/">\n<meta name="robots" content="noindex">', 1)
    if ld:
        block = '<script type="application/ld+json" id="page-ld">' + json.dumps({"@context": "https://schema.org", "@graph": ld}, ensure_ascii=False) + "</script>\n"
        h = h.replace("</head>", block + "</head>", 1)
    return h


# clear old generated folders so removed views don't linger
GEN = ["about", "featured", "services", "team", "contact", "work", "watch"] + [SPATH.get(k, k) for k in SERIES]
for d in GEN:
    if os.path.isdir(d) and os.path.exists(os.path.join(d, ".generated")):
        shutil.rmtree(d)

for path, meta, ld, og, v in pages:
    out = path.strip("/") + "/index.html"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(render(path, meta, ld, og))
for d in GEN:
    if os.path.isdir(d):
        open(os.path.join(d, ".generated"), "w").write("made by tools/build_seo.py, do not edit by hand\n")

# 404 page: same app, not indexed
open("404.html", "w", encoding="utf-8").write(render("/404/", {"title": "Page not found | PINKMOON", "description": "This page does not exist on pinkmoonhouse.com.", "h1": "Page not found"}, None, "img/landing-poster.jpg", noindex=True))

# sitemap with video entries
def x(s):
    return html.escape(str(s), quote=True)

today = TODAY[:10]
lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">',
         f"  <url><loc>{SITE}/</loc><lastmod>{today}</lastmod></url>"]
for path, meta, ld, og, v in pages:
    lines.append(f"  <url><loc>{SITE}{path}</loc><lastmod>{today}</lastmod>")
    if v:
        lines.append("    <video:video>")
        lines.append(f"      <video:thumbnail_loc>{x(v['thumbnailUrl'][0])}</video:thumbnail_loc>")
        lines.append(f"      <video:title>{x(v['name'])}</video:title>")
        lines.append(f"      <video:description>{x(v['description'])}</video:description>")
        lines.append(f"      <video:content_loc>{x(v['contentUrl'])}</video:content_loc>")
        if v.get("duration"):
            s = re.match(r"PT(?:(\d+)M)?(\d+)S", v["duration"])
            lines.append(f"      <video:duration>{int(s.group(1) or 0) * 60 + int(s.group(2))}</video:duration>")
        lines.append(f"      <video:publication_date>{v['uploadDate']}</video:publication_date>")
        lines.append("      <video:family_friendly>yes</video:family_friendly>")
        lines.append("    </video:video>")
    lines.append("  </url>")
lines.append("</urlset>")
open("sitemap.xml", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"built {len(pages)} pages, sitemap with {len(pages) + 1} urls")
