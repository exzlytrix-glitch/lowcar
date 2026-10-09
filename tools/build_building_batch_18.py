"""Four neighborhood Lowcar offices using the approved pastel architectural kit."""
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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_18"
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


def teal_glass_office():
    w,d,h=13.8,9.4,3.15
    front=b.frame(w,d,3,"teal",height=h)[0]
    original=front.window
    front.window=lambda u,sill,width,height,kind="window": None if kind=="lobby_void" else original(u,sill,width,height,kind)
    front.row(.15,h-.09,[(2.0,2.25,.78,2.74,"window"),(6.9,6.40,.15,2.76,"lobby_void"),
                        (11.8,2.25,.78,2.74,"window")],"teal")
    for level in (1,2):
        sill,head=level*h+.60,(level+1)*h-.48
        centers=(2.5,6.9,11.3)
        front.row(level*h+.15,(level+1)*h-.09,[(u,3.30,sill,head,"window") for u in centers],"teal")
        for u in centers:
            for du in (-.55,.55):
                front.part("Broad_glass_mullion",u+du,(sill+head)/2,.073,head-sill-.12,"ink",.06,-.13)
        front.part("Broad_cream_floor_band",w/2,level*h,w+.14,.30,"cream",.28,.055)
    for u in (.18,4.7,9.1,w-.18):
        front.part("Cream_upper_pier",u,6.33,.27,5.89,"cream",.24,.06)
    b.cornice(w,d,3*h,False)
    box("Low_blue_roof_cap",(0,0,3*h+.23),(w+.42,d+.42,.26),"roof",.03)
    before={obj.name for obj in a.collection.objects}
    ew,ed=7.0,1.6
    entry,right,rear,left=rectangle(ew,ed,"Projecting_lobby")
    box("Lobby_foundation",(0,0,.075),(ew,ed,.15),"stone",.025)
    box("Lobby_roof_plate",(0,0,h),(ew,ed,.18),"cream")
    entry.row(.15,h-.09,[(1.45,1.84,.43,2.75,"shop"),(3.5,1.43,.15,2.75,"lobby"),
                         (5.55,1.84,.43,2.75,"shop")],"cream")
    for wall in (left,right):
        wall.row(.15,h-.09,[(.8,.81,.77,2.70,"window")],"cream")
    b.cornice(ew,ed,h,False)
    box("Lobby_blue_cap",(0,0,h+.20),(ew+.35,ed+.35,.19),"roof",.025)
    move_new(before,Matrix.Translation(Vector((0,-5.5,0))))


def coral_stair_office():
    w,d,h=10.4,9.2,3.1
    before={obj.name for obj in a.collection.objects}
    front=b.frame(w,d,4,"cream",height=h)[0]
    front.row(.15,h-.09,[(1.83,2.05,.77,2.64,"window"),(5.2,1.57,.15,2.64,"lobby"),
                        (8.57,2.05,.77,2.64,"window")],"cream")
    for level in (1,2,3):
        sill,head=level*h+.70,(level+1)*h-.49
        front.row(level*h+.15,(level+1)*h-.09,[(u,2.05,sill,head,"window") for u in (1.83,5.2,8.57)],"cream")
        front.part("Cream_floor_band",w/2,level*h,w+.12,.21,"cream",.25,.065)
        if level==1:
            for u in (1.83,8.57):
                b.shutters(front,u,sill,2.05,head-sill,"blue_dark")
    for u in (.18,3.35,7.05,w-.18):
        front.part("Broad_cream_pier",u,6.24,.28,12.02,"cream",.24,.065)
    front.part("Lobby_canopy",5.2,2.88,2.23,.18,"cream",.95,.28,.025)
    b.cornice(w,d,4*h,True)
    box("Low_blue_roof_cap",(0,0,4*h+.23),(w+.42,d+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((1.6,0,0))))
    before={obj.name for obj in a.collection.objects}
    sw,sd=3.2,10.2
    walls=rectangle(sw,sd,"Coral_stair")
    box("Stair_foundation",(0,0,.075),(sw,sd,.15),"stone",.025)
    for level in range(4):
        z=level*h
        box("Stair_floor",(0,0,(level+1)*h),(sw,sd,.18),"cream")
        for i,wall in enumerate(walls):
            bays=[(wall.length/2,1.17,z+.74,(level+1)*h-.50,"window")] if i in (0,2) else [(wall.length*f,1.22,z+.74,(level+1)*h-.50,"window") for f in (.28,.72)]
            wall.row(z+.15,(level+1)*h-.09,bays,"coral")
        walls[0].part("White_floor_band",sw/2,(level+1)*h,sw+.08,.18,"cream",.23,.05)
    for u in (.14,sw-.14):
        walls[0].part("White_stair_edge",u,6.23,.24,12.04,"cream",.23,.06)
    walls[0].part("Cream_plinth",sw/2,.29,sw,.28,"cream",.20,.02)
    b.cornice(sw,sd,4*h,False)
    box("Low_coral_stair_cap",(0,0,4*h+.28),(sw+.40,sd+.40,.31),"coral_dark",.025)
    move_new(before,Matrix.Translation(Vector((-5.2,0,0))))


def square_blue_cap_office():
    w,d,h=11.4,11.4,3.05
    front=b.frame(w,d,4,"cream",height=h)[0]
    original=front.window
    front.window=lambda u,sill,width,height,kind="window": None if kind=="inset_entry" else original(u,sill,width,height,kind)
    front.row(.15,h-.09,[(2.1,1.90,.77,2.59,"window"),(5.7,1.90,.77,2.59,"window"),
                        (9.3,1.50,.15,2.59,"inset_entry")],"cream")
    cx=-w/2+9.3
    inset=a.Wall("Recessed_corner_lobby",(cx-.75,-d/2+.48),(cx+.75,-d/2+.48),(0,-1))
    inset.window(.75,.15,1.50,2.44,"lobby")
    for x in (cx-.83,cx+.83):
        box("Cream_lobby_return",(x,-d/2+.22,1.45),(.17,.57,2.60),"cream",.015)
    front.part("Corner_lobby_header",9.3,2.70,1.97,.19,"cream",.66,-.15,.02)
    front.part("Corner_lobby_canopy",9.3,2.87,2.24,.18,"roof",.97,.24,.025)
    for level in (1,2,3):
        sill,head=level*h+.70,(level+1)*h-.48
        front.row(level*h+.15,(level+1)*h-.09,[(u,1.90,sill,head,"window") for u in (2.1,5.7,9.3)],"cream")
        front.part("Cream_grid_band",w/2,level*h,w+.10,.20,"cream",.22,.055)
    for u in (.18,3.9,7.5,w-.18):
        front.part("Cream_grid_pier",u,6.13,.27,11.78,"cream",.24,.065)
    b.cornice(w,d,4*h,True)
    b.hip_roof(w,d,4*h+.18,13.0)


def joined_office_wings():
    for cx,w,d,h,color,dy in ((-5.9,6.4,10.4,3.1,"mint",0),(5.9,6.4,8.4,2.95,"blue",1.0)):
        before={obj.name for obj in a.collection.objects}
        front=b.frame(w,d,3,color,height=h)[0]
        for level in range(3):
            sill,head=level*h+.74,(level+1)*h-.47
            front.row(level*h+.15,(level+1)*h-.09,[(u,1.65,sill,head,"window") for u in (1.7,4.7)],color)
            front.part("White_floor_band",w/2,(level+1)*h,w+.1,.18,"cream",.23,.05)
        for u in (.17,w-.17):
            front.part("Cream_corner_trim",u,1.5*h+.06,.26,3*h-.31,"cream",.21,.05)
        b.cornice(w,d,3*h,False)
        a.parapet("Wing_roof_edge",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],3*h+.15,color,.32)
        box("Low_roof_setback",(0,2.15,3*h+.44),(2.05,2.51,.58),color,.025)
        box("Setback_cap",(0,2.15,3*h+.78),(2.28,2.74,.13),"cream",.02)
        move_new(before,Matrix.Translation(Vector((cx,dy,0))))
    before={obj.name for obj in a.collection.objects}
    w,d,h=5.4,6.6,3.1
    front=b.frame(w,d,1,"cream",height=h)[0]
    front.row(.15,h-.09,[(.98,.65,.74,2.66,"window"),(2.7,2.4,.15,2.66,"lobby"),
                        (4.42,.65,.74,2.66,"window")],"cream")
    front.part("Shared_lobby_canopy",2.7,2.87,3.14,.18,"cream",.91,.27,.025)
    b.cornice(w,d,h,False)
    box("Low_connecting_blue_roof",(0,0,h+.23),(w+.39,d+.39,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((0,1.9,0))))
    box("Open_forecourt_paving",(0,-3.3,.04),(5.4,3.8,.08),"stone")


models=[("teal_glass_office","TealGlassOffice",72,(13.8,11.0,9.45),"Broad teal three-story office; painted blue glass panels between cream floor bands; projecting cream lobby base.",teal_glass_office),
    ("coral_stair_office","CoralStairOffice",73,(13.6,10.2,12.4),"Broad cream four-story office with an integrated coral stair spine; three-window rhythm; substantial white trim; low roof cap.",coral_stair_office),
    ("square_blue_cap_office","SquareBlueCapOffice",74,(11.4,11.4,12.2),"Square cream four-story office; symmetrical window grid; broad cornice and shallow blue hip cap; recessed corner lobby.",square_blue_cap_office),
    ("joined_office_wings","JoinedOfficeWings",75,(18.2,10.4,9.3),"Two broad three-story office wings in mint and powder blue; low shared cream entrance; open forecourt; slightly different roof heights and setbacks.",joined_office_wings)]

teal_colliders=[((0,4.725,0),(13.8,9.45,9.4)),((0,1.575,5.5),(7.0,3.15,1.6))]
coral_colliders=[((1.6,6.2,0),(10.4,12.4,9.2)),((-5.2,6.2,0),(3.2,12.4,10.2))]
wing_colliders=[((-5.9,4.65,0),(6.4,9.3,10.4)),((5.9,4.425,-1.0),(6.4,8.85,8.4)),
                ((0,1.55,-1.9),(5.4,3.1,6.6)),((0,.04,3.3),(5.4,.08,3.8))]

scene_dir=a.PROJECT/"scenes/buildings/batch_18"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=teal_colliders if slug=="teal_glass_office" else coral_colliders if slug=="coral_stair_office" else wing_colliders if slug=="joined_office_wings" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_18/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_18/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_18/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_18_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":18,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 18\n\nTeal-Glass Office (072), Coral Stair Office (073), Square Blue-Cap Office (074), Joined Office Wings (075). Approved bright pastel French Quarter style, chunky cream trim, recessed painted blue glazing, broad three- and four-story proportions.\n\nPlacement scenes: `scenes/buildings/batch_18/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Simple boxes follow the projecting lobby, stair section, and joined wings. The central forecourt stays open. Canopies, ornamental trim, and roof details remain visual. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_18.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_18.py`.\n')
