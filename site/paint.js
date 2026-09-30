/* Painted brushwork: short thick strokes that follow a swirling flow field (Van Gogh style), plus helpers shared by all pages. */
(function(){
const PAL={
  wheat:{base:['#F2B90F','#E8A20C','#F7D24A','#D88A12','#F4C534','#C9760E'],accent:['#2743A8','#1B2E7A','#F8E7A0','#141715'],dark:'#8A4A08',vort:['#F8E7A0','#FFF6D6']},
  night:{base:['#1B2E7A','#223C96','#2F55B5','#15215A','#4A78C2','#2A4AA0'],accent:['#7FA9DE','#9EC1E6','#0E1638'],dark:'#0A1030',vort:['#F2C12E','#F7E07A','#FFF3B8','#E8A20C']},
  almond:{base:['#5E9FB0','#7DB6C2','#4A8799','#9CCBD0','#6AA8B6'],accent:['#F4F1E8','#EBDDD4','#2E4A3A','#E7C9C0'],dark:'#24424A',vort:['#FBF8EF','#F1E4DC']},
  crows:{base:['#E2A21A','#C98314','#F0BE36','#B8700F'],accent:['#1B2E7A','#0E0E0C','#2A5236'],dark:'#3A2508',vort:['#15215A','#0E1638','#223C96']},
  cypress:{base:['#1F3A2A','#2A5236','#13261B','#3E6B45'],accent:['#1B2E7A','#0E1638','#6E8F4E'],dark:'#0A140E',vort:['#F2C12E','#F7E07A']}
};
function rng(seed){let s=seed>>>0||1;return()=>((s=Math.imul(s^s>>>15,1|s)+0x6D2B79F5|0,((s^s>>>7)>>>0)%100000)/100000)}
function paint(cv,o={}){
  const p=PAL[o.palette||'night'];const R=rng(o.seed||7);
  const dpr=Math.min(devicePixelRatio||1,2);
  let W,H,ctx,vort,t=0,raf;
  function field(x,y,tt){
    const nx=x/W,ny=y/H;
    let a=Math.sin(ny*6.2+Math.sin(nx*4.1+tt)*1.4)*0.9+Math.cos(nx*3.3-ny*2.1+tt*.7)*0.6+(o.tilt||0);
    let vx=Math.cos(a),vy=Math.sin(a),core=0;
    for(const v of vort){const dx=x-v.x,dy=y-v.y,d2=dx*dx+dy*dy,r2=v.r*v.r;const w=Math.exp(-d2/r2);
      const tx=-dy*v.dir,ty=dx*v.dir,l=Math.hypot(tx,ty)||1;vx=vx*(1-w)+tx/l*w*1.4;vy=vy*(1-w)+ty/l*w*1.4;core=Math.max(core,Math.exp(-d2/(r2*.28)))}
    const l=Math.hypot(vx,vy)||1;return[vx/l,vy/l,core];
  }
  function tone(x,y){const v=(Math.sin(x/W*5.3+y/H*2.7)+Math.sin(y/H*8.1-x/W*1.3)+2)/4;return v}
  function stroke(x,y,tt,big){
    const [,,core]=field(x,y,tt);
    let col;
    if(core>.35&&R()<core+.1)col=p.vort[(R()*p.vort.length)|0];
    else if(R()<(o.accentRate||.07))col=p.accent[(R()*p.accent.length)|0];
    else{const k=Math.min(p.base.length-1,Math.floor(tone(x,y)*p.base.length+ (R()-.5)*1.6));col=p.base[Math.max(0,k)]}
    const len=(big?20:13)+R()*14,steps=6,sl=len*dpr/steps,lw=(big?5.5:3.4)+R()*2.4;
    ctx.beginPath();ctx.moveTo(x,y);let cx=x,cy=y;
    for(let i=0;i<steps;i++){const [fx,fy]=field(cx,cy,tt);cx+=fx*sl;cy+=fy*sl;ctx.lineTo(cx,cy)}
    ctx.lineCap='round';ctx.lineJoin='round';
    ctx.strokeStyle=p.dark;ctx.globalAlpha=.35;ctx.lineWidth=(lw+1.6)*dpr;ctx.stroke();
    ctx.strokeStyle=col;ctx.globalAlpha=.95;ctx.lineWidth=lw*dpr;ctx.stroke();
  }
  function size(){
    const r=cv.getBoundingClientRect();W=cv.width=Math.max(1,r.width*dpr);H=cv.height=Math.max(1,r.height*dpr);ctx=cv.getContext('2d');
    vort=(o.vortices||[]).map(v=>({x:v[0]*W,y:v[1]*H,r:v[2]*Math.min(W,H),dir:v[3]||1}));
    ctx.fillStyle=p.base[0];ctx.fillRect(0,0,W,H);
    const gap=(o.gap||7)*dpr;
    for(let y=-gap;y<H+gap;y+=gap)for(let x=-gap;x<W+gap;x+=gap)stroke(x+R()*gap,y+R()*gap,0,true);
    for(let i=0;i<(W*H)/(gap*gap)*.6;i++)stroke(R()*W,R()*H,0,false);
  }
  size();
  let rt;addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(size,200)});
  if(o.animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
    const loop=()=>{t+=.0025;for(let i=0;i<(o.rate||45);i++)stroke(R()*W,R()*H,t,false);raf=requestAnimationFrame(loop)};loop();
  }
}
function fill(box,cls,pal){
  const run=()=>{box.querySelectorAll('.filler').forEach(f=>f.remove());
    const cols=getComputedStyle(box).gridTemplateColumns.split(' ').filter(Boolean).length;
    const n=box.children.length,k=(cols-n%cols)%cols;
    for(let i=0;i<k;i++){const d=document.createElement('div');d.className=cls+' filler';d.setAttribute('aria-hidden','true');
      const c=document.createElement('canvas');c.className='pt';d.appendChild(c);box.appendChild(d);
      paint(c,{palette:pal,seed:n*7+i*13,vortices:[[0.5,0.5,0.4,i%2?1:-1]],gap:7})}};
  run();let t;addEventListener('resize',()=>{clearTimeout(t);t=setTimeout(run,250)});
}
window.Paint={paint,fill};
document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('canvas[data-paint]').forEach((c,i)=>{
    const o=JSON.parse(c.dataset.paint||'{}');paint(c,o);
  });
});

/* reader overlay shared by both pages */
window.Reader=(function(){
  let el;
  function esc(s){return s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
  const M=['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  function date(i){return i.y?(i.m?M[i.m]+' ':'')+i.y:''}
  function open(item,kind){
    if(!el){el=document.createElement('div');el.className='reader';el.setAttribute('role','dialog');el.setAttribute('aria-modal','true');document.body.appendChild(el);
      el.addEventListener('click',e=>{if(e.target===el||e.target.closest('.r-close'))close()});
      addEventListener('keydown',e=>{if(e.key==='Escape')close()})}
    const poem=kind==='poems';
    el.innerHTML=`<article class="r-card ${poem?'is-poem':''}"><button class="r-close" type="button">Close ✕</button>
      ${item.img?`<img class="r-img" src="${item.img}" alt="">`:(item.paint?'<div class="r-paint"><canvas class="pt"></canvas></div>':'')}
      <div class="r-body"><p class="r-meta">${esc(date(item))}</p><h2 class="r-title">${esc(item.t)}</h2>
      ${item.body.map(p=>`<p>${esc(p)}</p>`).join('')}${item.pdf?`<p><a href="${item.pdf}">Read the full dissertation (PDF) ↗</a></p>`:''}${item.credit?`<p class="r-meta">Image: ${esc(item.credit)}</p>`:''}</div></article>`;
    el.hidden=false;const rc=el.querySelector('.r-paint canvas');if(rc)paint(rc,item.paint);document.body.style.overflow='hidden';el.querySelector('.r-close').focus();el.scrollTop=0;
  }
  function close(){if(el){el.hidden=true;document.body.style.overflow=''}}
  return{open,close,date};
})();
})();
