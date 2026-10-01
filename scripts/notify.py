#!/usr/bin/env python3
"""Email subscribers about new posts. Runs on GitHub after every publish.

Needs three GitHub secrets (Settings → Secrets and variables → Actions):
  SUPABASE_URL          e.g. https://abcd1234.supabase.co
  SUPABASE_SERVICE_KEY  Supabase → Project Settings → API → service_role key (keep secret)
  RESEND_API_KEY        from resend.com, after verifying belihaazi.com there
Optional: MAIL_FROM (default "belihaazi <posts@belihaazi.com>"), MAIL_REPLY_TO.

How it decides what is new: the "announced" table remembers every post already emailed.
The very first run only records what exists today and sends nothing.
"""
import html, json, os, sys, time, urllib.error, urllib.request

SITE = "https://belihaazi.com"
SB = os.environ.get("SUPABASE_URL", "").rstrip("/")
SK = os.environ.get("SUPABASE_SERVICE_KEY", "")
RK = os.environ.get("RESEND_API_KEY", "")
FROM = os.environ.get("MAIL_FROM") or "belihaazi <posts@belihaazi.com>"
REPLY = os.environ.get("MAIL_REPLY_TO") or "utkarsh@1001stories.in"
MAX_NEW = 12   # more than this at once usually means renamed pages, not new writing


def req(url, body=None, headers=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"),
                               headers={"Content-Type": "application/json", "User-Agent": "belihaazi-notify", **(headers or {})})
    with urllib.request.urlopen(r, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw.strip() else None


def sb(path, body=None, prefer=None):
    h = {"apikey": SK}
    if SK.startswith("eyJ"):          # older "service_role" keys also go in the Authorization header
        h["Authorization"] = f"Bearer {SK}"
    if prefer: h["Prefer"] = prefer
    return req(f"{SB}/rest/v1/{path}", body, h)


def live_posts():
    for attempt in range(6):          # the new deploy can take a moment to appear
        try:
            return req(f"{SITE}/posts.json?t={int(time.time())}")
        except Exception as e:
            print("waiting for posts.json:", e); time.sleep(20)
    raise SystemExit("could not read posts.json")


def email_html(new, token):
    e = html.escape
    items = "".join(
        f'<tr><td style="padding:16px 0;border-bottom:3px solid #0E0E0C">'
        f'<div style="font:12px monospace;text-transform:uppercase;letter-spacing:.05em;color:#5B5B55">{e(p["section"])}</div>'
        f'<a href="{e(p["url"])}" style="font:900 22px/1.15 Arial,Helvetica,sans-serif;color:#0E0E0C;text-decoration:none">{e(p["title"])}</a>'
        + (f'<div style="font:15px/1.5 Georgia,serif;color:#333;margin-top:6px">{e(p["text"][:200])}…</div>' if p.get("text") else "")
        + f'<div style="margin-top:10px"><a href="{e(p["url"])}" style="font:700 12px monospace;text-transform:uppercase;'
          f'background:#F2C12E;color:#0E0E0C;padding:6px 10px;text-decoration:none;border:2px solid #0E0E0C">Read →</a></div></td></tr>'
        for p in new)
    unsub = f"{SITE}/unsubscribe/?t={token}"
    return (f'<div style="background:#F6F6F2;padding:24px 12px"><table role="presentation" width="100%" style="max-width:600px;margin:0 auto;'
            f'background:#fff;border:3px solid #0E0E0C;border-collapse:collapse"><tr><td style="background:#0E0E0C;color:#F6F6F2;padding:12px 18px;'
            f'font:900 20px Arial,Helvetica,sans-serif;letter-spacing:.02em">BELIHAAZI.COM</td></tr><tr><td style="padding:4px 18px 18px">'
            f'<table role="presentation" width="100%" style="border-collapse:collapse">{items}</table></td></tr>'
            f'<tr><td style="padding:12px 18px;font:12px monospace;color:#5B5B55">You signed up at belihaazi.com. '
            f'<a href="{unsub}" style="color:#5B5B55">Unsubscribe</a></td></tr></table></div>')


def email_text(new, token):
    lines = [f"{p['section']}: {p['title']}\n{p['url']}\n" for p in new]
    return "New on belihaazi.com\n\n" + "\n".join(lines) + f"\n--\nUnsubscribe: {SITE}/unsubscribe/?t={token}\n"


def subject(new):
    if len(new) == 1:
        lead = {"POV": "New POV", "Prose": "New prose", "Poem": "New poem", "Report": "New report", "Medium": "New on Medium"}
        return f"{lead.get(new[0]['section'], 'New')}: {new[0]['title']}"
    return f"{len(new)} new posts on belihaazi.com"


def main():
    missing = [n for n, v in (("SUPABASE_URL", SB), ("SUPABASE_SERVICE_KEY", SK), ("RESEND_API_KEY", RK)) if not v]
    if missing:
        print("New-post emails are not set up yet (missing", ", ".join(missing) + "). Skipping."); return
    posts = live_posts()
    seen = {r["url"] for r in (sb("announced?select=url&limit=10000") or [])}
    record = lambda ps: sb("announced", [{"url": p["url"], "title": p["title"]} for p in ps], prefer="resolution=ignore-duplicates")
    if not seen:
        record(posts); print(f"First run: recorded {len(posts)} existing posts. No emails sent."); return
    new = [p for p in posts if p["url"] not in seen]
    if not new:
        print("No new posts."); return
    if len(new) > MAX_NEW:
        record(new); print(f"{len(new)} 'new' posts at once looks like renamed pages. Recorded them without emailing."); return
    subs = sb("subscribers?select=email,token&active=eq.true&limit=10000") or []
    print(f"{len(new)} new post(s):", ", ".join(p["title"] for p in new), f"→ {len(subs)} subscriber(s)")
    msgs = [{"from": FROM, "to": [s["email"]], "reply_to": REPLY, "subject": subject(new),
             "html": email_html(new, s["token"]), "text": email_text(new, s["token"]),
             "headers": {"List-Unsubscribe": f"<{SITE}/unsubscribe/?t={s['token']}>"}} for s in subs]
    for i in range(0, len(msgs), 100):
        req("https://api.resend.com/emails/batch", msgs[i:i + 100], {"Authorization": f"Bearer {RK}"})
        print("sent", min(i + 100, len(msgs)), "of", len(msgs))
    record(new)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        print("HTTP error:", e.code, e.read().decode()[:500]); sys.exit(1)
