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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_25"
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


def produce_wholesaler():
    w,d,h=19.0,12.0,3.05
    walls=rectangle(w,d,"Produce")
    box("Produce_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    for level in range(2):
        box("Produce_floor",(0,0,(level+1)*h),(w,d,.18),"cream")
        for i,wall in enumerate(walls):
            if level==0 and i==0:
                shutter_bays(wall)
                bays=[(u,4.3,.15,2.55,"loading") for u in (3.2,9.5,15.8)]
            elif level==0:
                bays=[(wall.length*.27,1.25,.15,2.60,"door"),(wall.length*.72,2.0,1.65,2.60,"window")]
            else:
                count=6 if i==0 else 3
                bays=[(wall.length*(j+.5)/count,1.34,level*h+.97,(level+1)*h-.48,"window") for j in range(count)]
            wall.row(level*h+.15,(level+1)*h-.09,bays,"yellow")
            wall.part("Produce_cream_floor_band",wall.length/2,(level+1)*h,wall.length+.12,.23,"cream",.24,.055)
    front=walls[0]
    front.part("Produce_loading_canopy",w/2,2.87,w-.60,.18,"cream",1.22,.41,.025)
    front.part("Teal_loading_canopy_edge",w/2,2.84,w-.60,.23,"teal",.12,1.07,.015)
    front.part("Produce_name_panel",w/2,3.34,6.4,.48,"teal",.14,.11,.02)
    a.text("Produce_letters","PRODUCE",front.point(w/2,3.34,.20),.40)
    for wall in walls:
        for u in (.18,wall.length-.18):
            wall.part("Produce_cream_corner",u,3.10,.29,5.82,"cream",.23,.055)
    b.cornice(w,d,2*h,False)
    b.hip_roof(w,d,2*h+.18,2*h+1.04)


def body_repair_workshop():
    before={obj.name for obj in a.collection.objects}
    w,d,h=11.8,10.0,4.0
    walls=rectangle(w,d,"Body_workshop")
    box("Workshop_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Workshop_ceiling",(0,0,h),(w,d,.18),"cream")
    for i,wall in enumerate(walls):
        if i==0:
            shutter_bays(wall)
            bays=[(w/2,7.6,.15,3.38,"loading")]
        else:
            bays=[(wall.length*.5,2.08,2.13,3.46,"window")]
        wall.row(.15,h-.09,bays,"coral")
        wall.part("Workshop_cream_base",wall.length/2,.29,wall.length,.28,"cream",.20,.02)
    b.cornice(w,d,h,False)
    gable(w,d,h+.17,h+1.43)
    move_new(before,Matrix.Translation(Vector((-2.4,0,0))))
    before={obj.name for obj in a.collection.objects}
    w,d,h=4.8,10.0,3.02
    front=b.frame(w,d,2,"coral",height=h)[0]
    front.row(.15,h-.09,[(1.2,1.13,.15,2.58,"lobby"),(3.7,1.17,.77,2.58,"window")],"coral")
    front.row(h+.15,2*h-.09,[(u,1.16,h+.65,2*h-.47,"window") for u in (1.2,3.7)],"coral")
    front.part("Repair_cream_floor_band",w/2,h,w+.12,.23,"cream",.24,.055)
    front.part("Body_repair_name_panel",w/2,3.31,3.2,.43,"teal",.14,.11,.02)
    a.text("Body_repair_letters","BODY",front.point(w/2,3.31,.20),.36)
    for u in (.18,w-.18):
        front.part("Office_cream_corner",u,3.06,.28,5.77,"cream",.23,.055)
    b.cornice(w,d,2*h,False)
    box("Repair_office_blue_cap",(0,0,2*h+.23),(w+.42,d+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((5.9,0,0))))


def small_motor_garage():
    w,d,h=11.6,8.8,4.1
    walls=rectangle(w,d,"Motor_garage")
    box("Garage_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Open_bay_floor",(-3.15,0,.16),(4.22,d-.38,.04),"roof")
    box("Garage_ceiling",(0,0,h),(w,d,.18),"cream")
    front=walls[0]
    shutter_bays(front)
    closed_window=front.window
    front.window=lambda u,sill,width,height,kind="window": None if kind=="open" else closed_window(u,sill,width,height,kind)
    front.row(.15,h-.09,[(2.65,4.20,.15,3.42,"open"),(7.35,3.50,.15,3.42,"loading"),
                        (10.48,1.20,.15,2.72,"lobby")],"mint")
    for i,wall in enumerate(walls[1:]):
        bays=[(wall.length*.35,1.54,1.93,3.26,"window")]
        if i==1:
            bays.append((wall.length*.72,1.54,1.93,3.26,"window"))
        wall.row(.15,h-.09,bays,"mint")
    front.part("Garage_cream_header",w/2,3.82,w+.14,.28,"cream",.26,.055)
    front.part("Garage_name_panel",w/2,3.83,2.6,.33,"teal",.13,.20,.018)
    a.text("Motor_garage_letters","MOTOR",front.point(w/2,3.83,.29),.27)
    # A compact lift and cabinet give the open bay depth without visual clutter.
    for x in (-4.45,-1.85):
        box("Lift_post",(x,.55,1.31),(.22,.28,2.3),"teal",.025)
        box("Lift_foot",(x,.55,.23),(.56,.61,.15),"cream",.025)
    box("Rear_tool_cabinet",(-3.15,3.62,.79),(2.78,.76,1.26),"teal",.035)
    box("Rear_cabinet_worktop",(-3.15,3.60,1.49),(2.96,.88,.14),"cream",.025)
    for z in (.49,.84,1.18):
        box("Tool_drawer_line",(-3.15,3.225,z),(2.52,.035,.05),"cream")
    b.cornice(w,d,h,False)
    a.parapet("Garage_low_mint_parapet",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],h+.17,"mint",.39)


def long_loading_warehouse():
    w,d,h=12.4,18.0,4.0
    walls=rectangle(w,d,"Loading_warehouse")
    box("Warehouse_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Warehouse_ceiling",(0,0,h),(w,d,.18),"cream")
    for i,wall in enumerate(walls):
        if i==3:
            shutter_bays(wall)
            bays=[(wall.length*(j+.5)/5,2.64,.15,3.40,"loading") for j in range(5)]
        elif i==2:
            shutter_bays(wall)
            bays=[(3.1,3.1,.15,3.40,"loading"),(9.2,2.0,2.14,3.42,"window")]
        elif i==0:
            bays=[(w/2,3.22,2.30,3.43,"window")]
        else:
            bays=[(wall.length*f,2.0,2.20,3.43,"window") for f in (.20,.50,.80)]
        wall.row(.15,h-.09,bays,"cream")
        wall.part("Warehouse_cream_base",wall.length/2,.29,wall.length,.28,"cream",.20,.02)
        if i==3:
            for j in range(5):
                a.text("Loading_bay_number",str(j+1),wall.point(wall.length*(j+.5)/5,3.68,.09),.27,"teal",wall.angle)
    b.cornice(w,d,h,False)
    gable(w,d,h+.17,h+1.44)
    before={obj.name for obj in a.collection.objects}
    ow,od,oh=7.4,2.7,3.05
    front=b.frame(ow,od,1,"blue",height=oh)[0]
    front.row(.15,oh-.09,[(2.25,1.47,.15,2.58,"lobby"),(5.25,2.26,.74,2.58,"window")],"blue")
    front.part("Depot_name_panel",ow/2,2.88,3.0,.34,"teal",.12,.10,.018)
    a.text("Depot_letters","DEPOT",front.point(ow/2,2.88,.18),.28)
    b.cornice(ow,od,oh,False)
    box("Short_office_blue_cap",(0,0,oh+.23),(ow+.42,od+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((0,-9.15,0))))


models=[
    ("produce_wholesaler","ProduceWholesaler",100,(19.0,12.0,6.1),"Long butter-yellow two-story produce warehouse with large loading shutters, small upper windows, teal canopy and shallow roof ridge.",produce_wholesaler),
    ("body_repair_workshop","BodyRepairWorkshop",101,(16.6,10.0,6.04),"Coral low body-repair workshop with broad service shutter, blue pitched roof and attached two-story office.",body_repair_workshop),
    ("small_motor_garage","SmallMotorGarage",102,(11.6,8.8,4.1),"Compact mint one-story garage with one real open service bay, one closed shutter, low parapet and offset office entrance.",small_motor_garage),
    ("long_loading_warehouse","LongLoadingWarehouse",103,(12.4,19.5,4.0),"Long low cream warehouse with five side loading shutters, broad blue pitched roof and short powder-blue front office.",long_loading_warehouse)]

extra_colliders={
    "body_repair_workshop":[((-2.4,2.0,0),(11.8,4.0,10.0)),((5.9,3.02,0),(4.8,6.04,10.0))],
    "small_motor_garage":[((0,2.05,-4.21),(11.6,4.1,.38)),((-5.61,2.05,0),(.38,4.1,8.8)),((2.8,2.05,0),(6.0,4.1,8.8)),
                           ((-5.525,2.05,4.21),(.55,4.1,.38)),((-.625,2.05,4.21),(.85,4.1,.38)),((0,3.76,4.21),(11.6,.68,.38)),
                           ((0,.075,0),(11.6,.15,8.8)),((0,4.1,0),(11.6,.18,8.8))],
    "long_loading_warehouse":[((0,2.0,0),(12.4,4.0,18.0)),((0,1.525,9.15),(7.4,3.05,2.7))]}

scene_dir=a.PROJECT/"scenes/buildings/batch_25"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=extra_colliders.get(slug,[((0,h/2,0),(w,h,d))])
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_25/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_25/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_25/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_25_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":25,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 25\n\nProduce Wholesaler (100), Body Repair Workshop (101), Small Motor Garage (102), Long Loading Warehouse (103). Approved bright pastel French Quarter style with cream trim and painted blue glazing. Broad low industrial buildings with readable loading doors, ordinary office sections and blue roofs.\n\nPlacement scenes: `scenes/buildings/batch_25/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Body boxes follow attached offices. Small Motor Garage has separate rear wall, side, front piers, header, floor and ceiling collision keeping its left service bay open; its right shutter is closed. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_25.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_25.py`.\n')
