from PIL import Image, ImageDraw
import numpy as np, math, sys
from scipy import ndimage as ndi
S=sys.argv[1]
im=Image.open('/mnt/user-data/uploads/WhatsApp_Image_2026-10-27_at_16_43_53.jpeg').convert('RGB')
W,H=im.size; k=W/1932
crop=im.crop((int(380*k),int(540*k),int(1160*k),int(1050*k)))
a=np.asarray(crop).astype(float); sat=a.max(2)-a.min(2)
alpha=np.clip((sat-45)/45,0,1); m=ndi.binary_opening(alpha>0.5,iterations=1)
lab,n=ndi.label(m); sizes=ndi.sum(m,lab,range(1,n+1)); keep=np.zeros_like(m)
for i,s in enumerate(sizes):
    if s<800: continue
    ys,xs=np.where(lab==i+1)
    if xs.max()<0.28*m.shape[1] and ys.max()<0.32*m.shape[0]: continue
    keep|=(lab==i+1)
alpha=np.where(ndi.binary_dilation(keep,iterations=1),alpha,0); alpha=ndi.gaussian_filter(alpha,0.7)
inner=ndi.binary_erosion(keep,iterations=3); dist,(iy,ix)=ndi.distance_transform_edt(~inner,return_indices=True); rgb=a[iy,ix]
logo=Image.fromarray(np.dstack([rgb,alpha*255]).astype(np.uint8),'RGBA')
logo=logo.crop(logo.getchannel('A').point(lambda v:255 if v>30 else 0).getbbox())
SS=4; cw,ch=300*SS,260*SS; can=Image.new('RGBA',(cw,ch),(0,0,0,0)); d=ImageDraw.Draw(can)
cx,cy=150*SS,165*SS; rx,ry=135*SS,105*SS; PUR=(132,44,156,255); WHT=(250,246,252,255); EDGE=(88,26,108,255); nw=6
for i in range(nw):
    a0=math.pi+i*math.pi/nw; a1=math.pi+(i+1)*math.pi/nw
    d.polygon([(cx,cy)]+[(cx+rx*math.cos(a0+(a1-a0)*t/12),cy+ry*math.sin(a0+(a1-a0)*t/12)) for t in range(13)],fill=PUR if i%2==0 else WHT)
for i in range(nw):
    x0=cx+rx*math.cos(math.pi+i*math.pi/nw); x1=cx+rx*math.cos(math.pi+(i+1)*math.pi/nw); rr=abs(x1-x0)/2
    d.pieslice((min(x0,x1),cy-rr*0.7,max(x0,x1),cy+rr*0.7),0,180,fill=PUR if i%2==0 else WHT)
d.arc((cx-rx,cy-ry,cx+rx,cy+ry),180,360,fill=EDGE,width=5*SS)
for i in range(nw):
    x0=cx+rx*math.cos(math.pi+i*math.pi/nw); x1=cx+rx*math.cos(math.pi+(i+1)*math.pi/nw); rr=abs(x1-x0)/2
    d.arc((min(x0,x1),cy-rr*0.7,max(x0,x1),cy+rr*0.7),0,180,fill=EDGE,width=4*SS)
d.line([(cx,cy-ry),(cx,cy-ry-22*SS)],fill=EDGE,width=7*SS); d.line([(cx,cy+8*SS),(cx,cy+88*SS)],fill=(205,198,214,255),width=9*SS); d.line([(cx,cy+88*SS),(cx,cy+96*SS)],fill=EDGE,width=9*SS)
can=can.resize((300,260),Image.LANCZOS).rotate(24,resample=Image.BICUBIC,expand=True)
canvas=Image.new('RGBA',(logo.width+90,logo.height+170),(0,0,0,0)); canvas.alpha_composite(logo,(60,150)); canvas.alpha_composite(can,(0,0))
canvas=canvas.crop(canvas.getchannel('A').point(lambda v:255 if v>30 else 0).getbbox()); canvas.save(S+'logo_clean.png')
def sticker(img,px=10):
    pad=px+14; big=Image.new('RGBA',(img.width+pad*2,img.height+pad*2),(0,0,0,0)); big.alpha_composite(img,(pad,pad))
    A=np.asarray(big.getchannel('A')).astype(float)/255; dil=ndi.gaussian_filter((ndi.maximum_filter(A,size=px*2+1)>0.3).astype(float),1.2)
    out=Image.new('RGBA',big.size,(0,0,0,0)); sh=Image.new('RGBA',big.size,(0,0,0,0)); sh.putalpha(Image.fromarray((ndi.gaussian_filter(dil,10)*120).astype(np.uint8))); out.alpha_composite(sh,(0,8))
    white=Image.new('RGBA',big.size,(255,250,242,255)); white.putalpha(Image.fromarray((dil*255).astype(np.uint8))); out.alpha_composite(white); out.alpha_composite(big); return out
st=sticker(canvas); st.save(S+'logo_sticker.png'); print('sticker',st.size)
