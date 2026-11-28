import json,sys,numpy as np
from scipy.optimize import least_squares
src=open('build/fit/solve.py').read().split('rows=[]')[0]; exec(src)
L=float(sys.argv[1]); O=np.array([360.,640.])
ph=np.linspace(0,2*np.pi,48,endpoint=False); circ=np.stack([np.cos(ph),np.sin(ph),np.zeros_like(ph)])*D/2
def proj_cov(sx,sy,sc,rx,ry,rz):
    w=R(rx,ry,rz)@circ*sc; z=w[2]; f=L/(L-z)
    x=O[0]+(sx+w[0]-O[0])*f; y=O[1]+(sy+w[1]-O[1])*f
    return np.cov(np.vstack([x,y]),bias=True)/2   # boundary->filled
prev=json.load(open('build/fit/pose_final.json'))
RZK=[(1.17,-2),(1.5,0),(1.7,5),(1.85,14),(2.0,20),(2.3,22),(2.45,24),(2.6,22)]
rzfix=lambda t: float(np.interp(t,[a for a,_ in RZK],[b for _,b in RZK])) if 1.17<=t<=2.6 else None; out=[]; last=None
for row in prev:
    t,sx,sy,sc0,rx0,ry,rz0=row
    r=back.get(str(t)) if t<=2.1 else fwd.get(t)
    C=np.array([[r['cxx'],r['cxy']],[r['cxy'],r['cyy']]])
    fz=rzfix(t)
    def res(q):
        M=proj_cov(sx,sy,q[0],q[1],ry,q[2] if fz is None else fz); n=C[0,0]**.5*10
        return [(M[0,0]-C[0,0])/n,(M[0,1]-C[0,1])/n,(M[1,1]-C[1,1])/n]+([(q[1]-last[1])/150,(q[2]-last[2])/150] if last is not None else [])
    best=None
    for a in [rx0, max(0,rx0-15), rx0+10]:
        for c in [rz0, rz0-15, rz0+15]:
            s=least_squares(res,[sc0,a,c],bounds=([.1,0,-90],[20,85,90]))
            if best is None or s.cost<best.cost: best=s
    last=best.x
    if fz is not None: best.x[2]=fz
    if t<1.2: best.x[1]=rx0; best.x[2]=rz0   # keep the yaw-dominated stretch as solved before
    out.append([t,sx,sy,*[float(v) for v in best.x[:1]],float(best.x[1]),ry,float(best.x[2])])
A=np.array(out); S=A.copy(); w=np.array([1,4,6,4,1])/16
for c in [3,4,6]:
    p=np.pad(A[:,c],2,mode='edge'); S[:,c]=np.convolve(p,w,'valid')
for r in S[::4]: print(' '.join(f'{v:.2f}' for v in r))
json.dump(S.round(3).tolist(),open(f'build/fit/pose_L{int(L)}.json','w'))
