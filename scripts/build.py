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
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}">
{twimg}<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="icon" href="/favicon.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&family=Cormorant+Garamond:ital,wght@0,400;1,500&family=Tiro+Devanagari+Hindi&family=IBM+Plex+Mono&display=swap">
<script type="application/ld+json">{ld}</script>
<style>
body{{margin:0;background:{bg};color:{fg};font-family:{font};font-size:20px;line-height:1.6}}
a{{color:inherit}} .w{{max-width:760px;margin:0 auto;padding:24px 16px 80px}}
nav{{display:flex;justify-content:space-between;border:3px solid {fg};margin-bottom:24px}} nav a{{padding:10px 14px;text-decoration:none;font-family:"IBM Plex Mono",monospace;font-size:12px;text-transform:uppercase}}
nav a+a{{border-left:3px solid {fg}}} img{{width:100%;max-height:60vh;object-fit:cover;border:3px solid {fg}}} img[alt=""]{{border:0}}
.m{{font-family:"IBM Plex Mono",monospace;font-size:12px;text-transform:uppercase;opacity:.7}}
h1{{font-size:clamp(34px,6vw,56px);line-height:1;margin:.3em 0 .6em;{h1}}}
p{{margin:0 0 {pgap}}} .cr{{font-family:"IBM Plex Mono",monospace;font-size:11px;opacity:.6;margin-top:6px}}
</style></head><body><div class="w">
<nav><a href="/">Home</a><a href="/{back}.html">← {backlabel}</a></nav>
{img}<p class="m">{date}</p><h1>{title}</h1>
{body}
<div data-social="{path}" data-title="{title}"></div>
<div data-subscribe hidden style="margin-top:28px"></div>
</div><script src="/config.js"></script><script src="/social.js"></script></body></html>"""

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
        img = f'<img src="/{it["img"]}" alt="{html.escape(it["t"])}">' if it.get("img") else ""
        if it.get("credit"): img += f'<p class="cr">{html.escape(it["credit"])}</p>'
        page = PIECE_TPL.format(
            title=html.escape(it["t"]), site="belihaazi" if dark else "Utkarsh Singh", desc=desc, url=url,
            og=f'<meta property="og:image" content="{DOMAIN}/{it["img"][:-5]}.jpg">' if it.get("img") else "",
            twimg=f'<meta name="twitter:image" content="{DOMAIN}/{it["img"][:-5]}.jpg">' if it.get("img") else "",
            ld=json.dumps(ld, ensure_ascii=False), bg="#07091A" if dark else "#F6F6F2", fg="#EDE4CC" if dark else "#0E0E0C",
            font='"Cormorant Garamond","Tiro Devanagari Hindi",serif' if dark else '"Archivo","Tiro Devanagari Hindi",sans-serif',
            h1="font-style:italic;font-weight:500" if dark else "font-stretch:80%;font-weight:900;text-transform:uppercase",
            pgap=".2em" if kind == "poems" else "1em", path="/" + rel, back="belihaazi" if dark else "utkarsh", backlabel="belihaazi" if dark else "Utkarsh",
            img=img, date=d, body="\n".join(f"<p>{html.escape(p)}</p>" for p in it["body"]))
        os.makedirs(os.path.join(D, rel), exist_ok=True)
        open(os.path.join(D, rel, "index.html"), "w", encoding="utf-8").write(page)
        urls.append(url)
    return urls

# ---------- report pages (1001 Stories BiteGeists: concepts as crawlable text) ----------
REPORT_TPL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · 1001 Stories BiteGeist · Utkarsh Singh</title><meta name="description" content="{desc}">
<link rel="canonical" href="{url}"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<meta property="og:image" content="{ogimg}"><meta property="og:type" content="article"><meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}"><meta name="twitter:image" content="{ogimg}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="icon" href="/favicon.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&family=IBM+Plex+Mono&display=swap">
<script type="application/ld+json">{ld}</script>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#F6F6F2;color:#0E0E0C;font-family:"Archivo",Arial,sans-serif;font-size:18px;line-height:1.6}}
a{{color:inherit}} .w{{max-width:820px;margin:0 auto;padding:24px 16px 80px}}
.m{{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.05em;text-transform:uppercase}}
nav{{display:flex;border:3px solid #0E0E0C;margin-bottom:24px}} nav a{{padding:10px 14px;text-decoration:none}} nav a+a{{border-left:3px solid #0E0E0C}}
.top{{display:grid;grid-template-columns:200px 1fr;gap:24px;align-items:start;border:3px solid #0E0E0C;padding:18px;background:#fff}}
.top img{{width:100%;border:3px solid #0E0E0C;display:block}}
h1{{font-size:clamp(32px,5.4vw,54px);line-height:.95;margin:.25em 0 .2em;font-stretch:80%;font-weight:900;text-transform:uppercase}}
.sub{{font-weight:700;margin:0 0 10px}} .by{{color:#5B5B55}}
.go{{display:inline-block;background:#0E0E0C;color:#F6F6F2;padding:12px 16px;text-decoration:none;font-weight:800;margin-top:10px}} .go:hover{{background:#F2B90F;color:#0E0E0C}}
.sum p{{max-width:66ch}}
h2{{font-stretch:80%;font-weight:900;text-transform:uppercase;font-size:30px;background:#0E0E0C;color:#F6F6F2;padding:6px 12px;margin:36px 0 0}}
.toc{{border:3px solid #0E0E0C;border-top:0;padding:12px 16px;columns:2;column-gap:24px}} .toc a{{display:block;text-decoration:none;padding:2px 0;break-inside:avoid}} .toc a:hover{{background:#F2B90F}}
.c{{border:3px solid #0E0E0C;border-top:0;padding:18px 18px 8px;background:#F6F6F2}} .c:target{{background:#FFF4CC}}
.c h3{{margin:4px 0 8px;font-size:24px;line-height:1.1;font-stretch:85%;font-weight:900}} .c p{{margin:0 0 12px;max-width:66ch}}
blockquote{{margin:0 0 12px;border-left:6px solid #F2B90F;padding:2px 0 2px 14px;font-size:16px}} blockquote footer{{font-size:13px;color:#5B5B55;margin-top:4px}}
.src{{font-size:12px;color:#5B5B55}}
.end{{margin-top:36px;border:3px solid #0E0E0C;padding:18px;box-shadow:10px 10px 0 #F2B90F;background:#fff}}
@media (max-width:640px){{.top{{grid-template-columns:1fr}} .top img{{max-width:220px}} .toc{{columns:1}}}}
</style></head><body><div class="w">
<nav class="m"><a href="/">Home</a><a href="/utkarsh.html#work">← Utkarsh</a></nav>
<header class="top"><img src="/{img}" alt="Cover of {title}">
<div><p class="m">{label}{year}</p><h1>{title}</h1><p class="sub">{subtitle}</p><p class="by">By {authors}</p>
<a class="go m" href="{link}">Read the full report on 1001 Stories ↗</a></div></header>
<section class="sum">{summary}</section>
<h2>Concepts in this report</h2>
<div class="toc">{toc}</div>
{concepts}
<section class="end"><p><b>This page is a summary.</b> The concepts above are from <i>{title}</i>, a BiteGeist by 1001 Stories. Page numbers refer to the report PDF. The full report, with its data, illustrations and sources, is published by 1001 Stories.</p>
<a class="go m" href="{link}">Read the full report on 1001 Stories ↗</a></section>
<div data-social="/{rel}" data-title="{title}"></div>
<div data-subscribe hidden style="margin-top:28px"></div>
</div><script src="/config.js"></script><script src="/social.js"></script></body></html>"""

def report_pages(reps):
    urls = []
    for r in reps:
        if not r.get("concepts"): continue
        rel = f"reports/{r['slug']}/"
        url = f"{DOMAIN}/{rel}"
        e = html.escape
        ct = e(r["title"].rstrip("."))
        cite = lambda p: (f'<a href="{r["source_pdf"]}#page={p}">{ct}, 1001 Stories, PDF p. {p}</a>' if r.get("source_pdf")
                          else f'<a href="{r["link"]}">{ct}, 1001 Stories, PDF p. {p}</a>')
        blocks, toc, terms = [], [], []
        for c in r["concepts"]:
            cid = slugify(c["name"])
            q = ""
            if c.get("quote"):
                q = f'<blockquote><p>“{e(c["quote"])}”</p><footer>{e(c["by"])}{", p. " + str(c["qpage"]) if c.get("qpage") else ""}</footer></blockquote>'
            aka = f'<p class="src">Also written as: {e(", ".join(c["aka"]))}</p>' if c.get("aka") else ""
            blocks.append(f'<section class="c" id="{cid}"><p class="m">{e(c["kind"])}</p><h3>{e(c["name"])}</h3>'
                          f'<p>{e(c["def"])}</p>{q}{aka}<p class="src">Source: {cite(c["page"])}</p></section>')
            toc.append(f'<a href="#{cid}">{e(c["name"])}</a>')
            t = {"@type": "DefinedTerm", "name": c["name"], "description": c["def"], "url": f"{url}#{cid}",
                 "termCode": cid, "inDefinedTermSet": url + "#concepts"}
            if c.get("aka"): t["alternateName"] = c["aka"]
            terms.append(t)
        people = [{"@type": "Person", "name": a, **({"url": DOMAIN + "/utkarsh.html"} if a == "Utkarsh Singh" else {})} for a in r["authors"]]
        org = {"@type": "Organization", "name": "1001 Stories", "url": "https://1001stories.com"}
        report = {"@type": "Report", "@id": url + "#report", "name": r["title"], "alternativeHeadline": r.get("subtitle", ""),
                  "author": people, "publisher": org, "url": url, "sameAs": r["link"],
                  "description": " ".join(r["summary"]), "about": [{"@id": url + "#concepts"}]}
        if r.get("year"): report["datePublished"] = str(r["year"])
        if r.get("source_pdf"): report["associatedMedia"] = {"@type": "MediaObject", "contentUrl": r["source_pdf"], "encodingFormat": "application/pdf"}
        ld = {"@context": "https://schema.org", "@graph": [report,
              {"@type": "DefinedTermSet", "@id": url + "#concepts", "name": f"Concepts from {r['title']} (1001 Stories)", "hasDefinedTerm": terms}]}
        desc = e(r["summary"][0][:150] + ("…" if len(r["summary"][0]) > 150 else ""))
        page = REPORT_TPL.format(
            rel=rel, title=e(r["title"]), subtitle=e(r.get("subtitle", "")), desc=desc, url=url, link=e(r["link"]),
            ogimg=f"{DOMAIN}/{r['img'][:-5]}.jpg", img=r["img"], label=e(r["label"]), year=f" · {r['year']}" if r.get("year") else "",
            authors=e(", ".join(r["authors"])), summary="".join(f"<p>{e(p)}</p>" for p in r["summary"]),
            toc="".join(toc), concepts="\n".join(blocks), ld=json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"))
        os.makedirs(os.path.join(D, rel), exist_ok=True)
        open(os.path.join(D, rel, "index.html"), "w", encoding="utf-8").write(page)
        r["page"] = rel
        urls.append(url)
    return urls

# ---------- pre-render: write the JS-drawn cards into the HTML, so crawlers that don't run JavaScript see everything ----------
def _inject(fname, empty_tag, inner):
    p = os.path.join(D, fname)
    s = open(p, encoding="utf-8").read()
    if empty_tag not in s:
        log("prerender: could not find", empty_tag, "in", fname); return
    open(p, "w", encoding="utf-8").write(s.replace(empty_tag, empty_tag[:-6] + inner + "</div>"))

def _date(i):
    return (MN[i["m"]] + " " if i.get("m") else "") + (str(i["y"]) if i.get("y") else "")

def _card(href, img, title, date, hidden=False, tag="", hi=False):
    e = html.escape
    im = f'<img src="{e(img)}" alt="{e(title)}" loading="lazy">' if img else f'<div class="t-over"><b>{e(title)}</b></div>'
    return (f'<a class="card" href="{e(href)}"{" hidden" if hidden else ""}><div class="im">{im}{tag}</div>'
            f'<div class="tx"><span class="mono">{e(date)}</span><b{" class=d" if hi else ""}>{e(title)}</b></div></a>')

def prerender_pages(data):
    e = html.escape
    # utkarsh.html: reports
    cards = []
    for r in data["reports"]:
        href = r.get("page") or r.get("pdf") or r.get("link")
        cards.append(f'<a href="{e(href)}"><img src="{r["img"]}" alt="Cover of {e(r["title"])}" loading="lazy">'
                     f'<span class="mono">{e(r["label"])}</span><b>{e(r["title"])}</b></a>')
    _inject("utkarsh.html", '<div class="cell rep" id="reps"></div>', "".join(cards))
    # utkarsh.html: talks
    talks = []
    for t in data["talks"]:
        im = f'<img src="{e(t["img"])}" alt="{e(t["title"])}" loading="lazy">' if t.get("img") else ""
        talks.append(f'<a class="talk" href="{e(t.get("link") or "#talks")}"><div class="th">{im}</div><div class="tx">'
                     f'<span class="mono">{e(t.get("date", ""))}</span><b>{e(t["title"])}</b><span>{e(t.get("where", ""))}</span></div></a>')
    _inject("utkarsh.html", '<div class="cell talks" id="talk-grid"></div>', "".join(talks))
    # utkarsh.html: POVs (all of them; only the default shelf is visible before the script takes over)
    shelves = data.get("shelves") or list(dict.fromkeys(p.get("shelf") for p in data["povs"]))
    first = shelves[0] if shelves else None
    _inject("utkarsh.html", '<div class="cell cards" id="pov-cards"></div>',
            "".join(_card(f"povs/{p['s']}/", p.get("img"), p["t"], _date(p), hidden=p.get("shelf") != first) for p in data["povs"]))
    # belihaazi.html: every room (poems visible, the rest hidden until their tab is opened)
    hi = lambda s: bool(re.search("[ऀ-ॿ]", s))
    out = [_card(f"poems/{i['s']}/", i.get("img"), i["t"], _date(i), hi=hi(i["t"])) for i in data["poems"]]
    out += [_card(f"prose/{i['s']}/", i.get("img"), i["t"], _date(i), hidden=True, hi=hi(i["t"])) for i in data["prose"]]
    for key in ("spoken_word", "hip_hop"):
        out += [_card(i.get("link") or "https://instagram.com/belihaazi", i.get("img"), i["title"], str(i.get("year", "")), hidden=True,
                      tag='<span class="tag mono">▶ Play</span>') for i in data[key]]
    out += [_card(p["link"], p.get("img"), p["t"], _date(p), hidden=True, tag='<span class="tag mono">Medium ↗</span>') for p in data["medium"]]
    _inject("belihaazi.html", '<div class="cards" id="cards"></div>', "".join(out))

def solve_lines(sv):
    if not sv: return []
    L = ["## What Utkarsh can solve for you", f"In his words: \"{sv['lead']}\"", ""]
    for a in sv["areas"]:
        L.append(f"- {a['name']}: " + "; ".join(a["problems"]) + ".")
    L += ["", f"Industries and categories: {', '.join(sv['categories'])}.", sv["scales"], f"How: {sv['how']}",
          f"Book 30 minutes: {DOMAIN}/utkarsh.html#talk", ""]
    return L

def llms_txt(data):
    L = ["# Utkarsh Singh (belihaazi)", "",
         "> Utkarsh Singh is a context architect and behavioural scientist in India, at 1001 Stories. He writes as belihaazi.", "",
         *solve_lines(data.get("solve")),
         "## Pages", f"- [Utkarsh Singh: talks, POVs, frameworks, reports]({DOMAIN}/utkarsh.html)",
         f"- [Into the mind of belihaazi: poems, prose, spoken word, hip hop]({DOMAIN}/belihaazi.html)", "",
         "## Reports and the concepts they introduce (1001 Stories BiteGeists)"]
    for r in data["reports"]:
        if not r.get("page"): continue
        L.append(f"- [{r['title']}]({DOMAIN}/{r['page']}): by {', '.join(r['authors'])}. Full report: {r['link']}")
        for c in r["concepts"]:
            parts, line = c["def"].split(". "), ""
            for s in parts:
                line += s.rstrip(".") + ". "
                if len(line) > 80: break
            L.append(f"  - [{c['name']}]({DOMAIN}/{r['page']}#{slugify(c['name'])}): {line.strip()}")
    L += ["", "## Talks"]
    L += [f"- {t['title']}" + (f" ({t['where']}, {t['date']})" if t.get("where") else "") + (f": {t['link']}" if t.get("link") else "") for t in data["talks"]]
    L += ["", "## Points of view on behavioural science"]
    L += [f"- [{p['t']}]({DOMAIN}/povs/{p['s']}/)" for p in data["povs"]]
    L += ["", "## Writing as belihaazi", f"- [Why belihaazi (on the pen name)]({DOMAIN}/prose/why-belihaazi/)"]
    L += [f"- [{i['t']}]({DOMAIN}/prose/{i['s']}/) (prose)" for i in data["prose"] if i["s"] != "why-belihaazi"]
    L += [f"- [{i['t']}]({DOMAIN}/poems/{i['s']}/) (poem)" for i in data["poems"]]
    open(os.path.join(D, "llms.txt"), "w", encoding="utf-8").write("\n".join(L) + "\n")

# ---------- "What I solve" (content/utkarsh/solve.json): page section, structured data ----------
def render_solve(sv, profile):
    if not sv: return
    e = html.escape
    areas = "".join(f'<section class="cell solve-a"><h3 class="c">{e(a["name"])}</h3><ul>'
                    + "".join(f"<li>{e(p)}</li>" for p in a["problems"]) + "</ul></section>" for a in sv["areas"])
    block = (f'<div class="cell head" id="solve"><h2 class="c">{e(sv["title"])}</h2><span class="mono">{e(sv["sub"])}</span></div>'
             f'<div class="cell solve-lead"><p>{e(sv["lead"])}</p></div>{areas}'
             f'<div class="cell solve-x"><div><span class="mono">{e(sv.get("across", "Across"))}</span><ul>'
             + "".join(f"<li>{e(c)}</li>" for c in sv["categories"]) + f'</ul><p>{e(sv["scales"])}</p></div>'
             f'<div><span class="mono">How</span><p>{e(sv["how"])}</p>'
             f'<a class="go" href="{e(profile.get("booking_link") or "#talk")}">{e(sv["cta"])} →</a></div></div>')
    offers = [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{a['name']} problem solving with behavioural science",
               "description": "; ".join(a["problems"]), "provider": {"@id": DOMAIN + "/utkarsh.html#person"}, "areaServed": "India"}}
              for a in sv["areas"]]
    ld = {"@context": "https://schema.org", "@type": "Person", "@id": DOMAIN + "/utkarsh.html#person", "name": "Utkarsh Singh",
          "description": sv["lead"], "makesOffer": offers,
          "knowsAbout": [f"{a['name']} strategy" for a in sv["areas"]] + sv["categories"]}
    p = os.path.join(D, "utkarsh.html")
    s = open(p, encoding="utf-8").read()
    s = s.replace("<!--SOLVE-->", block, 1)
    s = s.replace("</head>", '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + "</script>\n</head>", 1)
    open(p, "w", encoding="utf-8").write(s)

# ---------- settings for social.js, the post list, RSS feed, unsubscribe page ----------
def site_config(profile):
    cfg = {"site": DOMAIN, "sb": (profile.get("supabase_url") or "").rstrip("/"), "key": profile.get("supabase_anon_key") or "",
           "book": profile.get("booking_link") or "", "linkedin": (profile.get("links") or {}).get("linkedin", "")}
    open(os.path.join(D, "config.js"), "w", encoding="utf-8").write("window.BELI=" + json.dumps(cfg) + ";\n")

def all_posts(data):
    """Every post, newest first: what the feed and the new-post emails use."""
    P = []
    names = {"povs": "POV", "prose": "Prose", "poems": "Poem"}
    for k in ("povs", "prose", "poems"):
        for i in data[k]:
            P.append({"url": f"{DOMAIN}/{k}/{i['s']}/", "title": i["t"], "section": names[k],
                      "date": f"{i['y']}-{(i.get('m') or 1):02d}-01" if i.get("y") else "",
                      "text": " ".join(i["body"])[:280]})
    for r in data["reports"]:
        if r.get("page"):
            P.append({"url": f"{DOMAIN}/{r['page']}", "title": r["title"], "section": "Report",
                      "date": f"{r['year']}-01-01" if r.get("year") else "", "text": r["summary"][0][:280]})
    for m in data["medium"]:
        P.append({"url": m["link"], "title": m["t"], "section": "Medium",
                  "date": f"{m['y']}-{(m.get('m') or 1):02d}-01" if m.get("y") else "", "text": ""})
    P.sort(key=lambda p: p["date"], reverse=True)
    return P

def feeds(posts):
    from email.utils import format_datetime
    from datetime import datetime, timezone
    json.dump(posts, open(os.path.join(D, "posts.json"), "w", encoding="utf-8"), ensure_ascii=False)
    e = html.escape
    items = []
    for p in posts:
        pd = f"<pubDate>{format_datetime(datetime.fromisoformat(p['date']).replace(tzinfo=timezone.utc))}</pubDate>" if p["date"] else ""
        items.append(f"<item><title>{e(p['title'])}</title><link>{e(p['url'])}</link><guid>{e(p['url'])}</guid>"
                     f"<category>{p['section']}</category>{pd}<description>{e(p['text'])}</description></item>")
    open(os.path.join(D, "feed.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f'<title>Utkarsh Singh · belihaazi</title><link>{DOMAIN}/</link>'
        f'<atom:link href="{DOMAIN}/feed.xml" rel="self" type="application/rss+xml"/>'
        '<description>POVs on behavioural science, reports, poems and prose by Utkarsh Singh (belihaazi).</description>'
        '<language>en</language>' + "".join(items) + "</channel></rss>\n")
    os.makedirs(os.path.join(D, "unsubscribe"), exist_ok=True)
    open(os.path.join(D, "unsubscribe", "index.html"), "w", encoding="utf-8").write(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="robots" content="noindex"><title>Unsubscribe · belihaazi</title><link rel="icon" href="/favicon.svg" type="image/svg+xml">'
        '<style>body{margin:0;background:#F6F6F2;color:#0E0E0C;font:18px/1.6 "IBM Plex Mono",ui-monospace,monospace}'
        '.w{max-width:620px;margin:12vh auto;padding:24px;border:3px solid #0E0E0C;box-shadow:10px 10px 0 #F2C12E;background:#fff}'
        'a{color:inherit}</style></head><body data-nofab><div class="w"><p data-unsubscribe>One moment…</p><p><a href="/">belihaazi.com</a></p></div>'
        '<script src="/config.js"></script><script src="/social.js"></script></body></html>')

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
        r["img"] = save_img(os.path.join(C, "utkarsh/reports", r["cover"]), f"img/reports/{slugify(r['title'])}.jpg", 420, og=True)
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
    report_urls = report_pages(data["reports"])
    prerender_pages(data)
    data["solve"] = load("utkarsh/solve.json")
    render_solve(data["solve"], data["profile"])

    json.dump(data, open(os.path.join(D, "data.json"), "w", encoding="utf-8"), ensure_ascii=False)

    urls = [DOMAIN + "/", DOMAIN + "/utkarsh.html", DOMAIN + "/belihaazi.html"]
    urls += piece_pages(data["povs"], "povs", False)
    urls += piece_pages(data["prose"], "prose", True)
    urls += piece_pages(data["poems"], "poems", True)
    urls += report_urls
    llms_txt(data)
    site_config(data["profile"])
    feeds(all_posts(data))
    today = date.today().isoformat()
    open(os.path.join(D, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    open(os.path.join(D, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    open(os.path.join(D, "CNAME"), "w").write("belihaazi.com\n")
    open(os.path.join(D, ".nojekyll"), "w").write("")
    log("done:", len(urls), "pages")

if __name__ == "__main__":
    main()
