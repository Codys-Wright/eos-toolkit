import json,math,sys,time
sys.path.insert(0,'/Users/codywright/Development/eosdump')
FT=0.3048
# ---- room, read off the loaded model
CEIL=3.454; Z_AUD=-0.203; Z_STAGE=0.0; Z_LIFT=0.152
UP_Y=2.95; SEAM=-1.01; FLARE_END=-2.39; FRONT=-3.76; BACK=-13.81
ST_HW=30*FT/2; TH_HW=39*FT/2
PIPE=CEIL-0.20                      # pars hang 8 in under the ceiling
TRUSS=CEIL-0.25
AUD_1_3 = FRONT - 12*FT           # 6 ceiling tiles at 2 ft, measured off the stage lip
AUD_FAR = FRONT - 20*FT           # furthest row: a little past halfway into the audience
TGT=(0.0,-0.70,1.20)                # look at mid-stage, chest height
INWARD={32,33,34,35,36,37,38,39}
def aim(px,py,pz,tx,ty,tz,cap=65.0):
    dx,dy,dz=tx-px,ty-py,tz-pz
    n=math.sqrt(dx*dx+dy*dy+dz*dz); dx,dy,dz=dx/n,dy/n,dz/n
    th=math.degrees(math.acos(max(-1,min(1,-dz))))
    ph=math.degrees(math.atan2(-dx,dy)) if th>1e-6 else 0.0
    return round(min(th,cap),1), round(ph,1)
R=[]
FAN_OUT, FAN_IN = 12.0, 4.0        # outer / inner splay within a group of four
def fan_angles(n):
    if n==4: return [-FAN_OUT,-FAN_IN,FAN_IN,FAN_OUT]
    if n==2: return [-FAN_IN,FAN_IN]
    if n==3: return [-FAN_IN,0.0,FAN_IN]
    return [0.0]*n
def row(chs,xs,y,z,label,pan_inward=False,tilt=None,pan=None,fan=False):
    fa=fan_angles(len(chs)) if fan else [0.0]*len(chs)
    for i,(ch,x) in enumerate(zip(chs,xs)):
        if tilt is not None: th,ph=tilt,(pan or 0.0)
        else:
            tx = x*0.45 if pan_inward else x
            th,ph=aim(x,y,z,tx,TGT[1],TGT[2])
            if not pan_inward: ph=round(fa[i],1)
        R.append((ch,round(x,2),round(y,2),round(z,2),th,ph,label))

# ---- overhead pars
row([43,44,45],       [-0.55,0.0,0.55],                     SEAM, PIPE, "seam centre")
row([32,33,34,35],    [-4.20,-3.55,-2.90,-2.25],            SEAM, PIPE, "seam SR", pan_inward=True)
row([36,37,38,39],    [2.25,2.90,3.55,4.20],                SEAM, PIPE, "seam SL", pan_inward=True)
row([24,25,26,27],    [-1.15,-0.40,0.40,1.15],              -2.70, PIPE, "mid stage", fan=True)
row([7,8],            [-5.30,-4.70],                        FRONT, PIPE, "stage end SR")
row([20,21,22,23],    [-3.60,-2.90,-2.20,-1.50],            FRONT, PIPE, "stage end C-SR", fan=True)
row([28,29,30,31],    [1.50,2.20,2.90,3.60],                FRONT, PIPE, "stage end C-SL", fan=True)
row([9,10],           [4.70,5.30],                          FRONT, PIPE, "stage end SL")
row([3,4],            [-5.30,-4.70],                        AUD_1_3, PIPE, "audience SR")
row([11,12,13,14],    [-3.60,-2.90,-2.20,-1.50],            AUD_1_3, PIPE, "audience C-SR", fan=True)
row([15,16,17,18],    [1.50,2.20,2.90,3.60],                AUD_1_3, PIPE, "audience C-SL", fan=True)
row([5,6],            [4.70,5.30],                          AUD_1_3, PIPE, "audience SL")
row([1,2],            [-5.00,5.00],                         AUD_FAR, PIPE, "audience far single")
row([40,41],          [-3.60,-2.90],                        1.80, PIPE, "upstage SR")
row([47,48],          [2.90,3.60],                          1.80, PIPE, "upstage SL")
# drum-kit corners, aimed at the kit itself
for ch,x in ((42,-2.40),(46,2.40)):
    th,ph=aim(x,1.20,PIPE, 0.0,0.60,Z_LIFT+0.90)
    R.append((ch,x,1.20,round(PIPE,2),th,ph,"drum corner"))
# ---- movers
row([80,81,82,83],    [-3.00,-1.00,1.00,3.00],              2.20, TRUSS, "OH truss")
row([85,86,87,88],    [-3.80,-1.30,1.30,3.80],              -1.30, Z_STAGE+0.02, "floor beam", tilt=180.0)
row([98],             [0.0],                                -1.30, Z_STAGE+0.02, "floor beam", tilt=180.0)
# ---- slimpars on the upstage wall, aimed downstage
for ch,x,z in ((50,-2.00,1.90),(51,-2.00,2.40),(52,2.00,2.40),(53,2.00,1.90)):
    R.append((ch,x,2.85,z,90.0,180.0,"upstage wall"))
# ---- strips and haze
row([90],[-3.50],2.85,Z_LIFT+0.05,"uplight - TV SR",  tilt=180.0)
row([91],[ 0.00],2.85,Z_LIFT+0.05,"uplight - TV centre",tilt=180.0)
row([92],[ 3.50],2.85,Z_LIFT+0.05,"uplight - TV SL",  tilt=180.0)
row([93],[-3.00],FRONT-0.12,Z_AUD+0.05,"footlight",tilt=180.0)
row([94],[ 3.00],FRONT-0.12,Z_AUD+0.05,"footlight",tilt=180.0)
row([95],[-4.90],-2.06,Z_STAGE+0.05,"uplight - flare TV SR",tilt=180.0)
row([96],[ 4.90],-2.06,Z_STAGE+0.05,"uplight - flare TV SL",tilt=180.0)
row([97],[ 0.00],FRONT-0.12,Z_AUD+0.05,"footlight",tilt=180.0)
row([100],[-4.20],2.60,Z_LIFT+0.10,"haze",tilt=0.0)
row([101],[4.20], 2.60,Z_LIFT+0.10,"haze",tilt=0.0)

print(f"{len(R)} fixtures   pipe z {PIPE:.2f}  ceiling {CEIL:.2f}  audience 1/3 at y {AUD_1_3:.2f}")
def hw(y):
    if y>=SEAM: return ST_HW
    if y>=FLARE_END: return ST_HW+(SEAM-y)
    return TH_HW
bad=[(c,x,y) for c,x,y,z,th,ph,l in R if abs(x)>hw(y)+1e-6]
print("outside the room:", bad or "none")
for c,x,y,z,th,ph,l in R[:6]+R[-6:]:
    print(f"  ch{c:>3} ({x:6.2f},{y:6.2f},{z:5.2f})  tilt {th:5.1f} pan {ph:7.1f}   {l}")
json.dump(R,open('/tmp/rig_plan.json','w'))
if "--send" in sys.argv:
    import eosdump as E
    conn=E.Conn("127.0.0.1",3032); fails=[]
    def snd(s):
        conn.send("/eos/newcmd",s+"#"); time.sleep(0.13)
        e=""
        for a,g in conn.recv():
            if a=="/eos/out/cmd" and g: e=g[0]
        if "Error" in e: fails.append((s,e))
    for c,x,y,z,th,ph,l in R:
        snd(f"Chan {c} Position {x} / {y} / {z}")
        snd(f"Chan {c} Orientation {th} / 0 / {ph}")
    print(f"\nsent {len(R)*2} commands, {len(fails)} errors")
    for s,e in fails[:6]: print("  !!",s,"->",e[:70])
