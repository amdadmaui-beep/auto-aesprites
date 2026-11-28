import json,re,sys
L=sys.argv[1]; pf=json.load(open(f'build/fit/pose_L{L}.json'))
def bump(t):
    return float(np.interp(t,[1.2,1.45,1.75,2.05],[0,1,1,0]))
import numpy as np
meas=[[r[0],r[1],r[2],0,r[3],r[4]+10*bump(r[0]),r[5],r[6]] for r in pf]
s=open('index.html').read()
s=re.sub(r"const PM=\[.*?\];\n","const PM="+json.dumps(meas,separators=(',',':'))+";\n",s,count=1,flags=re.S)
s=re.sub(r"let LENS=window.LENS\|\|\d+",f"let LENS=window.LENS||{L}",s)
open('index.html','w').write(s)
