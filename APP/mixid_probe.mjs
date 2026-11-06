// Isolate each original mix-id/Shazam SDK probe from native process failures.
import {createRequire} from 'node:module';
import {readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
const [project,file,mode,target]=process.argv.slice(2);
const localOnly=process.argv.includes('--local-only');
const require=createRequire(join(project,'package.json'));
const {Shazam,s16LEToSamplesArray}=require('shazam-api');
// Use the SDK's installed HTTP/1 client rather than Node 24's native fetch.
const nativeFetch=require('node-fetch');
globalThis.fetch=async (url,options)=>{
  const response=await nativeFetch(url,{...options,signal:AbortSignal.timeout(10000)});
  if(response.status===429){const error=new Error('HTTP 429: Anfragelimit');error.retryAfter=response.headers.get('retry-after');throw error;}
  if(!response.ok)throw new Error('HTTP '+response.status);
  return response;
};
try {
  const client=new Shazam();
  if(mode==='--send'){
    const saved=JSON.parse(readFileSync(file,'utf8'));
    if(typeof saved.uri!=='string'||!saved.uri.startsWith('data:')||!(saved.numberSamples>0)||saved.sampleRateHz!==16000)throw new Error('Invalid prepared fingerprint');
    const response=await client.endpoint.formatAndSendRecognizeRequest({...saved,encodeToUri:()=>saved.uri});
    const track=response?.track;
    if(response&&!track?.title)throw new Error('Malformed Shazam track response');
    console.log(JSON.stringify({status:'ok',track:track?{title:track.title,artist:track.subtitle}:null}));
    process.exit(0);
  }
  if(mode==='--prepare')client.endpoint.formatAndSendRecognizeRequest=async signature=>{
    writeFileSync(target,JSON.stringify({uri:signature.encodeToUri(),numberSamples:signature.numberSamples,sampleRateHz:signature.sampleRateHz}));
    return null;
  };
  const track=await client.recognizeSong(s16LEToSamplesArray(readFileSync(file)),phase=>{
    console.log(JSON.stringify({phase}));
    if(localOnly&&phase==='transmitting')throw new Error('LOCAL_ONLY_COMPLETE');
  });
  console.log(JSON.stringify({status:mode==='--prepare'?'prepared':'ok',track:track||null}));
  process.exit(0);
} catch(error) {
  const message=String(error.message||error).slice(0,350);
  if(message==='LOCAL_ONLY_COMPLETE'){console.log(JSON.stringify({status:'local_ok'}));process.exit(0);}
  console.log(JSON.stringify({status:message.includes('HTTP 429')?'rate_limit':'error',error:message,retry_after:error.retryAfter||null}));
  process.exit(2);
}
