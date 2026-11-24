/** Randomized local browser delay-injection experiment. No DNS measurements. */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import {performance} from 'node:perf_hooks';
import {fileURLToPath} from 'node:url';

const args={};
for(let i=2;i<process.argv.length;i++) {
  const key=process.argv[i];
  if(!key.startsWith('--')) throw new Error('Expected --option');
  args[key.slice(2)]=process.argv[++i];
}
const reps=Number(args.reps??20), base=Number(args['base-ms']??25), added=Number(args['added-ms']??25);
const seed=Number(args.seed??20261122), timeout=Number(args['timeout-ms']??5000);
if(!Number.isInteger(reps)||reps<1||!Number.isFinite(base)||base<0||!Number.isFinite(added)||added<=0) throw new Error('Invalid design');
const out=path.resolve(args.out??'data/browser-layout-2026-11-22');
fs.mkdirSync(out,{recursive:true});
if(fs.existsSync(path.join(out,'pages.jsonl'))) throw new Error('Output already contains pages; choose a new directory');
const require=createRequire(import.meta.url);
const moduleName=process.env.PLAYWRIGHT_MODULE??'playwright';
const {chromium}=require(moduleName);
const playwrightVersion=require(moduleName+'/package.json').version;
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const collectorPath=fileURLToPath(import.meta.url);
const analyzerPath=path.join(path.dirname(collectorPath),'analyze_browser_layout.py');
const write=(name,obj)=>fs.writeFileSync(path.join(out,name),JSON.stringify(obj,null,2)+'\n');
const append=(name,obj)=>fs.appendFileSync(path.join(out,name),JSON.stringify(obj)+'\n');
let state=seed>>>0;
const rng=()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state/4294967296;};
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
const conditions=['parallel','sequential'].flatMap(layout=>[0,added].map(extra=>({layout,extra,requested_gate_ms:base+extra})));
const schedule=shuffle(Array.from({length:reps},(_,i)=>i+1)).flatMap(rep=>shuffle([...conditions]).map(c=>({rep,...c})));
const image='<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="120" height="80" fill="#e3e9ef"/><text x="12" y="45">Fixture image</text><!--'+'x'.repeat(32768)+'--></svg>';
const html=`<!doctype html><html><head><meta charset="utf-8"><title>Controlled browser layout fixture</title><link rel="icon" href="data:,"><style>body{font-family:serif;margin:32px}img{width:120px;height:80px;margin:8px}</style></head><body><h1>Controlled browser layout fixture</h1><p>Seven fixed images with experimental delivery gates.</p>${Array.from({length:7},(_,i)=>`<img id="slot${i+1}" alt="Fixture ${i+1}">`).join('')}<script>
window.__fixture={layout:new URL(location.href).searchParams.get('layout'),requests:[],done:false,error:null};
async function runFixture(){
  const f=window.__fixture;
  f.start_ms=performance.now();
  const loadOne=i=>new Promise((resolve,reject)=>{
    const image=document.getElementById('slot'+i);
    const request={index:i,requested_ms:performance.now(),completed_ms:null};
    f.requests.push(request);
    image.onload=()=>{request.completed_ms=performance.now();request.loaded=image.complete&&image.naturalWidth>0;resolve();};
    image.onerror=()=>reject(new Error('Image '+i+' failed'));
    image.src='http://h'+i+'.fixture.test/resource-'+i+'.svg';
  });
  if(f.layout==='sequential') for(let i=1;i<=7;i++) await loadOne(i);
  else if(f.layout==='parallel') await Promise.all(Array.from({length:7},(_,i)=>loadOne(i+1)));
  else throw new Error('Invalid layout');
  f.completed_ms=performance.now();
  f.elapsed_ms=f.completed_ms-f.start_ms;
  f.loaded_images=[...document.images].filter(x=>x.complete&&x.naturalWidth>0).length;
  f.done=true;
}
runFixture().catch(e=>{window.__fixture.error=String(e);window.__fixture.done=true;});
</script></body></html>`;
fs.writeFileSync(path.join(out,'fixture.html'),html);
fs.writeFileSync(path.join(out,'fixture.svg'),image);
fs.copyFileSync(collectorPath,path.join(out,'collector_snapshot.mjs'));
fs.copyFileSync(analyzerPath,path.join(out,'analyzer_snapshot.py'));
write('design.json',{
  recorded_utc:new Date().toISOString(),study:'Controlled browser delay injection',
  live_dns:false,native_browser_dns:false,public_content_transfer:false,
  seed,repetitions:reps,conditions,resource_count:7,distinct_resource_hostnames:7,
  primary_metric:'fixture.elapsed_ms from script start to seven verified image completions',
  secondary_metric:'fixture.completed_ms relative to navigation time origin',
  diagnostic_metric:'Navigation Timing loadEventEnd; may precede fixture completion',
  html_sha256:hash(html),image_sha256:hash(image),html_bytes:Buffer.byteLength(html),image_bytes:Buffer.byteLength(image),
  collector_sha256:hash(fs.readFileSync(collectorPath)),analyzer_sha256:hash(fs.readFileSync(analyzerPath)),
  delay_policy:'Each resource route waits requested_gate_ms with setTimeout before fulfilling identical SVG bytes. Actual gate intervals are logged. Main document has no artificial delay.',
  randomization:'Seeded shuffle of repetition blocks and four conditions within each block',
  inference:'Paired layout-specific treatment-minus-baseline differences; synthetic timing treatments on one controlled fixture, not true DNS observations',
  timeout_ms:timeout,
});
write('schedule.json',schedule);
const browser=await chromium.launch({channel:args.channel??'chrome',headless:true,args:[
  '--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run',
  '--host-resolver-rules=MAP * ~NOTFOUND',
]});
write('environment.json',{
  started_utc:new Date().toISOString(),node:process.version,platform:process.platform,release:os.release(),arch:process.arch,
  cpu:os.cpus()[0]?.model,logical_processors:os.cpus().length,browser:browser.version(),playwright:playwrightVersion,
  headless:true,host_resolver_rules:'MAP * ~NOTFOUND',all_context_requests_intercepted:true,
  network_policy:'Only fixture.test and h1..h7.fixture.test routes are fulfilled. Other context requests are aborted. No public DNS or content target is queried.',
});
let failed=0,completedAttempts=0;
try {
  for(let index=0;index<schedule.length;index++){
    const condition=schedule[index];
    const row={id:`b${condition.rep}-${condition.layout}-${condition.extra}`,order:index+1,...condition,started_utc:new Date().toISOString(),status:'pending',gates:[],unexpected_requests:[],errors:[]};
    const context=await browser.newContext({serviceWorkers:'block'});
    const page=await context.newPage();
    const t0=performance.now();
    let active=0,maxActive=0;
    await context.route('**/*',async route=>{
      const url=new URL(route.request().url());
      try{
        if(url.hostname==='fixture.test'&&url.pathname==='/'){
          await route.fulfill({status:200,contentType:'text/html',headers:{'cache-control':'no-store'},body:html});
          return;
        }
        const match=/^h([1-7])\.fixture\.test$/.exec(url.hostname);
        if(!match||url.pathname!==`/resource-${match[1]}.svg`){
          row.unexpected_requests.push(route.request().url());await route.abort('blockedbyclient');return;
        }
        const gate={hostname:url.hostname,index:Number(match[1]),requested_delay_ms:condition.requested_gate_ms,start_ms:performance.now()-t0};
        row.gates.push(gate);active++;maxActive=Math.max(maxActive,active);
        await new Promise(resolve=>setTimeout(resolve,condition.requested_gate_ms));
        gate.release_ms=performance.now()-t0;
        gate.actual_wait_ms=gate.release_ms-gate.start_ms;
        active--;
        await route.fulfill({status:200,contentType:'image/svg+xml',headers:{'cache-control':'no-store'},body:image});
        gate.fulfilled_ms=performance.now()-t0;
      }catch(e){row.errors.push(String(e.message));}
    });
    try{
      await page.goto(`http://fixture.test/?layout=${condition.layout}`,{waitUntil:'domcontentloaded',timeout});
      await page.waitForFunction(()=>window.__fixture?.done,{},{timeout});
      row.fixture=await page.evaluate(()=>window.__fixture);
      // Diagnostic only; sequential JS image work may finish after load.
      await page.waitForTimeout(10);
      row.navigation=await page.evaluate(()=>performance.getEntriesByType('navigation')[0]?.toJSON());
      row.wall_ms=performance.now()-t0;
      row.max_concurrent_gates=maxActive;
      row.html_sha256=hash(html);row.image_sha256=hash(image);
      const req=row.fixture.requests;
      row.sequence_verified=condition.layout!=='sequential'||req.every((r,i)=>i===0||r.requested_ms>=req[i-1].completed_ms);
      const expectedHostnames=new Set(row.gates.map(g=>g.hostname)).size===7;
      const noErrors=!row.fixture.error&&!row.errors.length&&!row.unexpected_requests.length;
      const concurrence=condition.layout==='sequential'?maxActive===1:maxActive>=2;
      row.status=noErrors&&row.fixture.loaded_images===7&&row.gates.length===7&&expectedHostnames&&row.sequence_verified&&concurrence?'ok':'invalid';
      if(condition.rep===1&&condition.extra===0) await page.screenshot({path:path.join(out,`fixture-${condition.layout}.png`),fullPage:true});
    }catch(e){row.status='error';row.errors.push(String(e.message));}
    finally{
      await context.close();
      if(row.status!=='ok') failed++;
      append('pages.jsonl',row);
      completedAttempts++;
    }
    console.log(JSON.stringify({order:row.order,rep:row.rep,layout:row.layout,extra_ms:row.extra,status:row.status,fixture_elapsed_ms:row.fixture?.elapsed_ms,max_concurrent_gates:row.max_concurrent_gates}));
    await new Promise(resolve=>setTimeout(resolve,40));
  }
}finally{
  await browser.close();
  write('completion.json',{finished_utc:new Date().toISOString(),attempted:completedAttempts,planned:schedule.length,failed,status:completedAttempts===schedule.length?'complete':'interrupted'});
}
if(failed) process.exitCode=2;
