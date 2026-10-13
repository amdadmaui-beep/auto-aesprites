import sys, os, numpy as np
from PIL import Image, ImageDraw, ImageFilter
S=sys.argv[1]; A=S+'/assets/'; I=S+'/film/img/'
neutral=np.array(Image.open(A+'gen_neutral.jpg').convert('RGB')).astype(np.float32)
calm=np.array(Image.open(A+'gen_blink.jpg').convert('RGB')).astype(np.float32)
sheet=np.array(Image.open(A+'gen_poses.jpg').convert('RGB')).astype(np.float32)
cw,ch=4096//4,2304//2
names=['cat_lookup','cat_present','cat_focus_front','cat_focus_side','cat_curious','cat_confident','cat_wave','cat_impressed']
# source image + crop origin + bbox (in crop coords) for each cutout
bboxes={'cat_neutral':(1071,586,3550,3645),'cat_calm':(454,400,3824,3841),
 'cat_lookup':(147,26,911,1068),'cat_present':(0,19,935,1059),'cat_focus_front':(102,44,886,1053),'cat_focus_side':(0,34,973,1064),
 'cat_curious':(102,0,937,1103),'cat_confident':(131,0,815,1106),'cat_wave':(0,0,894,1106)}
def src_for(n):
    if n=='cat_neutral': return neutral,(0,0)
    if n=='cat_calm': return calm,(0,0)
    i=names.index(n); r,c=divmod(i,4); return sheet,(c*cw+6,r*ch+6)
def bg_rows(img,org,bb,H):
    # per-row background colour from margins of the source crop outside the subject bbox
    x0,y0=org; out=[]
    sub=img[y0:y0+H] if False else img
    for y in range(bb[1],bb[3]):
        yy=y0+y
        L=img[yy, max(x0, x0+bb[0]-160):max(x0+1,x0+bb[0]-20)]
        R=img[yy, x0+bb[2]+20:x0+bb[2]+160]
        px=np.concatenate([L,R]) if len(L)+len(R)>0 else img[yy,x0:x0+40]
        out.append(np.median(px,axis=0) if len(px) else np.array([142,147,153.]))
    return np.array(out)
def decontam(n):
    from scipy import ndimage
    im=Image.open(I+n+'.png').convert('RGBA'); a=np.array(im).astype(np.float32)
    img,org=src_for(n); bb=bboxes[n]
    B=bg_rows(img,org,bb,None)
    idx=np.clip((np.arange(a.shape[0])*(B.shape[0]/a.shape[0])).astype(int),0,B.shape[0]-1)
    Bimg=np.repeat(B[idx][:,None,:],a.shape[1],1)
    al=a[...,3]/255.0; rgb=a[...,:3]
    # edge band: within 9px of transparency
    solid=al>0.5
    dist=ndimage.distance_transform_edt(solid)
    band=(al>0)&(dist<9)
    d=np.linalg.norm(rgb-Bimg,axis=2)
    w=np.clip((d-16)/(60-16),0,1); w=w*w*(3-2*w)
    keep=np.where(band, w, 1.0)
    al2=al*keep
    # bleed interior colour into the band so hair tips carry fur colour, not backdrop grey
    core=(al2>0.9)&(dist>=3)
    cf=core.astype(np.float32)
    num=np.stack([ndimage.gaussian_filter(rgb[...,c]*cf,4) for c in range(3)],-1)
    den=ndimage.gaussian_filter(cf,4)[...,None]+1e-6
    inner=num/den
    t=np.where(band,(1-np.clip(dist/9,0,1))*0.75,0)[...,None]
    rgb2=rgb*(1-t)+inner*t
    # classic unmix for remaining partial alpha
    A=np.maximum(al2,1e-3)[...,None]
    un=np.clip((rgb2-(1-A)*Bimg)/A,0,255)
    mix=np.clip((al2[...,None]-0.15)/0.5,0,1)
    rgb3=np.where((al2[...,None]<0.98)&(al2[...,None]>0.01), rgb2*(1-mix*0.5)+un*(mix*0.5), rgb2)
    # drop thin detached strands (broken whiskers) outside the body silhouette
    body=ndimage.binary_opening(al2>0.35,structure=np.ones((9,9)))
    near=ndimage.binary_dilation(body,structure=np.ones((7,7)))
    al2=np.where(near,al2,0)
    out=np.dstack([rgb3,al2*255]).astype(np.uint8)
    return Image.fromarray(out,'RGBA')
def find_triangle(im):
    a=np.array(im).astype(np.int32); r,g,b,al=a[...,0],a[...,1],a[...,2],a[...,3]
    mx=np.maximum(np.maximum(r,g),b); mn=np.minimum(np.minimum(r,g),b)
    m=(al>250)&(mx-mn<22)&(mx>115)&(mx<250)
    # must be surrounded by dark bandana: dark mask dilated
    dark=(al>250)&(mx<75)
    dk=Image.fromarray((dark*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(31))
    m=m&(np.array(dk)>0)
    from scipy import ndimage
    lab,nl=ndimage.label(m)
    if nl==0: return None
    best=None
    for i in range(1,nl+1):
        ys,xs=np.nonzero(lab==i)
        if len(xs)<150: continue
        w=xs.max()-xs.min()+1; h=ys.max()-ys.min()+1
        fill=len(xs)/(w*h)
        if w<25 or h<25 or w>140 or h>140 or fill<0.3: continue
        if best is None or len(xs)>best[0]: best=(len(xs),(int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())))
    return best[1] if best else None
LIME=(200,255,46)
def bake_mark(im,bb,band):
    import cv2
    x0,y0,x1,y1=bb; w=x1-x0; h=y1-y0; cx=(x0+x1)/2; cy=(y0+y1)/2
    a=np.array(im); rgb=np.ascontiguousarray(a[...,:3]); al=a[...,3]
    r,g,b=[a[...,i].astype(int) for i in range(3)]
    mx=np.maximum(np.maximum(r,g),b); mn=np.minimum(np.minimum(r,g),b)
    m=np.zeros(al.shape,np.uint8)
    win=(slice(max(0,y0-14),y1+15),slice(max(0,x0-14),x1+15))
    sub=((mx-mn<30)&(mx>70))[win]
    m[win]=sub.astype(np.uint8)*255
    m=cv2.dilate(m,np.ones((7,7),np.uint8))
    rgb=cv2.inpaint(rgb,m,9,cv2.INPAINT_TELEA)
    a[...,:3]=rgb; im=Image.fromarray(a,'RGBA')
    SS=4; pad=int(max(w,h)); X0,Y0=int(cx-pad),int(cy-pad); size=2*pad
    def P(x,y): return ((x-X0)*SS,(y-Y0)*SS)
    mk=Image.new('RGBA',(size*SS,size*SS),(0,0,0,0)); d2=ImageDraw.Draw(mk)
    W=max(w,h)*0.92; H=W*0.84; t=W*0.25
    top=(cx,cy-H*0.52); bl=(cx-W/2,cy+H*0.48); br=(cx+W/2,cy+H*0.48)
    inner_top=(cx,cy-H*0.52+t*1.95)
    poly=[top,br,(br[0]-t*1.15,br[1]),inner_top,(bl[0]+t*1.15,bl[1]),bl]
    d2.polygon([P(*p) for p in poly],fill=LIME+(255,))
    # printed-ink feel: slight vertical shading
    arr=np.array(mk).astype(np.float32); yy=np.linspace(0,1,arr.shape[0])[:,None]
    arr[...,:3]*= (1.02-0.16*yy)[...,None]; mk=Image.fromarray(np.clip(arr,0,255).astype(np.uint8),'RGBA')
    mk=mk.resize((size,size),Image.LANCZOS)
    im.alpha_composite(mk,(X0,Y0))
    return im,(cx,cy,W)
def paw_cap(im):
    # present pose: arm clipped at x=0 -> extend canvas left and paint rounded cap
    a=np.array(im); col=a[:,2,:].copy()
    ext=46; H=a.shape[0]
    new=np.zeros((H,a.shape[1]+ext,4),np.uint8); new[:,ext:]=a
    ys=np.nonzero(a[:,1,3]>200)[0]; y0,y1=ys.min(),ys.max(); cy=(y0+y1)/2; ry=(y1-y0)/2
    for x in range(ext):
        dx=(ext-x)/ext  # 1 at far left
        for y in range(int(y0)-2,int(y1)+3):
            v=((y-cy)/ (ry+1))**2 + (dx*1.0)**2
            if v<1:
                al=min(1,(1-v)*6)
                c=col[min(max(y,0),H-1)].astype(float)
                shade=1-0.10*dx
                new[y,x,:3]=np.clip(c[:3]*shade,0,255); new[y,x,3]=int(255*al*(c[3]/255))
    return Image.fromarray(new,'RGBA'), ext
info={}
for n in ['cat_neutral','cat_calm','cat_present','cat_focus_front','cat_confident','cat_wave','cat_curious','cat_impressed','cat_lookup']:
    if not os.path.exists(I+n+'.png'): continue
    im=decontam(n) if n in bboxes else Image.open(I+n+'.png').convert('RGBA')
    off=0
    if n=='cat_present': im,off=paw_cap(im)
    tri=find_triangle(im) if n not in ('cat_present','cat_focus_front') else None
    mk=None
    if tri:
        im,mk=bake_mark(im,tri,(28,29,33))
    im.save(I+n+'_f.png')
    info[n]={'size':im.size,'tri':tri,'mark':mk,'off':off}
    print(n,im.size,tri)
import json; json.dump({k:{kk:(list(map(float,vv)) if isinstance(vv,(tuple,list)) else vv) for kk,vv in v.items()} for k,v in info.items()},open(I+'info.json','w'))
