/* Likes, comments, sharing, email sign-up and the floating contact button.
   Settings come from config.js (built from content/utkarsh/profile.json).
   Without a database configured, only sharing and the contact button show. */
(function(){
const B = window.BELI || {};
const ON = !!(B.sb && B.key);
const SITE = B.site || location.origin;
const GOLD = '#F2C12E', INK = '#0E0E0C';

/* ---------- small helpers ---------- */
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const store = {
  get(k, d){ try{ const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); }catch(e){ return d; } },
  set(k, v){ try{ localStorage.setItem(k, JSON.stringify(v)); }catch(e){} }
};
function voter(){
  let v = store.get('beli-voter');
  if(!v){ v = (crypto.randomUUID ? crypto.randomUUID() : 'xxxxxxxx-xxxx-4xxx-8xxx-xxxxxxxxxxxx'.replace(/x/g, () => (Math.random()*16|0).toString(16))); store.set('beli-voter', v); }
  return v;
}
function api(path, body, extra){
  return fetch(B.sb + '/rest/v1/' + path, {
    method: body ? 'POST' : 'GET',
    headers: Object.assign({ apikey: B.key, Authorization: 'Bearer ' + B.key, 'Content-Type': 'application/json' }, extra || {}),
    body: body ? JSON.stringify(body) : undefined
  }).then(async r => {
    const j = await r.json().catch(() => null);
    if(!r.ok) throw new Error((j && j.message) || 'Something went wrong. Try again.');
    return j;
  });
}
const M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const when = iso => { const d = new Date(iso); return d.getDate() + ' ' + M[d.getMonth()] + ' ' + d.getFullYear(); };

/* ---------- styles (colours follow the page via currentColor) ---------- */
const css = `
.sx{--sx-gold:${GOLD};--sx-ink:${INK};font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:13px;line-height:1.45;margin:28px 0 0;text-align:left}
.sx *{box-sizing:border-box}
.sx-row{display:flex;flex-wrap:wrap;gap:0;border:3px solid currentColor}
.sx-b{appearance:none;font:inherit;color:inherit;background:transparent;border:0;border-right:3px solid currentColor;padding:10px 14px;cursor:pointer;display:inline-flex;align-items:center;gap:8px;text-transform:uppercase;letter-spacing:.05em;text-decoration:none}
.sx-b:last-child{border-right:0}
.sx-b:hover,.sx-b:focus-visible{background:var(--sx-gold);color:var(--sx-ink)}
.sx-b[aria-pressed="true"]{background:var(--sx-gold);color:var(--sx-ink)}
.sx-b svg{width:16px;height:16px;flex:none}
.sx-share{display:flex;flex-wrap:wrap;border:3px solid currentColor;border-top:0}
.sx-share[hidden]{display:none}
.sx-share a,.sx-share button{flex:1 1 auto;text-align:center}
.sx-c{border:3px solid currentColor;border-top:0;padding:16px}
.sx-c[hidden]{display:none}
.sx-h{font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin:0 0 12px}
.sx-list{display:grid;gap:14px;margin:0 0 18px}
.sx-item{border-left:4px solid var(--sx-gold);padding:2px 0 2px 12px}
.sx-item .sx-who{opacity:.7;font-size:12px;margin-bottom:4px}
.sx-item .sx-txt{font-family:inherit;font-size:15px;line-height:1.55;white-space:pre-wrap;overflow-wrap:anywhere}
.sx-empty{opacity:.7;margin:0 0 14px}
.sx-f{display:grid;gap:8px}
.sx-f input,.sx-f textarea{font:inherit;font-size:15px;color:inherit;background:transparent;border:2px solid currentColor;padding:9px 10px;width:100%;border-radius:0}
.sx-f textarea{min-height:96px;resize:vertical}
.sx-f input::placeholder,.sx-f textarea::placeholder{color:inherit;opacity:.55}
.sx-f .sx-go{justify-self:start;background:var(--sx-gold);color:var(--sx-ink);border:2px solid currentColor;font-weight:700}
.sx-hp{position:absolute!important;left:-9999px!important;width:1px;height:1px;overflow:hidden}
.sx-msg{min-height:1.2em;font-size:12px}
.sx-sub{border:3px solid currentColor;padding:18px;display:grid;gap:10px}
.sx-sub .sx-t{font-family:"Archivo","Helvetica Neue",Arial,sans-serif;font-weight:900;font-stretch:80%;text-transform:uppercase;font-size:clamp(22px,3vw,30px);line-height:1;margin:0}
.sx-sub form{display:flex;flex-wrap:wrap;gap:8px}
.sx-sub input[type=email]{flex:1 1 220px;font:inherit;font-size:15px;color:inherit;background:transparent;border:2px solid currentColor;padding:10px;border-radius:0}
.sx-sub input::placeholder{color:inherit;opacity:.55}
.sx-sub .sx-go{background:var(--sx-gold);color:var(--sx-ink);border:2px solid currentColor;font-weight:700}
.sx-fab{position:fixed;right:16px;bottom:16px;z-index:40;font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:13px;display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.sx-fab .sx-btn{width:52px;height:52px;background:var(--sx-ink,${INK});border:3px solid ${GOLD};box-shadow:4px 4px 0 ${GOLD};cursor:pointer;padding:6px;display:grid;place-items:center;transition:transform .15s}
.sx-fab .sx-btn:hover{transform:translate(-2px,-2px);box-shadow:6px 6px 0 ${GOLD}}
.sx-fab .sx-btn[aria-expanded="true"] svg{transform:rotate(90deg)}
.sx-fab .sx-btn svg{width:100%;height:100%;transition:transform .25s}
.sx-fab .sx-menu{display:grid;border:3px solid ${INK};background:#F6F6F2;box-shadow:6px 6px 0 ${GOLD};min-width:220px}
.sx-fab .sx-menu[hidden]{display:none}
.sx-fab .sx-menu a{color:${INK};text-decoration:none;padding:12px 14px;display:flex;justify-content:space-between;gap:12px;text-transform:uppercase;letter-spacing:.05em}
.sx-fab .sx-menu a+a{border-top:3px solid ${INK}}
.sx-fab .sx-menu a:hover,.sx-fab .sx-menu a:focus-visible{background:${GOLD}}
.sx-fab .sx-menu small{display:block;text-transform:none;letter-spacing:0;opacity:.7;font-size:11px;margin-top:2px}
@media print{.sx,.sx-fab{display:none}}
@media (prefers-reduced-motion:reduce){.sx-fab *{transition:none!important}}
`;
const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

const ICON = {
  heart: f => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.1 0 3.6 1.2 4.3 2.6.1.2.4.2.5 0 .7-1.4 2.2-2.6 4.3-2.6 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z" fill="${f ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2.2"/></svg>`,
  share: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v13M6.5 8.5 12 3l5.5 5.5M4 14v6h16v-6" fill="none" stroke="currentColor" stroke-width="2.4"/></svg>`,
  talk: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 4h18v12H9l-5 4v-4H3z" fill="none" stroke="currentColor" stroke-width="2.4"/></svg>`,
  swirl: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 3a13 13 0 0 1 11.8 13 11 11 0 0 1-11.6 10.6A9 9 0 0 1 7.6 18 7.2 7.2 0 0 1 14.8 10.8 5.4 5.4 0 0 1 20 16a3.6 3.6 0 0 1-3.6 3.5" fill="none" stroke="${GOLD}" stroke-width="2.6" stroke-linecap="round"/><circle cx="16" cy="16" r="1.9" fill="${GOLD}"/></svg>`
};

/* ---------- like · share · comments ---------- */
function bar(el, o){
  const path = o.path, url = SITE + path, title = o.title || document.title;
  const liked = new Set(store.get('beli-liked', []));
  el.classList.add('sx');
  el.innerHTML = `
    <div class="sx-row">
      ${ON ? `<button class="sx-b sx-like" type="button" aria-pressed="${liked.has(path)}" aria-label="Like">${ICON.heart(liked.has(path))}<span class="sx-n">Like</span></button>` : ''}
      <button class="sx-b sx-sh" type="button" aria-expanded="false">${ICON.share}<span>Share</span></button>
      ${ON ? `<button class="sx-b sx-cm" type="button" aria-expanded="false">${ICON.talk}<span class="sx-cn">Comments</span></button>` : ''}
    </div>
    <div class="sx-share" hidden>
      <a class="sx-b" href="https://wa.me/?text=${encodeURIComponent(title + ' ' + url)}" target="_blank" rel="noopener">WhatsApp</a>
      <a class="sx-b" href="https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}" target="_blank" rel="noopener">LinkedIn</a>
      <a class="sx-b" href="https://x.com/intent/post?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}" target="_blank" rel="noopener">X</a>
      <a class="sx-b" href="mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(url)}">Email</a>
      <button class="sx-b sx-copy" type="button">Copy link</button>
    </div>
    ${ON ? `<div class="sx-c" hidden>
      <p class="sx-h">Comments</p>
      <div class="sx-list" aria-live="polite"></div>
      <form class="sx-f">
        <input name="author" maxlength="60" placeholder="Your name" required autocomplete="name">
        <textarea name="message" maxlength="2000" placeholder="Say something" required></textarea>
        <label class="sx-hp" aria-hidden="true">Website <input name="website" tabindex="-1" autocomplete="off"></label>
        <button class="sx-b sx-go" type="submit">Post</button>
        <div class="sx-msg" role="status"></div>
      </form>
    </div>` : ''}`;

  // share
  const shBtn = el.querySelector('.sx-sh'), shRow = el.querySelector('.sx-share');
  shBtn.addEventListener('click', () => {
    if(navigator.share && matchMedia('(pointer:coarse)').matches){ navigator.share({ title, url }).catch(() => {}); return; }
    shRow.hidden = !shRow.hidden; shBtn.setAttribute('aria-expanded', !shRow.hidden);
  });
  el.querySelector('.sx-copy').addEventListener('click', e => {
    const b = e.currentTarget, done = () => { b.textContent = 'Copied'; setTimeout(() => b.textContent = 'Copy link', 1600); };
    (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(done, () => { prompt('Copy this link', url); });
  });
  if(!ON) return;

  // likes
  const lk = el.querySelector('.sx-like'), ln = el.querySelector('.sx-n');
  const show = n => { ln.textContent = n ? n + (n === 1 ? ' like' : ' likes') : 'Like'; };
  api('rpc/like_count', { p: path }).then(show).catch(() => {});
  lk.addEventListener('click', () => {
    const now = !liked.has(path);
    lk.setAttribute('aria-pressed', now); lk.querySelector('svg').outerHTML = ICON.heart(now);
    now ? liked.add(path) : liked.delete(path); store.set('beli-liked', [...liked]);
    api('rpc/like_page', { p: path, vid: voter(), liked: now }).then(show).catch(() => {});
  });

  // comments
  const cBtn = el.querySelector('.sx-cm'), cBox = el.querySelector('.sx-c'), list = el.querySelector('.sx-list'), cn = el.querySelector('.sx-cn');
  let count = 0;
  const item = c => `<div class="sx-item"><div class="sx-who">${esc(c.name)} · ${when(c.created_at)}</div><div class="sx-txt">${esc(c.body)}</div></div>`;
  const label = () => { cn.textContent = count ? count + (count === 1 ? ' comment' : ' comments') : 'Comments'; };
  const render = rows => { count = rows.length; label(); list.innerHTML = rows.length ? rows.map(item).join('') : '<p class="sx-empty">No comments yet.</p>'; };
  api('comments?select=id,name,body,created_at&order=created_at.asc&page=eq.' + encodeURIComponent(path)).then(render).catch(() => render([]));
  cBtn.addEventListener('click', () => {
    cBox.hidden = !cBox.hidden; cBtn.setAttribute('aria-expanded', !cBox.hidden);
    if(!cBox.hidden){ const n = cBox.querySelector('[name=author]'); n.value = n.value || store.get('beli-name', ''); (n.value ? cBox.querySelector('textarea') : n).focus(); }
  });
  const f = el.querySelector('.sx-f'), msg = el.querySelector('.sx-msg');
  f.addEventListener('submit', e => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(f)), go = f.querySelector('.sx-go');
    go.disabled = true; msg.textContent = 'Posting…';
    api('rpc/add_comment', { p: path, author: d.author, message: d.message, website: d.website || '' })
      .then(rows => {
        store.set('beli-name', d.author.trim());
        if(rows && rows[0]){ if(!count) list.innerHTML = ''; list.insertAdjacentHTML('beforeend', item(rows[0])); count++; label(); }
        f.querySelector('textarea').value = ''; msg.textContent = 'Posted.';
      })
      .catch(err => { msg.textContent = err.message; })
      .finally(() => { go.disabled = false; });
  });
}

/* ---------- email sign-up ---------- */
function subscribe(el){
  if(!ON){ el.hidden = true; return; }
  el.hidden = false; el.classList.add('sx');
  el.innerHTML = `<div class="sx-sub">
    <p class="sx-t">New posts, by email</p>
    <span>Poems, prose, POVs and reports, when they go up. Unsubscribe from any email.</span>
    <form><input type="email" name="addr" placeholder="you@email.com" required autocomplete="email" aria-label="Email">
      <label class="sx-hp" aria-hidden="true">Website <input name="website" tabindex="-1" autocomplete="off"></label>
      <button class="sx-b sx-go" type="submit">Subscribe</button></form>
    <div class="sx-msg" role="status"></div></div>`;
  const f = el.querySelector('form'), msg = el.querySelector('.sx-msg');
  f.addEventListener('submit', e => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(f)), go = f.querySelector('.sx-go');
    go.disabled = true; msg.textContent = 'Adding you…';
    api('rpc/subscribe', { addr: d.addr, website: d.website || '' })
      .then(() => { f.reset(); msg.textContent = "Done. You'll get an email when something new goes up."; })
      .catch(err => { msg.textContent = err.message; })
      .finally(() => { go.disabled = false; });
  });
}

/* ---------- unsubscribe page ---------- */
function unsubscribe(el){
  const t = new URLSearchParams(location.search).get('t');
  if(!ON || !t){ el.textContent = 'This unsubscribe link is not complete. Reply to any email and you will be removed.'; return; }
  api('rpc/unsubscribe', { t }).then(ok => { el.textContent = ok ? "You're unsubscribed. No more emails." : 'This link has already been used, or is not valid.'; })
    .catch(() => { el.textContent = 'Something went wrong. Reply to any email and you will be removed.'; });
}

/* ---------- floating contact button ---------- */
function fab(){
  if(document.body.hasAttribute('data-nofab') || (!B.book && !B.linkedin)) return;
  const w = document.createElement('div'); w.className = 'sx-fab';
  w.innerHTML = `<nav class="sx-menu" id="sx-menu" hidden aria-label="Contact">
      ${B.book ? `<a href="${esc(B.book)}" target="_blank" rel="noopener"><span>Google Meet<small>Book 30 minutes</small></span><span>↗</span></a>` : ''}
      ${B.linkedin ? `<a href="${esc(B.linkedin)}" target="_blank" rel="noopener"><span>LinkedIn<small>Message me</small></span><span>↗</span></a>` : ''}
    </nav>
    <button class="sx-btn" type="button" aria-expanded="false" aria-controls="sx-menu" aria-label="Contact Utkarsh">${ICON.swirl}</button>`;
  document.body.appendChild(w);
  const btn = w.querySelector('.sx-btn'), menu = w.querySelector('.sx-menu');
  const set = open => { menu.hidden = !open; btn.setAttribute('aria-expanded', open); };
  btn.addEventListener('click', e => { e.stopPropagation(); set(menu.hidden); });
  document.addEventListener('click', e => { if(!w.contains(e.target)) set(false); });
  document.addEventListener('keydown', e => { if(e.key === 'Escape' && !menu.hidden){ set(false); btn.focus(); } });
}

/* ---------- auto-mount ---------- */
function mount(root){
  (root || document).querySelectorAll('[data-social]:not(.sx)').forEach(el => bar(el, { path: el.dataset.social, title: el.dataset.title }));
  (root || document).querySelectorAll('[data-subscribe]').forEach(subscribe);
  (root || document).querySelectorAll('[data-unsubscribe]').forEach(unsubscribe);
}
window.Social = { bar, subscribe, mount, on: ON };
if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => { mount(); fab(); });
else { mount(); fab(); }
})();
