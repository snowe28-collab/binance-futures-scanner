# -*- coding: utf-8 -*-
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Binance Futures V2",
    page_icon="📊",
    layout="wide",
)

st.title("📊 محلل بايننس فيوتشر V2")
st.caption("قوة الاتجاه + جودة الدخول + دعم ومقاومة")

PAGE = r"""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;padding:8px;background:#f3f6fb;color:#18253b;
font-family:Arial,sans-serif;font-size:16px}
.card{background:white;border:1px solid #dce3ed;border-radius:16px;
padding:17px;margin-bottom:14px}
h2{font-size:21px}
p{line-height:1.8}
label{display:block;margin:14px 0 7px}
input,select,button{font:inherit;border-radius:10px;padding:12px}
input,select{width:100%;border:1px solid #cbd5e1;background:white;color:#17243b}
button{border:0;background:#1260dc;color:white;cursor:pointer;
margin:8px 0;min-height:46px}
button:disabled{opacity:.5;cursor:wait}
.secondary{background:#42536e}
.info{background:#eaf2ff;padding:14px;border-radius:12px;line-height:1.8}
.small{font-size:14px;color:#536176;line-height:1.8}
.wrap{overflow:auto;max-height:650px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:12px;border-bottom:1px solid #e2e8f0;white-space:nowrap;text-align:right}
th{background:#edf2f8;position:sticky;top:0}
a{color:#075de8;font-weight:bold}
.good{color:#087d54;font-weight:bold}
.bad{color:#bd3042;font-weight:bold}
.metrics{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
.metric{background:#eef3fa;padding:12px;border-radius:12px;flex:1}
.metric b{display:block;font-size:24px;margin-top:6px}
progress{width:100%;height:18px}
summary{cursor:pointer;padding:12px;background:#eef3fa;border-radius:9px}
pre,#status{white-space:pre-wrap;line-height:1.8}
#levels td{white-space:normal}
</style>
</head>
<body>

<div class="card">
<h2>فحص عقود USDT الدائمة</h2>
<div class="info">
V2 — الاتجاه على اليومي و4 ساعات، ومستويات من قمم وقيعان مؤكدة.
الهدف الأول قبل أقرب مستوى معاكس.
درجة الاتجاه ليست نسبة نجاح، والبرنامج لا ينفذ صفقات.
</div>

<button id="test">1 — اختبار الاتصال</button>
<div id="connection" class="small">اختبر الاتصال أولًا.</div>

<label>عدد العملات حسب حجم تداول 24 ساعة</label>
<select id="count">
<option selected>20</option><option>50</option><option>100</option>
<option>200</option><option value="all">الكل</option>
</select>

<label>أقل حجم تداول — مليون USDT</label>
<input id="volume" type="number" min="0" value="10" step="5">

<label>أقل درجة اتجاه للدخول</label>
<select id="threshold">
<option>50</option><option>55</option><option>60</option>
<option selected>65</option><option>70</option><option>75</option>
<option>80</option><option>85</option>
</select>

<p class="small">
الحد الأدنى للعائد/المخاطرة إلى الهدف الأول: 1.2.
هذا شرط لجودة الدخول، وليس تقديرًا لاحتمال الربح.
</p>

<button id="scan" disabled>2 — تحليل السوق الآن</button>
<button id="stop" class="secondary" disabled>إيقاف</button>
<progress id="progress" value="0" max="1"></progress>
<div id="status">بانتظار الاختبار.</div>
<p class="small">
ابقَ بالصفحة أثناء الفحص. الأسعار لقطة وقت فحص كل عملة،
وتغيير الإعدادات يحتاج فحصًا جديدًا.
</p>
</div>

<div id="results" hidden>
<div class="card">
<h2>نتائج الفحص</h2>
<div id="stamp" class="small"></div>
<div id="metrics" class="metrics"></div>

<label>عرض النتائج</label>
<select id="filter">
<option value="all">الكل — فرص الدخول أولًا</option>
<option value="active">إشارات الدخول فقط</option>
<option value="long">شراء Long</option>
<option value="short">بيع Short</option>
<option value="watch">الانتظار والمراقبة</option>
</select>

<p class="small">
اسحب الجدول أفقيًا. الضغط على اسم العملة يفتح TradingView على 4 ساعات.
</p>
<div class="wrap" id="table"></div>
<button id="download" class="secondary">تنزيل CSV</button>
</div>

<div class="card">
<h2>🔎 تفاصيل العملة</h2>
<select id="selected"></select>
<div id="detail"></div>
</div>
</div>

<div class="card">
<details>
<summary>أخطاء الاتصال والعملات المستبعدة</summary>
<pre id="errors"></pre>
</details>
<details style="margin-top:14px">
<summary>طريقة حساب المستويات</summary>
<p class="small">
القمة أو القاع يتأكد بعد شمعتين مغلقتين على يمينه.
نبحث في آخر 180 شمعة على 4 ساعات و120 شمعة يومية،
ثم نختار أقرب دعم تحت السعر وأقرب مقاومة فوقه.
المستويات تاريخية وقد تُكسر؛ لا تمثل أوامر دفتر السوق.
</p>
<p class="small">
الوقف خلف أقرب مستوى حماية بهامش 0.2 ATR،
وبمسافة لا تقل عن 1.5 ATR على 4 ساعات.
الهدف الأول قبل المستوى المعاكس بهامش 0.2 ATR.
إذا غاب مستوى معاكس معروف يُعرض هدف تقديري عند 2R مع توضيح ذلك.
</p>
<p class="small">
الهدفان الثاني والثالث امتدادات حسابية مشروطة بتجاوز الهدف الأول
والمستويات التالية؛ وليسا توقعًا مضمونًا.
لا تُعرض خطة دخول فعالة عندما تكون الإشارة انتظارًا.
</p>
</details>
<p class="small">
الأرقام لحركة السعر دون رافعة، وقبل الرسوم والتمويل والانزلاق.
تحديد الوقف لا يضمن التنفيذ عند السعر نفسه.
</p>
</div>

<script>
"use strict";
const $=id=>document.getElementById(id);
const BASE="https://fapi.binance.com";
let rows=[],errors=[],ready=false,stopped=false,cooldown=0;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const last=a=>a[a.length-1];
const mean=a=>a.reduce((s,x)=>s+x,0)/a.length;
const esc=x=>String(x).replace(/[&<>"']/g,c=>({
"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[c]));
const fmt=x=>Number.isFinite(x)?
Number(x).toLocaleString("en-US",{maximumSignificantDigits:8}):"—";
const dec=x=>Number.isFinite(x)?x.toFixed(2):"—";
const tv=s=>"https://www.tradingview.com/chart/?symbol="+
encodeURIComponent("BINANCE:"+s+".P")+"&interval=240";

function fatal(message){
 const e=new Error(message);e.fatal=true;return e;
}
function log(symbol,message){
 errors.push(symbol+": "+message);
 $("errors").textContent=errors.join("\n");
}
function busy(value){
 $("test").disabled=value;
 $("scan").disabled=value||!ready;
 $("stop").disabled=!value;
 for(const id of ["count","volume","threshold"]) $(id).disabled=value;
}
async function get(path,params={}){
 if(Date.now()<cooldown) throw fatal("مهلة طلبات بايننس لم تنتهِ بعد.");
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),20000);
 try{
  const response=await fetch(BASE+path+"?"+new URLSearchParams(params),{
   signal:controller.signal,credentials:"omit"
  });
  if([403,451].includes(response.status))
   throw fatal("رفض الاتصال من بايننس: HTTP "+response.status);
  if([418,429].includes(response.status)){
   const retry=Number(response.headers.get("Retry-After"));
   cooldown=Date.now()+Math.max(300000,Number.isFinite(retry)?retry*1000:0);
   throw fatal("تم بلوغ حد الطلبات. انتظر 5 دقائق على الأقل قبل الاختبار.");
  }
  if(!response.ok) throw new Error("HTTP "+response.status);
  const data=await response.json();
  if(data&&!Array.isArray(data)&&Number(data.code)<0)
   throw new Error(data.msg||"خطأ من بايننس");
  return data;
 }catch(e){
  if(e.name==="AbortError") throw fatal("انتهت مهلة الاتصال.");
  if(e instanceof TypeError)
   throw fatal("تعذرت قراءة البيانات: تحقق من الشبكة أو قيود CORS.");
  throw e;
 }finally{clearTimeout(timer);}
}

$("test").onclick=async()=>{
 ready=false;busy(true);
 $("connection").textContent="جارٍ الاختبار...";
 try{
  const price=await get("/fapi/v2/ticker/price",{symbol:"BTCUSDT"});
  if(!(Number(price.price)>0)) throw new Error("سعر غير صالح");
  await get("/fapi/v1/exchangeInfo");
  const k=await get("/fapi/v1/klines",{symbol:"BTCUSDT",interval:"4h",limit:5});
  if(!Array.isArray(k)||!k.length) throw new Error("شموع غير صالحة");
  ready=true;
  $("connection").textContent="نجح الاتصال بالسعر والعقود والشموع.";
  $("status").textContent="جاهز للفحص.";
 }catch(e){
  $("connection").textContent=e.message;log("الاتصال",e.message);
 }finally{busy(false);}
};

function ema(a,n){
 const alpha=2/(n+1),out=[a[0]];
 for(let i=1;i<a.length;i++) out.push(alpha*a[i]+(1-alpha)*out[i-1]);
 return out;
}
function wilder(a,n){
 const out=Array(a.length).fill(NaN);
 if(a.length<n)return out;
 out[n-1]=mean(a.slice(0,n));
 for(let i=n;i<a.length;i++)out[i]=(out[i-1]*(n-1)+a[i])/n;
 return out;
}
function indicators(d){
 const c=d.map(x=>x.c),e20=ema(c,20),e50=ema(c,50);
 const fast=ema(c,12),slow=ema(c,26);
 const macd=fast.map((x,i)=>x-slow[i]),signal=ema(macd,9);
 const gains=[0],losses=[0];
 for(let i=1;i<c.length;i++){
  gains.push(Math.max(c[i]-c[i-1],0));
  losses.push(Math.max(c[i-1]-c[i],0));
 }
 const ag=wilder(gains,14),al=wilder(losses,14);
 const atr=wilder(d.map((x,i)=>i?Math.max(
  x.h-x.l,Math.abs(x.h-c[i-1]),Math.abs(x.l-c[i-1])
 ):x.h-x.l),14);
 return d.map((x,i)=>({
  ...x,e20:e20[i],e50:e50[i],atr:atr[i],hist:macd[i]-signal[i],
  rsi:al[i]===0?(ag[i]===0?50:100):100-100/(1+ag[i]/al[i]),
  momentum:i>=18?(x.c/c[i-18]-1)*100:NaN,
  vr:i>=20?x.v/mean(d.slice(i-20,i).map(z=>z.v)):NaN
 }));
}
async function candles(symbol,interval){
 const raw=await get("/fapi/v1/klines",{symbol,interval,limit:499});
 if(!Array.isArray(raw))throw new Error("رد شموع غير صالح");
 const now=Date.now(),duration=interval==="4h"?14400000:86400000;
 const d=raw.filter(x=>Number(x[6])<now).map(x=>({
  t:Number(x[0]),o:Number(x[1]),h:Number(x[2]),l:Number(x[3]),
  c:Number(x[4]),v:Number(x[5]),end:Number(x[6])
 }));
 if(d.length<210)throw new Error("تاريخ أقل من 210 شموع");
 if(now-last(d).end>duration*1.25)throw new Error("شموع قديمة");
 for(let i=0;i<d.length;i++){
  const x=d[i];
  if(![x.o,x.h,x.l,x.c,x.v].every(Number.isFinite)||
    x.l<=0||x.h<x.l||x.v<0)throw new Error("قيم غير صالحة");
  if(i&&x.t-d[i-1].t!==duration)throw new Error("فجوات بالشموع");
 }
 return indicators(d);
}
function score(h,d,side){
 const tests=[
  [side*(h.c-h.e20)>0,20,"السعر والمتوسط متوافقان"],
  [side*(h.e20-h.e50)>0,20,"اتجاه 4 ساعات داعم"],
  [side*(d.c-d.e50)>0,20,"اليومي داعم"],
  [side*h.hist>0,15,"MACD داعم"],
  [side*h.momentum>0,15,"زخم 3 أيام داعم"],
  [side===1?h.rsi>=48&&h.rsi<=70:h.rsi>=30&&h.rsi<=52,10,"RSI مناسب"]
 ];
 return {
  value:tests.reduce((sum,x)=>sum+(x[0]?x[1]:0),0),
  reasons:tests.filter(x=>x[0]).map(x=>x[2])
 };
}

// مستويات مؤكدة فقط: شمعتان مغلقتان على كل جانب.
function pivots(d,label,lookback){
 const out=[],start=Math.max(2,d.length-lookback);
 for(let i=start;i<d.length-2;i++){
  const x=d[i],others=[d[i-2],d[i-1],d[i+1],d[i+2]];
  if(others.every(z=>x.h>z.h))out.push({p:x.h,source:label+" قمة"});
  if(others.every(z=>x.l<z.l))out.push({p:x.l,source:label+" قاع"});
 }
 return out;
}
function nearby(h,d,p){
 const levels=[...pivots(h,"4س",180),...pivots(d,"يومي",120)];
 const below=levels.filter(x=>x.p<p).sort((a,b)=>b.p-a.p);
 const above=levels.filter(x=>x.p>p).sort((a,b)=>a.p-b.p);
 return {support:below[0]||null,resistance:above[0]||null};
}
function plan(p,a,side,support,resistance){
 const buffer=.2*a;
 const anchor=side===1?support:resistance;
 const stop=side===1?
  Math.min(anchor===null?p-1.5*a:anchor-buffer,p-1.5*a):
  Math.max(anchor===null?p+1.5*a:anchor+buffer,p+1.5*a);
 const risk=Math.abs(p-stop),barrier=side===1?resistance:support;
 const target=barrier===null?p+side*2*risk:barrier-side*buffer;
 const reward=side*(target-p),rr=reward/risk;
 return {stop,risk,target,rr,barrier,valid:stop>0&&target>0&&reward>0};
}
function comparison(d,side){
 const feature=x=>[
  (x.rsi-50)/20,
  Math.max(-6,Math.min(6,(x.c-x.e20)/x.atr)),
  Math.max(-6,Math.min(6,(x.e20-x.e50)/x.atr)),
  Math.max(-10,Math.min(10,x.momentum/100*x.c/x.atr))
 ];
 const current=feature(last(d)),candidates=[];
 for(let i=200;i<d.length-42;i++){
  const f=feature(d[i]);
  if(f.every(Number.isFinite))candidates.push({
   i,dist:f.reduce((s,x,j)=>s+(x-current[j])**2,0)
  });
 }
 candidates.sort((a,b)=>a.dist-b.dist);
 const selected=[];
 for(const x of candidates){
  if(selected.every(i=>Math.abs(i-x.i)>=42))selected.push(x.i);
  if(selected.length>=20)break;
 }
 return [3,5,7].map(days=>{
  const values=selected.map(i=>side*(d[i+days*6].c/d[i].c-1)*100);
  const sorted=[...values].sort((a,b)=>a-b),n=values.length;
  return {
   days,n,
   rate:n>=8?values.filter(x=>x>0).length/n*100:NaN,
   median:n>=8?(sorted[Math.floor((n-1)/2)]+sorted[Math.floor(n/2)])/2:NaN
  };
 });
}
async function analyze(t,funding,threshold){
 const symbol=t.symbol,h=await candles(symbol,"4h");
 if(stopped)throw fatal("تم إيقاف الفحص.");
 await sleep(100);
 const daily=await candles(symbol,"1d");
 if(stopped)throw fatal("تم إيقاف الفحص.");
 // سعر جديد لكل عملة، بدل الاعتماد على لقطة قديمة لبداية الفحص.
 const quote=await get("/fapi/v2/ticker/price",{symbol});
 const price=Number(quote.price),priceTime=Number(quote.time);
 if(!(price>0)||!Number.isFinite(priceTime)||
   Math.abs(Date.now()-priceTime)>120000)throw new Error("سعر غير حديث");
 const a=last(h),day=last(daily);
 if(!(a.atr>0))throw new Error("ATR غير صالح");
 const buy=score(a,day,1),sell=score(a,day,-1);
 const side=buy.value>=sell.value?1:-1,best=side===1?buy:sell;
 const levels=nearby(h,daily,price);
 const support=levels.support?levels.support.p:null;
 const resistance=levels.resistance?levels.resistance.p:null;
 const trade=plan(price,a.atr,side,support,resistance);
 const blocks=[];
 let waiting=false;
 if(best.value<threshold)blocks.push("اتفاق الاتجاه أقل من الحد");
 if(!trade.valid)blocks.push("المستويات لا تصلح لخطة دخول");
 if(trade.barrier!==null&&(!trade.valid||trade.rr<1.2)){
  waiting=true;
  blocks.push(side===1?
   "المقاومة قريبة مقارنة بالوقف؛ انتظار اختراق مؤكد وإعادة تقييم":
   "الدعم قريب مقارنة بالوقف؛ انتظار كسر مؤكد وإعادة تقييم");
 }
 if(trade.risk/price>.15)blocks.push("الوقف يتجاوز 15% من السعر");
 if(Math.abs(price-a.e20)>3*a.atr)blocks.push("السعر ممتد؛ انتظار تصحيح");
 if(Math.abs(price-a.c)>1.5*a.atr)blocks.push("حركة كبيرة بعد آخر إغلاق");

 const active=blocks.length===0;
 const decision=active?(side===1?"شراء Long":"بيع Short"):
  waiting?(side===1?"انتظار اختراق":"انتظار كسر"):"مراقبة";
 const quality=active?(trade.rr>=2?"جيد":"مقبول"):"غير جاهز";
 // الامتدادات حسابية ومشروطة وليست مستويات فنية جديدة.
 const extension2=trade.target+side*trade.risk;
 const extension3=trade.target+side*2*trade.risk;
 return {
  symbol,side,active,decision,quality,score:best.value,
  buy:buy.value,sell:sell.value,price,priceTime,
  entry:active?price:NaN,stop:active?trade.stop:NaN,
  t1:active?trade.target:NaN,
  t2:active&&extension2>0?extension2:NaN,
  t3:active&&extension3>0?extension3:NaN,
  rr:trade.valid?trade.rr:NaN,
  risk:trade.risk/price*100,
  support,resistance,
  supportSource:levels.support?levels.support.source:"غير متوفر",
  resistanceSource:levels.resistance?levels.resistance.source:"غير متوفر",
  targetType:trade.barrier===null?"تقديري 2R — لا مستوى معاكس معروف":
   side===1?"قبل أقرب مقاومة":"قبل أقرب دعم",
  funding:funding?Number(funding.lastFundingRate)*100:NaN,
  reason:active?best.reasons.join(" • "):blocks.join(" • "),
  volume:Number(t.quoteVolume),rsi:a.rsi,vr:a.vr,
  candles:h,candleTime:a.t,history:comparison(h,side)
 };
}
function renderTable(){
 const filter=$("filter").value;
 const visible=rows.filter(r=>filter==="all"||
  filter==="active"&&r.active||filter==="watch"&&!r.active||
  filter==="long"&&r.active&&r.side===1||
  filter==="short"&&r.active&&r.side===-1);
 if(!visible.length){$("table").textContent="لا نتائج لهذا الاختيار.";return;}
 const headers=["العملة","القرار","درجة الاتجاه","جودة الدخول","R/R إلى هدف1",
 "السعر","الدخول","الوقف","هدف1","نوع هدف1","هدف2 مشروط","هدف3 مشروط",
 "الدعم","المقاومة","مسافة الوقف %","التمويل %","السبب"];
 $("table").innerHTML="<table><thead><tr>"+
 headers.map(x=>"<th>"+x+"</th>").join("")+"</tr></thead><tbody>"+
 visible.map(r=>"<tr><td><a target='_blank' rel='noopener noreferrer' href='"+
 tv(r.symbol)+"'>"+esc(r.symbol)+" ↗</a></td>"+
 "<td class='"+(r.active?(r.side===1?"good":"bad"):"")+"'>"+r.decision+"</td>"+
 "<td>"+r.score+"</td><td>"+r.quality+"</td><td>"+dec(r.rr)+"</td>"+
 [r.price,r.entry,r.stop,r.t1].map(x=>"<td>"+fmt(x)+"</td>").join("")+
 "<td>"+(r.active?r.targetType:"—")+"</td>"+
 [r.t2,r.t3,r.support,r.resistance].map(x=>"<td>"+fmt(x)+"</td>").join("")+
 "<td>"+dec(r.risk)+"</td><td>"+dec(r.funding)+"</td>"+
 "<td>"+esc(r.reason)+"</td></tr>").join("")+"</tbody></table>";
}
function chart(r){
 const d=r.candles.slice(-100),values=d.map(x=>x.c);
 const levels=[
  [r.support,"دعم","#087d54"],[r.resistance,"مقاومة","#c33242"]
 ];
 if(r.active)levels.push(
  [r.entry,"دخول","#1260dc"],[r.stop,"وقف","#d34c27"],[r.t1,"هدف1","#008979"]
 );
 const valid=levels.filter(x=>Number.isFinite(x[0]));
 values.push(...valid.map(x=>x[0]));
 const lo=Math.min(...values),hi=Math.max(...values);
 const y=p=>230-(p-lo)/Math.max(hi-lo,1e-12)*200;
 const points=d.map((x,i)=>(20+i/(d.length-1)*750)+","+y(x.c)).join(" ");
 return "<svg viewBox='0 0 800 270' style='width:100%' "+
 "role='img' aria-label='إغلاقات أربع ساعات والمستويات'>"+
 "<rect width='800' height='270' fill='#f0f5fc'/>"+
 valid.map(([p,label,color])=>"<line x1='20' x2='770' y1='"+y(p)+
 "' y2='"+y(p)+"' stroke='"+color+"' stroke-dasharray='5 4'/>"+
 "<text x='765' y='"+(y(p)-5)+"' text-anchor='end' direction='rtl' "+
 "fill='"+color+"' font-size='12'>"+label+"</text>").join("")+
 "<polyline points='"+points+"' fill='none' stroke='#1260dc' stroke-width='2'/>"+
 "</svg><p class='small'>إغلاقات آخر 100 شمعة على 4 ساعات.</p>";
}
function detail(){
 const r=rows.find(x=>x.symbol===$("selected").value);
 if(!r)return;
 const levels=[
  ["السعر عند الفحص",fmt(r.price)],["الدخول المرجعي",fmt(r.entry)],
  ["الوقف",fmt(r.stop)],["الهدف الأول",fmt(r.t1)],
  ["نوع الهدف الأول",r.active?r.targetType:"لا توجد خطة فعالة"],
  ["الهدف الثاني — مشروط",fmt(r.t2)],["الهدف الثالث — مشروط",fmt(r.t3)],
  ["أقرب دعم",fmt(r.support)+" — "+r.supportSource],
  ["أقرب مقاومة",fmt(r.resistance)+" — "+r.resistanceSource],
  ["R/R إلى المستوى المعاكس",dec(r.rr)],
  ["مسافة الوقف المحسوبة %",dec(r.risk)]
 ];
 $("detail").innerHTML="<h2>"+esc(r.symbol)+" — "+r.decision+"</h2>"+
 "<p>"+esc(r.reason)+"</p><p>درجة الشراء: "+r.buy+" | درجة البيع: "+r.sell+
 " | جودة الدخول: <b>"+r.quality+"</b></p>"+
 "<p>RSI: "+dec(r.rsi)+" | حجم نسبي: "+dec(r.vr)+"</p>"+
 "<table id='levels'>"+levels.map(x=>"<tr><td>"+x[0]+"</td><td>"+
 esc(x[1])+"</td></tr>").join("")+"</table>"+
 "<p class='small'>وقت السعر: "+new Date(r.priceTime).toISOString()+
 "<br>بداية آخر شمعة مغلقة: "+new Date(r.candleTime).toISOString()+"</p>"+
 chart(r)+
 "<h3>مقارنة وصفية بحالات تاريخية</h3><div class='wrap'><table>"+
 "<tr><th>الأفق</th><th>العينات</th><th>حالات لصالح الاتجاه %</th>"+
 "<th>وسيط الحركة %</th></tr>"+
 r.history.map(x=>"<tr><td>"+x.days+" أيام</td><td>"+x.n+"</td><td>"+
 dec(x.rate)+"</td><td>"+dec(x.median)+"</td></tr>").join("")+
 "</table></div><p class='small'>ليست اختبارًا لاستراتيجية الدخول الجديدة "+
 "أو إصابة أهدافها. نخفي النسب إذا كانت العينات أقل من 8. "+
 "لا تشمل الرسوم والتمويل والانزلاق؛ والأفق ليس موعدًا لوصول الهدف.</p>";
}
function render(){
 rows.sort((a,b)=>Number(b.active)-Number(a.active)||b.score-a.score||b.volume-a.volume);
 $("results").hidden=!rows.length;
 const buys=rows.filter(r=>r.active&&r.side===1).length;
 const sells=rows.filter(r=>r.active&&r.side===-1).length;
 $("metrics").innerHTML=[["تم تحليلها",rows.length],["شراء",buys],["بيع",sells]].
 map(x=>"<div class='metric'>"+x[0]+"<b>"+x[1]+"</b></div>").join("");
 $("selected").innerHTML=rows.map(r=>"<option value='"+esc(r.symbol)+"'>"+
 esc(r.symbol)+"</option>").join("");
 renderTable();detail();
}
$("filter").onchange=renderTable;
$("selected").onchange=detail;
$("stop").onclick=()=>{
 stopped=true;$("status").textContent="جارٍ الإيقاف بعد الطلب الحالي...";
};
$("scan").onclick=async()=>{
 const minVolume=Number($("volume").value);
 if(!Number.isFinite(minVolume)||minVolume<0){
  $("status").textContent="أدخل حد حجم صحيحًا.";return;
 }
 const threshold=Number($("threshold").value),limit=$("count").value;
 stopped=false;rows=[];errors=[];
 $("errors").textContent="";$("results").hidden=true;$("progress").value=0;
 busy(true);
 let total=0,message="",started=new Date();
 try{
  $("status").textContent="تحميل قائمة العقود...";
  const exchange=await get("/fapi/v1/exchangeInfo");
  const allowed=new Set(exchange.symbols.filter(x=>
   x.quoteAsset==="USDT"&&x.contractType==="PERPETUAL"&&x.status==="TRADING"
  ).map(x=>x.symbol));
  const tickers=await get("/fapi/v1/ticker/24hr"),now=Date.now();
  let selected=tickers.filter(t=>allowed.has(t.symbol)&&
   Number(t.quoteVolume)>=minVolume*1e6&&
   now-Number(t.closeTime)>=-60000&&now-Number(t.closeTime)<300000
  ).sort((a,b)=>Number(b.quoteVolume)-Number(a.quoteVolume));
  if(limit!=="all")selected=selected.slice(0,Number(limit));
  total=selected.length;
  const funding={};
  try{
   for(const x of await get("/fapi/v1/premiumIndex"))funding[x.symbol]=x;
  }catch(e){
   if(e.fatal)throw e;
   log("التمويل","غير متوفر؛ تظهر قيمة مفقودة");
  }
  for(let i=0;i<selected.length;i++){
   if(stopped)break;
   const t=selected[i];
   $("status").textContent="تحليل "+t.symbol+" — "+(i+1)+" / "+total;
   try{
    const r=await analyze(t,funding[t.symbol],threshold);
    if(!stopped)rows.push(r);
   }catch(e){
    if(e.fatal)throw e;
    log(t.symbol,e.message);
   }
   $("progress").value=(i+1)/Math.max(total,1);
   await sleep(350);
  }
  message=stopped?"تم الإيقاف؛ النتائج جزئية.":"انتهى الفحص.";
 }catch(e){
  message="توقف الفحص: "+e.message;
  log("الفحص",e.message);
  if(e.fatal&&!stopped)ready=false;
 }finally{
  render();
  $("stamp").textContent="بداية: "+started.toLocaleString()+
   " | نهاية: "+new Date().toLocaleString()+
   " | نتائج "+rows.length+" من "+total+
   ". التمويل لقطة بداية الفحص.";
  $("status").textContent=message+"\nتم تحليل "+rows.length+" من "+total+
   (rows.length?"":"\nراجع تفاصيل الأخطاء.");
  busy(false);
 }
};
$("download").onclick=()=>{
 const fields=[
  ["symbol","العملة"],["decision","القرار"],["score","درجة الاتجاه"],
  ["quality","جودة الدخول"],["rr","R/R"],["price","السعر"],
  ["entry","الدخول"],["stop","الوقف"],["t1","هدف1"],["targetType","نوع هدف1"],
  ["t2","هدف2 مشروط"],["t3","هدف3 مشروط"],["support","دعم"],
  ["resistance","مقاومة"],["risk","مسافة الوقف%"],["reason","السبب"],
  ["priceTime","وقت السعر بالمللي ثانية"]
 ];
 const cell=x=>'"'+String(x??"").replace(/"/g,'""')+'"';
 const csv="\uFEFF"+fields.map(x=>cell(x[1])).join(",")+"\n"+
 rows.map(r=>fields.map(([key])=>cell(
  typeof r[key]==="number"&&!Number.isFinite(r[key])?"":r[key]
 )).join(",")).join("\n");
 const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
 const a=document.createElement("a");
 a.href=url;a.download="binance_futures_v2.csv";
 document.body.appendChild(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),10000);
};
</script>
</body>
</html>
"""

components.html(PAGE, height=1900, scrolling=True)
