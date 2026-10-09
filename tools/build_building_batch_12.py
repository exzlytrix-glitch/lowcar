"""Four neighborhood Lowcar houses using the approved pastel architectural kit."""
from pathlib import Path
import importlib.util
import json
import hashlib
from math import pi
from mathutils import Matrix, Vector

spec=importlib.util.spec_from_file_location("lowcar_batch_parts",Path(__file__).with_name("build_building_batch_01.py"))
b=importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
a=b.a
box,rod,mesh=a.box,a.rod,a.mesh
a.ASSET=a.PROJECT/"assets/models/buildings/batch_12"
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


def move_new(before,transform):
    a.bpy.context.view_layer.update()
    for obj in a.collection.objects:
        if obj.name not in before and obj.type=="MESH":
            obj.matrix_world=transform @ obj.matrix_world


def step_entry_house():
    w,d,h=7.6,8.6,3.10
    front=b.frame(w,d,2,"blue",height=h)[0]
    original=front.window
    front.window=lambda u,sill,width,height,kind="window": None if kind=="entry" else original(u,sill,width,height,kind)
    front.row(.15,h-.09,[(1.65,1.13,.60,2.75,"entry"),(5.09,2.13,.91,2.75,"window")],"blue")
    cx=-w/2+1.65
    inset=a.Wall("Deep_entry",(cx-.565,-d/2+.43),(cx+.565,-d/2+.43),(0,-1))
    inset.window(.565,.60,1.13,2.15,"door")
    for x in (cx-.65,cx+.65):
        box("Cream_entry_return",(x,-d/2+.22,1.70),(.18,.51,2.30),"cream",.015)
    front.part("Cream_entry_header",1.65,2.85,1.62,.22,"cream",.55,-.16,.02)
    for reach,depth,height in ((.22,.45,.60),(.67,.45,.40),(1.12,.45,.20)):
        box("Raised_entry_step",(cx,-d/2-reach,height/2),(1.78,depth,height),"cream",.025)
    sill,head=h+.65,2*h-.56
    front.row(h+.15,2*h-.09,[(u,1.12,sill,head,"window") for u in (1.51,3.80,6.09)],"blue")
    for u in (1.51,6.09):
        b.shutters(front,u,sill,1.12,head-sill,"mint_dark")
    b.shutters(front,5.09,.91,2.13,1.84,"mint_dark")
    for u in (.18,w-.18):
        front.part("Cream_corner_trim",u,3.18,.27,5.94,"cream",.21,.045)
    flat_roof(w,d,2*h,"blue",.39)
    box("Offset_roof_cap",(1.62,2.25,2*h+.52),(2.47,2.31,.74),"blue_dark",.035)
    box("Cream_roof_cap",(1.62,2.25,2*h+.95),(2.73,2.57,.15),"cream",.025)


def gabled_corner_home():
    w,d,h=10.2,9.4,3.10
    front,right,rear,left=rectangle(w,d,"CornerHome")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    for level in (1,2):
        box("Floor_plate",(0,0,level*h),(w,d,.18),"cream")
    for wall in (front,right,rear,left):
        if wall is front:
            ground=[(2.45,2.05,.79,2.67,"window"),(5.35,1.44,.91,2.67,"window"),(8.37,1.12,.15,2.67,"door")]
            upper=[(u,1.44,h+.67,2*h-.55,"window") for u in (2.14,5.10,8.06)]
        elif wall is right:
            ground=[(u,1.54,.84,2.67,"window") for u in (2.15,6.76)]
            upper=[(u,1.47,h+.69,2*h-.55,"window") for u in (2.15,6.76)]
        else:
            ground=[(wall.length*.55,1.10,.15 if wall is rear else 1.00,2.63,"door" if wall is rear else "window")]
            upper=[(wall.length*f,1.21,h+.69,2*h-.57,"window") for f in (.27,.70)]
        wall.row(.15,h-.09,ground,"mint")
        wall.row(h+.15,2*h-.09,upper,"mint")
        wall.part("Cream_base",wall.length/2,.30,wall.length,.28,"cream",.19,.015)
    for u in (2.14,8.06):
        b.shutters(front,u,h+.67,1.44,2*h-.55-(h+.67),"blue_dark")
    for u in (2.15,6.76):
        b.shutters(right,u,h+.69,1.47,2*h-.55-(h+.69),"blue_dark")
    front.part("Small_corner_porch_canopy",8.37,2.90,2.69,.20,"cream",1.34,.49,.025)
    box("Corner_porch_slab",(3.27,-d/2-.65,.08),(2.83,1.65,.16),"stone",.025)
    for x in (2.23,4.31):
        box("Porch_column",(x,-d/2-1.12,1.48),(.16,.16,2.76),"cream",.015)
        box("Column_foot",(x,-d/2-1.12,.20),(.29,.29,.24),"cream",.018)
        box("Column_capital",(x,-d/2-1.12,2.79),(.29,.29,.16),"cream",.015)
    b.cornice(w,d,2*h,False)
    gable(w+.35,d+.20,2*h+.18,8.06)
    before={obj.name for obj in a.collection.objects}
    gable(4.5,5.8,2*h+.18,7.81)
    transform=Matrix.Translation(Vector((2.5,-1.75,0))) @ Matrix.Rotation(pi/2,4,"Z")
    move_new(before,transform)


def attic_house():
    w,d,h=10.8,9.4,3.15
    front=b.frame(w,d,2,"yellow",height=h)[0]
    front.row(.15,h-.09,[(2.46,2.49,.77,2.72,"window"),(5.40,1.18,.15,2.72,"door"),(8.34,2.49,.77,2.72,"window")],"yellow")
    sill,head=h+.72,2*h-.58
    front.row(h+.15,2*h-.09,[(u,1.99,sill,head,"window") for u in (2.29,5.40,8.51)],"yellow")
    for u in (2.29,8.51):
        b.shutters(front,u,sill,1.99,head-sill,"blue_dark")
    front.part("Short_entry_canopy",5.40,2.92,2.21,.18,"cream",.83,.26,.025)
    box("Entry_step",(0,-d/2-.31,.075),(1.58,.70,.15),"cream",.02)
    for u in (.18,w-.18):
        front.part("Cream_corner_trim",u,3.23,.28,6.04,"cream",.20,.045)
    b.cornice(w,d,2*h,False)
    b.hip_roof(w,d,2*h+.18,8.35)
    for cx in (-2.61,2.61):
        y,low,top=-3.85,6.62,8.10
        dormer=a.Wall("Dormer_front",(cx-.90,y-.80),(cx+.90,y-.80),(0,-1),.20)
        dormer.row(low,top,[(.90,1.20,7.04,7.91,"window")],"cream")
        for x in (cx-.83,cx+.83):
            box("Dormer_side",(x,y,(low+top)/2),(.14,1.60,top-low),"cream",.015)
        box("Dormer_rear",(cx,y+.72,(low+top)/2),(1.80,.16,top-low),"cream",.015)
        box("Dormer_sill",(cx,y-.83,7.0),(1.98,.26,.14),"cream",.02)
        before={obj.name for obj in a.collection.objects}
        gable(2.02,1.79,8.15,8.61,cx)
        move_new(before,Matrix.Translation(Vector((0,y,0))))


def bay_window_house():
    w,d,h=7.8,9.1,3.10
    front=b.frame(w,d,3,"mint",height=h)[0]
    original=front.window
    front.window=lambda u,sill,width,height,kind="window": None if kind in ("bay","entry") else original(u,sill,width,height,kind)
    front.row(.15,h-.09,[(2.10,2.80,.68,2.76,"bay"),(6.16,1.13,.15,2.76,"entry")],"mint")
    front.row(h+.15,2*h-.09,[(2.10,2.80,h+.68,2*h-.34,"bay"),(6.16,1.19,h+.73,2*h-.57,"window")],"mint")
    front.row(2*h+.15,3*h-.09,[(u,1.19,2*h+.69,3*h-.56,"window") for u in (1.60,3.90,6.20)],"mint")
    for u in (1.60,6.20):
        b.shutters(front,u,2*h+.69,1.19,3*h-.56-(2*h+.69),"blue_dark")
    b.shutters(front,6.16,h+.73,1.19,2*h-.57-(h+.73),"blue_dark")
    cx=-w/2+6.16
    entry=a.Wall("Inset_house_entry",(cx-.565,-d/2+.35),(cx+.565,-d/2+.35),(0,-1))
    entry.window(.565,.15,1.13,2.61,"door")
    for x in (cx-.65,cx+.65):
        box("Cream_entry_return",(x,-d/2+.16,1.52),(.18,.43,2.87),"cream",.015)
    front.part("Door_canopy",6.16,2.95,1.73,.18,"cream",.81,.24,.025)
    outline=[(-3.30,-d/2),(-3.30,-d/2-.37),(-2.78,-d/2-.95),(-.82,-d/2-.95),(-.30,-d/2-.37),(-.30,-d/2)]
    for level in (0,1):
        low=level*h+.68
        high=level*h+2.79
        a.prism("Faceted_bay_base",outline,low-.14,low+.04,"cream",.018)
        a.prism("Faceted_bay_crown",outline,high,high+.16,"cream",.02)
        for i,(p,q) in enumerate(zip(outline,outline[1:])):
            normal=(q[1]-p[1],p[0]-q[0])
            wall=a.Wall("Bay_facet_%d_%d"%(level,i),p,q,normal,.17)
            openings=[] if i in (0,4) else [(wall.length/2,wall.length-.23,low+.14,high-.15,"window")]
            wall.row(low+.04,high,openings,"mint")
        for x in (-2.93,-.67):
            rod("Bay_under_bracket",(x,-d/2,low-.54),(x,-d/2-.62,low-.12),.11,"cream")
    for u in (.17,w-.17):
        front.part("Cream_corner_trim",u,4.72,.26,9.04,"cream",.20,.045)
    flat_roof(w,d,3*h,"mint",.39)
    box("Roof_stair_room",(1.91,2.41,3*h+.58),(2.31,2.37,.86),"mint_dark",.03)
    box("Roof_stair_cap",(1.91,2.41,3*h+1.08),(2.55,2.61,.14),"cream",.025)


models=[("step_entry_house","StepEntryHouse",43,(7.6,8.6,6.2),"Powder-blue two-story home; raised cream steps; deeply recessed door; flat parapet and offset roof cap.",step_entry_house),
        ("gabled_corner_home","GabledCornerHome",44,(10.2,9.4,6.2),"Mint two-story corner home; intersecting broad blue gables; windows on both street sides; small cream porch.",gabled_corner_home),
        ("attic_house","AtticHouse",45,(10.8,9.4,6.3),"Broad butter-yellow two-story attic home; two chunky cream dormers; broad upper windows; short entry canopy.",attic_house),
        ("bay_window_house","BayWindowHouse",46,(7.8,9.1,9.3),"Mint three-story home; two stacked faceted bays; inset side entrance; blue shutters; flat roof.",bay_window_house)]

step_colliders=[((0,3.1,0),(7.6,6.2,8.6)),
                ((-2.15,.30,4.52),(1.78,.60,.45)),
                ((-2.15,.20,4.97),(1.78,.40,.45)),
                ((-2.15,.10,5.42),(1.78,.20,.45))]

scene_dir=a.PROJECT/"scenes/buildings/batch_12"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=step_colliders if slug=="step_entry_house" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_12/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_12/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_12/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_12_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":12,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 12\n\nStep-Entry House (043), Gabled Corner Home (044), Attic House (045), Bay-Window House (046). Approved pastel French Quarter finish, substantial cream trim, painted blue glazing, and neighborhood proportions.\n\nPlacement scenes: `scenes/buildings/batch_12/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building, and simple world collision. The step-entry home includes three stair colliders beside its body box. Other homes use body boxes; porch, roof, and projecting bay details remain visual. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_12.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_12.py`.\n')
