"use strict";
const ids=["months","days","viewer","status","heading","subtitle","crumbs","total","search","back","year","viewer-date","viewer-name","open-pdf","download-pdf","pdf-frame"];
const el=Object.fromEntries(ids.map(id=>[id,document.getElementById(id)]));
const months=["January","February","March","April","May","June","July","August","September","October","November","December"];
const fmt=new Intl.DateTimeFormat("en-US",{timeZone:"UTC",weekday:"long",month:"long",day:"numeric",year:"numeric"});
let records=[],selectedYear=2026,loadError="";
const clean=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const dateValid=s=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&!Number.isNaN(Date.parse(s+"T00:00:00Z"));
const dayTitle=d=>fmt.format(new Date(d+"T00:00:00Z"));
const monthTitle=k=>months[Number(k.slice(5))-1]+" "+k.slice(0,4);
function route(){
const parts=decodeURIComponent(location.hash.slice(1)||"/").split("/").filter(Boolean);
const key=parts[0]==="month"&&/^\d{4}-(0[1-9]|1[0-2])$/.test(parts[1]||"")?parts[1]:null;
const item=parts[0]==="report"?records.find(x=>x.id===parts[1]):null;
const query=el.search.value.trim().toLowerCase();
el.months.hidden=el.days.hidden=el.viewer.hidden=true;
el.back.hidden=!key&&!item;
el.back.onclick=()=>location.hash=item?"#/month/"+item.month:"#/";
let crumb='<a href="#/">All Months</a>';
if(item){
  crumb+=' <span>›</span> <a href="#/month/'+item.month+'">'+monthTitle(item.month)+'</a> <span>›</span> '+item.date;
  el.heading.textContent="Daily Monitoring Report";el.subtitle.textContent="View the original daily research report.";
  el["viewer-date"].textContent=dayTitle(item.date)+(item.demo?" · DEMO":"");
  el["viewer-name"].textContent=item.name;
  const url=new URL(item.path,new URL(".",location.href.split("#")[0]));
  el["open-pdf"].href=url.href;el["download-pdf"].href=url.href;
  el["pdf-frame"].src=url.href+"#toolbar=1";el.viewer.hidden=false;el.status.textContent="";
} else if(key){
  const all=records.filter(x=>x.month===key);
  const items=all.filter(x=>!query||(x.date+" "+x.name).toLowerCase().includes(query));
  crumb+=' <span>›</span> '+monthTitle(key);
  el.heading.textContent=monthTitle(key)+" Reports";
  el.subtitle.textContent=all.length?all.length+" available report"+(all.length===1?"":"s")+", sorted by date.":"No reports have been published for this month yet.";
  el.days.innerHTML=items.map(x=>'<button class="day" data-id="'+clean(x.id)+'"><span class="day-date"><strong>'+Number(x.date.slice(8))+'</strong><small>'+months[Number(x.date.slice(5,7))-1].slice(0,3).toUpperCase()+'</small></span><span class="day-info"><strong>'+clean(dayTitle(x.date))+(x.demo?' · Demo':'')+'</strong><span>'+clean(x.name)+'</span></span><span class="day-arrow">→</span></button>').join("");
  el.days.hidden=false;
  el.days.querySelectorAll("button").forEach(b=>b.onclick=()=>location.hash="#/report/"+encodeURIComponent(b.dataset.id));
  el.status.textContent=items.length?"":all.length?"No reports match your search.":"No reports available for this month yet.";
} else {
  el.heading.textContent="Social Monitoring Reports";
  el.subtitle.textContent="Select a month to browse date-wise reports and view original PDFs.";
  const output=[];
  for(let i=0;i<12;i++){
    const month=String(i+1).padStart(2,"0"),k=selectedYear+"-"+month,items=records.filter(x=>x.month===k);
    if(query&&!months[i].toLowerCase().includes(query)&&!k.includes(query)&&!items.some(x=>x.date.includes(query)))continue;
    output.push('<button class="card '+(!items.length?'empty':'')+'" data-month="'+k+'"><span class="month-top"><span class="month-number">'+String(i+1).padStart(2,"0")+' / '+selectedYear+'</span><span class="month-icon">▦</span></span><h2>'+months[i]+'</h2><p>'+(items.length?(items.length+" report"+(items.length===1?"":"s")+" available"):"No reports yet")+'</p><div class="card-foot"><span class="pill '+(!items.length?"empty-pill":"")+'">'+items.length+' PDF'+(items.length===1?"":"s")+'</span><span>View month →</span></div></button>');
  }
  // Always render the entire selected year even where no PDFs exist.
  el.months.innerHTML=output.join("");
  el.months.hidden=false;
  el.months.querySelectorAll("button").forEach(b=>b.onclick=()=>location.hash="#/month/"+b.dataset.month);
  el.status.textContent=loadError||(!output.length?"No months match your search.":"");
}
el.crumbs.innerHTML=crumb;el.total.textContent=records.length;
}
el.search.addEventListener("input",route);
el.year.addEventListener("change",()=>{selectedYear=Number(el.year.value);location.hash="#/";route()});
window.addEventListener("hashchange",route);
(async()=>{try{
 const response=await fetch("reports-index.json",{cache:"no-store"});
 if(!response.ok)throw new Error("HTTP "+response.status);
 const data=await response.json();
 records=(Array.isArray(data)?data:[]).filter(x=>dateValid(x.date)&&/^\d{4}-(0[1-9]|1[0-2])$/.test(x.month)&&typeof x.path==="string"&&/^reports\/\d{4}\/\d{2}\/[^/]+\.pdf$/i.test(x.path)).sort((a,b)=>b.date.localeCompare(a.date)||Number(a.demo)-Number(b.demo));
}catch(e){loadError="Report index could not be loaded. Please refresh the page.";console.error(e)}
const years=[...new Set([2026,...records.map(x=>Number(x.date.slice(0,4)))])].sort((a,b)=>b-a);
selectedYear=years[0];el.year.innerHTML=years.map(y=>'<option value="'+y+'">'+y+'</option>').join("");
route();
})();