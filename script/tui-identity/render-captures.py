#!/usr/bin/env python3
"""Rasterize captured native cell spans, without reconstructing or inventing layout."""
import json,pathlib,sys,os
from PIL import Image,ImageDraw,ImageFont,ImageOps
root=pathlib.Path(__file__).resolve().parents[2]
base=root/'tmp'/'tui-identity'/'captures'/(sys.argv[1] if len(sys.argv)>1 else 'before')
candidates=[os.environ.get('TUI_CAPTURE_FONT'),'/System/Library/Fonts/Menlo.ttc','/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','DejaVuSansMono.ttf']
font=None
for candidate in candidates:
    if not candidate: continue
    try:
        font=ImageFont.truetype(candidate,16,index=0)
        font_path=candidate
        break
    except OSError: pass
if font is None: raise SystemExit('Set TUI_CAPTURE_FONT to a regular monospace TrueType font.')
fonts=[font]*4
if str(font_path).endswith('Menlo.ttc'):
    fonts=[ImageFont.truetype(font_path,16,index=i) for i in range(4)]
else:
    for index,suffix in [(1,'-Bold.ttf'),(2,'-Oblique.ttf'),(3,'-BoldOblique.ttf')]:
        try: fonts[index]=ImageFont.truetype(str(font_path).replace('.ttf',suffix),16)
        except OSError: pass
cw=font.getlength('M'); ch=20; pad=16
def rasterize(frame):
    rgb=lambda c:tuple(c['rgba'][:3])
    image=Image.new('RGB',(round(frame['cols']*cw+2*pad),frame['rows']*ch+2*pad),rgb(frame['lines'][0]['spans'][0]['bg']))
    draw=ImageDraw.Draw(image)
    for y,line in enumerate(frame['lines']):
        x=pad
        for span in line['spans']:
            w=span['width']*cw
            draw.rectangle((round(x),pad+y*ch,round(x+w),pad+(y+1)*ch-1),fill=rgb(span['bg']))
            if span['text'].strip():
                attr=span['attributes']
                face=fonts[(1 if attr & 1 else 0)+(2 if attr & 4 else 0)]
                draw.text((x,pad+y*ch-2),span['text'],fill=rgb(span['fg']),font=face)
                if attr & 8: draw.line((x,pad+y*ch+17,x+w,pad+y*ch+17),fill=rgb(span['fg']))
                if attr & 128: draw.line((x,pad+y*ch+9,x+w,pad+y*ch+9),fill=rgb(span['fg']))
            x+=w
    return image

for file in sorted(base.rglob('*.json')):
    if file.name.endswith('.meta.json') or file.name=='capture-results.json': continue
    frame=json.loads(file.read_text())
    if file.name == 'motion-series.json':
        if not frame: continue
        frames=[rasterize(item['frame']) for item in frame]
        delays=[max(20,round((b['elapsed']-a['elapsed'])/10)*10) for a,b in zip(frame,frame[1:])]
        # The last captured quiet frame holds for 8 seconds to show the rest cadence.
        frames[0].save(file.with_name('motion.gif'),save_all=True,append_images=frames[1:],duration=delays+[8000],loop=0,optimize=False)
        continue
    if 'lines' not in frame: continue
    image=rasterize(frame)
    image.save(file.with_suffix('.png'))
    if file.stem.startswith('session-'):
        ImageOps.grayscale(image).save(file.with_name(file.stem+'-mono.png'))
print('Rendered',len(list(base.rglob('*.png'))),'PNGs in',base)
