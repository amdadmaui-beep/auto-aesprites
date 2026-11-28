import json,numpy as np
from scipy.optimize import least_squares
back=json.load(open('../../.reanimate/ref6/avatar_back.json'))
fwd={round(r['t'],3):r for r in json.load(open('build/fit/avatar_track.json')) if r}
D=50.07
def R(rx,ry,rz):
    a,b,c=np.radians([rx,ry,rz])
    Rz=np.array([[np.cos(c),-np.sin(c),0],[np.sin(c),np.cos(c),0],[0,0,1]])
    Rx=np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])
    Ry=np.array([[np.cos(b),0,np.sin(b)],[0,1,0],[-np.sin(b),0,np.cos(b)]])
    return Rz@Rx@Ry
def cov(sc,rx,ry,rz):
    P=R(rx,ry,rz)[:2,:2]*sc
    return P@(np.eye(2)*(D/2)**2/4)@P.T
oldry=[(0.567,282),(0.6,294),(0.7,310),(0.8,321),(0.9,334),(1,340),(1.1,342),(1.17,344),(1.25,348),(1.35,352),(1.5,355),(1.65,357),(1.82,360),(2.95,360)]
def ryAt(t):
    if t>=2.95: return 360+22*np.sin(np.pi*(t-2.95)/.35) if t<3.3 else 360
    return float(np.interp(t,[a for a,_ in oldry],[b for _,b in oldry]))
rows=[]; prev=None
for k in range(17,130):
    t=round(k/30,3)
    r=back.get(str(t)) if t<=2.1 else fwd.get(t)
    if r is None: continue
    C=np.array([[r['cxx'],r['cxy']],[r['cxy'],r['cyy']]]); ev,vec=np.linalg.eigh(C); ang=np.degrees(np.arctan2(vec[1,1],vec[0,1]))
    ry=ryAt(t)
    def res(q):
        M=cov(q[0],q[1],ry,q[2]); n=C[0,0]**.5*10
        return [(M[0,0]-C[0,0])/n,(M[0,1]-C[0,1])/n,(M[1,1]-C[1,1])/n]+([(q[1]-prev[1])/150,(q[2]-prev[2])/150] if prev is not None else [])
    best=None
    for rx0 in [5,25,45,60]:
      for rz0 in [-60,-30,-10,0,10,30]:
        s=least_squares(res,[4*np.sqrt(ev[1])/D,rx0,rz0],bounds=([.1,0,-90],[20,80,90]))
        if best is None or s.cost<best.cost: best=s
    prev=best.x; rows.append([t,r['cx'],r['cy'],*[float(v) for v in best.x],ry])
    print(f"{t:.3f} c=({r['cx']:.0f},{r['cy']:.0f}) ang={ang:.0f} ax={4*ev[1]**.5:.0f}x{4*ev[0]**.5:.0f} sc={best.x[0]:.2f} rx={best.x[1]:.1f} rz={best.x[2]:.1f} ry={ry:.0f} cost={best.cost:.4f}")
json.dump(rows,open('build/fit/pose_avatar.json','w'))
