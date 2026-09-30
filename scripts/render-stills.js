// Pre-renders the brushwork as still images for phones. Run: node scripts/render-stills.js (needs playwright)
const {chromium}=require('playwright');const fs=require('fs');const path=require('path');
const site=path.join(__dirname,'..','site');
const big={
 'door-day':[820,1100,{palette:'wheat',seed:5,vortices:[[0.75,0.3,0.25,1],[0.25,0.75,0.3,-1]],gap:8}],
 'door-night':[820,1100,{palette:'night',seed:42,vortices:[[0.3,0.35,0.2,1],[0.6,0.5,0.15,-1],[0.85,0.8,0.1,1]],gap:7}],
 'hero-u':[800,1000,{palette:'wheat',seed:11,vortices:[[0.82,0.2,0.28,1],[0.2,0.78,0.3,-1]],gap:8}],
 'cta-u':[1100,520,{palette:'night',seed:3,vortices:[[0.15,0.4,0.35,1],[0.7,0.55,0.25,-1],[0.92,0.2,0.12,1]],gap:8}],
 'sky-b':[820,1400,{palette:'night',seed:42,vortices:[[0.3,0.2,0.2,1],[0.6,0.42,0.16,-1],[0.82,0.12,0.1,1],[0.2,0.7,0.1,1],[0.7,0.85,0.12,1]],gap:7}]};
for(const pal of ['night','wheat','almond','crows','cypress'])for(let v=0;v<3;v++)
 big[`tile-${pal}-${v}`]=[440,440,{palette:pal,seed:v*37+11,vortices:[[0.3+0.2*v,0.45,0.35,v%2?1:-1]],gap:6}];
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1400,height:900},deviceScaleFactor:1});
await p.setContent('<body style="margin:0"></body>');await p.addScriptTag({path:path.join(site,'paint.js')});
fs.mkdirSync(path.join(site,'paint'),{recursive:true});
for(const [name,[w,h,o]] of Object.entries(big)){
 const data=await p.evaluate(async([w,h,o])=>{document.body.innerHTML='';const c=document.createElement('canvas');c.style.cssText=`width:${w}px;height:${h}px;display:block`;document.body.appendChild(c);
   Paint.paint(c,o);await new Promise(r=>setTimeout(r,2500));return c.toDataURL('image/webp',0.8)},[w,h,o]);
 fs.writeFileSync(path.join(site,'paint',name+'.webp'),Buffer.from(data.split(',')[1],'base64'));console.log(name);}
await b.close();})();
