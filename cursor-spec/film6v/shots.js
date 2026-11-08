'use strict';
E.inQuart=x=>x*x*x*x;
// Cursor spec V2 — 23 shots. Each shot is a pure function of time; the manager hides every layer each frame
// and the active shot shows what it needs. The finale montage replays earlier shots at their own source times.
const ST=document.createElement('style');ST.textContent=`
.kc{position:absolute;transform-style:preserve-3d}
.kc .b{position:absolute;inset:12px 0 0 0;border-radius:22px;background:#090806}
.kc .c{position:absolute;left:0;right:0;top:0;bottom:12px;border-radius:22px;background:linear-gradient(180deg,#3C3B31 0%,#2B2A21 55%,#22211A 100%);
  box-shadow:inset 0 1.5px 0 rgba(255,255,255,.16),inset 0 -8px 12px rgba(0,0,0,.35),0 2px 0 #11100B;display:flex;align-items:flex-start;justify-content:space-between;padding:18px 20px;color:#DAD7CD;font-weight:500}
.tok{position:absolute;font-family:Mono;font-size:40px;white-space:pre;line-height:1}
.slab{position:absolute;left:0;height:62px;border-radius:12px;background:#17160F;border:1px solid #2E2D25;font-family:Mono;font-size:31px;line-height:62px;padding-left:22px;white-space:pre;box-shadow:0 20px 40px -20px rgba(0,0,0,.8)}
.fcard{position:absolute;width:480px;height:600px;border-radius:18px;background:linear-gradient(180deg,#1C1B14,#151409);border:1px solid #33322A;overflow:hidden;box-shadow:0 50px 90px -40px rgba(0,0,0,.9),inset 0 1px 0 rgba(255,255,255,.08)}
.fcard .hd{height:54px;border-bottom:1px solid #2B2A22;display:flex;align-items:center;gap:10px;padding:0 20px;font-size:17px;color:#E7E5DD}
.fcard .hd i{width:13px;height:13px;border-radius:3px;background:#3E7C6C}
.fcard .hd .pl{margin-left:auto;font-family:Mono;font-size:15px;color:#79C796}
.fcard .cl{position:relative;height:30px;font-family:Mono;font-size:15.5px;line-height:30px;white-space:pre;padding-left:20px;overflow:hidden}
.fcard .cl .bg{position:absolute;inset:0;background:rgba(120,200,150,.14);transform-origin:0 50%}
.fcard .cl .bar{position:absolute;left:6px;top:4px;bottom:4px;width:3px;border-radius:2px;background:#79C796}
.fcard .cl .tx{position:relative}
.fcard .cl .cm{position:absolute;top:50%;width:120px;height:4px;margin-top:-2px;transform:translateX(-100%);border-radius:4px;background:linear-gradient(90deg,rgba(255,190,100,0),#FFD38A 70%,#FFFBEF);box-shadow:0 0 14px 3px rgba(255,180,90,.75);opacity:0}
.ag .tl{position:relative;height:30px;font-family:Mono;font-size:15.5px;line-height:30px;white-space:pre;padding-left:22px}
.ag .tl .tx{display:inline-block}
.ag .tl .cm{position:absolute;top:50%;width:110px;height:4px;margin-top:-2px;transform:translateX(-100%);border-radius:4px;background:linear-gradient(90deg,rgba(255,190,100,0),#FFD38A 70%,#FFFBEF);box-shadow:0 0 14px 3px rgba(255,180,90,.75);opacity:0}
.ag .st{height:40px;display:flex;align-items:center;gap:10px;padding:0 22px;font-size:15px;color:#8A877D}
.ag .st b{width:10px;height:10px;border-radius:50%;border:1.5px solid #8A877D}
.ag .dn{position:absolute;right:20px;bottom:18px;height:36px;padding:0 18px;border-radius:18px;display:flex;align-items:center;gap:8px;font-size:15px;font-weight:600;color:#1A1408;background:linear-gradient(180deg,#FFE2A6,#F5B54E);box-shadow:0 0 30px rgba(255,180,80,.6)}
.ag .ck{position:absolute;right:18px;top:12px;width:30px;height:30px;border-radius:50%;background:radial-gradient(circle,#FFF3D6,#F5B54E 70%);color:#1A1408;font-size:18px;font-weight:700;display:flex;align-items:center;justify-content:center;box-shadow:0 0 22px 4px rgba(255,180,80,.7)}
.panel{position:absolute;border-radius:20px;background:linear-gradient(180deg,#1C1B14,#141309);border:1px solid #33322A;box-shadow:0 50px 90px -40px rgba(0,0,0,.9),inset 0 1px 0 rgba(255,255,255,.08);overflow:hidden}
.panel .hd{height:52px;border-bottom:1px solid #2B2A22;display:flex;align-items:center;padding:0 22px;font-size:13px;letter-spacing:.16em;color:#8A877D;font-family:Mono}
.big{position:absolute;font-weight:600;letter-spacing:-.035em;line-height:.95;white-space:nowrap}
.mini{position:absolute;background:#fff;border:1px solid #E6E4DC;border-radius:14px;box-shadow:0 14px 30px -18px rgba(20,18,11,.3);color:#14120B}
`;document.head.appendChild(ST);
const S={};const LAYERS=[];
function layer(z,bg){const l=el('div','L');css(l,{zIndex:z});if(bg)l.style.background=bg;LAYERS.push(l);return l;}
function kcap(parent,label,w=170,h=124,fs=24,icon=''){const k=el('div','kc',parent);css(k,{width:w+'px',height:h+'px'});el('div','b',k);
  k.c=el('div','c',k,`<span style="font-size:${fs}px">${label}</span>${icon}`);k.g=el('div','a',k);css(k.g,{left:'-40px',top:'-40px',right:'-40px',bottom:'-40px',borderRadius:'50px',background:'radial-gradient(closest-side,rgba(247,247,244,.2),transparent)'});return k;}
function pressKey(k,t,tp){const p=bump(t,tp,.04,.05,.12),f=bump(t,tp,.03,0,.45);css(k.c,{transform:`translateY(${p*10}px)`,filter:`brightness(${1+f*.4})`});k.g.style.opacity=f;}
// ---------- world placement (camera) ----------
function placeWorld(o){const{fx=850,fy=470,s=1,rx=0,ry=0,rz=0,X=960,Y=540,z=0,op=1}=o;
  css(W.win,{transform:`translate3d(${X-fx}px,${Y-fy}px,${z}px) scale(${s}) rotateX(${rx}deg) rotateY(${ry}deg) rotateZ(${rz}deg)`,transformOrigin:`${fx}px ${fy}px`,opacity:op});
  W.parts.forEach(p=>css(p,{transform:'none',opacity:1}));W.frame.style.opacity=1;W.sheen.style.opacity=0;W.icon.style.opacity=1;}
const wpt=(o,x,y)=>[(o.X??960)+(x-(o.fx??850))*(o.s??1),(o.Y??540)+(y-(o.fy??470))*(o.s??1)];
const CH_PX=12.0; // JetBrains Mono at 20px
function hookCode(n1,ghostA,solidF,flash=0){setTabs(['hook'],'hook');
  setCode('hook',{state:i=>{if(i<3)return{n:Infinity};if(i===3)return{n:n1};
    if(i>=4&&i<=11){if(ghostA<=0)return{n:0};const sf=solidF?solidF(i):0;return{ghost:true,solid:sf,gOp:ghostA*(typeof ghostA==='function'?1:1)};}return{n:0};}});
  W.lines.forEach((o,i)=>{if(i>=12)show(o.d,false);o.no.style.opacity=1;o.bg.style.background='rgba(247,247,244,.10)';
    const f=typeof flash==='function'?flash(i):0;o.bg.style.opacity=f;o.bg.style.transform='scaleX(1)';o.bar.style.opacity=0;});
  show(W.term,false);show(W.prev,false);show(W.sweep,false);}
function hideAgentUI(){W.bub.style.opacity=0;W.m1.style.opacity=0;W.done.style.opacity=0;W.steps.forEach(s=>s.style.opacity=0);
  W.inTxt.innerHTML='<span class="ph">Plan, search, build anything…</span>';}
function editorCode(key,addK){setTabs(['hook','card','rev','sig','page'],key);
  setCode(key,{state:i=>({n:Infinity,add:addK?addK(i):0})});W.lines.forEach(o=>{o.no.style.opacity=1;o.bg.style.background='var(--add)';});show(W.term,false);show(W.sweep,false);show(W.caret,false);}
// ---------- build ----------
function buildShots(){
  // stage light
  S.bg=layer(1);el('div','L',S.bg).style.background='radial-gradient(60% 55% at 50% 38%,rgba(247,238,214,.10),rgba(247,238,214,.03) 45%,transparent 72%)';
  S.grid=el('div','L',S.bg);css(S.grid,{backgroundImage:'radial-gradient(rgba(247,247,244,.09) 1px,transparent 1.4px)',backgroundSize:'36px 36px',WebkitMaskImage:'radial-gradient(55% 60% at 50% 45%,#000,transparent 75%)'});
  LAYERS.push(W.L,D.clip);W.L.style.zIndex=10;
  // tokens (shot 2)
  S.tok=layer(40);S.tokIn=el('div','L',S.tok);css(S.tokIn,{perspective:'1200px',transformStyle:'preserve-3d'});
  S.toks=[];const r=mulberry32(21);const LINES=FILES.hook.lines.slice(0,8);const bx=336,by=250;
  LINES.forEach((ln,li)=>{let col=0;for(const[w,c]of toks(ln)){if(/^\s+$/.test(w)){col+=w.length;continue;}
    const e=el('span','tok '+c,S.tokIn,esc(w));const x=bx+col*24,y=by+li*76;col+=w.length;
    S.toks.push({e,x,y,li,dx:(r()-.5)*1800,dy:(r()-.5)*1100,dz:-1400+r()*1800,rx:(r()-.5)*160,ry:(r()-.5)*160,d:r()*.08});}});
  // big type
  S.type=layer(80);S.ideas=el('div','big',S.type,'IDEAS.');S.into=el('div','big',S.type,'INTO REALITY.');
  S.typeBg=el('div','L',S.type);S.type.insertBefore(S.typeBg,S.type.firstChild);
  S.meet=el('div','big',S.type);S.meet.innerHTML='MEET<br>CURSOR.';
  S.less=el('div','big',S.type);S.more=el('div','big',S.type);S.moreL=[...'MORE BUILDING.'].map(ch=>{const s=el('span',null,S.more,ch===' '?'&nbsp;':ch);s.style.display='inline-block';return s;});
  S.one=el('div','big',S.type,'ONE PROMPT.');S.endl=el('div','big',S.type,'ENDLESS MOMENTUM.');
  S.from=el('div','big',S.type,'FROM CODE.');S.to=el('div','big',S.type,'TO CREATION.');
  S.tcar=el('div','a',S.type);css(S.tcar,{width:'10px',background:'#F7F7F4'});
  // keycaps
  S.keys=layer(70);S.kCmd=kcap(S.keys,'⌘',150,124,40);S.kK=kcap(S.keys,'K',150,124,34);
  S.kTab=kcap(S.keys,'tab',300,210,40,'<svg width="60" height="38" viewBox="0 0 34 22"><path d="M2 11h26M20 3l8 8-8 8M31 2v18" stroke="#DAD7CD" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>');
  S.div=el('div','a',S.keys);css(S.div,{left:'959px',top:0,width:'2px',height:'1080px',background:'linear-gradient(transparent,rgba(247,247,244,.35),transparent)'});
  // cube
  S.cubeL=layer(60);S.cube=el('div','a',S.cubeL);css(S.cube,{width:'360px',height:'411px'});
  S.cubeImg=el('img','a',S.cube);S.cubeImg.src='brand/CUBE_25D.png';css(S.cubeImg,{left:0,top:0,width:'100%',height:'100%'});
  S.cubeSh=el('div','a',S.cube);css(S.cubeSh,{left:0,top:0,width:'100%',height:'100%',WebkitMaskImage:'url(brand/CUBE_25D.png)',WebkitMaskSize:'100% 100%',
    background:'linear-gradient(115deg,transparent 40%,rgba(255,255,255,.6) 50%,transparent 60%)',backgroundSize:'300% 100%'});
  S.cubeGlow=el('div','a',S.cubeL);css(S.cubeGlow,{width:'900px',height:'900px',borderRadius:'50%',background:'radial-gradient(closest-side,rgba(247,238,214,.12),transparent)'});
  // slabs (shot 11)
  S.slabL=layer(45);S.slabG=el('div','a',S.slabL);css(S.slabG,{left:'260px',top:'150px',width:'1400px',height:'800px',transformStyle:'preserve-3d'});
  S.slabWrap=el('div','L',S.slabL);css(S.slabWrap,{perspective:'1800px'});S.slabWrap.appendChild(S.slabG);
  S.slabs=FILES.hook.lines.slice(0,12).map((ln,i)=>{const s=el('div','slab',S.slabG,hl(ln)||'&nbsp;');css(s,{top:(i*66)+'px',width:Math.max(300,ln.length*18.6+60)+'px'});return s;});
  S.sel=el('div','a',S.slabs[3]);css(S.sel,{top:'8px',height:'36px',borderRadius:'6px',background:'rgba(142,197,242,.28)',boxShadow:'0 0 0 1.5px rgba(142,197,242,.8)'});
  // file cards (shots 14–15)
  S.cardL=layer(42);S.cardW=el('div','L',S.cardL);css(S.cardW,{perspective:'2000px'});
  S.fcs=['card','rev','sig','page'].map(k=>{const F=FILES[k];const c=el('div','fcard',S.cardW,`<div class="hd"><i></i>${F.name}<span class="pl"></span></div>`);
    c.pl=c.querySelector('.pl');c.ls=F.lines.slice(0,17).map(ln=>{const d=el('div','cl',c);const bg=el('div','bg',d);const bar=el('div','bar',d);el('span','tx',d,hl(ln)||' ');const cm=el('div','cm',d);return{bg,bar,cm};});c.n=F.lines.length;return c;});
  // split: terminal + steps (shot 16)
  S.splitL=layer(44);S.term=el('div','panel',S.splitL,'<div class="hd">TERMINAL</div>');css(S.term,{left:'100px',top:'200px',width:'820px',height:'640px'});
  S.termB=el('div','a',S.term);css(S.termB,{left:'30px',top:'84px',fontFamily:'Mono',fontSize:'24px',lineHeight:'46px',color:'#CFCCC2',whiteSpace:'pre'});
  S.stepsP=el('div','panel',S.splitL,'<div class="hd">AGENT</div>');css(S.stepsP,{left:'1000px',top:'200px',width:'820px',height:'640px'});
  S.st=['Read app/page.tsx','Edited MetricCard.tsx','Edited RevenueChart.tsx','Edited SignupsChart.tsx','Edited app/dashboard/page.tsx','Ran npm run dev'].map((s,i)=>{
    const d=el('div','a',S.stepsP);css(d,{left:'30px',right:'30px',top:(84+i*86)+'px',height:'66px',borderRadius:'14px',border:'1px solid #2B2A22',background:'rgba(247,247,244,.03)',display:'flex',alignItems:'center',gap:'18px',padding:'0 22px',fontFamily:'Mono',fontSize:'22px',color:'#D8D5CB'});
    d.dot=el('div',null,d);css(d.dot,{width:'24px',height:'24px',borderRadius:'50%',border:'2.5px solid #5B594F',flex:'none'});el('span',null,d,s);return d;});
  S.prog=el('div','a',S.splitL);css(S.prog,{left:'100px',top:'880px',height:'6px',borderRadius:'3px',background:'#F7F7F4'});
  S.progBg=el('div','a',S.splitL);css(S.progBg,{left:'100px',top:'880px',width:'1720px',height:'6px',borderRadius:'3px',background:'#2B2A22'});S.splitL.appendChild(S.prog);
  // assembly: code → interface (shot 17)
  S.asmL=layer(46);S.asmCode=el('div','panel',S.asmL,'<div class="hd">app/dashboard/page.tsx</div>');css(S.asmCode,{left:'90px',top:'190px',width:'820px',height:'700px'});
  const PL=FILES.page.lines.slice(5,14);S.asmLines=PL.map((ln,i)=>{const d=el('div','a',S.asmCode);css(d,{left:0,right:0,top:(74+i*58)+'px',height:'50px',fontFamily:'Mono',fontSize:'19px',lineHeight:'50px',paddingLeft:'26px',whiteSpace:'pre'});
    d.bg=el('div','a',d);css(d.bg,{inset:0,background:'rgba(247,247,244,.10)',opacity:0});el('span',null,d,hl(ln.replace(/^ {4}/,'')));d.style.overflow='hidden';return d;});
  S.br=el('div','panel',S.asmL,'<div class="hd" style="letter-spacing:0;font-size:15px">localhost:3000/dashboard</div>');css(S.br,{left:'1000px',top:'190px',width:'830px',height:'700px',background:'#F2F1EC',borderColor:'#D9D7CF'});
  S.br.querySelector('.hd').style.cssText+='background:#E6E4DC;color:#5B594F;border-color:#D9D7CF';
  S.mcards=['$48.2K','12.9K','3.8%','1.2%'].map((v,i)=>{const m=el('div','mini',S.br,`<div style="font-size:12px;color:#77746B;font-weight:500">${['MRR','Active users','Conversion','Churn'][i]}</div><div style="font-size:30px;font-weight:600;letter-spacing:-.02em">${v}</div>`);
    css(m,{left:(26+i*196)+'px',top:'82px',width:'180px',height:'104px',padding:'16px 16px'});return m;});
  S.mrev=el('div','mini',S.br);css(S.mrev,{left:'26px',top:'206px',width:'470px',height:'460px'});
  S.mrev.innerHTML=`<div style="font-size:13px;color:#77746B;font-weight:500;padding:16px">Revenue</div><svg width="470" height="400" style="position:absolute;left:0;top:50px"><path d="${(()=>{const mx=Math.max(...LINE)*1.1;return 'M'+LINE.map((v,i)=>`${20+i*14.5} ${360-(v/mx)*300}`).join(' L');})()}" fill="none" stroke="#14120B" stroke-width="3" stroke-linejoin="round"/></svg>`;
  S.msig=el('div','mini',S.br);css(S.msig,{left:'514px',top:'206px',width:'290px',height:'460px'});
  S.msig.innerHTML='<div style="font-size:13px;color:#77746B;font-weight:500;padding:16px">Signups by channel</div>'+BARS.map((v,i)=>`<div style="position:absolute;left:${22+i*52}px;bottom:30px;width:36px;height:${v/320*320}px;border-radius:8px 8px 3px 3px;background:${i?'#CFCCC2':'#14120B'}"></div>`).join('');
  S.fly=el('div','a',S.asmL);css(S.fly,{borderRadius:'10px',background:'rgba(247,247,244,.14)',border:'1.5px solid rgba(247,247,244,.6)'});
  // dashboard extras: an Export button
  S.exp=el('div','a',D.base,'Export');css(S.exp,{right:'290px',top:'62px',padding:'10px 22px',borderRadius:'999px',background:'#14120B',color:'#F7F7F4',fontSize:'16px',fontWeight:600});
  D.parts=[D.base,...D.cards.map(c=>c.c),D.rc,D.bc];
  // lockup
  S.lockL=layer(85);S.lCube=el('img','a',S.lockL);S.lCube.src='brand/CUBE_25D.png';S.lWord=el('img','a',S.lockL);S.lWord.src='brand/WORDMARK_DARK.svg';
  S.tag=el('div','a',S.lockL,'BUILD WHAT’S NEXT.');css(S.tag,{left:0,width:'1920px',textAlign:'center',top:'770px',fontSize:'44px',fontWeight:600,letterSpacing:'.02em'});
  S.url=el('div','a mono',S.lockL,'cursor.com');css(S.url,{left:0,width:'1920px',textAlign:'center',top:'846px',fontSize:'26px',color:'#B5B2A8'});
  S.disc=el('div','a mono',S.lockL,'Spec ad by AVE Studio · not affiliated with or endorsed by Cursor');css(S.disc,{left:0,width:'1920px',textAlign:'center',top:'1030px',fontSize:'14px',color:'#5B594F',letterSpacing:'.04em'});
  S.lockSpot=el('div','L',S.lockL);S.lockL.insertBefore(S.lockSpot,S.lockL.firstChild);css(S.lockSpot,{background:'radial-gradient(45% 45% at 50% 42%,rgba(247,238,214,.10),transparent 70%)'});
  // finale: three parallel agents
  S.agL=layer(46);S.agW=el('div','L',S.agL);css(S.agW,{perspective:'2200px'});
  S.pill=el('div','a',S.agL);css(S.pill,{left:'0',right:'0',margin:'0 auto',top:'150px',width:'260px',height:'42px',borderRadius:'21px',display:'flex',alignItems:'center',justifyContent:'center',gap:'10px',fontSize:'17px',color:'#F7E7C8',border:'1px solid rgba(255,200,120,.45)',background:'rgba(255,180,80,.08)',boxShadow:'0 0 30px rgba(255,170,80,.25)'});
  const AG=[['Add dark mode toggle','Writing components','ThemeToggle.tsx',['export function ThemeToggle() {','  const [dark, setDark] = useState(false)','  useEffect(() => {','    document.documentElement','      .classList.toggle("dark", dark)','  }, [dark])','  return (','    <button onClick={() => setDark(!dark)}>','      {dark ? "Light" : "Dark"}']],
    ['Fix flaky checkout test','Running tests','checkout.test.ts',['test("checkout completes", async () => {','  await page.goto("/checkout")','  await page.fill("#email", "a@b.co")','  await page.click("text=Pay now")','  await expect(page.getByText("Paid"))','    .toBeVisible({ timeout: 10_000 })','})','','✓ 14 passed (3.2s)']],
    ['Refactor billing service','Refactoring','billing.ts',['export async function charge(id: string) {','  const sub = await db.subscription','    .findUniqueOrThrow({ where: { id } })','  const amount = priceFor(sub.plan)','  return stripe.paymentIntents.create({','    amount, currency: "usd",','    customer: sub.customerId,','  })','}']]];
  S.ags=AG.map(([ti,st,fn,lines],i)=>{const c=el('div','fcard ag',S.agW);css(c,{width:'500px',height:'540px'});
    el('div','hd',c,`<i style="background:#C9A35A"></i>${ti}`);const sr=el('div','st',c,`<b></b><span>${st}</span>`);el('div','st',c,`<span style="font-family:Mono;font-size:13px;color:#6F6C62">${fn}</span>`);
    const ls=lines.map(ln=>{const d=el('div','tl',c);const tx=el('span','tx',d,ln.startsWith('✓')?`<span style="color:#79C796">${esc(ln)}</span>`:hl(ln)||' ');const cm=el('div','cm',d);return{tx,cm,n:ln.length};});
    const dn=el('div','dn',c,'✓ Done');const ck=el('div','ck',c,'✓');return{c,ls,dn,ck,stS:sr.querySelector('span'),stB:sr.querySelector('b'),st};});
  S.black=layer(95,'#000');
  S.fx=layer(90);S.fx.style.pointerEvents='none';
  S.dust=el('div','a',S.fx);css(S.dust,{inset:0});S.motes=[];const rq=mulberry32(11);for(let i=0;i<70;i++){const m=el('div','a',S.dust);const z=rq();css(m,{width:(1+z*2.4)+'px',height:(1+z*2.4)+'px',borderRadius:'50%',background:'#FFD9A0'});S.motes.push({m,x:rq()*1920,y:rq()*1080,z,ph:rq()*6.28});}
  S.ember=el('div','a',S.fx);css(S.ember,{width:'40px',height:'40px',borderRadius:'50%',background:'radial-gradient(circle,#FFF4D6 0%,#FFB347 30%,rgba(255,110,30,.55) 55%,rgba(255,80,20,0) 72%)'});
  S.halo=el('div','a',S.fx);css(S.halo,{width:'600px',height:'600px',borderRadius:'50%',background:'radial-gradient(circle,rgba(255,150,60,.35) 0%,rgba(255,100,40,.12) 35%,rgba(255,80,30,0) 70%)'});
  S.flare=el('div','a',S.fx);css(S.flare,{inset:0,background:'radial-gradient(circle at 50% 48%,#FFFDF5 0%,#FFE3A8 14%,#FFA14A 34%,rgba(230,90,30,.55) 58%,rgba(120,30,10,0) 85%)'});
  S.ring=el('div','a',S.fx);css(S.ring,{borderRadius:'50%',border:'3px solid rgba(255,190,110,.9)',boxShadow:'0 0 40px rgba(255,150,60,.8),inset 0 0 40px rgba(255,150,60,.5)'});
  S.streak=el('div','a',S.fx);css(S.streak,{height:'6px',borderRadius:'6px',background:'linear-gradient(90deg,rgba(255,200,120,0),#FFF6E0 50%,rgba(255,200,120,0))',boxShadow:'0 0 30px 8px rgba(255,170,80,.55)'});
  S.chk=document.createElementNS('http://www.w3.org/2000/svg','svg');S.chk.setAttribute('viewBox','0 0 400 300');S.chk.setAttribute('class','a');S.fx.appendChild(S.chk);
  S.chk.innerHTML='<defs><filter id="gl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="9" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter><linearGradient id="gd" x1="0" x2="1"><stop offset="0" stop-color="#FFB547"/><stop offset="1" stop-color="#FFF1CC"/></linearGradient></defs><path id="ck" d="M70 160 L160 240 L340 50" fill="none" stroke="url(#gd)" stroke-width="22" stroke-linecap="round" stroke-linejoin="round" filter="url(#gl)"/><circle id="ckh" r="16" fill="#FFF8E6" filter="url(#gl)"/>';
  S.ckp=S.chk.querySelector('#ck');S.ckh=S.chk.querySelector('#ckh');S.ckL=S.ckp.getTotalLength();css(S.chk,{left:'1110px',top:'300px',width:'600px',height:'450px'});
  S.hz=el('div','a',S.fx);css(S.hz,{left:'-200px',width:'2320px',height:'4px',borderRadius:'4px',background:'linear-gradient(90deg,rgba(255,220,160,0),#FFF3D9 50%,rgba(255,220,160,0))',boxShadow:'0 0 60px 14px rgba(255,190,110,.45)'});
  S.hzG=el('div','a',S.fx);css(S.hzG,{left:'160px',width:'1600px',height:'420px',borderRadius:'50%',background:'radial-gradient(ellipse at 50% 50%,rgba(255,205,140,.42) 0%,rgba(255,170,90,.14) 40%,rgba(255,150,70,0) 70%)'});
  S.fxAll=[S.dust,S.ember,S.halo,S.flare,S.ring,S.streak,S.chk,S.hz,S.hzG];
}
// ---------- shots ----------
function ideaType(e,txt,size,x,y,color){css(e,{fontSize:size+'px',left:x+'px',top:y+'px',color});}
function SH1(t){ // macro of the editor, ⌘K pressed
  show(S.bg,1);show(W.L,1);const lt=t-C.sh1;hideAgentUI();
  hookCode(49,1,()=>1);show(W.caret,true);
  const o={fx:560,fy:240,s:lerp(2.7,3.2,E.outCubic(P(lt,0,.55))),rx:16,ry:-20,rz:-2,X:900,Y:520};placeWorld(o);
  css(W.caret,{left:`calc(72px + 49ch)`,top:(16+3*32+3)+'px',opacity:Math.floor(t*4)%2?0:1});
  show(S.keys,1);show(S.kTab,0);show(S.div,0);const kin=E.outBack(P(lt,.02,.2),1.6),kout=E.inCubic(P(t,C.sh2-.14,C.sh2));
  [[S.kCmd,1380,800],[S.kK,1550,800]].forEach(([k,x,y],i)=>{show(k,1);css(k,{left:x+'px',top:y+'px',opacity:kin*(1-kout),transform:`perspective(900px) rotateX(24deg) rotateZ(-5deg) scale(${lerp(.8,1,kin)})`});pressKey(k,t,i?C.cmdk2:C.cmdk);});
}
function SH2(t){ // code fragments align and lock, camera rushes through
  show(S.tok,1);show(S.bg,1);const pu=E.inCubic(P(t,C.push,C.ember));
  css(S.tokIn,{transform:`translateZ(${pu*900}px) scale(${1+pu*.4})`,opacity:1-P(t,C.ember-.12,C.ember),filter:`blur(${pu*6}px)`});
  for(const k of S.toks){const ta=C.lock0+k.li*.035+k.d,a=E.outBack(P(t,ta-.32,ta),1.25);
    css(k.e,{left:k.x+'px',top:k.y+'px',transform:`translate3d(${k.dx*(1-a)}px,${k.dy*(1-a)}px,${k.dz*(1-a)}px) rotateX(${k.rx*(1-a)}deg) rotateY(${k.ry*(1-a)}deg)`,opacity:P(t,ta-.32,ta-.22)});}
}
function SH3(t){show(S.type,1);show(S.typeBg,1);S.typeBg.style.background='#000';const k=E.outExpo(P(t,C.sh3,C.sh3+.28));
  show(S.ideas,1);ideaType(S.ideas,0,360,0,0,'#F7F7F4');const w=S.ideas.offsetWidth;css(S.ideas,{left:(960-w/2)+'px',top:'360px',transform:`scale(${lerp(1.3,1,k)*(1+.04*P(t,C.sh3,C.sh4))})`,filter:`blur(${(1-k)*14}px)`,transformOrigin:'50% 55%'});}
function SH4(t){show(S.type,1);show(S.typeBg,1);const sk=E.inQuart(P(t,C.suck,C.ember));
  S.typeBg.style.background='#F7F7F4';S.typeBg.style.clipPath=`circle(${lerp(1400,0,sk)}px at 50% 50%)`;
  show(S.into,1);ideaType(S.into,0,210,0,0,'#14120B');const w=S.into.offsetWidth;
  css(S.into,{left:(960-w/2)+'px',top:'430px',transform:`scale(${(1+.05*P(t,C.sh4,C.suck))*(1-sk)},${(1+.05*P(t,C.sh4,C.suck))*(1-sk*.92)})`,filter:`blur(${sk*10}px)`,transformOrigin:'50% 50%',letterSpacing:`${lerp(-.035,.02,P(t,C.sh4,C.suck))}em`});}
function cubeAt(cx,cy,w,ry,rx,op,sheenP){const h=w*1601/1402;css(S.cube,{left:(cx-w/2)+'px',top:(cy-h/2)+'px',width:w+'px',height:h+'px',opacity:op,transform:`perspective(1400px) rotateY(${ry}deg) rotateX(${rx}deg)`});
  S.cubeSh.style.backgroundPosition=`${lerp(100,-100,sheenP)}% 0`;css(S.cubeGlow,{left:(cx-450)+'px',top:(cy-450)+'px',opacity:op*.9});}
function SH5(t){show(S.bg,1);show(S.cubeL,1);flareOver(t);const k=E.outQuint(P(t,C.sh5,C.sh5+1.0));
  cubeAt(960,520,lerp(200,360,k),lerp(85,0,k),lerp(-30,0,k),P(t,C.sh5,C.sh5+.15),E.inOutSine(P(t,C.sheen,C.sheen+.7)));}
function SH6(t){ // camera orbits the brand composition as the editor assembles around the cube
  show(S.bg,1);show(W.L,1);show(S.cubeL,1);hideAgentUI();hookCode(0,0,null);show(W.caret,false);
  const o={fx:850,fy:470,s:lerp(.5,.56,P(t,C.sh6,C.sh7)),rx:lerp(24,9,E.inOutCubic(P(t,C.sh6,C.sh7))),ry:lerp(-42,-12,E.inOutCubic(P(t,C.sh6,C.sh7))),X:1000,Y:520};placeWorld(o);
  const offs=[[-620,60,-420],[0,120,-260],[620,60,-420],[0,-340,260]];[C.snap1,C.snap2,C.snap3,C.snap4].forEach((st,i)=>{const k=E.outBack(P(t,st-.45,st),1.25);const[dx,dy,dz]=offs[i];
    css(W.parts[i],{transform:`translate3d(${dx*(1-k)}px,${dy*(1-k)}px,${dz*(1-k)}px) rotateY(${(1-k)*(i===0?25:i===2?-25:0)}deg)`,opacity:P(t,C.sh6+i*.08,C.sh6+.25+i*.08)});});
  W.frame.style.opacity=P(t,C.snap4-.2,C.snap4);W.icon.style.opacity=t>=C.icon+.18?1:0;
  const fl=E.inOutCubic(P(t,C.icon,C.sh7));const[ix,iy]=wpt(o,850-92+8.5,20);
  cubeAt(lerp(960,ix,fl),lerp(520,iy,fl),lerp(300,17*o.s,fl),lerp(0,0,fl),0,fl>.97?0:1,0);
}
function SH7(t){show(S.bg,1);show(W.L,1);hideAgentUI();hookCode(0,0,null);show(W.caret,false);const k=E.inOutCubic(P(t,C.sh7,C.sh8));
  placeWorld({fx:850,fy:470,s:lerp(.56,.74,k),rx:lerp(9,4,k),ry:lerp(-12,-6,k),X:lerp(1000,1230,E.outCubic(P(t,C.sh7,C.sh7+.6))),Y:520});
  show(S.type,1);show(S.typeBg,0);show(S.meet,1);const m=E.outExpo(P(t,C.meet,C.meet+.6));
  css(S.meet,{fontSize:'150px',left:'110px',top:'360px',color:'#F7F7F4',clipPath:`inset(0 ${(1-m)*100}% 0 0)`,transform:`translateX(${(1-m)*-40}px)`,opacity:1-P(t,C.sh8-.12,C.sh8)});}
function SH8(t){ // macro: the caret, typing
  show(S.bg,1);show(W.L,1);hideAgentUI();const n1=typed(C.T1,t);hookCode(n1,0,null);show(W.caret,true);
  const cx=312+72+n1*CH_PX;const o={fx:lerp(cx-260,cx-120,P(t,C.sh8,C.sh9)),fy:210,s:lerp(3.6,3.3,P(t,C.sh8,C.sh9)),rx:7,ry:-9,X:900,Y:540};placeWorld(o);
  css(W.caret,{left:`calc(72px + ${n1}ch)`,top:(16+3*32+3)+'px',opacity:1});}
function SH9(t){ // the suggestion appears; camera tracks along it
  show(S.bg,1);show(W.L,1);hideAgentUI();const g=i=>P(t,C.ghost+(i-4)*.05,C.ghost+(i-4)*.05+.2);
  hookCode(49,1,()=>0,i=>i>=4&&i<=11?.12*bump(t,C.ghost+(i-4)*.05,.06,0,.25)*8:0);
  W.lines.forEach((o,i)=>{if(i>=4&&i<=11)o.gh.style.opacity=g(i);});show(W.caret,true);css(W.caret,{left:`calc(72px + 49ch)`,top:(16+3*32+3)+'px',opacity:Math.floor(t*3)%2?0:1});
  const k=E.inOutCubic(P(t,C.sh9,C.sh9+.5)),tr=E.inOutSine(P(t,C.sh9+.3,C.sh10));
  placeWorld({fx:lerp(860,700,k),fy:lerp(210,300+tr*40,k),s:lerp(3.3,1.55,k),rx:lerp(7,3,k),ry:lerp(-9,-4,k),X:960,Y:520});}
function SH10(t){ // split: the Tab key macro | the code accepting, character by character
  show(S.bg,1);show(W.L,1);hideAgentUI();const ac=i=>clamp((t-C.tab-(i-4)*.035)/.12);
  hookCode(49,1,ac,i=>i>=4&&i<=11?bump(t,C.tab+(i-4)*.035,.04,0,.35):0);show(W.caret,false);
  placeWorld({fx:700,fy:330,s:1.2,rx:2,ry:-4,X:1440,Y:540});W.L.style.clipPath='inset(0 0 0 962px)';
  show(S.keys,1);show(S.kCmd,0);show(S.kK,0);show(S.kTab,1);show(S.div,1);const kin=E.outBack(P(t,C.sh10,C.sh10+.22),1.5);
  css(S.kTab,{left:'330px',top:'430px',opacity:kin,transform:`perspective(1000px) rotateX(${lerp(40,26,kin)}deg) rotateZ(-6deg) scale(${lerp(1.5,1.8,kin)})`});pressKey(S.kTab,t,C.tab);}
function SH11(t){ // accepted lines lift into 3D slabs, snap back; then a satisfying selection
  show(S.bg,1);show(S.slabL,1);const up=E.inOutCubic(P(t,C.lift,C.lift+.45)),dn=E.inOutCubic(P(t,C.back,C.back+.55));const g=up*(1-dn);
  css(S.slabG,{transform:`rotateX(${g*22}deg) rotateY(${-g*24}deg) rotateZ(${-g*3}deg) scale(${1-g*.1})`});
  S.slabs.forEach((s,i)=>{const lf=E.outCubic(P(t,C.lift+i*.025,C.lift+i*.025+.4));const sb=E.outBack(P(t,C.back+i*.04,C.back+i*.04+.28),1.6);
    const z=lf*(i*34+30)*(1-sb);css(s,{transform:`translate3d(${(1-sb)*lf*(i%2?60:-40)}px,0,${z}px)`,opacity:P(t,C.sh11,C.sh11+.1),borderColor:i>=4&&sb>0&&sb<1?'#8A877D':'#2E2D25'});});
  const sk=E.outQuart(P(t,C.select,C.select+.22));css(S.sel,{left:(22+16*18.6)+'px',top:'10px',height:'42px',width:(10*18.6*sk)+'px',opacity:sk>0?1:0});}
function SH12(t){ // kinetic type over the code
  show(S.bg,1);show(W.L,1);hideAgentUI();hookCode(49,1,()=>1);show(W.caret,false);
  placeWorld({fx:lerp(620,820,P(t,C.sh12,C.sh13)),fy:lerp(260,360,P(t,C.sh12,C.sh13)),s:1.3,rx:4,ry:-8,X:1200,Y:540,op:.32});W.L.style.filter='blur(5px)';
  show(S.type,1);show(S.typeBg,0);const n=typed(C.TL,t);show(S.less,1);S.less.textContent='LESS TYPING.'.slice(0,n);css(S.less,{fontSize:'150px',left:'110px',top:'330px',color:'#F7F7F4'});
  const lw=S.less.offsetWidth;show(S.tcar,t<C.more+.2);css(S.tcar,{left:(110+lw+10)+'px',top:'340px',height:'130px',opacity:t<C.TL[C.TL.length-1]+.05||Math.floor(t*3)%2?1:0});
  show(S.more,1);css(S.more,{fontSize:'150px',left:'110px',top:'500px',color:'#8A877D'});
  S.moreL.forEach((s,i)=>{const k=E.outBack(P(t,C.more+i*.028,C.more+i*.028+.3),1.8);css(s,{transform:`translateY(${(1-k)*120}px) rotateX(${(1-k)*80}deg)`,opacity:P(t,C.more+i*.028,C.more+i*.028+.08)});});
  const out=E.inCubic(P(t,C.sh13-.18,C.sh13));css(S.type,{opacity:1-out});}
function SH13(t){ // the prompt
  show(S.bg,1);show(W.L,1);editorCode('hook');hideAgentUI();const pn=typed(C.TP,t),sent=t>=C.send+.08;
  W.inTxt.innerHTML=sent?'<span class="ph">Plan, search, build anything…</span>':esc('Build a responsive analytics dashboard.'.slice(0,pn))+'<span style="display:inline-block;width:2px;height:20px;background:#F7F7F4;vertical-align:-3px;margin-left:1px"></span>';
  css(W.send,{transform:`scale(${1-.16*bump(t,C.send,.05,0,.15)})`,opacity:pn>0&&!sent?1:.35});
  const b=E.outQuart(P(t,C.send+.04,C.send+.32));W.bub.style.opacity=b;W.bub.style.transform=`translateY(${(1-b)*480}px)`;
  const k=E.inOutCubic(P(t,C.send,C.sh14));placeWorld({fx:1456,fy:lerp(830,420,k),s:lerp(1.9,1.4,k),rx:4,ry:-7,X:960,Y:560});}
function fanPos(i,k){return{x:lerp(-560,170+i*400,k),y:230,z:-i*60,ry:lerp(70,-22,k),rz:-2,s:1};}
function SH14(t){ // files expand into layered panels
  show(S.bg,1);show(W.L,1);placeWorld({fx:1456,fy:420,s:1.4,rx:4,ry:-7,X:960,Y:560,op:.25});W.L.style.filter='blur(6px)';
  show(S.cardL,1);S.fcs.forEach((c,i)=>{const k=E.outBack(P(t,C.fan+i*.08,C.fan+i*.08+.34),1.25);const p=fanPos(i,k);
    css(c,{left:p.x+'px',top:p.y+'px',opacity:P(t,C.fan+i*.1,C.fan+i*.1+.1),transform:`translateZ(${p.z}px) rotateY(${p.ry}deg) rotateZ(${p.rz}deg) scale(${p.s})`});c.pl.textContent='';
    c.ls.forEach(l=>{l.bg.style.transform='scaleX(0)';l.bar.style.opacity=0;l.cm.style.opacity=0;});});}
function SH15(t){ // diff montage: each file comes forward and its diff slides in
  show(S.bg,1);show(S.cardL,1);const ds=[C.d1,C.d2,C.d3,C.d4];let a=0;ds.forEach((d,i)=>{if(t>=d)a=i;});
  S.fcs.forEach((c,i)=>{const on=i===a;const ti=ds[i];const k=on?E.outQuart(P(t,ti,ti+.3)):1;
    let x,y,z,ry,s,op;if(on){x=lerp(1400,720,k);y=150;z=lerp(-400,120,k);ry=lerp(45,-6,k);s=1.32;op=1;}
    else{const back=i<a?i:i-1;x=i<a?90+back*120:1500+(i-a-1)*120;y=270;z=-500;ry=i<a?28:-28;s=.82;op=.42;}
    css(c,{left:x+'px',top:y+'px',opacity:op,transform:`translateZ(${z}px) rotateY(${ry}deg) scale(${s})`,zIndex:on?5:1});
    const nAdd=c.n;let shown=0;c.ls.forEach((l,j)=>{const kk=E.outCubic(P(t,ti+.12+j*.03,ti+.3+j*.03));l.bg.style.transform=`scaleX(${kk})`;l.bar.style.opacity=kk;if(kk>.5)shown++;css(l.cm,{left:(kk*100)+'%',opacity:on&&kk>.01&&kk<.99?1:0});});
    c.pl.textContent=t>=ti?'+'+Math.min(nAdd,shown):'';});}
function SH16(t){ // split screen: terminal | agent steps, synced
  show(S.bg,1);show(S.splitL,1);const n=typed(C.TC,t);const sp='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'[Math.floor(t*14)%10];
  let L=`<span style="color:#79C796">$</span> ${'npm run dev'.slice(0,n)}${n<11?'▍':''}`;
  if(t>C.run+.3)L+='\n<span style="color:#8A877D">&gt; next dev</span>';if(t>C.run+.45&&t<C.ready)L+=`\n<span style="color:#C7A6F0">${sp}</span> Compiling /dashboard …`;
  if(t>=C.ready)L+='\n  - Local:   <span style="color:#8EC5F2">http://localhost:3000</span>\n<span style="color:#79C796">✓</span> Ready in 1.4s';S.termB.innerHTML=L;
  const k=E.outQuart(P(t,C.sh16,C.sh16+.3));css(S.term,{transform:`translateX(${(1-k)*-120}px)`,opacity:k});css(S.stepsP,{transform:`translateX(${(1-k)*120}px)`,opacity:k});
  S.st.forEach((d,i)=>{const tc=C.sh16+.18+i*.17;const done=t>=tc;d.dot.style.background=done?'#79C796':'transparent';d.dot.style.borderColor=done?'#79C796':'#5B594F';
    d.style.transform=`scale(${1+.04*bump(t,tc,.04,0,.12)})`;d.style.borderColor=done?'#3F5B47':'#2B2A22';});
  css(S.prog,{width:(1720*E.inOutSine(P(t,C.sh16+.1,C.ready)))+'px'});checkOver(t);}
function SH17(t){ // code → interface: lines turn into components
  show(S.bg,1);show(S.asmL,1);const k=E.outQuart(P(t,C.sh17,C.sh17+.3));css(S.asmCode,{opacity:k,transform:`translateX(${(1-k)*-60}px)`});css(S.br,{opacity:k,transform:`translateX(${(1-k)*60}px)`});
  const src=[[3,4,5,6],[7],[8]],tgt=[S.mcards,[S.mrev],[S.msig]],at=[C.a1,C.a2,C.a3];
  S.asmLines.forEach(d=>d.bg.style.opacity=0);let fl=null;
  at.forEach((a,g)=>{src[g].forEach(li=>S.asmLines[li].bg.style.opacity=bump(t,a-.12,.06,.1,.3));
    tgt[g].forEach((m,j)=>{const kk=E.outBack(P(t,a+.18+j*.05,a+.42+j*.05),1.5);css(m,{opacity:P(t,a+.18+j*.05,a+.24+j*.05),transform:`scale(${lerp(.7,1,kk)}) translateY(${(1-kk)*20}px)`});});
    if(t>=a-.02&&t<a+.24)fl={g,k:E.inOutCubic(P(t,a-.02,a+.22))};});
  show(S.fly,!!fl);if(fl){const sl=S.asmLines[src[fl.g][0]];const r0={x:90+26,y:190+74+src[fl.g][0]*58,w:700,h:50};const m=tgt[fl.g];
    const r1={x:1000+parseFloat(m[0].style.left),y:190+parseFloat(m[0].style.top),w:fl.g===0?770:parseFloat(m[0].style.width),h:parseFloat(m[0].style.height)};
    css(S.fly,{left:lerp(r0.x,r1.x,fl.k)+'px',top:(lerp(r0.y,r1.y,fl.k)-Math.sin(fl.k*Math.PI)*80)+'px',width:lerp(r0.w,r1.w,fl.k)+'px',height:lerp(r0.h,r1.h,fl.k)+'px',opacity:1-P(fl.k,.8,1)});}}
function dashRect(R,rad){css(D.clip,{left:R.x+'px',top:R.y+'px',width:R.w+'px',height:R.h+'px',borderRadius:rad+'px',opacity:1,boxShadow:'0 50px 100px -40px rgba(0,0,0,.9)',overflow:'hidden',background:'transparent',perspective:'none'});}
function dashFlat(sc,vals=1,line=1,bars=1,hover=0,exp=0){css(D.d,{transform:`scale(${sc})`,transformOrigin:'0 0'});D.parts.forEach(p=>css(p,{transform:'none',opacity:1,clipPath:'none'}));
  D.cards.forEach(c=>{const v=c.v*vals;c.val.textContent=c.pre+v.toFixed(1)+c.suf;});const L=D.rvL.getTotalLength();css(D.rvL,{strokeDasharray:L,strokeDashoffset:L*(1-line)});D.rvA.style.opacity=line;
  D.bars.forEach((b,i)=>b.style.transform=`scaleY(${typeof bars==='function'?bars(i):bars})`);const p=D.pts[22];css(D.dot,{left:(p[0]-8)+'px',top:(p[1]-8)+'px',transform:`scale(${hover})`});
  css(D.tip,{left:(p[0]-62)+'px',top:(p[1]-100)+'px',opacity:hover});css(S.exp,{transform:`scale(${1-.08*exp})`,filter:`brightness(${1+exp*.6})`});}
function SH18(t){ // preview grows; ONE PROMPT. ENDLESS MOMENTUM.
  show(S.bg,1);show(D.clip,1);const g=E.inOutCubic(P(t,C.sh18,C.sh19-.12)),f=E.inQuart(P(t,C.sh19-.14,C.sh19));
  const R0={x:1000,y:190,w:830,h:700},R1={x:960,y:150,w:900,h:760},F={x:0,y:0,w:1920,h:1080};
  let R={x:lerp(R0.x,R1.x,g),y:lerp(R0.y,R1.y,g),w:lerp(R0.w,R1.w,g),h:lerp(R0.h,R1.h,g)};R={x:lerp(R.x,F.x,f),y:lerp(R.y,F.y,f),w:lerp(R.w,F.w,f),h:lerp(R.h,F.h,f)};
  dashRect(R,lerp(20,0,f));dashFlat(R.w/1920);
  show(S.type,1);show(S.typeBg,0);const a=E.outExpo(P(t,C.onep,C.onep+.5)),b=E.outExpo(P(t,C.endless,C.endless+.5));
  show(S.one,1);show(S.endl,1);css(S.one,{fontSize:'104px',left:'110px',top:'380px',color:'#F7F7F4',clipPath:`inset(0 ${(1-a)*100}% 0 0)`,opacity:1-f});
  css(S.endl,{fontSize:'64px',left:'114px',top:'500px',color:'#8A877D',clipPath:`inset(0 ${(1-b)*100}% 0 0)`,letterSpacing:'-.02em',opacity:1-f});}
const EXZ=[60,160,200,240,280,330,380];
function SH19(t){ // exploded view
  show(S.bg,1);show(D.clip,1);dashRect({x:0,y:0,w:1920,h:1080},0);const e=E.outQuart(P(t,C.sh19,C.sh19+.9)),orb=E.inOutSine(P(t,C.sh19,C.sh20));
  dashFlat(1,1,1,1,0,0);D.clip.style.perspective='2400px';D.clip.style.overflow='visible';D.clip.style.boxShadow='none';
  css(D.d,{transform:`translate(960px,${lerp(540,600,e)}px) rotateX(${e*50}deg) rotateZ(${-e*(24+orb*8)}deg) scale(${lerp(1,.56,e)}) translate(-960px,-540px)`,transformOrigin:'0 0'});
  D.parts.forEach((p,i)=>css(p,{transform:`translateZ(${EXZ[i]*e*1.25}px)`}));}
function SH20(t){ // reconstruct: each component snaps home, then everything animates to its final values
  show(S.bg,1);show(D.clip,1);dashRect({x:0,y:0,w:1920,h:1080},0);D.clip.style.perspective='2400px';D.clip.style.overflow='visible';D.clip.style.boxShadow='none';
  const fl=E.inOutCubic(P(t,C.flat,C.flat+.8));
  const land=i=>C.r0+i*C.rStep+.2,line=E.inOutCubic(P(t,land(5),land(5)+1.1));
  dashFlat(1,1,line,i=>E.outBack(P(t,land(6)+i*.08,land(6)+i*.08+.4),1.3),E.outBack(P(t,C.hover,C.hover+.3),1.6),bump(t,C.export,.05,.03,.18));
  D.cards.forEach((c,j)=>{const v=c.v*E.outCubic(P(t,land(j+1),land(j+1)+.6));c.val.textContent=c.pre+v.toFixed(1)+c.suf;});
  css(D.d,{transform:`translate(960px,${lerp(600,540,fl)}px) rotateX(${50*(1-fl)}deg) rotateZ(${-32*(1-fl)}deg) scale(${lerp(.56,1,fl)}) translate(-960px,-540px)`,transformOrigin:'0 0'});
  D.parts.forEach((p,i)=>{const ts=C.r0+i*C.rStep,k=E.outBack(P(t,ts,ts+.32),1.7);const sx=(i%2?1:-1)*120*(1-k);
    css(p,{transform:`translate3d(${sx}px,${-(1-k)*40}px,${EXZ[i]*1.25*(1-k)}px) rotateZ(${(1-k)*(i%2?6:-6)}deg)`});});}
function SH21(t){ // one continuous move: the app pulls back into the editor that built it
  show(S.bg,1);show(W.L,1);show(D.clip,1);editorCode('page');hideAgentUI();show(W.prev,true);W.prev.style.transform='none';
  const k=E.inOutQuart(P(t,C.sh21,C.sh21+1.1)),dr=E.inOutSine(P(t,C.sh21+1.1,C.sh22));
  const o={fx:850,fy:470,s:lerp(1.9,.86,k)*lerp(1,.94,dr),rx:0,ry:0,X:960,Y:lerp(480,470,k)};placeWorld(o);
  const[x0,y0]=wpt(o,312,86),[x1,y1]=wpt(o,1212,940);const P0={x:x0,y:y0,w:x1-x0,h:y1-y0};
  const R={x:lerp(0,P0.x,k),y:lerp(0,P0.y,k),w:lerp(1920,P0.w,k),h:lerp(1080,P0.h,k)};dashRect(R,lerp(0,8,k));dashFlat(R.w/1920);D.clip.style.boxShadow='none';
  show(S.type,1);show(S.typeBg,0);const a=E.outExpo(P(t,C.fromc,C.fromc+.5)),b=E.outExpo(P(t,C.toc,C.toc+.5));show(S.from,1);show(S.to,1);
  css(S.from,{fontSize:'84px',left:'110px',top:'890px',color:'#F7F7F4',clipPath:`inset(0 ${(1-a)*100}% 0 0)`});
  css(S.to,{fontSize:'84px',left:'680px',top:'890px',color:'#8A877D',clipPath:`inset(0 ${(1-b)*100}% 0 0)`});}
function SH22cube(t){ // final zoom into the logo
  show(S.bg,1);show(S.cubeL,1);const k=E.inQuart(P(t,C.m5,C.black));cubeAt(960,520,lerp(320,2400,k),lerp(-30,0,E.outCubic(P(t,C.m5,C.m5+.6))),lerp(14,0,E.outCubic(P(t,C.m5,C.m5+.6))),1,E.inOutSine(P(t,C.m5+.1,C.m5+.7)));}
function SH23(t){show(S.lockL,1);horizonOver(t);const k=E.outQuint(P(t,C.sh23,C.sh23+.9));
  const Wc=200,ch=Wc*1601/1402,ww=Wc*4966/1402,wh=ww*837/4966,gap=Wc*265/1402,top=300;const sc=lerp(1.1,1,k);
  css(S.lCube,{left:(960-Wc*sc/2)+'px',top:(top+ch*(1-sc)/2)+'px',width:Wc*sc+'px',height:ch*sc+'px',opacity:P(t,C.sh23,C.sh23+.12)});
  const wr=E.inOutCubic(P(t,C.sh23+.15,C.sh23+.85));css(S.lWord,{left:(960-ww/2)+'px',top:(top+ch+gap)+'px',width:ww+'px',height:wh+'px',WebkitMaskImage:`linear-gradient(90deg,#000 ${wr*120-20}%,transparent ${wr*120}%)`});
  const tg=E.outExpo(P(t,C.tag,C.tag+.6));css(S.tag,{opacity:P(t,C.tag,C.tag+.2),transform:`translateY(${(1-tg)*16}px)`,letterSpacing:`${lerp(.14,.02,tg)}em`});
  css(S.url,{opacity:P(t,C.url,C.url+.3)});css(S.disc,{opacity:.9*P(t,C.disc,C.disc+.4)});}
function fxDust(t,a){show(S.fx,1);show(S.dust,1);S.dust.style.opacity=a;S.motes.forEach(o=>{const x=(o.x+t*(8+o.z*26))%1920,y=o.y+Math.sin(t*.7+o.ph)*14;css(o.m,{left:x+'px',top:y+'px',opacity:(.25+.6*o.z)*(.6+.4*Math.sin(t*2.3+o.ph))});});}
function SHEMBER(t){emberAt(t,C.ember,C.sh5);}
function SHEMBER2(t){emberAt(t,C.black,C.sh23);}
function emberAt(t,A,Z){ // everything has collapsed to one ember; it breathes in the music's break, then detonates on the hit
  show(S.bg,1);fxDust(t,P(t,A,A+.6)*.8);
  const g=E.inQuad(P(t,A,Z)),br=.85+.15*Math.sin(t*9);const sz=lerp(10,46,g)*br,hs=lerp(160,620,g);
  show(S.ember,1);css(S.ember,{left:(960-sz/2)+'px',top:(520-sz/2)+'px',width:sz+'px',height:sz+'px',opacity:P(t,A,A+.15)});
  show(S.halo,1);css(S.halo,{left:(960-hs/2)+'px',top:(520-hs/2)+'px',width:hs+'px',height:hs+'px',opacity:lerp(.3,1,g)*br});
  const pre=E.inQuart(P(t,Z-.18,Z));show(S.streak,pre>0);css(S.streak,{left:(960-900*pre)+'px',top:'517px',width:(1800*pre)+'px',opacity:pre});}
function flareOver(t){ // the detonation: white-out, shockwave ring and an anamorphic streak, decaying into the cube shot
  const u=t-C.sh5;if(u<0||u>1.4)return;show(S.fx,1);fxDust(t,1-P(u,.6,1.4));
  const f=Math.exp(-u/.16);show(S.flare,1);css(S.flare,{opacity:f,transform:`scale(${1+u*.6})`});
  const r=E.outCubic(P(u,0,.9)),R=lerp(120,1500,r);show(S.ring,1);css(S.ring,{left:(960-R/2)+'px',top:(520-R/2)+'px',width:R+'px',height:R+'px',opacity:(1-r)*.9});
  const s=Math.exp(-u/.35);show(S.streak,1);css(S.streak,{left:'0px',top:'517px',width:'1920px',height:(6+10*s)+'px',opacity:s});}
function checkOver(t){ // a comet of light draws the gold checkmark as the Agent reports Ready
  const a=C.ready-.36,u=P(t,a,C.ready);if(t<a||t>C.sh17)return;show(S.fx,1);show(S.chk,1);const k=E.inOutCubic(u);
  S.ckp.style.strokeDasharray=S.ckL;S.ckp.style.strokeDashoffset=S.ckL*(1-k);const p=S.ckp.getPointAtLength(S.ckL*k);
  S.ckh.setAttribute('cx',p.x);S.ckh.setAttribute('cy',p.y);S.ckh.style.opacity=k<1?1:0;
  const pop=bump(t,C.ready,.02,.03,.25);css(S.chk,{opacity:1-P(t,C.sh17-.15,C.sh17),transform:`scale(${1+pop*.08})`});}
function horizonOver(t){ // horizon lens flare under the lockup
  const u=t-C.sh23;if(u<0)return;{const f=Math.exp(-u/.12);show(S.flare,1);css(S.flare,{opacity:f*.85,transform:'scale(1)'});}show(S.fx,1);fxDust(t,.55);const s=Math.exp(-u/.5),w=E.outExpo(P(u,0,.5));
  const top=300+200*1601/1402+18;show(S.hz,1);css(S.hz,{top:top+'px',opacity:.35+.65*s,transform:`scaleX(${w})`});
  show(S.hzG,1);css(S.hzG,{top:(top-210)+'px',opacity:.55+.45*s});}
function SHAGENTS(t){ // three agents work at once; each ticks Done on the beat; they fold into one and collapse into the ember
  show(S.bg,1);show(S.agL,1);fxDust(t,.7);const ck=[C.ckA,C.ckB,C.ckC];
  const fd=E.inOutQuart(P(t,C.fold,C.collapse+.1)),cl=E.inQuart(P(t,C.collapse,C.black));
  const done=ck.filter(x=>t>=x).length;S.pill.innerHTML=done<3?`<span style="width:8px;height:8px;border-radius:50%;background:#F5B54E;box-shadow:0 0 10px #F5B54E;opacity:${.5+.5*Math.sin(t*12)}"></span>3 agents running`:'✓ 3 of 3 done';
  css(S.pill,{opacity:P(t,C.ag0+.15,C.ag0+.35)*(1-fd),transform:`scale(${1+.06*bump(t,C.ckC,.02,.03,.2)})`});
  S.ags.forEach((a,i)=>{const t0=C.ag0+i*.08,k=E.outQuint(P(t,t0,t0+.6));
    const x0=[150,710,1270][i],y0=250;const xf=710+(i-1)*14,yf=250+(1-i)*-10;
    const bob=(1-fd)*(6*Math.sin(t*2.1+i*1.9)),x=lerp(x0,xf,fd),y=lerp(y0,yf,fd)+bob,z=lerp(-900,0,k)+(fd>0?-i*40*fd:0),ry=lerp((i-1)*-22,0,k)+(i-1)*8*fd+(1-fd)*1.5*Math.sin(t*1.3+i),rz=(i-1)*-2*fd;
    const s=lerp(1,0.02,cl);
    css(a.c,{left:x+'px',top:y+'px',opacity:k*(1-P(cl,.7,1)),filter:`blur(${(1-k)*10+cl*6}px) brightness(${1+cl*2})`,
      transform:`translate(${(960-x-250)*cl}px,${(520-y-270)*cl}px) translateZ(${z}px) rotateY(${ry}deg) rotateZ(${rz}deg) scale(${s})`,zIndex:3-i});
    a.ls.forEach((l,j)=>{const ls=t0+.25+j*.09,kk=E.inOutSine(P(t,ls,ls+.16));css(l.tx,{clipPath:`inset(0 ${(1-kk)*100}% 0 0)`});
      css(l.cm,{left:(22+l.n*9.3*kk)+'px',opacity:kk>.01&&kk<.99?1:0});});
    const d=t>=ck[i],dk=E.outBack(P(t,ck[i],ck[i]+.25),2);a.stS.textContent=d?'Done':a.st;a.stS.style.color=d?'#F5C46B':'#8A877D';
    css(a.stB,{background:d?'#F5B54E':'transparent',borderColor:d?'#F5B54E':'#8A877D',boxShadow:d?'0 0 10px #F5B54E':'none'});
    css(a.dn,{opacity:P(t,ck[i],ck[i]+.1),transform:`scale(${lerp(.6,1,dk)})`});css(a.ck,{opacity:P(t,ck[i],ck[i]+.08),transform:`scale(${lerp(.3,1,dk)})`});
    a.c.style.boxShadow=d?`0 50px 90px -40px rgba(0,0,0,.9),0 0 ${40*(1-P(t,ck[i],ck[i]+.6))+14}px rgba(255,170,80,.35)`:'';});
  // the collapse leaves a single glowing point exactly where the ember will appear
  if(cl>0){show(S.fx,1);show(S.halo,1);const hs=lerp(900,160,cl);css(S.halo,{left:(960-hs/2)+'px',top:(520-hs/2)+'px',width:hs+'px',height:hs+'px',opacity:cl});
    show(S.ember,1);const sz=lerp(4,12,cl);css(S.ember,{left:(960-sz/2)+'px',top:(520-sz/2)+'px',width:sz+'px',height:sz+'px',opacity:P(cl,.5,1)});}}
// ---------- edit ----------
const EDIT=[[C.sh0,()=>{show(S.black,1);}],[C.sh3,SH3],[C.sh4,SH4],[C.sh1,SH1],[C.sh2,SH2],[C.ember,SHEMBER],[C.sh5,SH5],[C.sh6,SH6],[C.sh7,SH7],[C.sh8,SH8],[C.sh9,SH9],[C.sh10,SH10],[C.sh11,SH11],[C.sh12,SH12],
  [C.sh13,SH13],[C.sh14,SH14],[C.sh15,SH15],[C.sh16,SH16],[C.sh17,SH17],[C.sh18,SH18],[C.sh19,SH19],[C.sh20,SH20],[C.sh21,SH21],
  [C.ag0,SHAGENTS],[C.black,SHEMBER2],[C.sh23,SH23]];
function camRig(t){ // a living camera: slow float + a gentle push through every shot + a soft kick and blur on each cut
  let a=0,b=C.dur;for(const[c]of EDIT){if(c<=t)a=c;else{b=c;break;}}
  const u=P(t,a,b),push=1+.022*E.inOutSine(u);
  const kick=E.outCubic(P(t,a,a+.45)),ks=a>0.05?lerp(1.035,1,kick):1;
  const x=7*Math.sin(t*.37)+3*Math.sin(t*.91+.6),y=5*Math.sin(t*.29+1.1)+2*Math.sin(t*.77),r=.12*Math.sin(t*.23+.4);
  const bl=a>0.05?4*(1-E.outCubic(P(t,a,a+.12))):0,pre=b<C.dur?3*E.inCubic(P(t,b-.07,b)):0;
  window.CAM.style.transform=`translate(${x}px,${y}px) rotate(${r}deg) scale(${push*ks})`;
  window.CAM.style.filter=(bl+pre)>.05?`blur(${(bl+pre).toFixed(2)}px)`:'none';}
function render(t){
  for(const l of LAYERS){show(l,false);l.style.clipPath='none';l.style.filter='none';l.style.opacity='';}
  for(const k of[S.typeBg,S.ideas,S.into,S.meet,S.less,S.more,S.one,S.endl,S.from,S.to,S.tcar])show(k,0);S.type.style.opacity=1;S.typeBg.style.clipPath='none';
  W.L.style.clipPath='none';W.L.style.filter='none';show(KEY,false);S.fxAll.forEach(e=>show(e,0));S.black.style.opacity='';
  let fn=EDIT[0][1];for(const[a,f]of EDIT)if(t>=a)fn=f;fn(t);
  S.grid.style.backgroundPosition=`${(t*8)%36}px ${(t*4)%36}px`;
}
