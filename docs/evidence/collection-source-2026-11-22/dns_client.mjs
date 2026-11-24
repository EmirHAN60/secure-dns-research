/** Direct IPv4 UDP and RFC 8484 HTTP/2 clients. No external dependencies. */
import dgram from 'node:dgram';
import http2 from 'node:http2';
import { randomInt } from 'node:crypto';
import { performance } from 'node:perf_hooks';

export const PROVIDERS = {
  cloudflare: { ip: '1.1.1.1', host: 'cloudflare-dns.com', path: '/dns-query' },
  google: { ip: '8.8.8.8', host: 'dns.google', path: '/dns-query' },
};
export const DOMAINS = ['example.com','wikipedia.org','mozilla.org','github.com','cloudflare.com','google.com','microsoft.com','apple.com','bbc.com','amazon.com'];

export function makeQuery(name, id = randomInt(65536)) {
  const labels = name.replace(/\.$/, '').toLowerCase().split('.');
  if (!labels.length || labels.some(l => !l.length || l.length > 63 || !/^[a-z0-9-]+$/.test(l))) throw new Error('Invalid qname');
  const h = Buffer.alloc(12); h.writeUInt16BE(id,0); h.writeUInt16BE(0x0100,2); h.writeUInt16BE(1,4);
  return Buffer.concat([h,...labels.flatMap(l=>[Buffer.from([l.length]),Buffer.from(l,'ascii')]),Buffer.from([0,0,1,0,1])]);
}

function readName(b, start) {
  let p=start, end=null, labels=[], seen=new Set();
  for(let hop=0;hop<128;hop++) {
    if(p>=b.length) throw new Error('Truncated DNS name');
    if(seen.has(p)) throw new Error('DNS compression loop'); seen.add(p);
    const n=b[p];
    if((n&0xc0)===0xc0) { if(p+1>=b.length)throw new Error('Truncated compression pointer'); if(end===null)end=p+2; p=((n&63)<<8)|b[p+1];continue; }
    if(n&0xc0)throw new Error('Invalid label bits');
    p++;
    if(!n)return {name:labels.join('.').toLowerCase(),end:end??p};
    if(p+n>b.length)throw new Error('Truncated DNS label');
    labels.push(b.subarray(p,p+n).toString('ascii'));p+=n;
  }
  throw new Error('DNS name too deep');
}

export function parseResponse(b, query) {
  if(!Buffer.isBuffer(b)||b.length<12)throw new Error('Short DNS response');
  const flags=b.readUInt16BE(2);
  if(!(flags&0x8000))throw new Error('QR flag missing');
  if((flags&0x7800)!==0)throw new Error('Unexpected opcode');
  if(b.readUInt16BE(0)!==query.readUInt16BE(0))throw new Error('Transaction ID mismatch');
  if(b.readUInt16BE(4)!==1)throw new Error('Unexpected question count');
  const q=readName(b,12), expected=readName(query,12);
  if(q.name!==expected.name||q.end+4>b.length||b.readUInt16BE(q.end)!==1||b.readUInt16BE(q.end+2)!==1)throw new Error('Question mismatch');
  let p=q.end+4; const counts=[b.readUInt16BE(6),b.readUInt16BE(8),b.readUInt16BE(10)]; const answers=[];
  for(let sec=0;sec<3;sec++)for(let i=0;i<counts[sec];i++){
    const n=readName(b,p);p=n.end;
    if(p+10>b.length)throw new Error('Truncated RR header');
    const type=b.readUInt16BE(p),cls=b.readUInt16BE(p+2),ttl=b.readUInt32BE(p+4),len=b.readUInt16BE(p+8);p+=10;
    if(p+len>b.length)throw new Error('Truncated RR data');
    if(sec===0&&cls===1&&(type===1||type===28)) {
      if((type===1&&len!==4)||(type===28&&len!==16))throw new Error('Invalid address length');
      const address=type===1?[...b.subarray(p,p+len)].join('.'):Array.from({length:8},(_,j)=>b.readUInt16BE(p+j*2).toString(16)).join(':');
      answers.push({name:n.name,type,ttl,address});
    }
    p+=len;
  }
  const rcode=flags&15,truncated=!!(flags&0x0200);
  return {rcode,truncated,answer_count:counts[0],addresses:answers.map(a=>a.address),ttls:answers.map(a=>a.ttl),valid:rcode===0&&!truncated&&answers.some(a=>a.type===1)};
}

function responseFields(body,q) {
  const parsed=parseResponse(body,q);
  return {...parsed,response_bytes:body.length,response_base64:body.toString('base64'),error:parsed.valid?null:`DNS rcode=${parsed.rcode} TC=${parsed.truncated} A=${parsed.addresses.length}`};
}

export async function udpQuery(provider, name, {timeoutMs=3000}={}) {
  const p=typeof provider==='string'?PROVIDERS[provider]:provider, q=makeQuery(name), t=performance.now();
  return await new Promise(resolve=>{
    const s=dgram.createSocket('udp4');let done=false;
    const finish=r=>{if(done)return;done=true;clearTimeout(timer);try{s.close()}catch{};resolve({elapsed_ms:performance.now()-t,query_base64:q.toString('base64'),...r})};
    const timer=setTimeout(()=>finish({valid:false,error:'UDP timeout',timeout:true}),timeoutMs);
    s.on('error',e=>finish({valid:false,error:e.message}));
    s.on('message',(b,peer)=>{
      if(peer.address!==p.ip||peer.port!==53)return;
      try{finish(responseFields(b,q))}catch(e){finish({valid:false,error:e.message,response_base64:b.toString('base64')})}
    });
    s.send(q,53,p.ip,e=>{if(e)finish({valid:false,error:e.message})});
  });
}

export class DohClient {
  constructor(provider,{timeoutMs=3000}={}) { this.provider=typeof provider==='string'?PROVIDERS[provider]:provider;this.timeoutMs=timeoutMs;this.session=null;this.connectPromise=null;this.connectionInfo=null;this.queryCount=0; }
  async connect() {
    if(this.connectPromise)return this.connectPromise;
    if(this.session&&!this.session.destroyed&&!this.session.closed)return this.connectionInfo;
    const p=this.provider, t=performance.now();
    this.connectPromise=new Promise((resolve,reject)=>{
      const s=http2.connect('https://'+p.host,{servername:p.host,family:4,lookup:(h,o,cb)=>o.all?cb(null,[{address:p.ip,family:4}]):cb(null,p.ip,4),rejectUnauthorized:true,ALPNProtocols:['h2'],session:undefined});
      this.session=s;s.on('error',()=>{});
      const timer=setTimeout(()=>{s.destroy();reject(new Error('DoH connection timeout'))},this.timeoutMs);
      s.once('error',e=>{clearTimeout(timer);reject(e)});
      s.once('connect',()=>{
        clearTimeout(timer);
        const socket=s.socket;
        if(s.alpnProtocol!=='h2'){s.destroy();reject(new Error('HTTP/2 not negotiated'));return;}
        this.connectionInfo={connect_ms:performance.now()-t,alpn:s.alpnProtocol,tls_version:socket.getProtocol(),tls_session_reused:socket.isSessionReused(),remote_address:socket.remoteAddress};
        resolve(this.connectionInfo);
      });
    }).finally(()=>{this.connectPromise=null});
    return this.connectPromise;
  }
  async query(name) {
    const q=makeQuery(name),t=performance.now();
    const wasEstablished=!!(this.session&&!this.session.destroyed&&!this.session.closed);
    try {
      const ci=await this.connect();const s=this.session;
      const r=await new Promise(resolve=>{
        let done=false,headers={},chunks=[];
        const req=s.request({':method':'POST',':path':this.provider.path,':authority':this.provider.host,'content-type':'application/dns-message','accept':'application/dns-message','content-length':q.length});
        const finish=r=>{if(done)return;done=true;clearTimeout(timer);resolve(r)};
        const timer=setTimeout(()=>{req.close();finish({valid:false,error:'DoH query timeout',timeout:true})},this.timeoutMs);
        req.on('response',h=>{headers=h}); req.on('data',b=>chunks.push(b));
        req.on('error',e=>finish({valid:false,error:e.message}));
        req.on('end',()=>{
          const body=Buffer.concat(chunks),status=headers[':status'];
          if(status!==200){finish({valid:false,error:`HTTP ${status}`,http_status:status,response_bytes:body.length});return;}
          if(!String(headers['content-type']??'').startsWith('application/dns-message')){finish({valid:false,error:'Unexpected DoH media type',http_status:status});return;}
          try { finish({...responseFields(body,q),http_status:status}) } catch(e){finish({valid:false,error:e.message,http_status:status,response_base64:body.toString('base64')})}
        });
        req.end(q);
      });
      this.queryCount++;
      return {elapsed_ms:performance.now()-t,query_base64:q.toString('base64'),connection_preexisting:wasEstablished,connection_query_number:this.queryCount,...ci,...r};
    } catch(e){return {elapsed_ms:performance.now()-t,valid:false,error:e.message,query_base64:q.toString('base64'),connection_preexisting:wasEstablished};}
  }
  close(){if(this.session){this.session.destroy();this.session=null;this.connectionInfo=null;this.queryCount=0;}}
}

export function seededRng(seed) { let a=seed>>>0; return ()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return ((t^t>>>14)>>>0)/4294967296}; }
export function shuffle(arr,rng){const a=[...arr];for(let i=a.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
