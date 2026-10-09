"""Four everyday Lowcar food shops using the approved pastel architectural kit."""
from pathlib import Path
import importlib.util
import json
import hashlib

spec=importlib.util.spec_from_file_location("lowcar_batch_parts",Path(__file__).with_name("build_building_batch_01.py"))
b=importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
a=b.a
box,rod,mesh=a.box,a.rod,a.mesh
a.ASSET=a.PROJECT/"assets/models/buildings/batch_11"
a.SOURCE=a.ASSET/"source"
a.PREVIEWS=a.ASSET/"previews"
for folder in (a.ASSET,a.SOURCE,a.PREVIEWS):
    folder.mkdir(parents=True,exist_ok=True)
for folder in (a.SOURCE,a.PREVIEWS):
    (folder/".gdignore").write_text("")


def rectangle(w,d,label="Wall"):
    return [a.Wall(label+"_front",(-w/2,-d/2),(w/2,-d/2),(0,-1)),
            a.Wall(label+"_right",(w/2,-d/2),(w/2,d/2),(1,0)),
            a.Wall(label+"_rear",(w/2,d/2),(-w/2,d/2),(0,1)),
            a.Wall(label+"_left",(-w/2,d/2),(-w/2,-d/2),(-1,0))]


def sign(wall,u,z,width,words,size=.34):
    wall.part("Shop_sign",u,z,width,.48,"teal",.14,.14,.025)
    a.text("Shop_letters",words,wall.point(u,z,.22),size)


def flat_roof(w,d,z,color,height=.40):
    b.cornice(w,d,z,True)
    a.parapet("Roof_parapet",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],z+.14,color,height)


def gable(w,d,z,peak,cx=0):
    half=w/2
    # Closed triangular end slabs preserve stable outward normals at both ends.
    for end in (-1,1):
        tri=[(cx-half,end*d/2,z),(cx+half,end*d/2,z),(cx,end*d/2,peak)]
        tri += [(x,y-end*.12,zz) for x,y,zz in tri]
        mesh("Cream_gable_end",tri,[(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)],"cream")
    over=.17
    for side in (-1,1):
        verts=[(cx+side*half,-d/2-over,z+.03),(cx,-d/2-over,peak+.06),
               (cx,d/2+over,peak+.06),(cx+side*half,d/2+over,z+.03)]
        # Closed roof slabs give the importer consistent outward normals.
        verts += [(x,y,z-.10) for x,y,z in verts]
        mesh("Blue_gable_roof",verts,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],"roof")
        for y in (-d/2-over,d/2+over):
            rod("White_gable_fascia",(cx+side*half,y,z+.02),(cx,y,peak+.08),.13,"cream")
        rod("White_eave",(cx+side*half,-d/2-over,z),(cx+side*half,d/2+over,z),.13,"cream")
    rod("White_ridge",(cx,-d/2-over,peak+.07),(cx,d/2+over,peak+.07),.13,"cream")


def taco_corner():
    w,d,h=11.6,9.4,3.15
    outline=[(-5.8,-4.7),(-.7,-4.7),(-.7,.5),(5.8,.5),(5.8,4.7),(-5.8,4.7)]
    a.prism("L_foundation",outline,0,.15,"stone",.025)
    a.prism("L_roof_plate",outline,h-.09,h+.15,"cream",.025)
    walls=[a.Wall("Taco_front",outline[0],outline[1],(0,-1)),
           a.Wall("Taco_inner_side",outline[1],outline[2],(1,0)),
           a.Wall("Taco_terrace_front",outline[2],outline[3],(0,-1)),
           a.Wall("Taco_right",outline[3],outline[4],(1,0)),
           a.Wall("Taco_rear",outline[4],outline[5],(0,1)),
           a.Wall("Taco_left",outline[5],outline[0],(-1,0))]
    for i,wall in enumerate(walls):
        if i==0:
            bays=[(2.55,3.72,.62,2.67,"shop")]
        elif i==1:
            bays=[(1.67,2.19,.63,2.67,"shop"),(4.18,1.10,.15,2.67,"door")]
        elif i==2:
            bays=[(2.14,2.75,.63,2.67,"shop"),(5.29,1.13,.15,2.67,"door")]
        elif i==4:
            bays=[(wall.length*.31,1.04,.15,2.60,"door"),(wall.length*.73,1.27,1.05,2.60,"window")]
        else:
            bays=[(wall.length*.54,1.25,1.05,2.60,"window")]
        wall.row(.15,h-.09,bays,"coral_dark")
        wall.part("Cream_base",wall.length/2,.30,wall.length,.28,"cream",.18,.015)
    walls[0].part("Mint_front_canopy",2.55,2.94,5.20,.17,"mint_dark",.93,.28,.025)
    walls[2].awning(3.25,6.10,2.98,.91)
    sign(walls[0],2.55,3.36,4.40,"TACO CORNER",.35)
    a.parapet("Low_L_roof_edge",outline,h+.15,"coral_dark",.21)
    box("Rear_kitchen",(2.75,2.60,h+.75),(4.15,3.05,1.20),"mint_dark",.035)
    box("Kitchen_cream_cap",(2.75,2.60,h+1.42),(4.41,3.31,.17),"cream",.025)
    box("Terrace_paving",(2.55,-2.1,.035),(6.5,5.2,.07),"stone")
    for cx,width in ((.75,2.90),(5.0,1.60)):
        box("Terrace_front_wall",(cx,-4.7,.42),(width,.18,.84),"mint",.02)
        box("Front_wall_cap",(cx,-4.7,.88),(width+.05,.29,.12),"cream",.015)
    box("Terrace_side_wall",(5.8,-2.1,.42),(.18,5.2,.84),"mint",.02)
    box("Side_wall_cap",(5.8,-2.1,.88),(.29,5.25,.12),"cream",.015)
    for x,y in ((1.03,-2.01),(4.38,-1.48)):
        box("Terrace_table",(x,y,.85),(.89,.89,.12),"cream",.035)
        rod("Table_pedestal",(x,y,.09),(x,y,.79),.12,"teal")
        for side in (-1,1):
            box("Terrace_stool",(x+side*.65,y,.43),(.35,.43,.14),"mint_dark",.025)
            rod("Stool_leg",(x+side*.65,y,.08),(x+side*.65,y,.37),.10,"teal")


def neighborhood_restaurant():
    w,d,h=10.2,9.4,3.3
    front=b.frame(w,d,3,"coral",height=h)[0]
    front.row(.15,h-.09,[(2.49,3.37,.46,2.83,"shop"),(5.10,1.30,.15,2.83,"door"),(7.71,3.37,.46,2.83,"shop")],"coral_dark")
    front.part("Cream_restaurant_canopy",w/2,2.98,w+.16,.21,"cream",.99,.34,.025)
    sign(front,w/2,3.14,7.74,"NEIGHBORHOOD TABLE",.40)
    sill,head=h+.33,2*h-.57
    front.row(h+.15,2*h-.09,[(u,1.50,sill,head,"window") for u in (2.55,7.65)],"coral")
    for u in (2.55,7.65):
        b.gallery(front,u,h+.18,2.54,.93,"scroll")
        b.shutters(front,u,sill,1.50,head-sill,"blue_dark")
    sill,head=2*h+.66,3*h-.59
    front.row(2*h+.15,3*h-.09,[(u,1.32,sill,head,"window") for u in (2.05,5.10,8.15)],"coral")
    for u in (2.05,8.15):
        b.shutters(front,u,sill,1.32,head-sill,"blue_dark")
    for u in (.19,w-.19):
        front.part("Cream_corner_trim",u,5.0,.30,9.55,"cream",.21,.05)
    b.cornice(w,d,3*h,True)
    # Low railing is set back from the cornice, making a modest roof dining terrace.
    terrace=[(-4.10,-2.80),(4.10,-2.80),(4.10,3.0),(-4.10,3.0)]
    a.parapet("Setback_roof_terrace",terrace,3*h+.14,"cream",.48)
    box("Rear_roof_kitchen",(-2.32,3.28,3*h+.69),(3.0,2.09,1.09),"coral_dark",.035)
    box("Kitchen_roof_cap",(-2.32,3.28,3*h+1.31),(3.24,2.33,.15),"cream",.025)
    for x,y in ((-2.37,-1.42),(2.39,-1.42),(2.39,1.38)):
        box("Roof_table",(x,y,3*h+.93),(1.08,.93,.12),"cream",.035)
        rod("Table_stem",(x,y,3*h+.15),(x,y,3*h+.87),.12,"teal")
        for side in (-1,1):
            box("Roof_stool",(x+side*.74,y,3*h+.54),(.37,.43,.14),"blue_dark",.025)
    a.planter("Roof_planter",(-3.59,1.99,3*h+.15),.36,.49)


def city_food_hall():
    w,d,h=16.0,11.0,3.50
    front,right,rear,left=rectangle(w,d,"FoodHall")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Upper_floor_left",(-4.95,0,h),(6.10,d,.18),"cream")
    box("Upper_floor_right",(4.95,0,h),(6.10,d,.18),"cream")
    box("Roof_plate",(0,0,2*h),(w,d,.18),"cream")
    front.row(.15,2*h-.09,[(3.01,4.40,.62,6.41,"shop"),(8.00,3.14,.15,6.41,"door"),(12.99,4.40,.62,6.41,"shop")],"yellow")
    for u in (3.01,12.99):
        for offset in (-.74,.74):
            front.part("Grouped_window_mullion",u+offset,3.52,.12,5.65,"cream",.09,-.07)
        front.part("Upper_floor_window_band",u,h,4.37,.19,"cream",.11,-.07)
    front.part("Entry_transom",8.0,2.83,3.02,.14,"cream",.12,-.07)
    for u in (5.44,10.56):
        front.part("Tall_entry_pier",u,3.58,.37,6.62,"cream",.28,.08,.015)
    front.part("Broad_entrance_canopy",8.0,3.06,4.91,.22,"cream",1.17,.42,.03)
    sign(front,8.0,3.51,4.66,"FOOD HALL",.42)
    for wall in (right,rear,left):
        for level in (0,1):
            if level==0:
                bays=[(wall.length*.52,1.20,.15,2.88,"door")] if wall is rear else [(wall.length*f,1.46,1.08,2.91,"window") for f in (.25,.70)]
            else:
                bays=[(wall.length*f,1.52,h+.77,2*h-.63,"window") for f in (.22,.49,.76)]
            wall.row(level*h+.15,(level+1)*h-.09,bays,"yellow")
        wall.part("Cream_base",wall.length/2,.30,wall.length,.28,"cream",.20,.015)
    for u in (.20,w-.20):
        front.part("Cream_corner_pier",u,3.60,.32,6.66,"cream",.23,.045)
    b.cornice(w,d,2*h,False)
    # Three low sawtooth roof segments occupy only the rear half of the hall.
    base=2*h+.17
    for y0 in (.55,2.05,3.55):
        y1=y0+1.50
        peak=base+.73
        verts=[(x,y,z) for x in (-w/2,w/2) for y,z in ((y0,base),(y1,peak),(y1,base))]
        mesh("Sawtooth_roof_volume",verts,[(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)],"yellow_dark")
        top=[(-w/2-.10,y0-.04,base+.06),(w/2+.10,y0-.04,base+.06),(w/2+.10,y1+.04,peak+.06),(-w/2-.10,y1+.04,peak+.06)]
        slab=top+[(x,y,z-.10) for x,y,z in top]
        mesh("Blue_sawtooth_roof_slab",slab,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],"roof")
        for x in (-w/2-.10,w/2+.10):
            rod("White_sawtooth_fascia",(x,y0-.04,base+.06),(x,y1+.04,peak+.06),.11,"cream")
        rod("Sawtooth_ridge",(-w/2-.13,y1+.04,peak+.08),(w/2+.13,y1+.04,peak+.08),.12,"cream")


def paired_semi_detached():
    w,d,h=12.0,9.4,3.10
    box("Shared_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    for level in (1,2):
        box("Shared_floor",(0,0,level*h),(w,d,.18),"cream")
    fronts=[]
    for offset,color in ((-3.0,"coral"),(3.0,"mint")):
        front=a.Wall("Home_front_"+color,(offset-3,-d/2),(offset+3,-d/2),(0,-1))
        fronts.append(front)
        if offset<0:
            original=front.window
            front.window=lambda u,sill,width,height,kind="window": None if kind=="bay" else original(u,sill,width,height,kind)
            ground=[(1.70,2.55,.71,2.67,"bay"),(4.95,1.12,.15,2.67,"door")]
        else:
            ground=[(1.05,1.12,.15,2.67,"door"),(4.30,2.04,.71,2.67,"window")]
        front.row(.15,h-.09,ground,color)
        sill,head=h+.59,2*h-.57
        front.row(h+.15,2*h-.09,[(u,1.21,sill,head,"window") for u in (1.51,4.49)],color)
        for u in (1.51,4.49):
            b.shutters(front,u,sill,1.21,head-sill,"teal" if offset<0 else "blue_dark")
        door=4.95 if offset<0 else 1.05
        front.part("Door_canopy",door,2.86,1.66,.18,"cream",.75,.22,.025)
        box("Entry_step",(offset-3+door,-d/2-.26,.075),(1.45,.58,.15),"cream",.025)
        rear=a.Wall("Home_rear_"+color,(offset+3,d/2),(offset-3,d/2),(0,1))
        rear.row(.15,h-.09,[(3.0,1.05,.15,2.61,"door")],color)
        rear.row(h+.15,2*h-.09,[(u,1.19,h+.68,2*h-.60,"window") for u in (1.60,4.40)],color)
    right=a.Wall("Home_right",(w/2,-d/2),(w/2,d/2),(1,0))
    left=a.Wall("Home_left",(-w/2,d/2),(-w/2,-d/2),(-1,0))
    for wall,color in ((right,"mint"),(left,"coral")):
        for level in (0,1):
            wall.row(level*h+.15,(level+1)*h-.09,[(u,1.22,level*h+.86,(level+1)*h-.61,"window") for u in (2.32,6.77)],color)
        wall.part("Cream_base",wall.length/2,.29,wall.length,.27,"cream",.18,.015)
    bay=a.Wall("Coral_projecting_bay",(-5.67,-d/2-.70),(-2.93,-d/2-.70),(0,-1),.20)
    bay.row(.67,2.76,[(1.37,2.51,.73,2.64,"window")],"coral")
    for x in (-5.67,-2.93):
        box("Bay_return",(x,-d/2-.36,1.73),(.18,.72,2.10),"cream",.015)
    for z in (.60,2.86):
        box("Bay_white_cap",(-4.30,-d/2-.36,z),(3.00,.95,.18),"cream",.025)
    for x in (-5.82,0,5.82):
        box("Front_cream_pilaster",(x,-d/2-.05,3.18),(.26,.20,6.03),"cream",.018)
    b.cornice(w,d,2*h,False)
    gable(w+.24,d+.10,2*h+.18,2*h+1.63)


models=[("taco_corner","TacoCorner",34,(11.6,9.4,3.15),"Terracotta one-story L-shaped taco restaurant; open mint-walled terrace; broad recessed windows; taller rear kitchen.",taco_corner),
        ("neighborhood_restaurant","NeighborhoodRestaurant",35,(10.2,9.4,9.9),"Coral three-story neighborhood restaurant; paired cream galleries; shuttered upper windows; setback roof dining terrace.",neighborhood_restaurant),
        ("city_food_hall","CityFoodHall",36,(16.0,11.0,7.0),"Broad butter-yellow two-story food hall; tall grouped windows; central double-height entry; shallow rear sawtooth roof.",city_food_hall),
        ("paired_semi_detached","PairedSemiDetached",41,(12.0,9.4,6.2),"Attached coral and mint two-story homes; mirrored doors; projecting coral bay; shared broad blue gable.",paired_semi_detached)]

taco_colliders=[((-3.25,1.575,0),(5.1,3.15,9.4)),((2.55,1.575,-2.6),(6.5,3.15,4.2)),
                ((2.55,.035,2.1),(6.5,.07,5.2)),((.75,.42,4.7),(2.9,.84,.18)),
                ((5.0,.42,4.7),(1.6,.84,.18)),((5.8,.42,2.1),(.18,.84,5.2))]

scene_dir=a.PROJECT/"scenes/buildings/batch_11"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=taco_colliders if slug=="taco_corner" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_11/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_11/{slug}.glb" id="1"]\n']
    for i,(_,dim) in enumerate(colliders):
        parts.append(f'[sub_resource type="BoxShape3D" id="Body{i}"]\nsize = Vector3({dim[0]}, {dim[1]}, {dim[2]})\n')
    parts.extend([f'[node name="{name}" type="Node3D"]\n',
                  '[node name="Visual" parent="." instance=ExtResource("1")]\n',
                  '[node name="BuildingBody" type="StaticBody3D" parent="."]\ncollision_layer = 1\ncollision_mask = 0\n'])
    for i,(at,_) in enumerate(colliders):
        node="Collision" if i==0 else f"Collision{i}"
        parts.append(f'[node name="{node}" type="CollisionShape3D" parent="BuildingBody"]\nposition = Vector3({at[0]}, {at[1]}, {at[2]})\nshape = SubResource("Body{i}")\n')
    (scene_dir/(slug+".tscn")).write_text('\n'.join(parts))
    import_path=a.ASSET/(slug+".glb.import")
    if not import_path.exists():
        template=(a.PROJECT/"assets/models/buildings/batch_01/corner_cafe.glb.import").read_text()
        resource_path="res://assets/models/buildings/batch_11/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_11_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":11,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 11\n\nTaco Corner (034), Neighborhood Restaurant (035), City Food Hall (036), Paired Semi-Detached (041). The approved pastel French Quarter finish: substantial cream trim, painted recessed blue glazing, shutters, and modest neighborhood scale.\n\nPlacement scenes: `scenes/buildings/batch_11/`. Meters, ground-center origins, Godot +Z front, and one shared static visual mesh per building. Taco Corner uses six box colliders to preserve its open terrace; other buildings use simple body boxes. Tables, roof details, canopies, balconies, and the home’s display bay remain visual details. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_11.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_11.py`.\n')
