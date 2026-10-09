"""Four neighborhood Lowcar buildings using the approved pastel architectural kit."""
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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_26"
a.SOURCE=a.ASSET/"source"
a.PREVIEWS=a.ASSET/"previews"
for folder in (a.ASSET,a.SOURCE,a.PREVIEWS):
    folder.mkdir(parents=True,exist_ok=True)
for folder in (a.SOURCE,a.PREVIEWS):
    (folder/".gdignore").write_text("")


def move_new(before,transform):
    a.bpy.context.view_layer.update()
    for obj in a.collection.objects:
        if obj.name not in before and obj.type=="MESH":
            obj.matrix_world=transform @ obj.matrix_world


def inset_lobby(front,depth=.48):
    original=front.window
    back=a.Wall("Recessed_lobby",(front.start.x,front.start.y+depth),(front.end.x,front.end.y+depth),(0,-1))
    def glazing(u,sill,width,height,kind="window"):
        if kind not in ("door","lobby"):
            return original(u,sill,width,height,kind)
        back.window(u,sill,width,height,kind)
        for du in (-width/2,width/2):
            front.part("Lobby_reveal_jamb",u+du,sill+height/2,.15,height+.17,"cream",depth+.22,-depth/2,.015)
        for z in (sill,sill+height):
            front.part("Lobby_reveal_lintel",u,z,width+.16,.14,"cream",depth+.22,-depth/2,.015)
    front.window=glazing


def rectangle(w,d,label):
    return [a.Wall(label+"_front",(-w/2,-d/2),(w/2,-d/2),(0,-1)),
            a.Wall(label+"_right",(w/2,-d/2),(w/2,d/2),(1,0)),
            a.Wall(label+"_rear",(w/2,d/2),(-w/2,d/2),(0,1)),
            a.Wall(label+"_left",(-w/2,d/2),(-w/2,-d/2),(-1,0))]


def shutter_bays(wall):
    original=wall.window
    def window(u,sill,width,height,kind="window"):
        if kind!="loading":
            return original(u,sill,width,height,kind)
        wall.part("Closed_loading_shutter",u,sill+height/2,width,height,"roof",.14,-.14,.025)
        for i in range(6):
            wall.part("Loading_shutter_slat",u,sill+.24+i*(height-.48)/5,width-.14,.065,"reflection",.06,-.035)
        for du in (-width/2,width/2):
            wall.part("Loading_cream_jamb",u+du,sill+height/2,.16,height+.14,"cream",.22,.025)
        wall.part("Loading_cream_header",u,sill+height,width+.25,.17,"cream",.22,.025)
        wall.part("Shutter_handle",u,sill+.87,.53,.095,"cream",.08,-.005,.015)
    wall.window=window


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


def raised_roof_storehouse():
    w,d,h=14.0,14.4,4.3
    walls=rectangle(w,d,"Storehouse")
    box("Storehouse_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Storehouse_ceiling",(0,0,h),(w,d,.18),"cream")
    for i,wall in enumerate(walls):
        if i==0:
            shutter_bays(wall)
            bays=[(3.1,4.12,.15,3.73,"loading"),(7.0,1.32,.15,2.70,"lobby"),(10.9,4.12,.15,3.73,"loading")]
        elif i==2:
            bays=[(wall.length*.30,1.24,.15,2.65,"door"),(wall.length*.73,2.21,2.18,3.56,"window")]
        else:
            bays=[(wall.length*f,1.38,2.19,3.56,"window") for f in (.23,.50,.77)]
        wall.row(.15,h-.09,bays,"yellow")
        wall.part("Storehouse_cream_base",wall.length/2,.29,wall.length,.28,"cream",.20,.02)
    b.cornice(w,d,h,False)
    box("Lower_blue_roof_wings",(0,0,h+.23),(w+.42,d+.42,.26),"roof",.03)
    cw,cd=6.0,14.4
    for i,wall in enumerate(rectangle(cw,cd,"Central_roof_strip")):
        centers=(1.60,4.40) if i in (0,2) else (2.65,7.2,11.75)
        bays=[(u,1.18 if i in (0,2) else 1.74,4.70,5.29,"window") for u in centers]
        wall.row(4.49,5.55,bays,"yellow")
    b.cornice(cw,cd,5.64,False)
    box("Higher_central_blue_cap",(0,0,5.86),(cw+.42,cd+.42,.26),"roof",.03)
    walls[0].part("Storehouse_door_canopy",7.0,2.93,2.06,.18,"cream",.89,.28,.025)


def textile_factory():
    before={obj.name for obj in a.collection.objects}
    w,d,h=14.0,12.0,3.1
    front=b.frame(w,d,3,"coral_dark",height=h)[0]
    for level in range(3):
        sill,head=level*h+.42,(level+1)*h-.43
        bays=[(u,1.69,sill,head,"window") for u in (2.0,5.3,8.7,12.0)]
        if level==0:
            bays[1]=(5.3,1.54,.15,2.66,"lobby")
        front.row(level*h+.15,(level+1)*h-.09,bays,"coral_dark")
        front.part("Thick_factory_floor_band",w/2,(level+1)*h,w+.16,.33,"cream",.30,.06,.018)
    for u in (.19,w-.19):
        front.part("Factory_corner_trim",u,4.70,.32,8.98,"cream",.26,.06)
    front.part("Textile_name_panel",w/2,3.31,5.18,.43,"teal",.14,.11,.02)
    a.text("Textile_letters","TEXTILE",front.point(w/2,3.31,.20),.37)
    b.cornice(w,d,3*h,False)
    box("Factory_flat_blue_cap",(0,0,3*h+.23),(w+.42,d+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((-2.6,0,0))))
    before={obj.name for obj in a.collection.objects}
    lw,ld,lh=5.2,8.0,3.8
    walls=rectangle(lw,ld,"Textile_loading_wing")
    box("Loading_wing_foundation",(0,0,.075),(lw,ld,.15),"stone",.025)
    box("Loading_wing_ceiling",(0,0,lh),(lw,ld,.18),"cream")
    for i,wall in enumerate(walls):
        if i==0:
            shutter_bays(wall)
            bays=[(lw/2,4.04,.15,3.22,"loading")]
        else:
            bays=[(wall.length*.5,1.52,2.04,3.22,"window")]
        wall.row(.15,lh-.09,bays,"cream")
    b.cornice(lw,ld,lh,False)
    box("Loading_wing_blue_cap",(0,0,lh+.23),(lw+.42,ld+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((7.0,2.0,0))))


def print_workshop():
    w,d,h=15.6,10.2,3.25
    front=b.frame(w,d,2,"blue",height=h)[0]
    shutter_bays(front)
    front.row(.15,h-.09,[(4.0,4.30,.15,2.79,"loading"),(7.8,1.35,.15,2.79,"lobby"),
                        (11.6,4.30,.15,2.79,"loading")],"blue")
    front.row(h+.15,2*h-.09,[(u,4.05,h+.50,2*h-.41,"window") for u in (3.0,7.8,12.6)],"blue")
    for u in (3.0,7.8,12.6):
        for du in (-.69,.69):
            front.part("Print_studio_glazing_bar",u+du,4.92,.075,2.19,"ink",.06,-.12)
    front.part("Print_cream_floor_band",w/2,h,w+.13,.25,"cream",.26,.055)
    front.part("Print_name_panel",w/2,3.46,4.70,.39,"teal",.14,.12,.018)
    a.text("Print_name","PRINT",front.point(w/2,3.46,.21),.33)
    for u in (.18,w-.18):
        front.part("Print_corner_pier",u,3.30,.29,6.20,"cream",.24,.055)
    front.part("Print_entry_canopy",7.8,3.01,2.08,.18,"cream",.88,.27,.025)
    b.cornice(w,d,2*h,True)
    a.parapet("Blue_flat_print_parapet",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],2*h+.17,"blue_dark",.40)
    front.part("Raised_print_center_step",w/2,7.35,7.0,.62,"blue_dark",.23,-.04,.018)
    front.part("Print_step_cream_cap",w/2,7.70,7.20,.13,"cream",.36,-.025,.015)


def carpenters_workshop():
    w,d,h=12.0,6.8,3.6
    before={obj.name for obj in a.collection.objects}
    walls=rectangle(w,d,"Carpenter_shed")
    box("Shed_ceiling",(0,0,h),(w,d,.18),"cream")
    for i,wall in enumerate(walls):
        if i==0:
            shutter_bays(wall)
            bays=[(3.1,4.05,.15,3.10,"loading"),(8.9,4.05,.15,3.10,"loading")]
        else:
            bays=[(wall.length*.5,1.71,1.83,3.08,"window")]
        wall.row(.15,h-.09,bays,"cream")
        wall.part("Shed_teal_base",wall.length/2,.29,wall.length,.28,"teal",.20,.02)
    move_new(before,Matrix.Translation(Vector((-2.8,-.2,0))))
    box("Full_L_shed_foundation",(-2.8,-1.4,.075),(12.0,9.2,.15),"stone",.025)
    box("Covered_workfront_ceiling",(-2.8,-4.8,3.6),(12.0,2.4,.18),"cream")
    for x in (-8.50,-2.80,2.90):
        box("Workfront_column",(x,-5.78,1.88),(.25,.25,3.45),"cream",.018)
        box("Workfront_column_foot",(x,-5.78,.20),(.44,.44,.27),"cream",.02)
        box("Workfront_column_capital",(x,-5.78,3.49),(.46,.46,.18),"cream",.02)
    before={obj.name for obj in a.collection.objects}
    gable(12.0,9.2,3.77,5.08)
    move_new(before,Matrix.Translation(Vector((-2.8,-1.4,0))))
    for x in (-6.5,.80):
        box("Covered_work_bench",(x,-4.17,.73),(2.25,.66,1.15),"teal",.035)
        box("Bench_cream_top",(x,-4.17,1.38),(2.42,.78,.15),"cream",.025)
    before={obj.name for obj in a.collection.objects}
    ow,od,oh=5.6,6.2,3.05
    front=b.frame(ow,od,1,"cream",height=oh)[0]
    front.row(.15,oh-.09,[(1.45,1.59,.72,2.58,"window"),(3.95,1.36,.15,2.58,"lobby")],"cream")
    front.part("Carpenter_name_panel",ow/2,2.88,4.15,.34,"teal",.12,.10,.018)
    a.text("Carpenter_name","WOODWORK",front.point(ow/2,2.88,.18),.26)
    b.cornice(ow,od,oh,False)
    box("Carpenter_office_blue_cap",(0,0,oh+.23),(ow+.42,od+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((6.0,2.9,0))))


models=[
    ("raised_roof_storehouse","RaisedRoofStorehouse",104,(14.0,14.4,5.64),"Butter-yellow low storehouse with two front shutters, raised central roof strip and narrow clerestory windows.",raised_roof_storehouse),
    ("textile_factory","TextileFactory",105,(19.2,12.0,9.3),"Broad terracotta three-story factory with tall repeated windows, thick cream floor bands and low attached loading wing.",textile_factory),
    ("print_workshop","PrintWorkshop",106,(15.6,10.2,6.5),"Powder-blue two-story print shop with broad upper studio windows, two ground service shutters and stepped navy parapet.",print_workshop),
    ("carpenters_workshop","CarpentersWorkshop",107,(17.6,12.0,3.6),"Low cream L-shaped carpenter shed with a deep covered workfront, blue gable roof, teal benches and attached office.",carpenters_workshop)]

extra_colliders={
    "raised_roof_storehouse":[((0,2.15,0),(14.0,4.3,14.4)),((0,4.97,0),(6.0,1.34,14.4))],
    "textile_factory":[((-2.6,4.65,0),(14.0,9.3,12.0)),((7.0,1.9,-2.0),(5.2,3.8,8.0))],
    "carpenters_workshop":[((-2.8,1.8,.2),(12.0,3.6,6.8)),((6.0,1.525,-2.9),(5.6,3.05,6.2)),
                            ((-8.5,1.88,5.78),(.44,3.6,.44)),((-2.8,1.88,5.78),(.44,3.6,.44)),((2.9,1.88,5.78),(.44,3.6,.44)),
                            ((-2.8,.075,4.8),(12.0,.15,2.4)),((-2.8,3.6,4.8),(12.0,.18,2.4))]}

scene_dir=a.PROJECT/"scenes/buildings/batch_26"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=extra_colliders.get(slug,[((0,h/2,0),(w,h,d))])
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_26/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_26/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_26/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_26_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":26,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 26\n\nRaised-Roof Storehouse (104), Textile Factory (105), Print Workshop (106), Carpenter’s Workshop (107). Bright pastel French Quarter industrial buildings with chunky cream trim, blue glazing and roofs, low service wings and readable shutters.\n\nPlacement scenes: `scenes/buildings/batch_26/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Body boxes follow raised roof strips and attached wings; carpenter collision preserves the covered workfront with separate column, floor and ceiling boxes. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_26.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_26.py`.\n')
