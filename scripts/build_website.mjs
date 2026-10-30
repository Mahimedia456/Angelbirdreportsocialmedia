import { existsSync, mkdirSync, readdirSync, copyFileSync, writeFileSync, rmSync } from 'node:fs';
import { join, relative, dirname } from 'node:path';
const root=process.cwd(), out=join(root,'_site');
if(existsSync(out))rmSync(out,{recursive:true,force:true});
mkdirSync(out,{recursive:true});
for(const f of ['index.html','styles.css','app.js'])copyFileSync(join(root,'website',f),join(out,f));
const pdfRe=/^Atomos-Social-Monitoring-(\d{4}-\d{2}-\d{2})(-DEMO)?\.pdf$/i;
const items=[];
const walk=dir=>{
  if(!existsSync(dir))return;
  for(const ent of readdirSync(dir,{withFileTypes:true})){
    const path=join(dir,ent.name);
    if(ent.isDirectory())walk(path);
    else if(ent.isFile()&&ent.name.toLowerCase().endsWith('.pdf')){
      const m=ent.name.match(pdfRe);if(!m)continue;
      const date=m[1], demo=!!m[2], [year,month]=date.split('-');
      const rel=relative(root,path).replaceAll('\\','/');
      if(!rel.startsWith('reports/'+year+'/'+month+'/'))continue;
      const target=join(out,rel);mkdirSync(dirname(target),{recursive:true});copyFileSync(path,target);
      items.push({id:date+(demo?'-DEMO':''),date,month:year+'-'+month,name:ent.name,demo,path:rel});
    }
  }
};
walk(join(root,'reports'));
items.sort((a,b)=>b.date.localeCompare(a.date)||Number(a.demo)-Number(b.demo));
writeFileSync(join(out,'reports-index.json'),JSON.stringify(items,null,2));
console.log('Atomos archive build complete:',items.length,'PDF(s)');
