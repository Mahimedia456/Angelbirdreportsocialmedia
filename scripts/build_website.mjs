import { existsSync, mkdirSync, readdirSync, copyFileSync, writeFileSync, rmSync } from 'node:fs';
import { join, relative, dirname } from 'node:path';

const root=process.cwd();
const out=join(root,'_site');
const brand='Angelbird';
const dailyRe=new RegExp('^'+brand+'-Social-Monitoring-(\\d{4}-\\d{2}-\\d{2})(-DEMO)?\\.pdf$','i');
const periodRe=new RegExp('^'+brand+'-Social-Monitoring-(Weekly|Monthly)-(\\d{4}-\\d{2}-\\d{2})_to_(\\d{4}-\\d{2}-\\d{2})\\.pdf$','i');

if(existsSync(out))rmSync(out,{recursive:true,force:true});
mkdirSync(out,{recursive:true});
for(const file of ['index.html','styles.css','app.js']){
  copyFileSync(join(root,'website',file),join(out,file));
}
writeFileSync(join(out,'.nojekyll'),'');
const items=[];
function walk(dir){
  if(!existsSync(dir))return;
  for(const entry of readdirSync(dir,{withFileTypes:true})){
    const file=join(dir,entry.name);
    if(entry.isDirectory()){walk(file);continue;}
    if(!entry.isFile()||!entry.name.toLowerCase().endsWith('.pdf'))continue;
    let item=null;
    const daily=entry.name.match(dailyRe);
    const period=entry.name.match(periodRe);
    if(daily){
      const date=daily[1],demo=Boolean(daily[2]);
      item={id:date+(demo?'-DEMO':''),date,month:date.slice(0,7),type:'daily',
            name:entry.name,demo};
    }else if(period){
      const type=period[1].toLowerCase(),start=period[2],end=period[3];
      item={id:type+'-'+start+'-'+end,date:end,month:end.slice(0,7),type,
            start,end,name:entry.name,demo:false};
    }else{continue;}
    const rel=relative(root,file).replaceAll('\\','/');
    if(!rel.startsWith('reports/'+item.month.replace('-','/')+'/'))continue;
    const target=join(out,rel);
    mkdirSync(dirname(target),{recursive:true});
    copyFileSync(file,target);
    item.path=rel;
    items.push(item);
  }
}
walk(join(root,'reports'));
for(const period of ['monthly','weekly']){
  const src=join(root,'reports',period+'-latest.json');
  if(!existsSync(src))continue;
  const dest=join(out,'reports',period+'-latest.json');
  mkdirSync(dirname(dest),{recursive:true});
  copyFileSync(src,dest);
}

const typeRank={monthly:0,weekly:1,daily:2};
items.sort((a,b)=>b.date.localeCompare(a.date)||(typeRank[a.type]-typeRank[b.type])||a.name.localeCompare(b.name));
writeFileSync(join(out,'reports-index.json'),JSON.stringify(items,null,2)+'\n');
const types=items.reduce((acc,item)=>(acc[item.type]=(acc[item.type]||0)+1,acc),{});
console.log(brand+' report site built, all frequency PDFs:',types);
