import json,sys
sys.path.insert(0,'.')
FPS=24000/1001
snap=lambda t: round(round(t*FPS)/FPS,6)
src={"clip1":"c1_words.json","clip2":"c2_words.json"}
import importlib.util
spec=importlib.util.spec_from_file_location("e","edit.py")
txt=open("edit.py").read()
ns={"__file__":"edit.py"}; exec(txt.split("# Eye height")[0].replace("import cv2, numpy as np",""),ns)
for name in ("clip1","clip2"):
    W=json.load(open(src[name])); out=[]; t=0
    for a,b,c,m in ns["CLIPS"][name]:
        a,b=snap(a),snap(b)
        for s,e,w in W:
            mid=(s+e)/2
            if a<=mid<b: out.append((round(t+max(s,a)-a,2),round(t+min(e,b)-a,2),w.strip()))
        t+=b-a
    json.dump(out,open(name+"_outwords.json","w"))
    print(name,len(out)," ".join(f"{i}:{w[2]}" for i,w in enumerate(out)))
