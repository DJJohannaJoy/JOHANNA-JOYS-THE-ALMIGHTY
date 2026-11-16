// Google Sound Search wire schema adapted from niizam/humtosong (MIT).
// See licenses/humtosong-MIT.txt. No account cookies or OAuth tokens are used.
import http2 from 'node:http2';
import {readFileSync} from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';

const cat=(...parts)=>Buffer.concat(parts);
function vint(n){let x=BigInt(n),out=[];while(x>127n){out.push(Number(x&127n)|128);x>>=7n;}out.push(Number(x));return Buffer.from(out);}
const integer=(id,n)=>cat(vint(BigInt(id)*8n),vint(n));
function bytes(id,b){if(typeof b==='string')b=Buffer.from(b);return cat(vint(BigInt(id)*8n+2n),vint(b.length),b);}
function frame(b){const h=Buffer.alloc(5);h.writeUInt32BE(b.length,1);return cat(h,b);}
export function packets(audio){
 const rate=Buffer.alloc(4);rate.writeFloatLE(16000);
 const init=cat(bytes(1,'sound-search'),integer(2,1),bytes(293000,bytes(3,cat(bytes(1,'en-US'),integer(2,2)))),
  bytes(293100,cat(vint(21),rate,integer(3,8),integer(4,1))),
  bytes(35351945,cat(bytes(1,cat(integer(2,0),bytes(4,'en-US'),bytes(7,'IE'),integer(13,3))),bytes(2,cat(integer(1,4),integer(2,4))),integer(3,0),bytes(10,Buffer.alloc(0)))));
 const out=[frame(init)];
 for(let i=0;i<audio.length;i+=2048)out.push(frame(bytes(293101,bytes(1,audio.subarray(i,i+2048)))));
 out.push(frame(integer(3,1)));return cat(...out);
}
function varint(b,p){let n=0n,shift=0n;for(let i=0;i<10;i++){
 if(p>=b.length)throw Error('Truncated varint');const v=b[p++];n|=BigInt(v&127)<<shift;
 if(!(v&128)){if(n>BigInt(Number.MAX_SAFE_INTEGER))return [n,p];return [Number(n),p];}shift+=7n;
 }throw Error('Invalid varint');}
function fields(b){const out=new Map();let p=0;while(p<b.length){
 let tag;[tag,p]=varint(b,p);if(typeof tag!=='number'||!(tag>>3))throw Error('Invalid field');
 const id=tag>>>3,wire=tag&7;let value,size;
 if(wire===0)[value,p]=varint(b,p);
 else if(wire===1||wire===5){size=wire===1?8:4;value=b.subarray(p,p+size);p+=size;}
 else if(wire===2){[size,p]=varint(b,p);if(typeof size!=='number'||size>1e6)throw Error('Invalid field size');value=b.subarray(p,p+size);p+=size;}
 else throw Error('Unsupported protobuf field');
 if(p>b.length)throw Error('Truncated field');if(!out.has(id))out.set(id,[]);out.get(id).push(value);
 }return out;}
const nested=(f,id)=>(f.get(id)||[]).filter(Buffer.isBuffer).map(fields);
const string=(f,id)=>(f.get(id)||[]).find(Buffer.isBuffer)?.toString('utf8')||'';
export function decodeResponse(raw){
 let p=0;const matches=[];
 while(p<raw.length){
  if(p+5>raw.length)throw Error('Truncated gRPC header');const flag=raw[p],n=raw.readUInt32BE(p+1);p+=5;
  if(n>1e6||p+n>raw.length)throw Error('Truncated gRPC frame');let b=raw.subarray(p,p+n);p+=n;
  if(flag===1)b=gunzipSync(b,{maxOutputLength:1e6});else if(flag!==0)throw Error('Unsupported compression');
  for(const ext of nested(fields(b),35351945))for(const group of nested(ext,1))
   for(const candidate of nested(group,1))for(const song of nested(candidate,3)){
    const title=string(song,2),youtube_id=string(song,22);
    if(title)matches.push({title,artist:string(song,1),album:string(song,3),youtube_id});
   }
 }
 return matches;
}
export function recognize(audio,headers,timeout=25000){return new Promise(resolve=>{
 const started=Date.now(),session=http2.connect('https://speechs3proto2-pa.googleapis.com');
 let finished=false,head={},trailers={},chunks=[],size=0;
 const redact=s=>String(s).replaceAll(headers['x-goog-api-key']||'\0','<redacted>').replace(/AIza[0-9A-Za-z_-]{35}/g,'<redacted>');
 function end(error){if(finished)return;finished=true;clearTimeout(timer);
  let message=String(trailers['grpc-message']??head['grpc-message']??'');try{message=decodeURIComponent(message);}catch{}
  const status=String(trailers['grpc-status']??head['grpc-status']??'missing');
  const result={status:'error',http_status:head[':status']??0,grpc_status:status,elapsed_ms:Date.now()-started};
  try{
   if(error)throw error;
   if(head[':status']!==200||status!=='0')throw Error(`HTTP ${result.http_status} / gRPC ${status}: ${message}`);
   result.matches=decodeResponse(cat(...chunks));result.status='ok';
  }catch(exc){result.error=redact(exc.message).slice(0,220);result.retryable=!!error||['4','8','13','14'].includes(status)||result.http_status>=500;}
  session.destroy();resolve(result);
 }
 const timer=setTimeout(()=>end(Error('Google request timed out')),timeout);session.on('error',end);
 session.on('connect',()=>{
  try{
   const request=session.request({':method':'POST',':path':'/speech.s3.S3StubbyClientConnectorService/S3Bidi','content-type':'application/grpc',te:'trailers','grpc-accept-encoding':'gzip',...headers});
   request.on('response',value=>head=value);request.on('trailers',value=>trailers=value);
   request.on('error',end);request.on('data',b=>{size+=b.length;if(size>1e6){end(Error('Response cap exceeded'));return;}chunks.push(b);});
   request.on('end',()=>end());request.end(packets(audio));
  }catch(exc){end(exc);}
 });
});}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 try{
  const headers=JSON.parse(readFileSync(process.argv[2],'utf8'));
  if(!/^AIza[\w-]{35}$/.test(headers['x-goog-api-key']||''))throw Error('Google access file invalid');
  const allowed={};for(const name of ['x-goog-api-key','x-android-package','x-android-cert','user-agent'])if(headers[name])allowed[name]=headers[name];
  const audio=readFileSync(process.argv[3]);if(!audio.length||audio.length>2e6)throw Error('Invalid audio size');
  console.log(JSON.stringify(await recognize(audio,allowed)));
 }catch{console.log(JSON.stringify({status:'error',error:'Google access file or audio unreadable',retryable:false}));process.exitCode=1;}
}
