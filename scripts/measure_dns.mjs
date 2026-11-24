import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { PROVIDERS, DOMAINS, DohClient, udpQuery, windowRng, shuffle } from './dns_client.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.dirname(here);
const args=process.argv.slice(2);const get=(flag,def)=>{const i=args.indexOf(flag);return i<0?def:args[i+1]};
const out=path.resolve(get('--out',path.join(root,'data','new-run')));fs.mkdirSync(out,{recursive:true});
const windows=Number(get('--windows','3')),reps=Number(get('--reps','10')),interval=Number(get('--interval-seconds','300')),seed=Number(get('--seed','20261115'));
const rawfile=path.join(out,'dns_raw.jsonl');if(fs.existsSync(rawfile))throw new Error('Output already contains dns_raw.jsonl; choose a fresh directory');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const start=Date.now();
const metadata={study:'Direct same-provider DNS transport benchmark',started_utc:new Date().toISOString(),client_timezone:'Europe/Warsaw',execution_timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,platform:os.platform(),release:os.release(),arch:os.arch(),cpu_model:os.cpus()[0]?.model,logical_cpus:os.cpus().length,total_memory_gib:os.totalmem()/2**30,node:process.version,openssl:process.versions.openssl,providers:PROVIDERS,domains:DOMAINS,windows,reps,interval_seconds:interval,seed,qtype:'A',transport:'IPv4',timeout_ms:3000,policy:'All attempts retained. No retries. Query response and validation retained. Local OS resolver bypassed. Resolver cache pre-primed but hit status unobservable. Fresh DoH uses new TLS socket without session resumption.',status:'running'};
fs.writeFileSync(path.join(out,'environment.json'),JSON.stringify(metadata,null,2));
let count=0,valid=0;
const save=row=>{fs.appendFileSync(rawfile,JSON.stringify(row)+'\n');count++;if(row.valid)valid++;};
for(let w=1;w<=windows;w++){
  const due=start+(w-1)*interval*1000;
  while(Date.now()<due)await sleep(Math.min(30000,due-Date.now()));
  const windowStart=new Date().toISOString();console.log(JSON.stringify({event:'window_start',window:w,time:windowStart}));
  const clients=Object.fromEntries(Object.keys(PROVIDERS).map(p=>[p,new DohClient(p)]));
  for(const p of Object.keys(PROVIDERS)){
    for(const domain of DOMAINS){
      for(const protocol of ['udp','doh_warm']){
        const result=protocol==='udp'?await udpQuery(p,domain):await clients[p].query(domain);
        save({phase:'prime',window:w,provider:p,domain,protocol,started_utc:new Date().toISOString(),...result});await sleep(20);
      }
    }
  }
  const rng=windowRng(seed,w,'direct-lookup');let block=0;
  for(let rep=1;rep<=reps;rep++){
    const tasks=shuffle(Object.keys(PROVIDERS).flatMap(provider=>DOMAINS.map(domain=>({provider,domain}))),rng);
    for(const {provider,domain} of tasks){
      block++;const block_id=`w${w}-b${block}`;
      let order=0;
      for(const protocol of shuffle(['udp','doh_fresh','doh_warm'],rng)){
        const stamp=new Date().toISOString();let result;
        if(protocol==='udp')result=await udpQuery(provider,domain);
        else if(protocol==='doh_warm')result=await clients[provider].query(domain);
        else{const c=new DohClient(provider);result=await c.query(domain);c.close();}
        if(protocol==='doh_warm'&&!result.connection_preexisting){result.valid=false;result.error='Warm session was unexpectedly re-established';}
        save({phase:'measure',window:w,rep,block_id,order:++order,provider,domain,protocol,started_utc:stamp,...result});await sleep(25);
      }
    }
  }
  for(const c of Object.values(clients))c.close();
  console.log(JSON.stringify({event:'window_complete',window:w,time:new Date().toISOString(),cumulative_rows:count,cumulative_valid:valid}));
  const pageScript=get('--page-script',null);
  if(pageScript){
    console.log(JSON.stringify({event:'page_window_start',window:w,time:new Date().toISOString()}));
    await new Promise((resolve,reject)=>{
      const child=spawn(process.execPath,[path.resolve(pageScript),'--window',`w${w}`,'--reps',String(reps),'--seed',String(seed),'--out',out],{stdio:['ignore','pipe','pipe'],env:process.env,windowsHide:true});
      child.stdout.on('data',b=>{process.stdout.write(b);fs.appendFileSync(path.join(out,'collection.log'),b)});
      child.stderr.on('data',b=>{process.stderr.write(b);fs.appendFileSync(path.join(out,'collection.log'),b)});
      child.once('error',reject);child.once('exit',code=>code===0?resolve():reject(new Error(`Page collector exited ${code}`)));
    });
    console.log(JSON.stringify({event:'page_window_complete',window:w,time:new Date().toISOString()}));
  }
}
metadata.finished_utc=new Date().toISOString();metadata.status='complete';metadata.total_rows=count;metadata.valid_rows=valid;
fs.writeFileSync(path.join(out,'environment.json'),JSON.stringify(metadata,null,2));
console.log(JSON.stringify({event:'complete',rows:count,valid}));
