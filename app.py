# -*- coding: utf-8 -*-
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Binance Futures Browser Scanner",
    page_icon="📊",
    layout="wide",
)

st.title("📊 محلل بايننس فيوتشر")
st.caption("نسخة المتصفح — يومي + 4 ساعات — شراء وبيع")

PAGE = r"""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;padding:10px;font-family:Arial,sans-serif;
background:#f5f7fb;color:#17243b;font-size:16px}
.card{background:white;border:1px solid #dce3ed;border-radius:16px;
padding:18px;margin-bottom:14px}
h2{font-size:21px;margin:0 0 16px}
p{line-height:1.8}
label{display:block;margin:14px 0 7px}
input,select,button{font:inherit;border-radius:10px;padding:12px;
border:1px solid #cbd5e1;max-width:100%}
input,select{width:100%;background:white;color:#17243b}
button{cursor:pointer;background:#075de8;color:white;border:0;
margin:10px 0;min-height:46px}
button:disabled{opacity:.5;cursor:wait}
.secondary{background:#344963}
.info{background:#eaf2ff;padding:14px;border-radius:12px;line-height:1.8}
.small{font-size:14px;color:#536176;line-height:1.8}
#status{white-space:pre-wrap;line-height:1.8}
.wrap{overflow:auto;max-height:600px;border:1px solid #e2e8f0}
table{border-collapse:collapse;min-width:900px;width:100%;font-size:14px}
th,td{padding:12px;border-bottom:1px solid #e2e8f0;text-align:right;
white-space:nowrap}
th{background:#edf2f8;position:sticky;top:0}
a{color:#075de8;font-weight:bold}
.good{color:#087d54;font-weight:bold}
.bad{color:#c33242;font-weight:bold}
.metrics{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}
.metric{background:#eef3fa;padding:14px;border-radius:12px;flex:1}
.metric b{display:block;font-size:24px;margin-top:8px}
progress{width:100%;height:18px}
details{margin:12px 0}
summary{cursor:pointer;padding:12px;background:#eef3fa;border-radius:9px}
#chart{overflow:auto}
</style>
</head>
<body>

<div class="card">
<h2>فحص عقود USDT الدائمة</h2>
<div class="info">
الاتصال من متصفحك مباشرة ببايننس، دون مفتاح API.
الدرجة تقييم اتجاه وليست نسبة نجاح.
البرنامج لا ينفذ صفقات.
</div>

<button id="test">1 — اختبار الاتصال</button>
<div id="connection" class="small">اختبر الاتصال قبل الفحص.</div>

<label>عدد العملات حسب حجم تداول 24 ساعة</label>
<select id="count">
<option>20</option>
<option selected>50</option>
<option>100</option>
<option>200</option>
<option value="all">الكل</option>
</select>

<label>أقل حجم تداول — مليون USDT</label>
<input id="volume" type="number" min="0" value="10" step="5">

<label>أقل درجة لإشارة الدخول</label>
<select id="threshold">
<option>50</option><option>55</option><option>60</option>
<option selected>65</option><option>70</option>
<option>75</option><option>80</option><option>85</option>
</select>

<button id="scan" disabled>2 — تحليل السوق الآن</button>
<button id="stop" class="secondary" disabled>إيقاف الفحص</button>
<progress id="progress" value="0" max="1"></progress>
<div id="status">بانتظار اختبار الاتصال.</div>
<p class="small">
ابقَ على الصفحة أثناء الفحص. النتائج لقطة وقت الفحص؛
تغيير الإعدادات يتطلب فحصًا جديدًا.
</p>
</div>

<div id="results" hidden>
<div class="card">
<h2>نتائج الفحص</h2>
<div id="stamp" class="small"></div>
<div id="metrics" class="metrics"></div>
<label>عرض النتائج</label>
<select id="filter">
<option value="all">جميع العملات</option>
<option value="active">إشارات الدخول فقط</option>
<option value="long">شراء Long</option>
<option value="short">بيع Short</option>
<option value="watch">مراقبة</option>
</select>
<p class="small">اسحب الجدول أفقيًا. اضغط اسم العملة لفتح TradingView.</p>
<div class="wrap" id="table"></div>
<button id="download" class="secondary">تنزيل النتائج CSV</button>
</div>

<div class="card">
<h2>تحليل عملة بالتفصيل</h2>
<select id="selected"></select>
<div id="detail"></div>
</div>
</div>

<div class="card">
<details>
<summary>أخطاء الاتصال والعملات المستبعدة</summary>
<pre id="errors" style="white-space:pre-wrap;line-height:1.8"></pre>
</details>
<p class="small">
المستويات مرجعية وليست أوامر منفذة. الأهداف حسابية بحسب مسافة الوقف،
ولا تتضمن الرسوم أو التمويل أو الانزلاق أو أثر الرافعة.
</p>
</div>

<script>
"use strict";
const $ = id => document.getElementById(id);
const BASE = "https://fapi.binance.com";
let rows = [], errorRows = [], stopped = false, busy = false;
let ready = false, cooldownUntil = 0;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const mean = a => a.reduce((s,x)=>s+x,0)/a.length;
const last = a => a[a.length-1];
const fmt = x => Number.isFinite(x) ?
  Number(x).toLocaleString("en-US",{maximumSignificantDigits:9}) : "—";
const esc = x => String(x).replace(/[&<>"']/g,c=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[c]));
const tv = s => "https://www.tradingview.com/chart/?symbol="+
  encodeURIComponent("BINANCE:"+s+".P");

function logError(symbol, message){
  errorRows.push(symbol+": "+message);
  $("errors").textContent=errorRows.join("\n");
}
function fatal(message){
  const e=new Error(message);
  e.fatal=true;
  return e;
}
async function get(path, params={}){
  if(Date.now()<cooldownUntil){
    throw fatal("انتظر انتهاء مهلة بايننس قبل إعادة الطلب.");
  }
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),20000);
  try{
    const response=await fetch(
      BASE+path+"?"+new URLSearchParams(params),
      {signal:controller.signal,credentials:"omit"}
    );
    if([403,451].includes(response.status)){
      throw fatal("رفض بايننس الاتصال: HTTP "+response.status+
        ". توقف الفحص؛ لا يوجد تحويل إلى خادم بديل.");
    }
    if([418,429].includes(response.status)){
      const header=response.headers.get("Retry-After");
      const seconds=Number(header);
      const wait=header && Number.isFinite(seconds)
        ? Math.max(60000,seconds*1000) : 300000;
      cooldownUntil=Date.now()+wait;
      throw fatal("حد طلبات بايننس: HTTP "+response.status+
        ". توقف الفحص. أعد المحاولة بعد "+
        Math.ceil(wait/60000)+" دقائق.");
    }
    if(!response.ok) throw new Error("HTTP "+response.status);
    const data=await response.json();
    if(data && !Array.isArray(data) && Number(data.code)<0){
      throw new Error(data.msg || "خطأ من بايننس");
    }
    return data;
  }catch(e){
    if(e.name==="AbortError"){
      throw fatal("انتهت مهلة الاتصال. تحقق من الشبكة.");
    }
    if(e instanceof TypeError){
      throw fatal("المتصفح لم يتمكن من قراءة رد بايننس. "+
        "قد يكون السبب الشبكة أو سياسة CORS. "+
        "فتح الرابط مباشرة لا يثبت السماح بالقراءة من هذه الصفحة.");
    }
    throw e;
  }finally{
    clearTimeout(timer);
  }
}
function setBusy(value){
  busy=value;
  $("test").disabled=value;
  $("scan").disabled=value || !ready;
  $("stop").disabled=!value;
  for(const id of ["count","volume","threshold"]){
    $(id).disabled=value;
  }
}
$("test").onclick=async()=>{
  setBusy(true);
  ready=false;
  $("connection").textContent="جاري اختبار قراءة البيانات من داخل الصفحة...";
  try{
    const p=await get("/fapi/v2/ticker/price",{symbol:"BTCUSDT"});
    if(!(Number(p.price)>0)) throw new Error("رد السعر غير صالح");
    await get("/fapi/v1/exchangeInfo");
    const k=await get("/fapi/v1/klines",{
      symbol:"BTCUSDT",interval:"4h",limit:5
    });
    if(!Array.isArray(k)||!k.length) throw new Error("رد الشموع غير صالح");
    ready=true;
    $("connection").textContent="نجح اختبار السعر وقائمة العقود والشموع. "+
      "سعر BTC عند الاختبار: "+fmt(Number(p.price));
    $("status").textContent="الاتصال جاهز. ابدأ بـ20 عملة للتجربة.";
  }catch(e){
    $("connection").textContent=e.message;
    logError("اختبار الاتصال",e.message);
  }finally{
    setBusy(false);
  }
};

function ema(a,n){
  const alpha=2/(n+1), out=[a[0]];
  for(let i=1;i<a.length;i++){
    out.push(alpha*a[i]+(1-alpha)*out[i-1]);
  }
  return out;
}
function wilder(a,n){
  const out=Array(a.length).fill(NaN);
  if(a.length<n) return out;
  out[n-1]=mean(a.slice(0,n));
  for(let i=n;i<a.length;i++){
    out[i]=(out[i-1]*(n-1)+a[i])/n;
  }
  return out;
}
function indicators(d){
  const close=d.map(x=>x.c);
  const e20=ema(close,20), e50=ema(close,50), e200=ema(close,200);
  const e12=ema(close,12), e26=ema(close,26);
  const macd=e12.map((v,i)=>v-e26[i]), signal=ema(macd,9);
  const gains=[0], losses=[0];
  for(let i=1;i<d.length;i++){
    const change=close[i]-close[i-1];
    gains.push(Math.max(change,0));
    losses.push(Math.max(-change,0));
  }
  const ag=wilder(gains,14), al=wilder(losses,14);
  const tr=d.map((x,i)=>i ? Math.max(
    x.h-x.l,Math.abs(x.h-close[i-1]),Math.abs(x.l-close[i-1])
  ) : x.h-x.l);
  const atr=wilder(tr,14);
  return d.map((x,i)=>({
    ...x,e20:e20[i],e50:e50[i],e200:e200[i],atr:atr[i],
    hist:macd[i]-signal[i],
    rsi:al[i]===0 ? (ag[i]===0?50:100) : 100-100/(1+ag[i]/al[i]),
    momentum:i>=18 ? (x.c/close[i-18]-1)*100 : NaN,
    vr:i>=20 ? x.v/mean(d.slice(i-20,i).map(z=>z.v)) : NaN
  }));
}
async function candles(symbol,interval){
  const raw=await get("/fapi/v1/klines",{symbol,interval,limit:499});
  if(!Array.isArray(raw)) throw new Error("رد شموع غير صالح");
  const now=Date.now(), duration=interval==="4h"?14400000:86400000;
  const d=raw.filter(x=>Number(x[6])<now).map(x=>({
    t:Number(x[0]),o:Number(x[1]),h:Number(x[2]),l:Number(x[3]),
    c:Number(x[4]),v:Number(x[5]),end:Number(x[6])
  }));
  if(d.length<210) throw new Error("تاريخ أقل من 210 شموع مغلقة");
  if(now-last(d).end>duration*1.25) throw new Error("الشموع قديمة");
  for(let i=0;i<d.length;i++){
    const x=d[i];
    if(![x.o,x.h,x.l,x.c,x.v].every(Number.isFinite) ||
      x.l<=0 || x.h<x.l || x.v<0) throw new Error("قيم شموع غير صالحة");
    if(i && x.t-d[i-1].t!==duration) throw new Error("فجوات في الشموع");
  }
  return indicators(d);
}
function score(h,d,side){
  const checks=[
    [side*(h.c-h.e20)>0,20,"السعر والمتوسط القصير متوافقان"],
    [side*(h.e20-h.e50)>0,20,"اتجاه 4 ساعات داعم"],
    [side*(d.c-d.e50)>0,20,"الاتجاه اليومي داعم"],
    [side*h.hist>0,15,"MACD داعم"],
    [side*h.momentum>0,15,"زخم آخر 3 أيام داعم"],
    [side===1 ? h.rsi>=48&&h.rsi<=70 : h.rsi>=30&&h.rsi<=52,
      10,"RSI مناسب"]
  ];
  return {
    value:checks.reduce((s,c)=>s+(c[0]?c[1]:0),0),
    reasons:checks.filter(c=>c[0]).map(c=>c[2])
  };
}
function comparison(d,side){
  const feature=x=>[
    (x.rsi-50)/20,
    Math.max(-6,Math.min(6,(x.c-x.e20)/x.atr)),
    Math.max(-6,Math.min(6,(x.e20-x.e50)/x.atr)),
    Math.max(-10,Math.min(10,x.momentum/100*x.c/x.atr))
  ];
  const current=feature(last(d)), candidates=[];
  for(let i=200;i<d.length-42;i++){
    const f=feature(d[i]);
    if(!f.every(Number.isFinite)) continue;
    candidates.push({i,dist:f.reduce((s,v,j)=>s+(v-current[j])**2,0)});
  }
  candidates.sort((a,b)=>a.dist-b.dist);
  const chosen=[];
  for(const x of candidates){
    if(chosen.every(j=>Math.abs(j-x.i)>=42)) chosen.push(x.i);
    if(chosen.length>=20) break;
  }
  return [3,5,7].map(days=>{
    const returns=chosen.map(i=>side*(d[i+days*6].c/d[i].c-1)*100);
    const sorted=[...returns].sort((a,b)=>a-b), n=sorted.length;
    const median=n ? (sorted[Math.floor((n-1)/2)]+sorted[Math.floor(n/2)])/2 : NaN;
    return {days,n,rate:n>=8?returns.filter(v=>v>0).length/n*100:NaN,
      median:n>=8?median:NaN};
  });
}
async function analyze(t,funding,threshold){
  const symbol=t.symbol;
  const h=await candles(symbol,"4h");
  if(stopped) throw fatal("تم إيقاف الفحص بطلبك.");
  await sleep(100);
  const daily=await candles(symbol,"1d");
  const a=last(h), day=last(daily);
  const buy=score(a,day,1), sell=score(a,day,-1);
  const side=buy.value>=sell.value?1:-1;
  const best=side===1?buy:sell;
  const price=Number(t.lastPrice), atr=a.atr;
  if(!(price>0)||!(atr>0)) throw new Error("سعر أو ATR غير صالح");
  const support=Math.min(...h.slice(-30).map(x=>x.l));
  const resistance=Math.max(...h.slice(-30).map(x=>x.h));
  const stop=side===1 ?
    Math.min(support-.3*atr,price-1.8*atr) :
    Math.max(resistance+.3*atr,price+1.8*atr);
  const risk=Math.abs(price-stop);
  const targets=[1.5,2,3].map(r=>price+side*r*risk);
  const blocks=[];
  if(best.value<threshold) blocks.push("درجة أقل من الحد المختار");
  if(Math.abs(price-a.e20)>3*atr) blocks.push("السعر ممتد عن المتوسط");
  if(Math.abs(price-a.c)>1.5*atr) blocks.push("حركة كبيرة بعد آخر إغلاق");
  if(risk/price>.15) blocks.push("مسافة الوقف تتجاوز 15%");
  if(stop<=0||Math.min(...targets)<=0) blocks.push("مستويات غير مناسبة");
  const active=blocks.length===0;
  return {
    symbol,side,score:best.value,buy:buy.value,sell:sell.value,
    decision:active?(side===1?"شراء Long":"بيع Short"):"مراقبة",
    active,price,entry:active?price:NaN,stop:active?stop:NaN,
    t1:active?targets[0]:NaN,t2:active?targets[1]:NaN,
    t3:active?targets[2]:NaN,risk:risk/price*100,
    funding:funding?Number(funding.lastFundingRate)*100:NaN,
    support,resistance,rsi:a.rsi,vr:a.vr,
    volume:Number(t.quoteVolume),change:Number(t.priceChangePercent),
    reason:(active?best.reasons:blocks).join(" • "),
    candleTime:a.t,priceTime:Number(t.closeTime),
    history:comparison(h,side),candles:h
  };
}
function renderTable(){
  const f=$("filter").value;
  const visible=rows.filter(r=>
    f==="all" || (f==="active"&&r.active) ||
    (f==="watch"&&!r.active) ||
    (f==="long"&&r.active&&r.side===1) ||
    (f==="short"&&r.active&&r.side===-1)
  );
  if(!visible.length){
    $("table").textContent="لا توجد نتائج لهذا الاختيار.";
    return;
  }
  $("table").innerHTML="<table><thead><tr>"+
    ["العملة","القرار","الدرجة","السعر عند الفحص","الدخول المرجعي",
     "الوقف","هدف 1","هدف 2","هدف 3","مسافة الوقف %","التمويل الحالي %",
     "السبب"].map(x=>"<th>"+x+"</th>").join("")+
    "</tr></thead><tbody>"+visible.map(r=>"<tr>"+
      '<td><a target="_blank" rel="noopener noreferrer" href="'+tv(r.symbol)+'">'+
      esc(r.symbol)+" ↗</a></td>"+
      '<td class="'+(r.active?(r.side===1?"good":"bad"):"")+'">'+r.decision+"</td>"+
      [r.score,r.price,r.entry,r.stop,r.t1,r.t2,r.t3,r.risk,r.funding].
      map(x=>"<td>"+fmt(x)+"</td>").join("")+
      "<td>"+esc(r.reason)+"</td></tr>"
    ).join("")+"</tbody></table>";
}
function chart(r){
  const d=r.candles.slice(-100), width=800,height=260;
  const lo=Math.min(...d.map(x=>x.c));
  const hi=Math.max(...d.map(x=>x.c));
  const points=d.map((x,i)=>
    (20+i/(d.length-1)*760)+","+
    (230-(x.c-lo)/Math.max(hi-lo,1e-12)*200)).join(" ");
  return '<div id="chart"><svg role="img" aria-label="إغلاقات 4 ساعات" '+
    'viewBox="0 0 '+width+" "+height+'" style="width:100%;min-width:280px">'+
    '<rect width="800" height="260" fill="#f0f5fc"/>'+
    '<polyline points="'+points+'" fill="none" stroke="#075de8" stroke-width="2"/>'+
    '</svg></div><p class="small">إغلاقات آخر 100 شمعة على 4 ساعات.</p>';
}
function detail(){
  const r=rows.find(x=>x.symbol===$("selected").value);
  if(!r) return;
  const history="<div class='wrap'><table><tr>"+
    "<th>الأفق</th><th>العينات</th><th>حالات لصالح الاتجاه %</th>"+
    "<th>وسيط الحركة %</th></tr>"+r.history.map(x=>"<tr><td>"+x.days+
    " أيام</td><td>"+x.n+"</td><td>"+fmt(x.rate)+"</td><td>"+
    fmt(x.median)+"</td></tr>").join("")+"</table></div>";
  $("detail").innerHTML="<h2 style='margin-top:20px'>"+esc(r.symbol)+
    " — "+r.decision+"</h2><p>"+esc(r.reason)+"</p>"+
    "<p>درجة الشراء: <b>"+r.buy+"</b> | درجة البيع: <b>"+r.sell+"</b></p>"+
    "<p>RSI: "+fmt(r.rsi)+" | الحجم النسبي: "+fmt(r.vr)+"</p>"+
    "<p>الدعم: "+fmt(r.support)+" | المقاومة: "+fmt(r.resistance)+"</p>"+
    "<p class='small'>بداية آخر شمعة مغلقة: "+
    new Date(r.candleTime).toISOString()+"<br>وقت بيانات السعر: "+
    new Date(r.priceTime).toISOString()+"</p>"+
    chart(r)+
    "<h3>مقارنة بحالات تاريخية مشابهة</h3>"+history+
    "<p class='small'>هذه مقارنة وصفية وليست اختبار نجاح للوقف والأهداف. "+
    "عند أقل من 8 عينات لا نعرض النسب. لا تشمل الرسوم أو التمويل "+
    "أو الانزلاق، والأفق الزمني ليس موعدًا لوصول الهدف.</p>";
}
function finishRender(){
  rows.sort((a,b)=>b.score-a.score||b.volume-a.volume);
  $("results").hidden=!rows.length;
  const buys=rows.filter(r=>r.active&&r.side===1).length;
  const sells=rows.filter(r=>r.active&&r.side===-1).length;
  $("metrics").innerHTML=[
    ["تم تحليلها",rows.length],["شراء",buys],["بيع",sells]
  ].map(x=>'<div class="metric">'+x[0]+"<b>"+x[1]+"</b></div>").join("");
  $("selected").innerHTML=rows.map(r=>
    '<option value="'+esc(r.symbol)+'">'+esc(r.symbol)+"</option>").join("");
  renderTable();
  detail();
}
$("filter").onchange=renderTable;
$("selected").onchange=detail;
$("stop").onclick=()=>{
  stopped=true;
  $("status").textContent="جارٍ الإيقاف بعد اكتمال الطلب الحالي...";
};
$("scan").onclick=async()=>{
  const minVolume=Number($("volume").value);
  if(!Number.isFinite(minVolume)||minVolume<0){
    $("status").textContent="أدخل حد حجم تداول صحيحًا.";
    return;
  }
  const threshold=Number($("threshold").value);
  const limit=$("count").value;
  stopped=false;
  rows=[];
  errorRows=[];
  $("errors").textContent="";
  $("results").hidden=true;
  $("progress").value=0;
  setBusy(true);
  let total=0, message="";
  const started=new Date();
  try{
    $("status").textContent="تحميل قائمة العقود والأسعار...";
    const exchange=await get("/fapi/v1/exchangeInfo");
    const allowed=new Set(exchange.symbols.filter(x=>
      x.quoteAsset==="USDT"&&x.contractType==="PERPETUAL"&&x.status==="TRADING"
    ).map(x=>x.symbol));
    const tickers=await get("/fapi/v1/ticker/24hr");
    const now=Date.now();
    let selected=tickers.filter(t=>
      allowed.has(t.symbol)&&Number(t.quoteVolume)>=minVolume*1e6&&
      now-Number(t.closeTime)>=-60000&&now-Number(t.closeTime)<300000
    ).sort((a,b)=>Number(b.quoteVolume)-Number(a.quoteVolume));
    if(limit!=="all") selected=selected.slice(0,Number(limit));
    total=selected.length;
    let funding={};
    try{
      const raw=await get("/fapi/v1/premiumIndex");
      for(const x of raw) funding[x.symbol]=x;
    }catch(e){
      if(e.fatal) throw e;
      logError("التمويل","غير متاح؛ يُعرض كقيمة مفقودة");
    }
    for(let i=0;i<selected.length;i++){
      if(stopped) break;
      const t=selected[i];
      $("status").textContent="تحليل "+t.symbol+" — "+(i+1)+" / "+total;
      try{
        if(Date.now()-Number(t.closeTime)>300000){
          throw new Error("لقطة السعر تجاوزت 5 دقائق؛ أعد فحص عدد أقل.");
        }
        const row=await analyze(t,funding[t.symbol],threshold);
        if(!stopped) rows.push(row);
      }catch(e){
        if(e.fatal) throw e;
        logError(t.symbol,e.message);
      }
      $("progress").value=(i+1)/Math.max(total,1);
      await sleep(200);
    }
    message=stopped?"الفحص متوقف؛ النتائج جزئية.":"انتهى الفحص.";
  }catch(e){
    message="توقف الفحص: "+e.message;
    logError("الفحص",e.message);
    if(e.fatal) ready=false;
  }finally{
    finishRender();
    $("stamp").textContent="بداية الفحص: "+started.toLocaleString()+
      " | النهاية: "+new Date().toLocaleString()+
      " | نتائج "+rows.length+" من "+total+" عملة مختارة.";
    $("status").textContent=message+"\nتم تحليل "+rows.length+" من "+total+
      (rows.length?"":"\nراجع الأخطاء أدناه.");
    setBusy(false);
  }
};
$("download").onclick=()=>{
  const fields=[
    ["symbol","العملة"],["decision","القرار"],["score","الدرجة"],
    ["price","السعر"],["entry","الدخول"],["stop","الوقف"],
    ["t1","هدف1"],["t2","هدف2"],["t3","هدف3"],
    ["risk","مسافة الوقف%"],["funding","التمويل%"],["reason","السبب"]
  ];
  const cell=x=>'"'+String(x??"").replace(/"/g,'""')+'"';
  const csv="\uFEFF"+fields.map(x=>cell(x[1])).join(",")+"\n"+
    rows.map(r=>fields.map(([key])=>cell(
      typeof r[key]==="number"&&!Number.isFinite(r[key])?"":r[key]
    )).join(",")).join("\n");
  const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  const a=document.createElement("a");
  a.href=url;a.download="binance_futures_scan.csv";
  document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),10000);
};
</script>
</body>
</html>
"""

components.html(PAGE, height=1800, scrolling=True)
