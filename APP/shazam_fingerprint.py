"""Native ShazamIO audio analysis runs outside the GUI process. No network."""
import asyncio,json,sys
from pathlib import Path

async def prepare(source,destination):
    from shazamio import Shazam
    async with Shazam() as client:
        sig=await client.core_recognizer.recognize_path(value=str(source))
    result={'timezone':sig.timezone,'timestamp':sig.timestamp,
            'signature':{'uri':sig.signature.uri,'samples':sig.signature.samples}}
    if not str(result['signature']['uri']).startswith('data:'):raise ValueError('Invalid fingerprint')
    temporary=destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(result),encoding='utf-8');temporary.replace(destination)

if __name__=='__main__':
    try:asyncio.run(prepare(Path(sys.argv[1]),Path(sys.argv[2])))
    except Exception:
        print('ShazamIO fingerprint preparation failed',flush=True);raise SystemExit(1)
