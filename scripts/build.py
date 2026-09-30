#!/usr/bin/env python3
"""Build belihaazi.com from the content/ folder into dist/.

Run:  python scripts/build.py            (normal, fetches Medium, YouTube covers, paintings)
      python scripts/build.py --offline  (skips everything that needs the internet)
"""
import html, io, json, os, re, shutil, sys, urllib.parse, xml.etree.ElementTree as ET, zipfile
from datetime import date
from PIL import Image
import docx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "content")
SITE = os.path.join(ROOT, "site")
D = os.path.join(ROOT, "dist")
DOMAIN = "https://belihaazi.com"
OFFLINE = "--offline" in sys.argv
UA = {"User-Agent": "belihaazi.com site builder (utkarsh@1001stories.in)"}
MON = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
MN = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def log(*a): print("·", *a, flush=True)
def load(p, default=None):
    p = os.path.join(C, p)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default
def slugify(t): return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60] or "piece"

def get(url, timeout=20):
    if OFFLINE: return None
    try:
        import requests
        r = requests.get(url, headers=UA, timeout=timeout)
        return r.content if r.ok else None
    except Exception as e:
        log("could not fetch", url, e); return None

def save_img(data_or_img, rel, size=900, q=74, og=False):
    rel = os.path.splitext(rel)[0] + ".webp"
    out = os.path.join(D, rel); os.makedirs(os.path.dirname(out), exist_ok=True)
    try:
        im = data_or_img if isinstance(data_or_img, Image.Image) else Image.open(io.BytesIO(data_or_img) if isinstance(data_or_img, bytes) else data_or_img)
        im = im.convert("RGB"); im.thumbnail((size, size)); im.save(out, "WEBP", quality=q, method=6)
        if og:
            j = im.copy(); j.thumbnail((1200, 1200)); j.save(out[:-5] + ".jpg", quality=80, optimize=True)
        return rel
    except Exception as e:
        log("bad image", rel, e); return None

# ---------- writing (Word files) ----------
TITLES = load("titles.json", {})
def parse_name(fn):
    b = os.path.splitext(fn)[0]
    m = re.match(r"(.*?)[_\- ]+([A-Za-z]+)[_ ](\d{2,4})$", b)
    if m and m.group(2)[:3].lower() in MON:
        t, mo, y = b[:m.start(2) - 1], MON[m.group(2)[:3].lower()], int(m.group(3))
        y = y + 2000 if y < 100 else y
    else:
        t, mo, y = b, None, None
    t = t.strip()
    t = TITLES.get(t, re.sub(r"\s+", " ", t.replace("_s ", "'s ").replace("_", " ")).strip(" ."))
    return t, y, mo

def read_docx(path):
    d = docx.Document(path)
    paras = [p.text.strip() for p in d.paragraphs]
    paras = [p for p in paras if p and not p.startswith("Liked by")]
    best = None
    with zipfile.ZipFile(path) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/") and n.lower().endswith((".png", ".jpg", ".jpeg"))]
        if media:
            n = max(media, key=lambda n: z.getinfo(n).file_size)
            try:
                im = Image.open(io.BytesIO(z.read(n)))
                if im.width >= 120: best = im
            except Exception: pass
    return paras, best

def writing(kind, folder, shelves=None):
    items = []
    src = os.path.join(C, folder)
    for fn in sorted(os.listdir(src)):
        if not fn.lower().endswith(".docx") or fn.startswith("~"): continue
        t, y, mo = parse_name(fn)
        body, im = read_docx(os.path.join(src, fn))
        s = slugify(t)
        it = {"t": t, "y": y, "m": mo, "s": s, "kind": kind, "body": body,
              "img": save_img(im, f"img/w/{kind}-{s}.jpg", 640, og=True) if im else None}
        if shelves:
            it["shelf"] = next((k for k, v in shelves.items() if any(x.lower() in t.lower() for x in v)), list(shelves)[0])
        items.append(it)
    items.sort(key=lambda i: (i["y"] or 0, i["m"] or 0), reverse=True)
    log(kind, len(items), "pieces,", sum(1 for i in items if i["img"]), "with their own image")
    return items

# ---------- public-domain paintings for pieces without an image ----------
def commons(query):
    if OFFLINE: return None
    api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": query + " filetype:bitmap",
        "gsrlimit": 1, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 900, "format": "json"})
    raw = get(api)
    if not raw: return None
    try:
        page = next(iter(json.loads(raw)["query"]["pages"].values()))
        info = page["imageinfo"][0]
        meta = info.get("extmetadata", {})
        credit = re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
        return info.get("thumburl") or info["url"], page["title"], credit
    except Exception:
        return None

def add_art(items, art):
    for it in items:
        if it["img"]: continue
        a = art.get(it["t"])
        if not a: continue
        it["paint"] = {"palette": a.get("paint", "night"), "seed": len(it["t"]) * 17 + 3, "gap": 6,
                       "vortices": [[0.5, 0.45, 0.35, 1 if len(it["t"]) % 2 else -1]]}
        found = commons(a["search"]) if a.get("search") else None
        if found:
            url, title, credit = found
            data = get(url)
            if data:
                it["img"] = save_img(data, f"img/art/{it['kind']}-{it['s']}.jpg", 800, og=True)
                it["credit"] = f"{credit} · {title.replace('File:', '')} · Wikimedia Commons"
                log("painting for", it["t"], "→", title)

# ---------- Medium ----------
def medium():
    known = load("belihaazi/medium.json", [])
    posts = {p["link"].split("?")[0]: p for p in known}
    raw = get("https://medium.com/feed/@belihaazi")
    if raw:
        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
        for item in ET.fromstring(raw).iter("item"):
            link = item.findtext("link", "").split("?")[0]
            enc = item.findtext("content:encoded", "", ns)
            m = re.search(r'<img[^>]+src="([^"]+)"', enc)
            pd = item.findtext("pubDate", "")
            try:
                from email.utils import parsedate_to_datetime
                d = parsedate_to_datetime(pd).date().isoformat()
            except Exception: d = ""
            p = posts.get(link, {})
            p.update({"title": item.findtext("title", "").strip(), "link": link, "date": p.get("date") or d})
            if m and not p.get("image"): p["image"] = m.group(1)
            posts[link] = p
    out = []
    for p in sorted(posts.values(), key=lambda p: p.get("date", ""), reverse=True):
        img = None
        if p.get("image"):
            data = get(p["image"])
            if data: img = save_img(data, f"img/medium/{slugify(p['title'])}.jpg", 480)
        y, mo = (int(p["date"][:4]), int(p["date"][5:7])) if p.get("date") else (None, None)
        out.append({"t": p["title"], "link": p["link"], "img": img, "y": y, "m": mo, "pinned": p.get("pinned", False)})
    log("medium", len(out), "posts")
    return out

# ---------- piece pages (for search engines and sharing) ----------
PIECE_TPL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {site}</title><meta name="description" content="{desc}">
<link rel="canonical" href="{url}"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
{og}<meta property="og:type" content="article"><meta property="og:url" content="{url}">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&family=Cormorant+Garamond:ital,wght@0,400;1,500&family=Tiro+Devanagari+Hindi&family=IBM+Plex+Mono&display=swap">
<script type="application/ld+json">{ld}</script>
<style>
body{{margin:0;background:{bg};color:{fg};font-family:{font};font-size:20px;line-height:1.6}}
a{{color:inherit}} .w{{max-width:760px;margin:0 auto;padding:24px 16px 80px}}
nav{{display:flex;justify-content:space-between;border:3px solid {fg};margin-bottom:24px}} nav a{{padding:10px 14px;text-decoration:none;font-family:"IBM Plex Mono",monospace;font-size:12px;text-transform:uppercase}}
nav a+a{{border-left:3px solid {fg}}} img{{width:100%;max-height:60vh;object-fit:cover;border:3px solid {fg}}}
.m{{font-family:"IBM Plex Mono",monospace;font-size:12px;text-transform:uppercase;opacity:.7}}
h1{{font-size:clamp(34px,6vw,56px);line-height:1;margin:.3em 0 .6em;{h1}}}
p{{margin:0 0 {pgap}}} .cr{{font-family:"IBM Plex Mono",monospace;font-size:11px;opacity:.6;margin-top:6px}}
</style></head><body><div class="w">
<nav><a href="/">Home</a><a href="/{back}.html">← {backlabel}</a></nav>
{img}<p class="m">{date}</p><h1>{title}</h1>
{body}
</div></body></html>"""

def piece_pages(items, kind, dark):
    urls = []
    for it in items:
        rel = f"{kind}/{it['s']}/"
        url = f"{DOMAIN}/{rel}"
        desc = html.escape(" ".join(it["body"])[:155])
        d = (MN[it["m"]] + " " if it.get("m") else "") + (str(it["y"]) if it.get("y") else "")
        ld = {"@context": "https://schema.org", "@type": "CreativeWork" if kind != "povs" else "Article",
              "headline": it["t"], "author": {"@type": "Person", "name": "Utkarsh Singh", "alternateName": "belihaazi", "url": DOMAIN + "/utkarsh.html"},
              "url": url}
        if it.get("y"): ld["datePublished"] = f"{it['y']}-{(it.get('m') or 1):02d}-01"
        img = f'<img src="/{it["img"]}" alt="">' if it.get("img") else ""
        if it.get("credit"): img += f'<p class="cr">{html.escape(it["credit"])}</p>'
        page = PIECE_TPL.format(
            title=html.escape(it["t"]), site="belihaazi" if dark else "Utkarsh Singh", desc=desc, url=url,
            og=f'<meta property="og:image" content="{DOMAIN}/{it["img"][:-5]}.jpg">' if it.get("img") else "",
            ld=json.dumps(ld, ensure_ascii=False), bg="#07091A" if dark else "#F6F6F2", fg="#EDE4CC" if dark else "#0E0E0C",
            font='"Cormorant Garamond","Tiro Devanagari Hindi",serif' if dark else '"Archivo","Tiro Devanagari Hindi",sans-serif',
            h1="font-style:italic;font-weight:500" if dark else "font-stretch:80%;font-weight:900;text-transform:uppercase",
            pgap=".2em" if kind == "poems" else "1em", back="belihaazi" if dark else "utkarsh", backlabel="belihaazi" if dark else "Utkarsh",
            img=img, date=d, body="\n".join(f"<p>{html.escape(p)}</p>" for p in it["body"]))
        os.makedirs(os.path.join(D, rel), exist_ok=True)
        open(os.path.join(D, rel, "index.html"), "w", encoding="utf-8").write(page)
        urls.append(url)
    return urls

# ---------- main ----------
def main():
    shutil.rmtree(D, ignore_errors=True); os.makedirs(D)
    for f in os.listdir(SITE):
        src = os.path.join(SITE, f)
        if os.path.isdir(src): shutil.copytree(src, os.path.join(D, f))
        else: shutil.copy(src, D)

    shelves = load("utkarsh/shelves.json")
    data = {"povs": writing("povs", "utkarsh/povs", shelves),
            "prose": writing("prose", "belihaazi/prose"),
            "poems": writing("poems", "belihaazi/poems")}
    art = load("art.json", {})
    for k in data: add_art(data[k], art)

    # talks
    talks = load("utkarsh/talks.json", [])
    for i, t in enumerate(talks):
        if t.get("poster"):
            t["img"] = save_img(os.path.join(C, "utkarsh/talks", t["poster"]), f"img/talks/{i}.jpg", 480)
        if t.get("youtube"):
            data_ = get(f"https://i.ytimg.com/vi/{t['youtube']}/hqdefault.jpg")
            t["img"] = save_img(data_, f"img/talks/yt-{t['youtube']}.jpg", 480) if data_ else None
            t["link"] = f"https://youtu.be/{t['youtube']}"
    data["talks"] = talks
    data["talk_photos"] = [save_img(os.path.join(C, "utkarsh/talk-photos", f), f"img/photos/{f}", 900)
                           for f in sorted(os.listdir(os.path.join(C, "utkarsh/talk-photos"))) if not f.startswith("portrait")]
    data["fieldwork"] = [save_img(os.path.join(C, "utkarsh/fieldwork", f), f"img/field/{f}", 800)
                         for f in sorted(os.listdir(os.path.join(C, "utkarsh/fieldwork")), key=lambda x: (len(x), x))]
    por = os.path.join(C, "utkarsh/talk-photos/portrait.jpg")
    if os.path.exists(por): save_img(por, "img/portrait.jpg", 700, og=True)

    reps = load("utkarsh/reports.json", [])
    for r in reps:
        r["img"] = save_img(os.path.join(C, "utkarsh/reports", r["cover"]), f"img/reports/{slugify(r['title'])}.jpg", 420)
        if r.get("pdf"):
            os.makedirs(os.path.join(D, "files"), exist_ok=True)
            shutil.copy(os.path.join(C, "utkarsh/reports", r["pdf"]), os.path.join(D, "files", r["pdf"]))
            r["pdf"] = "files/" + r["pdf"]
    data["reports"] = reps
    data["profile"] = load("utkarsh/profile.json", {})
    data["shelves"] = list((shelves or {}).keys())

    for key in ("spoken-word", "hip-hop"):
        m = load(f"belihaazi/{key}.json", {"items": []})
        for it in m["items"]:
            if it.get("cover"):
                cp = os.path.join(C, "belihaazi/covers", it["cover"])
                if os.path.exists(cp): it["img"] = save_img(cp, f"img/covers/{it['cover']}", 480)
            if it.get("video") and os.path.exists(os.path.join(C, "belihaazi/videos", it["video"])):
                os.makedirs(os.path.join(D, "video"), exist_ok=True)
                shutil.copy(os.path.join(C, "belihaazi/videos", it["video"]), os.path.join(D, "video", it["video"]))
                it["src"] = "video/" + it["video"]
        data[key.replace("-", "_")] = m["items"]
    data["medium"] = medium()

    json.dump(data, open(os.path.join(D, "data.json"), "w", encoding="utf-8"), ensure_ascii=False)

    urls = [DOMAIN + "/", DOMAIN + "/utkarsh.html", DOMAIN + "/belihaazi.html"]
    urls += piece_pages(data["povs"], "povs", False)
    urls += piece_pages(data["prose"], "prose", True)
    urls += piece_pages(data["poems"], "poems", True)
    today = date.today().isoformat()
    open(os.path.join(D, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    open(os.path.join(D, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    open(os.path.join(D, "CNAME"), "w").write("belihaazi.com\n")
    open(os.path.join(D, ".nojekyll"), "w").write("")
    log("done:", len(urls), "pages")

if __name__ == "__main__":
    main()
