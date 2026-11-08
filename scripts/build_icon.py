"""Encode the original high-resolution artwork as a Windows multi-resolution icon.
Largest frame first: image viewers must not upscale the first 16-pixel frame.
Each frame is sampled directly from the PNG master, never from another icon.
"""
from pathlib import Path
from io import BytesIO
import struct
from PIL import Image
assets=Path(__file__).resolve().parents[1]/'APP/assets'
master=Image.open(assets/'almighty_icon.png').convert('RGBA')
assert master.width==master.height and master.width>=1024
sizes=(256,128,96,64,48,40,32,24,20,16)
blocks=[]
for size in sizes:
    out=BytesIO()
    master.resize((size,size),Image.Resampling.LANCZOS).save(out,format='PNG',optimize=True)
    blocks.append(out.getvalue())
offset=6+16*len(sizes);directory=[]
for size,block in zip(sizes,blocks):
    directory.append(struct.pack('<BBBBHHII',size%256,size%256,0,0,1,32,len(block),offset))
    offset+=len(block)
(assets/'almighty_icon.ico').write_bytes(struct.pack('<HHH',0,1,len(sizes))+b''.join(directory)+b''.join(blocks))
print('ICON OK: original HD PNG, largest-first ICO and ten native Windows sizes.')
