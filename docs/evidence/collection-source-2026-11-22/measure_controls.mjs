/** Prospective client-lifecycle controls. Built-ins only; no OS DNS changes. */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import dgram from 'node:dgram';
import { randomInt, createHash } from 'node:crypto';
import { performance } from 'node:perf_hooks';
import { fileURLToPath } from 'node:url';
import { PROVIDERS, DOMAINS, makeQuery, parseResponse, DohClient, seededRng, shuffle } from './dns_client.mjs';

const script=fileURLToPath(import.meta.url), root=path.dirname(path.dirname(script));
const argv=process.argv.slice(2), get=(flag,def)=>{const i=argv.indexOf(flag);return i<0?def:argv[i+1]};
const out=path.resolve(get('--out',path.join(root,'data/control-2026-11-20')));
const windows=Number(get('--windows','10')), reps=Number(get('--reps','10')), interval=Number(get('--interval-seconds','90')), seed=Number(get('--seed','20261120'));
const domains=get('--domains',DOMAINS.join(',')).split(',');
const modes=['udp_fresh','udp_bound','doh_warm'], timeoutMs=3000;
if(![windows,reps,interval].every(n=>Number.isInteger(n)&&n>0))throw new Error('Positive integer design parameters required');
const plannedQueries=windows*(reps+1)*domains.length*Object.keys(PROVIDERS).length*modes.length;
if(plannedQueries>65536)throw new Error('Design exceeds the 65,536 unique transaction-ID budget; use fewer windows/repetitions/domains');
fs.mkdirSync(out,{recursive:true});
const raw=path.join(out,'control_raw.jsonl');if(fs.existsSync(raw))throw new Error('Refusing to overwrite control_raw.jsonl');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const usedIDs=new Set();function query(name){let id;do{id=randomInt(65536)}while(usedIDs.has(id));usedIDs.add(id);return makeQuery(name,id)}
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const design={schema_version:1,study:'Prospective UDP socket lifecycle and established DoH controls',windows,reps,interval_seconds:interval,seed,domains,providers:PROVIDERS,modes,qtype:'A',ip_version:4,timeout_ms:timeoutMs,expected_measured_attempts:windows*reps*domains.length*Object.keys(PROVIDERS).length*modes.length,priming:'Each name queried through all three treatments before each window; resolver cache-hit status remains unknown',fresh_udp:'New unconnected udp4 socket, explicit await bind(0) inside whole-call timing, then send and validation. Historical collector used implicit bind, so this is an explicit implementation change.',bound_udp:'One unconnected udp4 socket per provider/window; bind occurs outside measured calls and the source port is retained.',doh:'One established HTTP/2 TLS connection per provider/window, primed before measured calls; no reconnect or TLS resumption permitted in a valid measured warm call.',timing:'Query construction excluded. elapsed_ms includes socket lifecycle where applicable, submission, response and validation. UDP transport_elapsed_ms is send() call to message callback after both modes have bound. H2 phase fields are event-loop/client timestamps, not packet-capture transmission times.',interpretation:'Fresh-versus-bound contrasts can also reflect source-port dependent routing, ECMP, NAT or resolver affinity. Neither phase decomposition nor matched provider establishes pure CPU or encryption cost.',failure_policy:'No retries or imputation. All attempts including setup/timeout failures are stored. Failed timings are excluded from successful latency estimates.',source_sha256:{'measure_controls.mjs':sha(script),'dns_client.mjs':sha(path.join(path.dirname(script),'dns_client.mjs'))}};
fs.writeFileSync(path.join(out,'design.json'),JSON.stringify({...design,declared_utc:new Date().toISOString()},null,2)+'\n');
const meta={...design,started_utc:new Date().toISOString(),status:'running',platform:os.platform(),release:os.release(),arch:os.arch(),cpu_model:os.cpus()[0]?.model,logical_cpus:os.cpus().length,total_memory_gib:os.totalmem()/2**30,node:process.version,openssl:process.versions.openssl,execution_timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,local_ip_addresses_recorded:false,window_events:[]};
const persist=()=>fs.writeFileSync(path.join(out,'environment.json'),JSON.stringify(meta,null,2)+'\n');
const event=e=>{const row={...e,utc:new Date().toISOString()};fs.appendFileSync(path.join(out,'events.jsonl'),JSON.stringify(row)+'\n');meta.window_events.push(row);persist();console.log(JSON.stringify(row))};
let all=0, measured=0, valid=0;
const save=row=>{fs.appendFileSync(raw,JSON.stringify(row)+'\n');all++;if(row.phase==='measure')measured++;if(row.valid)valid++;};
const wire=(b,q)=>{const p=parseResponse(b,q);return {...p,error:p.valid?null:`DNS rcode=${p.rcode} TC=${p.truncated}`,response_bytes:b.length,response_base64:b.toString('base64')};};

async function bindSocket(socket){
  await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{cleanup();reject(new Error('UDP bind timeout'))},timeoutMs);
    const fail=e=>{cleanup();reject(e)}, ready=()=>{cleanup();resolve()};
    const cleanup=()=>{clearTimeout(timer);socket.off('error',fail);socket.off('listening',ready)};
    socket.once('error',fail);socket.once('listening',ready);socket.bind(0,'0.0.0.0');
  });
}

class BoundUDP {
  constructor(provider){this.provider=provider;this.socket=dgram.createSocket('udp4');this.socket.on('error',()=>{});this.ready=false;this.count=0;this.bind_ms=null;}
  async open(){const t=performance.now();await bindSocket(this.socket);this.bind_ms=performance.now()-t;this.ready=true;this.local_port=this.socket.address().port;}
  close(){try{this.socket.close()}catch{};this.ready=false;}
}

async function udp(provider,name,bound=null){
  const q=query(name), t0=performance.now();let socket=bound?.socket,create_ms=0,bind_ms=0,bind_ready_ms=0,local_port=bound?.local_port??null;
  const common={query_base64:q.toString('base64'),bound_before_timing:!!bound,udp_connected:false,remote_address:provider.ip,remote_port:53,local_port};
  try {
    if(bound&&!bound.ready)throw new Error('Reusable UDP socket was not established');
    if(!bound){const tc=performance.now();socket=dgram.createSocket('udp4');socket.on('error',()=>{});create_ms=performance.now()-tc;const tb=performance.now();await bindSocket(socket);bind_ms=performance.now()-tb;bind_ready_ms=performance.now()-t0;local_port=socket.address().port;}
    const sendTime=performance.now();let callbackTime=null,ignored=0;
    const result=await new Promise(resolve=>{
      let done=false;
      const finish=r=>{if(done)return;done=true;clearTimeout(timer);socket.off('message',message);socket.off('error',error);resolve(r)};
      const error=e=>finish({valid:false,error:e.message});
      const message=(b,peer)=>{
        if(peer.address!==provider.ip||peer.port!==53||b.length<2||b.readUInt16BE(0)!==q.readUInt16BE(0)){ignored++;return;}
        const receive=performance.now();let decoded;
        try{decoded=wire(b,q)}catch(e){decoded={valid:false,error:e.message,response_base64:b.toString('base64'),response_bytes:b.length};}
        const end=performance.now();
        finish({...decoded,receive_ms:receive-t0,transport_elapsed_ms:receive-sendTime,post_bind_elapsed_ms:end-sendTime,post_send_callback_ms:callbackTime===null?null:receive-callbackTime,validation_ms:end-receive});
      };
      const timer=setTimeout(()=>finish({valid:false,error:'UDP response timeout',timeout:true}),timeoutMs);
      socket.on('message',message);socket.once('error',error);
      socket.send(q,53,provider.ip,e=>{callbackTime=performance.now();if(e)error(e)});
    });
    if(bound)bound.count++;
    let close_call_ms=0;
    if(!bound){const tc=performance.now();socket.close();close_call_ms=performance.now()-tc;socket=null;}
    return {...common,...result,local_port,socket_create_ms:create_ms,bind_wait_ms:bind_ms,bind_ready_ms,pre_send_ms:sendTime-t0,send_callback_ms:callbackTime===null?null:callbackTime-t0,close_call_ms,ignored_datagrams:ignored,connection_query_number:bound?bound.count:1,elapsed_ms:performance.now()-t0};
  }catch(e){return {...common,local_port,valid:false,error:e.message,socket_create_ms:create_ms,bind_wait_ms:bind_ms,bind_ready_ms,elapsed_ms:performance.now()-t0};}
  finally{if(!bound&&socket)try{socket.close()}catch{}}
}

class PhaseDoh {
  constructor(key){this.client=new DohClient(key,{timeoutMs});this.provider=PROVIDERS[key];this.count=0;this.ready=false;this.connection=null;}
  async open(){this.connection=await this.client.connect();this.ready=true;this.local_port=this.client.session.socket.localPort;this.connection_id=`${this.provider.ip}:${this.local_port}`;}
  close(){this.client.close();this.ready=false;}
  async query(name){
    const q=query(name),t0=performance.now();let request_created=null,write_finish=null,headers_at=null,first_data=null,response_end=null;
    const common={query_base64:q.toString('base64'),connection_preexisting:this.ready,connection_id:this.connection_id??null,local_port:this.local_port??null,remote_port:443,...(this.connection??{})};
    try{
      const session=this.client.session;
      if(!this.ready||!session||session.destroyed||session.closed)throw new Error('Established DoH session is unavailable; no reconnect attempted');
      const result=await new Promise(resolve=>{
        let done=false,headers={},chunks=[];
        const request=session.request({':method':'POST',':path':this.provider.path,':authority':this.provider.host,'content-type':'application/dns-message','accept':'application/dns-message','content-length':q.length});
        request_created=performance.now();
        const finish=r=>{if(done)return;done=true;clearTimeout(timer);resolve(r)};
        const timer=setTimeout(()=>{request.close();finish({valid:false,error:'DoH response timeout',timeout:true})},timeoutMs);
        request.on('finish',()=>{write_finish=performance.now()});
        request.on('response',h=>{headers_at=performance.now();headers=h});
        request.on('data',b=>{if(first_data===null)first_data=performance.now();chunks.push(b)});
        request.on('error',e=>finish({valid:false,error:e.message}));
        request.on('end',()=>{
          response_end=performance.now();const body=Buffer.concat(chunks);let decoded;
          if(headers[':status']!==200)decoded={valid:false,error:`HTTP ${headers[':status']}`,response_bytes:body.length,response_base64:body.toString('base64')};
          else if(!String(headers['content-type']??'').startsWith('application/dns-message'))decoded={valid:false,error:'Unexpected DoH media type',response_bytes:body.length,response_base64:body.toString('base64')};
          else try{decoded=wire(body,q)}catch(e){decoded={valid:false,error:e.message,response_bytes:body.length,response_base64:body.toString('base64')};}
          finish({...decoded,http_status:headers[':status'],validation_ms:performance.now()-response_end});
        });
        request.end(q);
      });
      this.count++;
      const rel=x=>x===null?null:x-t0;
      return {...common,...result,connection_query_number:this.count,request_create_ms:rel(request_created),request_write_finish_ms:rel(write_finish),response_headers_ms:rel(headers_at),first_body_ms:rel(first_data),response_end_ms:rel(response_end),elapsed_ms:performance.now()-t0};
    }catch(e){return {...common,valid:false,error:e.message,elapsed_ms:performance.now()-t0};}
  }
}

persist();const started=Date.now();
try{
  for(let window=1;window<=windows;window++){
    const due=started+(window-1)*interval*1000;while(Date.now()<due)await sleep(Math.min(30000,due-Date.now()));
    event({event:'window_start',window,scheduled_utc:new Date(due).toISOString()});
    const reusable={},doh={};
    try{
      for(const key of Object.keys(PROVIDERS)){
        reusable[key]=new BoundUDP(PROVIDERS[key]);doh[key]=new PhaseDoh(key);
        for(const [kind,client]of[['udp_bound',reusable[key]],['doh_warm',doh[key]]]){
          try{await client.open();event({event:'connection_established',window,provider:key,protocol:kind,local_port:client.local_port,bind_ms:client.bind_ms??null,connect_ms:client.connection?.connect_ms??null});}
          catch(e){event({event:'connection_setup_failed',window,provider:key,protocol:kind,error:e.message});}
        }
        for(const domain of domains)for(const protocol of modes){
          const stamp=new Date().toISOString();const result=protocol==='doh_warm'?await doh[key].query(domain):await udp(PROVIDERS[key],domain,protocol==='udp_bound'?reusable[key]:null);
          save({schema_version:1,phase:'prime',window,provider:key,domain,protocol,started_utc:stamp,...result});await sleep(10);
        }
      }
      const rng=seededRng(seed+window);let block=0;
      for(let rep=1;rep<=reps;rep++)for(const task of shuffle(Object.keys(PROVIDERS).flatMap(provider=>domains.map(domain=>({provider,domain}))),rng)){
        const block_id=`w${window}-b${++block}`;let order=0;
        for(const protocol of shuffle(modes,rng)){
          const stamp=new Date().toISOString();const result=protocol==='doh_warm'?await doh[task.provider].query(task.domain):await udp(PROVIDERS[task.provider],task.domain,protocol==='udp_bound'?reusable[task.provider]:null);
          if(protocol==='doh_warm'&&result.valid&&(!result.connection_preexisting||result.alpn!=='h2'||result.tls_session_reused!==false)){result.valid=false;result.error='Established DoH treatment mismatch';}
          save({schema_version:1,phase:'measure',window,rep,block_id,order:++order,...task,protocol,started_utc:stamp,...result});await sleep(10);
        }
      }
    }finally{for(const c of Object.values(reusable))c.close();for(const c of Object.values(doh))c.close();}
    event({event:'window_complete',window,total_rows:all,measured_rows:measured,valid_rows:valid});
  }
  meta.status='complete';meta.finished_utc=new Date().toISOString();meta.total_rows=all;meta.measured_rows=measured;meta.valid_rows=valid;event({event:'complete',total_rows:all,measured_rows:measured,valid_rows:valid});
}catch(e){meta.status='failed';meta.finished_utc=new Date().toISOString();meta.error=e.message;persist();event({event:'collector_failed',error:e.message});throw e;}
