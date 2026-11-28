# usage: loop2.py KEY POLARITY(dark|bright) ITERS t0:t1[,t0:t1...]   -> build/lfit/KEY.json (fix keys)
import cv2,numpy as np,json,subprocess,sys
KEY,POL,N=sys.argv[1],sys.argv[2],int(sys.argv[3])
segs=[[round(k/30,3) for k in range(round(float(a)*30),round(float(b)*30)+1)] for a,b in (x.split(':') for x in sys.argv[4].split(','))]
T=[t for s in segs for t in s]; json.dump(T,open('build/lfit/times.json','w'))
cap=cv2.VideoCapture('../../.reanimate/ref6/ref.mp4'); fr={}; k=0
while True:
    ok,f=cap.read()
    if not ok: break
    t=round(k/30,3)
    if t in T: fr[t]=cv2.resize(f,(360,640))
    k+=1
def stats(img):
    L=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY).astype(np.float32)
    if POL=='dark': m=L<cv2.GaussianBlur(L,(0,0),18)-28
    else: m=L>70
    ys,xs=np.nonzero(m)
    if len(xs)<200: return None
    return np.array([np.percentile(xs,50),np.percentile(ys,50),np.percentile(xs,92)-np.percentile(xs,8),np.percentile(ys,92)-np.percentile(ys,8)])*2
fix={t:[0,0,1] for t in T}
for it in range(N+1):
    json.dump([[t,*fix[t]] for t in T],open(f'build/lfit/{KEY}.json','w'))
    if it==N: break
    subprocess.run(['node','build/lfit/shots.mjs',KEY,f'build/lfit/{KEY}.json','build/lfit/times.json'],check=True)
    err=[]; new={}
    for t in T:
        a=stats(fr[t]); b=stats(cv2.imread(f'build/lfit/o_{t:.3f}.png')); dx,dy,s=fix[t]
        if a is None or b is None: new[t]=[dx,dy,s]; continue
        ds=float(np.clip(np.sqrt((a[2]*a[3])/(b[2]*b[3])),.85,1.18))
        if not .7<=s*ds<=1.4: ds=1.0
        C=np.array([360,640]); bc=C+ds*(b[:2]-C); d=(a[:2]-bc)*.8
        new[t]=[ds*dx+d[0],ds*dy+d[1],s*ds]; err.append(np.hypot(*(a[:2]-b[:2])))
    for seg in segs:
        A=np.array([new[t] for t in seg]); w=np.array([1,2,3,2,1])/9
        for c in range(3): A[:,c]=np.convolve(np.pad(A[:,c],2,mode='edge'),w,'valid')
        for t,row in zip(seg,A): fix[t]=[float(v) for v in row]
    print('iter',it,'err',round(float(np.mean(err)),1),flush=True)
