#!/usr/bin/env python3
"""Generate wholly original approximation sprites (never original Dobry Cola art)."""
from pathlib import Path
from PIL import Image, ImageDraw
import math

root=Path(__file__).resolve().parents[1] / 'games' / 'snake' / 'assets'
root.mkdir(parents=True,exist_ok=True)
for name,color,mark in [('moose','#bd7542','M'),('red','#e76b65','R'),('blue','#4a91cf','B'),('gift','#f4c53d','G'),('girl','#d65d9a','X'),('flake','#b4e5ff','F'),('drift','#818daa','D'),('speed','#76d5a9','S')]:
    im=Image.new('RGBA',(64,64),(0,0,0,0));d=ImageDraw.Draw(im)
    d.ellipse((4,4,59,59),fill=color,outline='#1a4968',width=3)
    if name=='gift':
        d.rectangle((14,23,49,49),fill='#e8a11c',outline='#664506',width=2)
        d.rectangle((29,16,35,50),fill='white');d.line((15,33,49,33),fill='white',width=4)
    elif name=='moose':
        d.ellipse((23,20,43,49),fill='#89532e')
        d.ellipse((25,34,32,42),fill='white');d.ellipse((36,34,43,42),fill='white')
        d.ellipse((28,37,30,39),fill='#151b21');d.ellipse((39,37,41,39),fill='#151b21')
    elif name=='flake':
        for a in range(0,180,45):
            angle=math.radians(a);dx=20*math.cos(angle);dy=20*math.sin(angle)
            d.line((32-dx,32-dy,32+dx,32+dy),fill='#ffffff',width=4)
    else:d.text((29,25),mark,fill='white')
    im.save(root/f'{name}.png')

im=Image.new('RGBA',(1148,646),'#d7ecfa');d=ImageDraw.Draw(im)
d.rounded_rectangle((208,118,939,529),radius=80,fill='#a8d9f1',outline='#f5fcff',width=8)
for i in range(18):
    x=234+i*40;d.line((x,143,x,504),fill='#d5edf9',width=1)
for j in range(10):
    y=144+j*40;d.line((234,y,914,y),fill='#d5edf9',width=1)
d.rounded_rectangle((208,118,939,529),radius=80,outline='#80c6e7',width=5)
im.save(root/'rink.png')
print(f'Generated {len(list(root.glob("*.png")))} original proxy sprites in {root}')