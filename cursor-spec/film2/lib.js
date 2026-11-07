'use strict';
const C=window.CUES, stage=document.getElementById('stage');
const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x)), lerp=(a,b,t)=>a+(b-a)*t, P=(t,a,b)=>clamp((t-a)/(b-a));
const E={outCubic:x=>1-Math.pow(1-x,3),outQuart:x=>1-Math.pow(1-x,4),outQuint:x=>1-Math.pow(1-x,5),outExpo:x=>x>=1?1:1-Math.pow(2,-10*x),
  inCubic:x=>x*x*x,inQuad:x=>x*x,inOutCubic:x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2,inOutQuart:x=>x<.5?8*x*x*x*x:1-Math.pow(-2*x+2,4)/2,
  inOutSine:x=>-(Math.cos(Math.PI*x)-1)/2,outBack:(x,s=1.4)=>1+(s+1)*Math.pow(x-1,3)+s*Math.pow(x-1,2)};
function bump(t,a,up=.06,hold=0,down=.14){if(t<a)return 0;const k=t-a;if(k<up)return 1-Math.pow(1-k/up,2);if(k<up+hold)return 1;return 1-E.inOutSine(clamp((k-up-hold)/down));}
function mulberry32(a){return function(){a|=0;a=a+0x6d2b79f5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function el(tag,cls,parent,html){const e=document.createElement(tag);if(cls)e.className=cls;if(html!=null)e.innerHTML=html;(parent||stage).appendChild(e);return e;}
function css(e,o){for(const k in o)e.style[k]=o[k];return e;}
function show(e,on){e.style.display=on?'':'none';}
const typed=(arr,t)=>{let n=0;for(const x of arr)if(t>=x)n++;return n;};
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

// ---------------- syntax highlighting (TS/TSX) ----------------
const KW=new Set(['import','from','export','function','const','return','type','default','new','use']);
function toks(s){const out=[];const re=/("(?:[^"\\]|\\.)*"|`(?:[^`\\]|\\.)*`)|(\b\d+(?:\.\d+)?\b)|(<\/?[A-Za-z][\w.]*)|([A-Za-z_$][\w$]*)|(\s+)|([^\sA-Za-z0-9_$"`])/g;let m;
  while((m=re.exec(s))){let c='p';const w=m[0];
    if(m[1])c='s';else if(m[2])c='n';else if(m[3])c='f';
    else if(m[4]){const nx=s.slice(re.lastIndex).match(/^\s*\(/);c=KW.has(w)?'k':/^[A-Z]/.test(w)?'y':nx?'f':'i';}
    else if(m[5])c='';out.push([w,c]);}
  return out;}
function hl(s,n=Infinity){let h='',k=0;for(const[w,c]of toks(s)){if(k>=n)break;const part=w.slice(0,n-k);k+=part.length;h+=c?`<span class="${c}">${esc(part)}</span>`:esc(part);}return h;}

// ---------------- stage: light, depth, grain ----------------
const BG={};
function buildBG(){
  BG.L=el('div','L');
  BG.spot=el('div','L',BG.L);css(BG.spot,{background:'radial-gradient(60% 55% at 50% 32%,rgba(247,238,214,.10),rgba(247,238,214,.03) 45%,transparent 72%)'});
  BG.grid=el('div','L',BG.L);css(BG.grid,{backgroundImage:'radial-gradient(rgba(247,247,244,.10) 1px,transparent 1.4px)',backgroundSize:'36px 36px',
    WebkitMaskImage:'radial-gradient(55% 60% at 50% 45%,#000,transparent 75%)'});
  BG.floor=el('div','a',BG.L);css(BG.floor,{left:'260px',width:'1400px',top:'860px',height:'160px',borderRadius:'50%',background:'radial-gradient(closest-side,rgba(0,0,0,.65),transparent)'});
}
function updBG(t,on){show(BG.L,on);if(!on)return;
  const s2=P(t,C.open,C.cube+.6);BG.L.style.opacity=s2;
  css(BG.grid,{backgroundPosition:`${(t*6)%36}px ${(t*3)%36}px`});
  css(BG.spot,{transform:`translateX(${Math.sin(t*.25)*60}px)`});
}

// ---------------- the editor world + camera ----------------
const W={};
const FILES={
  hook:{name:'useMetrics.ts',ic:'ts',lines:['import { useEffect, useState } from "react"','import type { Metric } from "@/lib/types"','',
    'export function useMetrics(range: "7d" | "30d") {','  const [data, setData] = useState<Metric[]>([])','  useEffect(() => {','    fetch(`/api/metrics?range=${range}`)',
    '      .then((r) => r.json())','      .then(setData)','  }, [range])','  return data','}','',
    'export const compact = (n: number) =>','  new Intl.NumberFormat("en", { notation: "compact" }).format(n)']},
  card:{name:'MetricCard.tsx',ic:'tx',lines:['type Props = { label: string; value: string; delta: number }','',
    'export function MetricCard({ label, value, delta }: Props) {','  return (','    <div className="card">','      <p className="label">{label}</p>',
    '      <h3 className="value">{value}</h3>','      <span className="delta">','        {delta > 0 ? "+" : ""}{delta}%','      </span>','    </div>','  )','}']},
  rev:{name:'RevenueChart.tsx',ic:'tx',lines:['"use client"','import { Area, AreaChart, ResponsiveContainer } from "recharts"','import { useMetrics } from "@/hooks/useMetrics"','',
    'export function RevenueChart() {','  const data = useMetrics("30d")','  return (','    <ResponsiveContainer height={420}>','      <AreaChart data={data}>',
    '        <Area dataKey="revenue" strokeWidth={2.5} />','      </AreaChart>','    </ResponsiveContainer>','  )','}']},
  sig:{name:'SignupsChart.tsx',ic:'tx',lines:['"use client"','import { Bar, BarChart, ResponsiveContainer } from "recharts"','',
    'const channels = ["Organic", "Social", "Referral", "Ads", "Email"]','','export function SignupsChart({ data }: { data: number[] }) {','  const rows = data.map((v, i) => ({ channel: channels[i], v }))',
    '  return (','    <ResponsiveContainer height={420}>','      <BarChart data={rows}>','        <Bar dataKey="v" radius={8} />','      </BarChart>','    </ResponsiveContainer>','  )','}']},
  page:{name:'page.tsx',ic:'tx',lines:['import { compact } from "@/hooks/useMetrics"','import { MetricCard } from "@/components/MetricCard"','import { RevenueChart } from "@/components/RevenueChart"',
    'import { SignupsChart } from "@/components/SignupsChart"','','export default function Dashboard() {','  return (','    <main className="dashboard">',
    '      <MetricCard label="MRR" value={"$" + compact(48200)} delta={12.4} />','      <MetricCard label="Active users" value={compact(12904)} delta={8.1} />',
    '      <MetricCard label="Conversion" value="3.8%" delta={0.6} />','      <MetricCard label="Churn" value="1.2%" delta={-0.3} />',
    '      <RevenueChart />','      <SignupsChart data={[320, 210, 180, 260, 140]} />','    </main>','  )','}']},
};
const TREE=[['app/',0,''],['dashboard/',1,''],['page.tsx',2,'page','tx'],['layout.tsx',1,'','tx'],['components/',0,''],['MetricCard.tsx',1,'card','tx'],['RevenueChart.tsx',1,'rev','tx'],['SignupsChart.tsx',1,'sig','tx'],
  ['hooks/',0,''],['useMetrics.ts',1,'hook','ts'],['lib/',0,''],['types.ts',1,'','ts'],['package.json',0,''],['tsconfig.json',0,'']];
function buildWorld(){
  const L=W.L=el('div','L');css(L,{perspective:'2600px',perspectiveOrigin:'50% 45%'});
  const w=W.win=el('div',null,L);w.id='win';
  W.frame=el('div','frame',w);
  W.tb=el('div','tb',w,'acme-analytics');el('div','dots',W.tb,'<i></i><i></i><i></i>');
  W.icon=el('img','a',W.tb);W.icon.src='brand/CUBE_25D.png';css(W.icon,{left:'calc(50% - 92px)',top:'10px',width:'17px'});
  // sidebar
  W.side=el('div','pane side',w);const act=el('div','act',W.side,'<i class="on"></i><i></i><i></i><i></i>');
  const tr=el('div','tree',W.side);el('div','h',tr,'EXPLORER');
  W.rows={};for(const[nm,d,key,ic]of TREE){const r=el('div','r'+(d?' d'+Math.min(d,1):''),tr);if(d===2)r.style.paddingLeft='58px';
    el('i','ic'+(ic?' '+ic:''),r);el('span',null,r,nm);if(key)W.rows[key]=r;}
  // editor
  W.ed=el('div','pane ed',w);W.tabs=el('div','tabs',W.ed);W.tabEls={};
  W.codeBox=el('div','code',W.ed);W.lines=[];for(let i=0;i<26;i++){const d=el('div','ln',W.codeBox);const o={d,bg:el('div','bg',d),bar:el('div','bar',d),no:el('div','no',d,String(i+1)),tx:el('div','tx',d),gh:el('div','gh',d),k:''};W.lines.push(o);}
  W.caret=el('div','caret',W.codeBox);
  W.sweep=el('div','a',W.codeBox);css(W.sweep,{left:0,right:0,height:'3px',background:'linear-gradient(90deg,transparent,rgba(247,247,244,.9),transparent)',boxShadow:'0 0 16px rgba(247,247,244,.6)'});
  W.term=el('div','term',W.ed,'<div class="hd"><span style="color:#E7E5DD">TERMINAL</span><span>PROBLEMS</span><span>OUTPUT</span></div>');
  W.tl=[];for(let i=0;i<6;i++){const d=el('div',null,W.term);css(d,{padding:'0 20px',whiteSpace:'pre'});W.tl.push(d);}
  const TL=['<span style="color:#79C796">$</span> npm run dev','<span style="color:#8A877D">&gt; acme-analytics@0.1.0 dev</span>','<span style="color:#8A877D">&gt; next dev</span>','',
    '  - Local:   <span style="color:#8EC5F2">http://localhost:3000</span>','<span style="color:#79C796">✓</span> Ready in 1.4s'];
  W.tl.forEach((d,i)=>d.innerHTML=TL[i]);
  // preview pane (Cursor's browser tab) — filled by the dashboard element during the reveal
  W.prev=el('div','preview',w,'<div class="url"><span>localhost:3000/dashboard</span></div>');
  // agent
  W.ag=el('div','pane agent',w,'<div class="hd"><b>Agent</b><span style="color:#5B594F;font-size:13px;margin-left:auto">⌘I</span></div>');
  W.inp=el('div','input',W.ag);W.inTxt=el('div',null,W.inp);W.send=el('div','send',W.inp,'<svg width="16" height="16" viewBox="0 0 16 16"><path d="M8 13V3M3.5 7.5L8 3l4.5 4.5" stroke="#14120B" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>');
  W.bub=el('div','bubble',W.ag,'Build a responsive analytics dashboard.');css(W.bub,{top:'64px'});
  W.m1=el('div','msg',W.ag,'I’ll add metric cards, a revenue chart and a signups chart, then wire them into a dashboard page.');css(W.m1,{top:'176px'});
  const STEPS=[['Read app/page.tsx','',''],['Edited MetricCard.tsx','+13',''],['Edited RevenueChart.tsx','+14',''],['Edited SignupsChart.tsx','+15',''],['Edited app/dashboard/page.tsx','+17','−2'],['Ran npm run dev','','']];
  W.steps=STEPS.map(([a,p,m],i)=>{const s=el('div','step',W.ag,`<span class="dot"></span><span>${a}</span><span class="dif"><span class="pl">${p}</span><span class="mi">${m}</span></span>`);css(s,{top:(270+i*50)+'px'});return s;});
  W.done=el('div','msg',W.ag,'Done. The dashboard is running at <span style="color:#8EC5F2">localhost:3000</span>.');css(W.done,{top:'580px'});
  // panel offsets for the exploded build
  W.parts=[W.side,W.ed,W.ag,W.tb];
  W.sheen=el('div','a',w);css(W.sheen,{left:0,top:0,width:'1700px',height:'940px',borderRadius:'16px',pointerEvents:'none',
    background:'linear-gradient(115deg,transparent 35%,rgba(247,247,244,.07) 48%,rgba(247,247,244,.02) 54%,transparent 62%)',backgroundSize:'260% 100%'});
}
function setCode(fileKey,opt={}){
  const F=FILES[fileKey];
  for(let i=0;i<W.lines.length;i++){const o=W.lines[i],s=F.lines[i];const has=s!==undefined;
    show(o.d,has);if(!has)continue;
    const st=opt.state?opt.state(i):{n:Infinity,ghost:false,solid:1,add:0};
    const key=fileKey+'|'+i+'|'+st.n+'|'+st.ghost;
    if(o.k!==key){o.k=key;o.tx.innerHTML=st.ghost?'':hl(s,st.n);o.gh.textContent=st.ghost?s:'';}
    o.tx.style.clipPath=st.ghost&&st.solid<1?`inset(0 ${100-st.solid*100}% 0 0)`:'none';
    if(st.ghost&&st.solid>0){o.tx.innerHTML=hl(s);o.tx.style.clipPath=`inset(0 ${100-st.solid*100}% 0 0)`;o.gh.style.opacity=1-st.solid;}else o.gh.style.opacity=st.gOp??1;
    o.bg.style.transform=`scaleX(${st.add||0})`;o.bg.style.opacity=st.add?1:0;o.bar.style.opacity=st.add?1:0;
  }
}
function setTabs(list,on){const key=list.join(',')+'|'+on;if(W.tabKey===key)return;W.tabKey=key;W.tabs.innerHTML='';
  for(const k of list){const tdiv=el('div','t'+(k===on?' on':''),W.tabs,`<i class="ic ${FILES[k].ic}" style="width:11px;height:11px;border-radius:3px;display:inline-block;background:${FILES[k].ic==='ts'?'#3B5E86':'#3E7C6C'}"></i>${FILES[k].name}`);}
  for(const k in W.rows)W.rows[k].classList.toggle('on',k===on);}
// camera keys: t, focus x/y in window px, scale, rotateX, rotateY, frame anchor x/y
let KEY;function buildKey(){KEY=el('div');KEY.id='key';css(KEY,{zIndex:58});el('div','base',KEY);
  KEY.cap=el('div','cap',KEY,'<span>tab</span><svg width="34" height="22" viewBox="0 0 34 22"><path d="M2 11h26M20 3l8 8-8 8M31 2v18" stroke="#D8D5CB" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>');
  KEY.glow=el('div','a',KEY);css(KEY.glow,{left:'-30px',top:'-30px',right:'-30px',bottom:'-30px',borderRadius:'40px',background:'radial-gradient(closest-side,rgba(247,247,244,.18),transparent)'});}
// ---------------- 5 · the dashboard ----------------
const D={};
const LINE=(()=>{const r=mulberry32(5);let v=40;return Array.from({length:30},(_,i)=>{v+=(r()-.38)*9+.9;return Math.max(18,v);});})();
const BARS=[320,210,180,260,140],CH=['Organic','Social','Referral','Ads','Email'];
function buildDash(){
  D.clip=el('div','a');css(D.clip,{zIndex:50,overflow:'hidden',perspective:'2400px'});
  const d=D.d=el('div',null,D.clip);d.id='dash';
  D.base=el('div','L',d);
  el('div','a',D.base,'<div style="font-size:34px;font-weight:600;letter-spacing:-.02em">Analytics</div><div style="font-size:17px;color:#77746B;margin-top:6px;font-weight:500">acme · last 30 days</div>').style.cssText+='left:120px;top:52px';
  const seg=el('div','a',D.base,'<span style="padding:8px 16px;border-radius:999px">7d</span><span style="padding:8px 16px;border-radius:999px;background:#14120B;color:#F7F7F4">30d</span>');
  css(seg,{right:'120px',top:'62px',display:'flex',gap:'4px',padding:'4px',borderRadius:'999px',background:'#E6E4DC',fontSize:'16px',fontWeight:600});
  const CARDS=[['MRR','$',48.2,'K','+12.4%'],['Active users','',12.9,'K','+8.1%'],['Conversion','',3.8,'%','+0.6%'],['Churn','',1.2,'%','−0.3%']];
  D.cards=CARDS.map(([lab,pre,v,suf,dl],i)=>{const c=el('div','card',d);css(c,{left:(120+i*426)+'px',top:'150px',width:'402px',height:'190px'});
    el('div','lab a',c,lab).style.cssText+='left:30px;top:28px';const val=el('div','val a',c);val.style.cssText+='left:30px;top:66px';
    const ch=el('div','chip a',c,dl);ch.style.cssText+=`left:30px;top:142px;background:${dl[0]==='−'?'#F6E4DF':'#E3F1E7'};color:${dl[0]==='−'?'#A4472F':'#2F7A4F'}`;return{c,val,pre,v,suf};});
  // revenue area chart
  const rc=D.rc=el('div','card',d);css(rc,{left:'120px',top:'366px',width:'1104px',height:'480px'});
  el('div','lab a',rc,'Revenue').style.cssText+='left:30px;top:26px';
  const W_=1044,H_=360,mx=Math.max(...LINE)*1.1;const pts=LINE.map((v,i)=>[30+i*(W_-30)/29,96+H_-(v/mx)*H_]);
  const path='M'+pts.map(p=>p.map(x=>x.toFixed(1)).join(' ')).join(' L');
  rc.insertAdjacentHTML('beforeend',`<svg class="a" style="left:0;top:0" width="1104" height="480"><g stroke="#ECEAE3">${[0,1,2,3].map(k=>`<line x1="30" x2="1074" y1="${120+k*96}" y2="${120+k*96}"/>`).join('')}</g>
    <path id="rvA" d="${path} L ${pts[29][0]} 456 L 30 456 Z" fill="url(#rg)"/><defs><linearGradient id="rg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#14120B" stop-opacity=".12"/><stop offset="1" stop-color="#14120B" stop-opacity="0"/></linearGradient></defs>
    <path id="rvL" d="${path}" fill="none" stroke="#14120B" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/></svg>`);
  D.rvL=rc.querySelector('#rvL');D.rvA=rc.querySelector('#rvA');D.pts=pts;
  D.tip=el('div','a',rc,'<div style="font-size:14px;color:#77746B;font-weight:500">Nov 24</div><div style="font-size:22px;font-weight:600">$1,840</div>');
  css(D.tip,{background:'#14120B',color:'#F7F7F4',borderRadius:'12px',padding:'10px 14px'});D.tip.firstChild.style.color='#B5B2A8';
  D.dot=el('div','a',rc);css(D.dot,{width:'16px',height:'16px',borderRadius:'50%',background:'#14120B',boxShadow:'0 0 0 5px #fff,0 0 0 6px #14120B'});
  // signups bars
  const bc=D.bc=el('div','card',d);css(bc,{left:'1248px',top:'366px',width:'552px',height:'480px'});
  el('div','lab a',bc,'Signups by channel').style.cssText+='left:30px;top:26px';
  D.bars=BARS.map((v,i)=>{const b=el('div','a',bc);css(b,{left:(40+i*102)+'px',width:'70px',bottom:'64px',height:(v/320*300)+'px',borderRadius:'10px 10px 4px 4px',background:i===0?'#14120B':'#CFCCC2',transformOrigin:'50% 100%'});
    el('div','a',bc,CH[i]).style.cssText+=`left:${30+i*102}px;width:90px;text-align:center;bottom:26px;font-size:15px;color:#77746B;font-weight:500`;return b;});
}
// film grain
let grain;function buildGrain(){grain=el('div','L');css(grain,{zIndex:900,pointerEvents:'none',mixBlendMode:'overlay',opacity:'.045'});const tiles=[];
  for(let k=0;k<4;k++){const c=document.createElement('canvas');c.width=c.height=256;const g=c.getContext('2d');const d=g.createImageData(256,256);const r=mulberry32(101+k);for(let i=0;i<d.data.length;i+=4){const v=r()*255;d.data[i]=d.data[i+1]=d.data[i+2]=v;d.data[i+3]=255;}g.putImageData(d,0,0);tiles.push(c.toDataURL());}grain.tiles=tiles;}
function updGrain(t){const f=Math.floor(t*C.fps);grain.style.backgroundImage=`url(${grain.tiles[f%4]})`;const r=mulberry32(f*31+7);grain.style.backgroundPosition=`${Math.floor(r()*256)}px ${Math.floor(r()*256)}px`;}

