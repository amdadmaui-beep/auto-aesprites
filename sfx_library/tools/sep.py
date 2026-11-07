# REPET-SIM: the music bed repeats, the sound effects don't. Median over the most similar frames = music;
# the soft-masked remainder = foreground (SFX). Writes <name>_fg.wav and <name>_bg.wav.
import sys, librosa, numpy as np, soundfile as sf
name=sys.argv[1]; margin=float(sys.argv[2]) if len(sys.argv)>2 else 3
y,sr=librosa.load(name+'.wav',sr=48000,mono=False)
n_fft,hop=int(sys.argv[3]) if len(sys.argv)>3 else 4096,(int(sys.argv[3])//4 if len(sys.argv)>3 else 1024)
D=[librosa.stft(c,n_fft=n_fft,hop_length=hop) for c in y]; S=np.abs(D[0])+np.abs(D[1])
Sf=librosa.decompose.nn_filter(S,aggregate=np.median,metric='cosine',width=int(librosa.time_to_frames(1.0,sr=sr,hop_length=hop)))
Sf=np.minimum(S,Sf)
mf=librosa.util.softmask(S-Sf,margin*Sf,power=2); mb=librosa.util.softmask(Sf,(S-Sf),power=2)
fg=np.stack([librosa.istft(d*mf,hop_length=hop,length=y.shape[1]) for d in D],1)
bg=np.stack([librosa.istft(d*mb,hop_length=hop,length=y.shape[1]) for d in D],1)
sf.write(name+'_fg.wav',fg,sr); sf.write(name+'_bg.wav',bg,sr)
r=lambda x:20*np.log10(np.sqrt((x**2).mean())+1e-9); print(name,'mix %.1f fg %.1f bg %.1f dB'%(r(y.T),r(fg),r(bg)))
