import sys, os
from PIL import Image
from rembg import remove, new_session
S=sys.argv[1]
A=os.path.join(S,'assets'); O=os.path.join(S,'film','img')
sess=new_session('birefnet-general')
jobs=[]
neutral=Image.open(os.path.join(A,'gen_neutral.jpg')).convert('RGB')
jobs.append(('cat_neutral',neutral))
blink=Image.open(os.path.join(A,'gen_blink.jpg')).convert('RGB')
jobs.append(('cat_calm',blink))
sheet=Image.open(os.path.join(A,'gen_poses.jpg')).convert('RGB')
names=['cat_lookup','cat_present','cat_focus_front','cat_focus_side','cat_curious','cat_confident','cat_wave','cat_impressed']
cw,ch=sheet.width//4, sheet.height//2
for i,n in enumerate(names):
    r,c=divmod(i,4)
    cell=sheet.crop((c*cw+6, r*ch+6, (c+1)*cw-6, (r+1)*ch-6))
    jobs.append((n,cell))
only=set(sys.argv[2:])
for n,im in jobs:
    if only and n not in only: continue
    if os.path.exists(os.path.join(O,n+".png")): continue
    out=remove(im, session=sess, post_process_mask=True)
    bb=out.getchannel('A').point(lambda v:255 if v>8 else 0).getbbox()
    out=out.crop(bb)
    if out.height>1500:
        s=1500/out.height; out=out.resize((round(out.width*s),1500), Image.LANCZOS)
    out.save(os.path.join(O,n+'.png'))
    print(n, out.size, bb)
