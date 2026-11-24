// Controlled DNS-gated page fixture. This does not configure Chromium's resolver.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { performance } from 'node:perf_hooks';
import { fileURLToPath } from 'node:url';

const args = Object.fromEntries(process.argv.slice(2).map((x,i,a)=>x.startsWith('--') ? [x.slice(2), a[i+1]?.startsWith('--') ? true : a[i+1]] : []).filter(x=>x.length));
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const dns = await import('./dns_client.mjs');
const api = {
  providers:Object.keys(dns.PROVIDERS).map(name=>({name})),
  queryUdp:async(p,n)=>{const r=await dns.udpQuery(p.name,n);return {...r,status:r.valid?'ok':'error'};},
  openDoh:async(p)=>{const c=new dns.DohClient(p.name);await c.connect();return c;},
  queryDoh:async(c,n)=>{const before=c.connectionInfo;const r=await c.query(n);if(!r.connection_preexisting||r.alpn!=='h2'||r.tls_session_reused!==false||r.connect_ms!==before?.connect_ms){r.valid=false;r.error='Unexpected DoH connection state';}return {...r,status:r.valid?'ok':'error'};},
  closeDoh:c=>c.close(),
};

const names = ['example.com','example.net','example.org','iana.org','wikipedia.org','python.org','kernel.org','w3.org'];
const modes = ['udp','doh_fresh','doh_reused'];
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const output = path.resolve(args.out || path.join(root,'data','new-run'));
fs.mkdirSync(output, { recursive:true });
const windowId = args.window || 'w1';
if(fs.existsSync(path.join(output,'pages.jsonl')) && fs.readFileSync(path.join(output,'pages.jsonl'),'utf8').split('\n').filter(Boolean).some(line=>JSON.parse(line).window===windowId)) throw new Error('This output already contains the requested window; use a new directory or window identifier.');
const reps = Number(args.reps || 10);
const seed = Number(args.seed || 20261115);
const rng = dns.windowRng(seed, windowId, 'live-dns-browser');
const shuffle = values => dns.shuffle(values, rng);
const append = (file, row) => fs.appendFileSync(path.join(output, file), JSON.stringify(row)+'\n');
let evidenceCaptured = false;

const image = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="120" height="80" fill="#e3e9ef"/><text x="12" y="45">DNS fixture</text><!--'+'x'.repeat(32768)+'--></svg>';
function html(layout){return '<!doctype html><html><head><meta charset="utf-8"><title>Controlled DNS page fixture</title><link rel="icon" href="data:,"><style>body{font-family:serif;margin:32px}img{width:120px;height:80px;margin:8px}</style></head><body><h1>Controlled DNS page fixture</h1><p>Seven fixed image resources. Content is identical across DNS transports.</p>'+Array.from({length:7},(_,i)=>`<img alt="Fixture ${i+1}" src="https://${layout===1?names[0]:names[i+1]}/fixture-${i}.svg">`).join('')+'</body></html>';}

// A page-local memoizer models one lookup per origin. Returned addresses are
// validated and recorded but never contacted: fixed fixture bytes are fulfilled.
async function runPage(browser, provider, mode, layout, rep){
  const id=`${windowId}-${provider.name}-${layout}-${rep}-${mode}`;
  const context=await browser.newContext({serviceWorkers:'block'});
  const page=await context.newPage();
  let client=null;
  let connectionPromise=null;
  const lookups=new Map();
  const failures=[];
  const row={kind:'page',id,window:windowId,provider:provider.name,mode,origins:layout,rep,seed,utc:new Date().toISOString(),fixture:'dns-gated-local-content-v1',status:'pending'};
  try {
    if(mode==='doh_reused') {
      client=await api.openDoh(provider);
      const prime=await api.queryDoh(client,'cloudflare.com');
      append('page-dns.jsonl',{...prime,page_id:id,phase:'connection-prime'});
      if(prime.status!=='ok') throw new Error('Connection primer failed: '+prime.error);
    }
    await context.route('**/*',async route=>{
      const url=new URL(route.request().url());
      const hostname=url.hostname;
      if(!names.includes(hostname)){failures.push('unexpected origin '+hostname);await route.abort();return;}
      if(!lookups.has(hostname)) lookups.set(hostname,(async()=>{
        const started=performance.now();
        let result;
        try {
          if(mode==='udp') result=await api.queryUdp(provider,hostname);
          else {
            if(!client) {
              if(!connectionPromise) connectionPromise=api.openDoh(provider);
              client=await connectionPromise;
            }
            result=await api.queryDoh(client,hostname);
          }
          const record={...result,page_id:id,phase:'navigation',hostname,gate_ms:performance.now()-started};
          append('page-dns.jsonl',record);
          if(result.status!=='ok') throw new Error(result.error||'invalid DNS response');
        } catch(e) {
          failures.push(String(e.message));
          append('page-dns.jsonl',{page_id:id,phase:'gate-error',hostname,error:String(e.message),gate_ms:performance.now()-started});
          throw e;
        }
      })());
      try {await lookups.get(hostname);}
      catch {await route.abort('namenotresolved');return;}
      if(url.pathname==='/') await route.fulfill({status:200,contentType:'text/html',headers:{'cache-control':'no-store'},body:html(layout)});
      else await route.fulfill({status:200,contentType:'image/svg+xml',headers:{'cache-control':'no-store'},body:image});
    });
    const started=performance.now();
    await page.goto('https://example.com/',{waitUntil:'load',timeout:30000});
    await page.waitForFunction(()=>performance.getEntriesByType('navigation')[0]?.loadEventEnd>0);
    row.wall_ms=performance.now()-started;
    row.navigation=await page.evaluate(()=>performance.getEntriesByType('navigation')[0].toJSON());
    row.loaded_images=await page.evaluate(()=>[...document.images].filter(x=>x.complete&&x.naturalWidth>0).length);
    row.lookup_count=lookups.size;
    row.plt_ms=row.navigation.loadEventEnd-row.navigation.startTime;
    row.status=failures.length===0 && row.loaded_images===7 && lookups.size===layout ? 'ok':'invalid';
    row.errors=failures;
    if(args.screenshots && !evidenceCaptured && layout===8 && row.status==='ok') {
      const folder=path.resolve(args.screenshots);fs.mkdirSync(folder,{recursive:true});
      const screenshot=path.join(folder,'fixture-eight-hostnames.png');
      await page.screenshot({path:screenshot,fullPage:true});
      fs.writeFileSync(path.join(folder,'fixture-eight-hostnames.json'),JSON.stringify({captured_utc:new Date().toISOString(),page_id:id,provider:provider.name,mode,origins:layout,loaded_images:row.loaded_images,source:'Actual Playwright browser screenshot after a successful evidence-only fixture navigation',screenshot:'fixture-eight-hostnames.png'},null,2)+'\n');
      evidenceCaptured = true;
    }
  } catch(e) {row.status='error';row.error=String(e.message);row.errors=failures;}
  finally {
    if(client) api.closeDoh(client);
    await context.close();
    append('pages.jsonl',row);
  }
  return row;
}

const browser=await chromium.launch({channel:'chrome',headless:true,args:['--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run']});
append('page-environment.jsonl',{utc:new Date().toISOString(),window:windowId,node:process.version,platform:process.platform,arch:process.arch,browser:browser.version(),playwright:require((process.env.PLAYWRIGHT_MODULE||'playwright')+'/package.json').version,reps,seed,names,modes,timeout_ms:30000,fixture_image_bytes:Buffer.byteLength(image)});
try {
  // Equal prewarm attempt through each provider, outside page measurements.
  for(const p of api.providers) for(const name of names) append('page-dns.jsonl',{...await api.queryUdp(p,name),window:windowId,phase:'resolver-prewarm',hostname:name,provider:p.name});
  const blocks=shuffle(api.providers.flatMap(p=>[1,8].flatMap(layout=>Array.from({length:reps},(_,rep)=>({p,layout,rep})))));
  for(const {p,layout,rep} of blocks) for(const mode of shuffle([...modes])) {
    const r=await runPage(browser,p,mode,layout,rep);
    console.log(JSON.stringify({id:r.id,status:r.status,plt_ms:r.plt_ms,error:r.error}));
    await new Promise(resolve=>setTimeout(resolve,80));
  }
} finally {await browser.close();}

