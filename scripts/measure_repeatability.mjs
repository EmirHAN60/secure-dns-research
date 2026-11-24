/** Balanced fixed-position A/A and cross-mode public-DNS controls. */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import dgram from 'node:dgram';
import { randomInt, createHash } from 'node:crypto';
import { performance } from 'node:perf_hooks';
import { fileURLToPath } from 'node:url';
import { PROVIDERS, DOMAINS, makeQuery, parseResponse, DohClient, windowRng, shuffle } from './dns_client.mjs';
const script=fileURLToPath(import.meta.url), root=path.dirname(path.dirname(script));
const argv=process.argv.slice(2),get=(key,fallback)=>{const i=argv.indexOf(key);return i<0?fallback:argv[i+1]};
const sessionId=get('--session-id','repeatability-2026-11-23-a');
const out=path.resolve(get('--out',path.join(root,'data/control-repeatability-2026-11-23-a')));
const windows=Number(get('--windows','3')),reps=Number(get('--reps','12')),interval=Number(get('--interval-seconds','120')),seed=Number(get('--seed','20261123'));
const stepMs=Number(get('--step-ms','100')),flowCount=2,timeoutMs=3000,domains=[...DOMAINS];
const modes=['udp_bound','doh_warm'],conditions=['repeat_flow','distinct_flows'];
const sequences=['UUDD','UDUD','UDDU','DUUD','DUDU','DDUU'];
if(!/^[a-zA-Z0-9._-]+$/.test(sessionId))throw new Error('Session ID must be a stable nonprivate label');
if(![windows,reps,interval,stepMs].every(v=>Number.isInteger(v)&&v>0)||reps%12!==0)throw new Error('Positive integer parameters and reps divisible by 12 required');
if(Object.keys(PROVIDERS).sort().join(',')!=='cloudflare,google'||PROVIDERS.cloudflare.ip!=='1.1.1.1'||PROVIDERS.google.ip!=='8.8.8.8')throw new Error('Only the two declared public resolvers are allowed');
const expectedMeasured=windows*Object.keys(PROVIDERS).length*domains.length*reps*4;
const expectedPrimes=windows*Object.keys(PROVIDERS).length*domains.length*flowCount*modes.length;
if(expectedMeasured+expectedPrimes>65536)throw new Error('Design exceeds the unique 16-bit transaction-ID budget');
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const planArg=get('--plan',null),planHash=get('--plan-sha256',null);
if(!planArg||!planHash||sha(path.resolve(planArg))!==planHash)throw new Error('A matching frozen local analysis plan is required');
fs.mkdirSync(out,{recursive:true});
const raw=path.join(out,'repeatability_raw.jsonl');if(fs.existsSync(raw))throw new Error('Refusing to overwrite repeatability_raw.jsonl');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const ids=new Set();function query(name){let id;do{id=randomInt(65536)}while(ids.has(id));ids.add(id);return makeQuery(name,id)}
const wire=(b,q)=>{const p=parseResponse(b,q);return {...p,error:p.valid?null:`DNS rcode=${p.rcode} TC=${p.truncated}`,response_bytes:b.length,response_base64:b.toString('base64')};};
const design={schema_version:1,study:'Balanced fixed-position DNS repeatability and distinct-flow controls',session_id:sessionId,windows,reps,interval_seconds:interval,seed,step_ms:stepMs,domains,providers:PROVIDERS,modes,flow_conditions:conditions,flows_per_mode_provider_window:flowCount,sequences,timeout_ms:timeoutMs,qtype:'A',ip_version:4,expected_measured_attempts:expectedMeasured,expected_priming_attempts:expectedPrimes,analysis_plan:planArg,analysis_plan_sha256:planHash,
 randomization:'Construct the complete provider/domain/flow-condition/six-order pool before independently shuffling each window using SHA-256-derived windowRng streams whose namespace includes session ID. First-flow assignments are separately seeded and balanced 3/3 within each six-order cell.',
 flow_definition:'Two separately established UDP sockets and two H2 sessions per provider/window. repeat_flow uses the same mode-specific flow twice; distinct_flows switches to the other prepared mode-specific flow for the second occurrence. Distinct flows are not assumed statistically independent.',
 timing:'Each four-attempt block targets offsets 0, step, 2*step, 3*step ms. Previous response is awaited; late starts and failures remain. Query construction is outside elapsed_ms. Actual monotonic starts/ends allow exact position-pair and observed-lag comparisons. All UDP and H2 resources are ready before query timing.',
 estimands:'Same-mode repeated-query differences and absolute differences, separately by flow condition, mode, exact position pair and observed start lag; cross-mode DoH-minus-UDP contrasts in corresponding randomized position strata. A/A and cross-mode lag matching is across balanced orders, not inside every block. No subtraction of a jitter median is claimed to identify encryption cost.',
 failure_policy:'All attempts retained with no retries, replacements or imputation. Successful paired estimates condition on both replies. Failed/late observations are separately reported; the collector applies no analysis lag exclusions.',
 priming:'Each domain is queried once through every prepared flow before measurement; remote cache-hit state remains unobserved.',
 source_sha256:{'measure_repeatability.mjs':sha(script),'dns_client.mjs':sha(path.join(path.dirname(script),'dns_client.mjs'))}};
fs.writeFileSync(path.join(out,'design.json'),JSON.stringify({...design,declared_utc:new Date().toISOString()},null,2)+'\n');
const meta={...design,started_utc:new Date().toISOString(),status:'running',platform:os.platform(),release:os.release(),arch:os.arch(),cpu_model:os.cpus()[0]?.model,logical_cpus:os.cpus().length,total_memory_gib:os.totalmem()/2**30,node:process.version,openssl:process.versions.openssl,execution_timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,local_ip_addresses_recorded:false,window_events:[]};
const persist=()=>fs.writeFileSync(path.join(out,'environment.json'),JSON.stringify(meta,null,2)+'\n');
const event=value=>{const row={...value,utc:new Date().toISOString()};fs.appendFileSync(path.join(out,'events.jsonl'),JSON.stringify(row)+'\n');meta.window_events.push(row);persist();console.log(JSON.stringify(row))};
let totalRows=0,measuredRows=0,validRows=0;
const save=row=>{fs.appendFileSync(raw,JSON.stringify(row)+'\n');totalRows++;if(row.phase==='measure')measuredRows++;if(row.valid)validRows++};
function blockPool(window){
  const pool=[];
  for(const provider of Object.keys(PROVIDERS))for(const domain of domains)for(let cycle=0;cycle<reps/12;cycle++)for(let c=0;c<conditions.length;c++){
    const condition=conditions[c],stem=`${sessionId}/repeatability/first-flow/${provider}/${domain}/${condition}/${cycle}`;
    const udpStarts=shuffle([0,0,0,1,1,1],windowRng(seed,window,stem+'/udp'));
    const dohStarts=shuffle([0,0,0,1,1,1],windowRng(seed,window,stem+'/doh'));
    for(let s=0;s<sequences.length;s++)pool.push({provider,domain,cycle,rep:cycle*12+c*6+s+1,flow_condition:condition,sequence:sequences[s],first_udp_flow:udpStarts[s],first_doh_flow:dohStarts[s]});
  }
  return shuffle(pool,windowRng(seed,window,`${sessionId}/repeatability/full-block-pool`));
}

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
  const common={query_start_monotonic_ms:t0,query_base64:q.toString('base64'),bound_before_timing:!!bound,udp_connected:false,remote_address:provider.ip,remote_port:53,local_port};
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
    const common={query_start_monotonic_ms:t0,query_base64:q.toString('base64'),connection_preexisting:this.ready,connection_id:this.connection_id??null,local_port:this.local_port??null,remote_port:443,...(this.connection??{})};
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
    const pool=blockPool(window);
    fs.writeFileSync(path.join(out,`schedule-window-${window}.json`),JSON.stringify(pool,null,2)+'\n');
    event({event:'window_start',window,scheduled_utc:new Date(due).toISOString(),planned_blocks:pool.length});
    const clients={};
    try{
      for(const provider of Object.keys(PROVIDERS)){
        clients[provider]={udp_bound:[],doh_warm:[]};
        for(const protocol of modes)for(let flow_index=0;flow_index<flowCount;flow_index++){
          const client=protocol==='udp_bound'?new BoundUDP(PROVIDERS[provider]):new PhaseDoh(provider);
          const flow_id=`${sessionId}/w${window}/${provider}/${protocol}/f${flow_index}`;
          clients[provider][protocol].push(client);client.flow_id=flow_id;
          try{await client.open();event({event:'flow_established',window,provider,protocol,flow_index,flow_id,local_port:client.local_port,connect_ms:client.connection?.connect_ms??null,bind_ms:client.bind_ms??null});}
          catch(e){event({event:'flow_setup_failed',window,provider,protocol,flow_index,flow_id,error:e.message});}
        }
        for(const domain of domains)for(const protocol of modes)for(let flow_index=0;flow_index<flowCount;flow_index++){
          const client=clients[provider][protocol][flow_index],stamp=new Date().toISOString();
          const result=protocol==='udp_bound'?await udp(PROVIDERS[provider],domain,client):await client.query(domain);
          save({schema_version:1,phase:'prime',session_id:sessionId,window,provider,domain,protocol,flow_index,flow_id:client.flow_id,started_utc:stamp,...result});await sleep(5);
        }
      }
      let block_order=0;
      for(const cell of pool){
        const block_id=`w${window}-b${++block_order}`,anchor=performance.now(),seen={U:0,D:0};
        for(let p=0;p<4;p++){
          const planned=anchor+p*stepMs;while(performance.now()<planned)await sleep(Math.max(0,planned-performance.now()));
          const letter=cell.sequence[p],protocol=letter==='U'?'udp_bound':'doh_warm',repeat_index=++seen[letter];
          const initial=letter==='U'?cell.first_udp_flow:cell.first_doh_flow;
          const flow_index=cell.flow_condition==='distinct_flows'&&repeat_index===2?1-initial:initial;
          const client=clients[cell.provider][protocol][flow_index],stamp=new Date().toISOString(),dispatch=performance.now();
          const result=protocol==='udp_bound'?await udp(PROVIDERS[cell.provider],cell.domain,client):await client.query(cell.domain);
          if(protocol==='doh_warm'&&result.valid&&(!result.connection_preexisting||result.alpn!=='h2'||result.tls_session_reused!==false)){result.valid=false;result.error='Established H2 treatment mismatch';}
          const actual=result.query_start_monotonic_ms;
          save({schema_version:1,phase:'measure',session_id:sessionId,window,block_id,block_order,...cell,position:p+1,protocol,repeat_index,flow_index,flow_id:client.flow_id,started_utc:stamp,block_anchor_monotonic_ms:anchor,planned_offset_ms:p*stepMs,planned_start_monotonic_ms:planned,dispatch_monotonic_ms:dispatch,actual_start_monotonic_ms:actual,measurement_end_monotonic_ms:actual+result.elapsed_ms,start_lateness_ms:actual-planned,...result});
        }
      }
    }finally{for(const provider of Object.values(clients))for(const group of Object.values(provider))for(const client of group)client.close();}
    event({event:'window_complete',window,total_rows:totalRows,measured_rows:measuredRows,valid_rows:validRows});
  }
  meta.status='complete';meta.finished_utc=new Date().toISOString();meta.total_rows=totalRows;meta.measured_rows=measuredRows;meta.valid_rows=validRows;event({event:'complete',total_rows:totalRows,measured_rows:measuredRows,valid_rows:validRows});
}catch(e){meta.status='failed';meta.finished_utc=new Date().toISOString();meta.error=e.message;event({event:'collector_failed',error:e.message});throw e;}
