import json,math,sys
B=sys.argv[1]; STAGE_W_FT=float(sys.argv[2]) if len(sys.argv)>2 else 30.0
STAGE_D_FT=float(sys.argv[3]) if len(sys.argv)>3 else 22.0
FT=0.3048; IN=FT/12
PJ=f"{B}/a3d/Scene/Primitive.json"
prim=json.load(open(PJ)); items=prim["items"]
def named(n): return [i for i in items if i["obj"].get("name")==n]

# ---- every dimension declared in FEET; scale is back-calculated from the mesh
THEATER_W = 39.0
STAGE_W   = STAGE_W_FT
LIFT_D    = 13.0                    # 13 ft from the upstage wall to the seam
AUD_D     = 33.0
ALCOVE_D  = 7.0
ROOM_H    = 12.0
FLARE_W   = (THEATER_W-STAGE_W)/2   # per side
FLARE_D   = FLARE_W                 # 45 degrees
UP_Y   = 2.95
SEAM   = UP_Y - LIFT_D*FT
DIAG_DN= SEAM - FLARE_D*FT
FRONT  = UP_Y - STAGE_D_FT*FT        # stage depth measured from the upstage wall, not the flare
BACK   = FRONT - AUD_D*FT
DEEP   = BACK - ALCOVE_D*FT
Z_STAGE=0.0; Z_AUD=-8*IN; Z_LIFT=6*IN; Z_CEIL=Z_AUD+ROOM_H*FT
print(f"stage {STAGE_D_FT:.0f} ft deep, {STAGE_W:.0f} ft wide -> flare {FLARE_W:.1f} ft per side over {FLARE_D:.1f} ft of depth")
print(f"  seam {SEAM:.2f}  flare ends {DIAG_DN:.2f}  stage front {FRONT:.2f}  back {BACK:.2f}  alcove {DEEP:.2f}")

def put(name,size_ft,pos,eulz=0.0):
    """size_ft: (x,y,z) in FEET, 0 = leave that axis alone (flat planes)."""
    for it in named(name):
        o=it["obj"]; b=o["local_bounds"]["size"]
        sc={}
        for ax,want in zip("xyz",size_ft):
            if b[ax]>0.001 and want>0:
                sc[ax]=(want*FT)/b[ax]
            else:
                sc[ax]=o["local"]["scale"][ax] if b[ax]<=0.001 else o["local"]["scale"][ax]
        a=math.radians(eulz); q={"w":math.cos(a/2),"x":0,"y":0,"z":math.sin(a/2)}
        for k in ("local","world"):
            o[k]["pos"]={"x":pos[0],"y":pos[1],"z":pos[2]}
            o[k]["scale"]=dict(sc)
            if eulz is not None:
                o[k]["eulers"]={"x":o[k]["eulers"]["x"],"y":0,"z":eulz}
                ex=math.radians(o[k]["eulers"]["x"])
                cz,sz=math.cos(a/2),math.sin(a/2); cx,sx=math.cos(ex/2),math.sin(ex/2)
                o[k]["quat"]={"w":cz*cx,"x":cz*sx,"y":sz*sx,"z":sz*cx}
        for ax in "xyz": o["size"][ax]=b[ax]*sc[ax]
        dz=o["size"]["z"]/2 if o["size"]["z"]>0.001 else 0
        o["center"]={"x":pos[0],"y":pos[1],"z":pos[2]+dz}

TH_HW=THEATER_W*FT/2; ST_HW=STAGE_W*FT/2
H=ROOM_H; H_STAGE=(Z_CEIL-Z_STAGE)/FT; H_LIFT=(Z_CEIL-Z_LIFT)/FT
put("Floor - Audience",(THEATER_W,AUD_D,0),(0,(BACK+FRONT)/2,Z_AUD))
put("Stage - Downstage",(THEATER_W,(FRONT-SEAM)/-FT*-1,0),(0,(FRONT+SEAM)/2,Z_STAGE))
put("Stage - Upstage Lift",(STAGE_W,LIFT_D,0),(0,(SEAM+UP_Y)/2,Z_LIFT))
put("Floor - Alcove",(20.0,ALCOVE_D,0),(2.90,(DEEP+BACK)/2,Z_AUD))
put("Ceiling",(THEATER_W,(UP_Y-DEEP)/FT,0),(0,(UP_Y+DEEP)/2,Z_CEIL))
put("Wall - Upstage",(STAGE_W,0,H_LIFT),(0,UP_Y,Z_LIFT))
put("Wall - Stage Side L",(0,LIFT_D,H_STAGE),( ST_HW,(SEAM+UP_Y)/2,Z_STAGE))
put("Wall - Stage Side R",(0,LIFT_D,H_STAGE),(-ST_HW,(SEAM+UP_Y)/2,Z_STAGE))
FL=math.hypot(FLARE_W,FLARE_D)
put("Wall - Flare SR",(FL,0,H_STAGE),(-(TH_HW+ST_HW)/2,(SEAM+DIAG_DN)/2,Z_STAGE), 45.0)
put("Wall - Flare SL",(FL,0,H_STAGE),( (TH_HW+ST_HW)/2,(SEAM+DIAG_DN)/2,Z_STAGE),-45.0)
put("Wall - Stage Left",(0,(DIAG_DN-DEEP)/FT,H),( TH_HW,(DEEP+DIAG_DN)/2,Z_AUD))
put("Wall - Stage Right",(0,(DIAG_DN-BACK)/FT,H),(-TH_HW,(BACK+DIAG_DN)/2,Z_AUD))
put("Face - Riser",(STAGE_W,0,(Z_LIFT-Z_STAGE)/FT),(0,SEAM,Z_STAGE))
put("Face - Stage Lip",(THEATER_W,0,(Z_STAGE-Z_AUD)/FT),(0,FRONT,Z_AUD))

# ---- alcove / sound booth / closet, all keyed off the new back wall
ALC_W=20.0; BOOTH_W=13.0; CLOSET_W=7.0
X_IN = TH_HW - ALC_W*FT                    # inner edge of the alcove
X_CLO = TH_HW - CLOSET_W*FT                # booth / closet divider
put("Wall - House Back",((X_IN+TH_HW)/FT-ALC_W+0.0 if False else (X_IN+TH_HW)/1,0,H),(0,0,0)) if False else None
put("Wall - House Back",((TH_HW+X_IN)/FT,0,H),(((-TH_HW)+X_IN)/2,BACK,Z_AUD),180.0)
put("Wall - Alcove Back",(ALC_W,0,H),((X_IN+TH_HW)/2,DEEP,Z_AUD),180.0)
put("Wall - Alcove Step",(0,ALCOVE_D,H),(X_IN,(DEEP+BACK)/2,Z_AUD),180.0)
put("Wall - Booth Front",(BOOTH_W,0,ROOM_H/2),((X_IN+X_CLO)/2,BACK,Z_AUD),180.0)
put("Wall - Closet Front",(CLOSET_W,0,H),((X_CLO+TH_HW)/2,BACK,Z_AUD),180.0)
put("Wall - Closet Divider",(0,ALCOVE_D,H),(X_CLO,(DEEP+BACK)/2,Z_AUD),0.0)

json.dump(prim,open(PJ,"w"),indent=1)
print("\n--- what the flare would look like at other stage widths ---")
for w in (27,30,33,36):
    f=(THEATER_W-w)/2
    print(f"  stage {w} ft -> {f:.1f} ft inward per side, diagonal {math.hypot(f,f):.1f} ft long")
