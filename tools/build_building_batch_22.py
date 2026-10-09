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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_22"
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


def three_wing_office():
    for w,d,cx,cy,h,color,center in ((5.2,10.8,-6.3,0,3.0,"mint",False),
                                    (7.4,8.4,0,1.2,3.1,"cream",True),
                                    (5.2,9.0,6.3,.9,3.18,"mint",False)):
        before={obj.name for obj in a.collection.objects}
        front=b.frame(w,d,3,color,height=h)[0]
        for level in range(3):
            sill,head=level*h+.67,(level+1)*h-.47
            if center and level==0:
                bays=[(1.32,1.18,.78,2.64,"window"),(3.7,1.70,.15,2.64,"lobby"),
                      (6.08,1.18,.78,2.64,"window")]
            else:
                bays=[(w*f,1.80 if center else 1.15,sill,head,"window") for f in (.25,.75)]
            front.row(level*h+.15,(level+1)*h-.09,bays,color)
            front.part("Cream_floor_band",w/2,(level+1)*h,w+.12,.23,"cream",.24,.055)
        for u in (.17,w-.17):
            front.part("Cream_wing_pier",u,1.5*h,.27,3*h-.3,"cream",.23,.055)
        if center:
            front.part("Recessed_entry_canopy",w/2,2.87,2.49,.18,"roof",.90,.25,.025)
        b.cornice(w,d,3*h,False)
        a.parapet("Matching_cream_parapet",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],3*h+.17,"cream",.35)
        move_new(before,Matrix.Translation(Vector((cx,cy,0))))


def department_store():
    w,d,h=18.4,13.0,3.12
    walls=rectangle(w,d,"Department")
    box("Department_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    for level in range(4):
        z=level*h
        box("Department_floor_plate",(0,0,(level+1)*h),(w,d,.18),"cream")
        for index,wall in enumerate(walls):
            if level==0 and index==0:
                bays=[(3.1,4.80,.43,2.77,"shop"),(9.2,3.05,.15,2.77,"lobby"),
                      (15.3,4.80,.43,2.77,"shop")]
            elif level==0 and index==3:
                bays=[(3.25,3.70,.43,2.77,"shop"),(9.75,3.70,.43,2.77,"shop")]
            elif level==0:
                bays=[(wall.length*.48,1.22,.15,2.63,"door"),(wall.length*.76,2.07,.82,2.63,"window")]
            else:
                count=5 if wall.length>15 else 3
                bays=[(wall.length*(j+.5)/count,2.16,z+.72,(level+1)*h-.49,"window") for j in range(count)]
            wall.row(z+.15,(level+1)*h-.09,bays,"coral" if level==0 else "cream")
            wall.part("Wraparound_cream_band",wall.length/2,(level+1)*h,wall.length+.17,.29,"cream",.29,.055,.018)
    for wall in walls:
        wall.part("Cream_base",wall.length/2,.29,wall.length,.28,"cream",.20,.02)
        for u in (.19,wall.length-.19):
            wall.part("Store_corner_pier",u,6.30,.33,12.08,"cream",.27,.065)
    front=walls[0]
    front.part("Entry_canopy",9.2,2.98,4.28,.18,"cream",1.18,.39,.025)
    front.part("Coral_store_name_panel",9.2,3.39,6.8,.46,"coral_dark",.14,.08,.02)
    a.text("Department_store_name","DEPARTMENT",front.point(9.2,3.39,.17),.40)
    b.cornice(w,d,4*h,True)
    a.parapet("Store_roof_border",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],4*h+.17,"coral",.42)
    box("Low_roof_service_room",(4.7,4.35,4*h+.65),(3.6,3.2,.96),"cream",.035)
    box("Service_room_blue_cap",(4.7,4.35,4*h+1.19),(3.84,3.44,.17),"roof",.025)


def supermarket():
    w,d,h=19.0,12.0,4.2
    front=b.frame(w,d,1,"mint",height=h)[0]
    front.row(.15,h-.09,[(4.1,5.60,.42,3.43,"shop"),(9.5,2.65,.15,3.43,"lobby"),
                        (14.9,5.60,.42,3.43,"shop")],"mint")
    for u in (4.1,14.9):
        for du in (-1.0,1.0):
            front.part("Broad_storefront_mullion",u+du,1.92,.10,2.88,"teal",.07,-.12)
    front.part("Long_cream_canopy",w/2,3.64,w-.62,.21,"cream",1.62,.55,.025)
    front.part("Canopy_mint_fascia",w/2,3.62,w-.62,.28,"mint_dark",.13,1.40,.018)
    front.part("Market_sign_panel",w/2,4.03,4.46,.40,"mint_dark",.16,.08,.02)
    a.text("Market_letters","MARKET",front.point(w/2,4.03,.18),.37)
    for u in (.20,w-.20):
        front.part("Supermarket_corner_trim",u,2.13,.31,3.94,"cream",.24,.055)
    b.cornice(w,d,h,False)
    box("Supermarket_blue_roof",(0,0,h+.23),(w+.42,d+.42,.26),"roof",.03)
    sw,sd,sz=10.8,4.8,h+.15
    before={obj.name for obj in a.collection.objects}
    box("Stockroom_floor",(0,0,sz+.02),(sw,sd,.16),"cream")
    for i,wall in enumerate(rectangle(sw,sd,"Raised_stockroom")):
        bays=[(u,1.55,sz+.36,sz+1.10,"window") for u in (2.1,5.4,8.7)] if i==0 else []
        wall.row(sz+.10,sz+1.46,bays,"mint_dark")
    b.cornice(sw,sd,sz+1.55,False)
    box("Taller_stockroom_blue_cap",(0,0,sz+1.78),(sw+.42,sd+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((0,3.5,0))))


def garden_office():
    w,d,h=17.6,10.4,3.15
    front=b.frame(w,d,3,"blue",height=h)[0]
    inset_lobby(front,.62)
    front.row(.15,h-.09,[(3.0,3.30,.78,2.70,"window"),(8.8,2.40,.15,2.70,"lobby"),
                        (14.6,3.30,.78,2.70,"window")],"blue")
    for level in (1,2):
        sill,head=level*h+.67,(level+1)*h-.45
        front.row(level*h+.15,(level+1)*h-.09,[(u,3.24,sill,head,"window") for u in (2.4,6.67,10.93,15.2)],"blue")
        front.part("Garden_cream_band",w/2,level*h,w+.12,.22,"cream",.24,.055)
    for u in (.18,w-.18):
        front.part("Garden_corner_pier",u,4.78,.29,9.10,"cream",.24,.055)
    front.part("Inset_lobby_canopy",w/2,2.94,3.20,.19,"cream",1.07,.34,.025)
    b.cornice(w,d,3*h,False)
    box("Garden_flat_blue_cap",(0,0,3*h+.23),(w+.42,d+.42,.26),"roof",.03)
    for x in (-5.8,5.8):
        for y in (-6.335,-5.665):
            box("Front_planter_long_wall",(x,y,.40),(5.60,.13,.56),"cream",.02)
            box("Front_planter_long_cap",(x,y,.72),(5.72,.20,.11),"cream",.018)
        for dx in (-2.735,2.735):
            box("Front_planter_end_wall",(x+dx,-6.0,.40),(.13,.67,.56),"cream",.02)
        box("Planter_soil",(x,-6.0,.53),(5.35,.55,.11),"stone")
        for i in range(-2,3):
            a.shrub("Low_planter_hedge",(x+i*.97,-6.0,.98),(.72,.32,.45),"green" if i%2 else "green_dark")


models=[
    ("three_wing_office","ThreeWingOffice",88,(17.8,10.8,9.54),"Three connected mint and cream three-story wings with a recessed central entrance and gently staggered matching parapets.",three_wing_office),
    ("department_store","DepartmentStore",89,(18.4,13.0,12.48),"Broad cream four-story department store with coral ground floor, large street glazing and a strong wraparound cornice.",department_store),
    ("supermarket","Supermarket",90,(19.0,12.0,5.9),"Low wide mint supermarket with two broad glazed bays, a long cream canopy and taller enclosed rear stockroom.",supermarket),
    ("garden_office","GardenOffice",91,(17.6,10.4,9.45),"Wide powder-blue three-story office with a central inset lobby, broad upper windows and two low front planters.",garden_office)]

extra_colliders={
    "three_wing_office":[((-6.3,4.5,0),(5.2,9.0,10.8)),((0,4.65,-1.2),(7.4,9.3,8.4)),((6.3,4.77,-.9),(5.2,9.54,9.0))],
    "supermarket":[((0,2.1,0),(19.0,4.2,12.0)),((0,5.05,-3.5),(10.8,1.7,4.8))],
    "garden_office":[((0,4.725,0),(17.6,9.45,10.4)),((-5.8,.4,6.0),(5.6,.8,.8)),((5.8,.4,6.0),(5.6,.8,.8))]}

scene_dir=a.PROJECT/"scenes/buildings/batch_22"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=extra_colliders.get(slug,[((0,h/2,0),(w,h,d))])
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_22/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_22/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_22/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_22_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":22,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 22\n\nThree-Wing Office (088), Department Store (089), Supermarket (090), Garden Office (091). Approved pastel French Quarter style, substantial cream trim, recessed blue glazing and broad one- to four-story proportions.\n\nPlacement scenes: `scenes/buildings/batch_22/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Separate body boxes retain the recessed three-wing entrance and raised stockroom; front planters collide. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_22.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_22.py`.\n')
