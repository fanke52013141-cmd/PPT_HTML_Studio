"""Deterministic slot extraction for the recorded v2 sheet; requires Pillow.
No matting, background edits, contour cleanup or automatic recognition.
Existing crop files are reproduced from the immutable chosen source.
"""
from pathlib import Path
from PIL import Image
folder=Path(__file__).resolve().parent
image=Image.open(folder/'asset-board-v2.png')
assert image.mode=='RGBA'
w,h=image.size
slots={'plane':(0,0,w//2,h//2),'cloud-large':(w//2,0,w,h//2),'cloud-small':(0,h//2,w//2,h)}
(folder/'assets').mkdir(exist_ok=True)
for name,rect in slots.items():
    image.crop(rect).save(folder/'assets'/(name+'.png'))
print('Three full-slot crops reproduced; see asset-evidence.json for original hashes and anchors.')
