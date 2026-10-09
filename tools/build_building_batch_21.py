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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_21"
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


def frame_office_block():
    w,d,h=14.8,10.4,3.08
    front=b.frame(w,d,4,"cream",height=h)[0]
    inset_lobby(front,.52)
    for level in range(4):
        sill,head=level*h+.61,(level+1)*h-.46
        bays=[(u,3.36,sill,head,"window") for u in (2.7,7.4,12.1)]
        if level==0:
            bays[1]=(7.4,2.15,.15,2.68,"lobby")
        front.row(level*h+.15,(level+1)*h-.09,bays,"blue_dark")
        front.part("Strong_cream_frame_band",w/2,(level+1)*h,w+.16,.38,"cream",.31,.065,.02)
    for u in (.23,5.05,9.75,w-.23):
        front.part("Full_height_cream_frame",u,6.20,.40,12.1,"cream",.32,.065,.02)
    b.cornice(w,d,4*h,False)
    box("Flat_blue_office_cap",(0,0,4*h+.23),(w+.42,d+.42,.26),"roof",.03)


def balcony_mixed_use_block():
    w,d,h=13.6,10.0,3.1
    front=b.frame(w,d,3,"coral",ground_color="cream",height=h)[0]
    front.row(.15,h-.09,[(3.0,3.9,.53,2.68,"shop"),(7.65,1.48,.15,2.68,"lobby"),
                        (11.05,2.60,.53,2.68,"shop")],"cream")
    front.part("Shared_shop_canopy",w/2,2.98,w-.55,.19,"cream",.90,.25,.025)
    for level in (1,2):
        sill,head=level*h+.33,(level+1)*h-.48
        front.row(level*h+.15,(level+1)*h-.09,[(2.45,1.53,sill,head,"door"),
                (7.25,2.50,sill+.33,head,"window"),(11.05,2.50,sill+.33,head,"window")],"coral")
        for u in (7.25,11.05):
            front.part("Paired_window_bar",u,(sill+.33+head)/2,.09,head-sill-.44,"cream",.08,-.12)
        b.gallery(front,2.45,level*h+.20,3.5,.88,"scroll")
        front.part("White_floor_band",w/2,level*h,w+.12,.21,"cream",.23,.06)
    for u in (.17,w-.17):
        front.part("Cream_corner_trim",u,4.70,.28,8.95,"cream",.23,.055)
    b.cornice(w,d,3*h,True)
    a.parapet("Top_terrace_edge",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],3*h+.17,"cream",.56)
    before={obj.name for obj in a.collection.objects}
    uw,ud=10.8,8.0
    upper=b.frame(uw,ud,1,"coral",height=h)[0]
    upper.row(.15,h-.09,[(2.0,1.50,.15,2.60,"door"),(5.45,2.12,.65,2.60,"window"),
                         (8.80,2.12,.65,2.60,"window")],"coral")
    b.shutters(upper,5.45,.65,2.12,1.95,"mint_dark")
    b.cornice(uw,ud,h,False)
    box("Top_blue_cap",(0,0,h+.23),(uw+.42,ud+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((.7,.7,3*h))))
    a.planter("Terrace_corner_pot",(-5.63,-3.85,3*h+.18),.34,.48)


def long_city_office():
    w,d,h=19.0,8.4,3.05
    front=b.frame(w,d,3,"blue",height=h)[0]
    for level in range(3):
        sill,head=level*h+.71,(level+1)*h-.46
        bays=[(u,2.38,sill,head,"window") for u in (1.9,5.7,9.5,13.3,17.1)]
        if level==0:
            bays[2]=(9.5,2.0,.15,2.59,"lobby")
        front.row(level*h+.15,(level+1)*h-.09,bays,"blue")
        front.part("Quiet_cream_band",w/2,(level+1)*h,w+.13,.18,"cream",.22,.04)
    for u in (.18,w-.18):
        front.part("Long_office_corner_trim",u,4.63,.27,8.82,"cream",.23,.055)
    b.cornice(w,d,3*h,False)
    box("Main_flat_blue_cap",(0,0,3*h+.23),(w+.42,d+.42,.26),"roof",.03)
    before={obj.name for obj in a.collection.objects}
    lw,ld=5.8,3.0
    lobby=b.frame(lw,ld,1,"cream",height=h)[0]
    lobby.row(.15,h-.09,[(lw/2,2.45,.15,2.60,"lobby")],"cream")
    for u in (.22,lw-.22):
        lobby.part("Lobby_blue_pier",u,1.57,.27,2.84,"blue",.22,.065)
    b.cornice(lw,ld,h,False)
    box("Lower_entrance_blue_cap",(0,0,h+.24),(lw+.42,ld+.42,.27),"roof",.03)
    move_new(before,Matrix.Translation(Vector((0,-5.0,0))))


def capped_civic_office():
    w,d,h=14.0,10.0,3.2
    front=b.frame(w,d,3,"cream",height=h)[0]
    inset_lobby(front,.54)
    front.row(.15,h-.09,[(2.45,2.55,.72,2.85,"window"),(7.0,2.50,.15,2.85,"lobby"),
                        (11.55,2.55,.72,2.85,"window")],"cream")
    for level in (1,2):
        sill,head=level*h+.48,(level+1)*h-.40
        front.row(level*h+.15,(level+1)*h-.09,[(u,1.85,sill,head,"window") for u in (2.1,5.35,8.65,11.9)],"cream")
        for u in (2.1,5.35,8.65,11.9):
            front.part("Tall_window_blue_brow",u,head+.19,2.23,.15,"blue_dark",.15,.055,.012)
        front.part("Civic_floor_band",w/2,level*h,w+.15,.27,"cream",.28,.06)
    for u in (.23,w-.23):
        front.part("Civic_corner_pilaster",u,4.85,.39,9.25,"cream",.30,.075)
    for x in (-2.32,2.32):
        box("Lobby_column_base",(x,-6.0,.20),(.68,.68,.40),"cream",.035)
        box("Lobby_column",(x,-6.0,1.67),(.42,.42,2.68),"cream",.03)
        box("Lobby_column_capital",(x,-6.0,3.04),(.70,.70,.22),"cream",.025)
    box("Portico_cream_entablature",(0,-5.72,3.26),(5.60,2.32,.30),"cream",.035)
    box("Portico_blue_lip",(0,-5.72,3.47),(5.76,2.47,.13),"roof",.025)
    b.cornice(w,d,3*h,True)
    low,peak=3*h+.20,3*h+1.28
    halfw,halfd=w/2+.20,d/2+.20
    vertices=[(-halfw,-halfd,low),(halfw,-halfd,low),(halfw,halfd,low),(-halfw,halfd,low),(0,0,peak)]
    mesh("Shallow_pyramidal_blue_roof",vertices,[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],"roof")
    box("Cream_roof_finial",(0,0,peak+.06),(.23,.23,.15),"cream",.02)


models=[
    ("frame_office_block","FrameOfficeBlock",84,(14.8,10.4,12.32),"Broad four-story office with a substantial cream facade grid, muted navy infill and recessed central doorway.",frame_office_block),
    ("balcony_mixed_use_block","BalconyMixedUseBlock",85,(13.6,10.0,12.4),"Coral four-story neighborhood block over shops; stacked ornamental balconies, paired windows and small top terrace.",balcony_mixed_use_block),
    ("long_city_office","LongCityOffice",86,(19.0,8.4,9.15),"Long powder-blue three-story office with repeating blue windows, quiet cream cornice and lower projecting entrance.",long_city_office),
    ("capped_civic_office","CappedCivicOffice",87,(14.0,10.0,9.6),"Broad cream three-story civic office; tall blue windows, columned lobby and shallow blue pyramidal roof.",capped_civic_office)]

extra_colliders={
    "balcony_mixed_use_block":[((0,4.65,0),(13.6,9.3,10.0)),((.7,10.85,-.7),(10.8,3.1,8.0))],
    "long_city_office":[((0,4.575,0),(19.0,9.15,8.4)),((0,1.525,5.0),(5.8,3.05,3.0))],
    "capped_civic_office":[((0,4.8,0),(14.0,9.6,10.0)),((-2.32,1.55,6.0),(.68,3.1,.68)),((2.32,1.55,6.0),(.68,3.1,.68))]}

scene_dir=a.PROJECT/"scenes/buildings/batch_21"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=extra_colliders.get(slug,[((0,h/2,0),(w,h,d))])
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_21/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_21/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_21/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_21_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":21,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 21\n\nFrame Office Block (084), Balcony Mixed-Use Block (085), Long City Office (086), Capped Civic Office (087). Approved pastel French Quarter style, cream trim, painted blue glazing and broad three- or four-story proportions.\n\nPlacement scenes: `scenes/buildings/batch_21/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Body boxes follow the upper terrace room and projecting lobby; civic columns also collide. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_21.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_21.py`.\n')
