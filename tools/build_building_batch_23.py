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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_23"
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


def courtyard_shopping_centre():
    h=3.12
    for cx in (-7.15,7.15):
        before={obj.name for obj in a.collection.objects}
        w,d=4.7,12.0
        walls=rectangle(w,d,"Shopping_wing")
        box("Wing_foundation",(0,0,.075),(w,d,.15),"stone",.025)
        for level in range(2):
            box("Wing_floor",(0,0,(level+1)*h),(w,d,.18),"cream")
            for i,wall in enumerate(walls):
                inner=i==(1 if cx<0 else 3)
                if i==0:
                    bays=[(w/2,2.82,.35 if level==0 else h+.68,2.65 if level==0 else 2*h-.48,"shop" if level==0 else "window")]
                elif inner:
                    centers=(2.3,6.0) if cx<0 else (6.0,9.7)
                    bays=[(u,2.95 if level==0 else 1.86,level*h+.35 if level==0 else level*h+.66,(level+1)*h-.48,"shop" if level==0 else "window") for u in centers]
                else:
                    centers=(wall.length*.27,wall.length*.73)
                    bays=[(u,1.15,level*h+.78,(level+1)*h-.48,"window") for u in centers]
                wall.row(level*h+.15,(level+1)*h-.09,bays,"yellow")
                wall.part("Cream_shop_floor_band",wall.length/2,(level+1)*h,wall.length+.12,.22,"cream",.24,.05)
                if level==0 and inner:
                    wall.part("Court_continuous_canopy",3.9 if cx<0 else 8.1,2.92,7.50,.18,"cream",1.15,.40,.025)
                    wall.part("Court_teal_canopy_edge",3.9 if cx<0 else 8.1,2.88,7.50,.22,"teal",.10,1.00,.015)
        b.cornice(w,d,2*h,False)
        a.parapet("Wing_yellow_roof_edge",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],2*h+.17,"yellow",.40)
        move_new(before,Matrix.Translation(Vector((cx,0,0))))
    before={obj.name for obj in a.collection.objects}
    w,d=9.6,4.2
    front=b.frame(w,d,2,"yellow",height=h)[0]
    front.row(.15,h-.09,[(2.0,2.25,.38,2.65,"shop"),(4.8,1.55,.15,2.65,"lobby"),(7.6,2.25,.38,2.65,"shop")],"yellow")
    front.row(h+.15,2*h-.09,[(u,1.70,h+.66,2*h-.48,"window") for u in (2.0,4.8,7.6)],"yellow")
    front.part("Central_court_canopy",w/2,2.92,w-.42,.18,"cream",1.20,.41,.025)
    front.part("Teal_entry_panel",w/2,3.33,3.5,.45,"teal",.14,.12,.02)
    a.text("Court_letters","COURT",front.point(w/2,3.33,.21),.34)
    b.cornice(w,d,2*h,True)
    a.parapet("Rear_yellow_roof_edge",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],2*h+.17,"yellow",.40)
    front.part("Raised_central_entry_crown",w/2,6.95,3.9,.74,"yellow",.22,-.04,.02)
    front.part("Crown_cream_cap",w/2,7.35,4.08,.13,"cream",.36,-.02,.015)
    move_new(before,Matrix.Translation(Vector((0,3.9,0))))


def neighborhood_bank():
    w,d,h=15.4,10.0,3.35
    front=b.frame(w,d,2,"cream",height=h)[0]
    inset_lobby(front,.73)
    front.row(.15,h-.09,[(2.1,2.35,.77,2.86,"window"),(6.0,2.15,.15,2.86,"lobby"),
                        (9.4,2.15,.15,2.86,"lobby"),(13.3,2.35,.77,2.86,"window")],"cream")
    front.row(h+.15,2*h-.09,[(u,1.84,h+.62,2*h-.44,"window") for u in (2.1,5.85,9.55,13.3)],"cream")
    for u in (2.1,5.85,9.55,13.3):
        front.part("Navy_window_brow",u,2*h-.26,2.20,.14,"blue_dark",.16,.06,.012)
    for x in (-3.4,0,3.4):
        box("Bank_pier_foot",(x,-5.64,.20),(.92,.92,.40),"cream",.035)
        box("Thick_bank_entrance_pier",(x,-5.64,1.73),(.64,.64,2.76),"cream",.03)
        box("Bank_pier_capital",(x,-5.64,3.14),(.95,.95,.23),"cream",.025)
    box("Bank_entrance_entablature",(0,-5.46,3.38),(8.66,1.85,.29),"cream",.035)
    box("Bank_navy_canopy_lip",(0,-5.46,3.57),(8.82,2.03,.13),"roof",.025)
    front.part("Navy_bank_name_panel",w/2,3.82,4.04,.43,"blue_dark",.15,.095,.02)
    a.text("Bank_name","BANK",front.point(w/2,3.82,.19),.36)
    for u in (.20,w-.20):
        front.part("Bank_corner_pier",u,3.40,.35,6.44,"cream",.28,.07)
    b.cornice(w,d,2*h,True)
    box("Bank_flat_blue_cap",(0,0,2*h+.23),(w+.42,d+.42,.26),"roof",.03)
    box("Raised_lobby_roof_section",(0,1.9,2*h+.71),(6.6,5.0,.90),"cream",.035)
    box("Raised_lobby_blue_cap",(0,1.9,2*h+1.23),(6.84,5.24,.17),"roof",.025)


def corner_clinic():
    h=3.05
    outline=[(-7.2,-3.1),(-5.1,-5.2),(7.2,-5.2),(7.2,5.2),(-7.2,5.2)]
    a.prism("Clinic_foundation",outline,0,.15,"stone",.025)
    walls=[]
    for i,p in enumerate(outline):
        q=outline[(i+1)%len(outline)]
        walls.append(a.Wall("Clinic_face_%d"%i,p,q,(q[1]-p[1],p[0]-q[0])))
    for level in range(4):
        a.prism("Clinic_floor_plate",outline,(level+1)*h-.09,(level+1)*h+.09,"cream",.015)
        for i,wall in enumerate(walls):
            if i==0:
                bays=[(wall.length/2,1.96 if level==0 else 1.68,.15 if level==0 else level*h+.74,(level+1)*h-.47,"lobby" if level==0 else "window")]
            elif i==1:
                if level==0:
                    bays=[(3.0,4.10,.53,2.61,"shop"),(9.15,4.10,.53,2.61,"shop")]
                else:
                    bays=[(u,3.11,level*h+.93,(level+1)*h-.60,"window") for u in (2.05,6.15,10.25)]
            else:
                count=3 if wall.length>=10 else 2
                bays=[(wall.length*(j+1)/(count+1),2.12,level*h+.88,(level+1)*h-.55,"window") for j in range(count)]
            wall.row(level*h+.15,(level+1)*h-.09,bays,"mint")
            wall.part("Clinic_cream_floor_band",wall.length/2,(level+1)*h,wall.length+.13,.24,"cream",.27,.055)
    for wall in walls:
        wall.part("Clinic_cream_base",wall.length/2,.29,wall.length,.28,"cream",.20,.02)
        for u in (.17,wall.length-.17):
            wall.part("Clinic_facet_trim",u,6.16,.28,11.90,"cream",.23,.055)
        wall.part("Clinic_wrap_cornice",wall.length/2,4*h+.04,wall.length+.19,.27,"cream",.42,.055,.025)
    corner=walls[0]
    corner.part("Corner_glazed_entry_canopy",corner.length/2,2.90,2.46,.18,"cream",1.04,.34,.025)
    corner.part("Clinic_symbol_panel",corner.length/2,3.33,.69,.55,"teal",.13,.12,.02)
    corner.part("Clinic_plus_horizontal",corner.length/2,3.33,.35,.09,"cream",.04,.20)
    corner.part("Clinic_plus_vertical",corner.length/2,3.33,.09,.35,"cream",.04,.20)
    a.prism("Clinic_faceted_blue_roof",[(x*1.012,y*1.012) for x,y in outline],4*h+.19,4*h+.43,"roof",.03)


def hardware_superstore():
    w,d,h=13.8,12.0,4.25
    before={obj.name for obj in a.collection.objects}
    walls=rectangle(w,d,"Hardware_shed")
    box("Hardware_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Hardware_ceiling",(0,0,h),(w,d,.18),"cream")
    for i,wall in enumerate(walls):
        if i==0:
            bays=[(3.2,4.2,.48,3.52,"shop"),(9.4,4.2,.48,3.52,"shop")]
        elif i==3:
            bays=[(6.8,4.2,.15,3.66,"loading")]
            original=wall.window
            def loading_window(u,sill,width,height,kind="window",wall=wall,original=original):
                if kind!="loading":
                    return original(u,sill,width,height,kind)
                wall.part("Closed_loading_shutter",u,sill+height/2,width,height,"roof",.14,-.14,.025)
                for z in (sill+.28,sill+.90,sill+1.52,sill+2.14,sill+2.76,sill+3.30):
                    wall.part("Loading_shutter_slat",u,z,width-.14,.07,"reflection",.06,-.035)
                for du in (-width/2,width/2):
                    wall.part("Loading_cream_jamb",u+du,sill+height/2,.17,height+.14,"cream",.22,.025)
                wall.part("Loading_cream_header",u,sill+height,width+.25,.17,"cream",.22,.025)
            wall.window=loading_window
        else:
            bays=[(wall.length*.5,2.50,2.42,3.56,"window")]
        wall.row(.15,h-.09,bays,"yellow")
        wall.part("Hardware_cream_base",wall.length/2,.29,wall.length,.28,"cream",.20,.02)
    front=walls[0]
    front.part("Deep_store_canopy",w/2,3.83,w-.44,.20,"cream",1.68,.57,.025)
    front.part("Blue_canopy_fascia",w/2,3.80,w-.44,.28,"roof",.14,1.37,.015)
    b.cornice(w,d,h,False)
    b.hip_roof(w,d,h+.19,h+1.19)
    move_new(before,Matrix.Translation(Vector((-2.6,0,0))))
    before={obj.name for obj in a.collection.objects}
    ow,od,oh=5.2,12.0,3.02
    office=b.frame(ow,od,2,"yellow",height=oh)[0]
    office.row(.15,oh-.09,[(1.38,1.31,.15,2.57,"lobby"),(3.93,1.27,.78,2.57,"window")],"yellow")
    office.row(oh+.15,2*oh-.09,[(u,1.35,oh+.65,2*oh-.47,"window") for u in (1.35,3.85)],"yellow")
    office.part("Office_cream_band",ow/2,oh,ow+.12,.24,"cream",.25,.055)
    office.part("Hardware_name_panel",ow/2,3.34,4.55,.47,"roof",.15,.11,.02)
    a.text("Hardware_letters","HARDWARE",office.point(ow/2,3.34,.21),.35)
    b.cornice(ow,od,2*oh,False)
    box("Office_blue_roof_cap",(0,0,2*oh+.23),(ow+.42,od+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((6.9,0,0))))


models=[
    ("courtyard_shopping_centre","CourtyardShoppingCentre",92,(19.0,12.0,6.24),"Butter-yellow two-story shops around an open front courtyard; continuous teal-edged canopies and raised central entry crown.",courtyard_shopping_centre),
    ("neighborhood_bank","NeighborhoodBank",93,(15.4,10.0,6.7),"Broad cream two-story bank with three thick entrance piers, recessed blue doors and a short raised lobby roof section.",neighborhood_bank),
    ("corner_clinic","CornerClinic",94,(14.4,10.4,12.2),"Mint four-story corner clinic with a chamfered glazed entrance, long narrow blue window groups and thick cream trim.",corner_clinic),
    ("hardware_superstore","HardwareSuperstore",95,(19.0,12.0,6.04),"Low butter-yellow hardware shed with blue roof, deep canopy, closed side loading door and attached two-story office.",hardware_superstore)]

extra_colliders={
    "courtyard_shopping_centre":[((-7.15,3.12,0),(4.7,6.24,12.0)),((7.15,3.12,0),(4.7,6.24,12.0)),((0,3.12,-3.9),(9.6,6.24,4.2))],
    "neighborhood_bank":[((0,3.35,0),(15.4,6.7,10.0)),((-3.4,1.65,5.64),(.92,3.3,.92)),((0,1.65,5.64),(.92,3.3,.92)),((3.4,1.65,5.64),(.92,3.3,.92))],
    "corner_clinic":[((1.05,6.1,0),(12.3,12.2,10.4)),((-6.15,6.1,-1.05),(2.1,12.2,8.3))],
    "hardware_superstore":[((-2.6,2.125,0),(13.8,4.25,12.0)),((6.9,3.02,0),(5.2,6.04,12.0))]}
clinic_hull=[(-7.2,0,3.1),(-5.1,0,5.2),(-5.1,0,3.1),(-7.2,12.2,3.1),(-5.1,12.2,5.2),(-5.1,12.2,3.1)]

scene_dir=a.PROJECT/"scenes/buildings/batch_23"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=extra_colliders.get(slug,[((0,h/2,0),(w,h,d))])
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_23/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    hull=clinic_hull if slug=="corner_clinic" else []
    if hull:
        entry["collision_hull_godot_m"]=hull
    parts=[f'[gd_scene load_steps={len(colliders)+2+(1 if hull else 0)} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_23/{slug}.glb" id="1"]\n']
    for i,(_,dim) in enumerate(colliders):
        parts.append(f'[sub_resource type="BoxShape3D" id="Body{i}"]\nsize = Vector3({dim[0]}, {dim[1]}, {dim[2]})\n')
    if hull:
        values=", ".join(str(v) for point in hull for v in point)
        parts.append('[sub_resource type="ConvexPolygonShape3D" id="CornerHull"]\npoints = PackedVector3Array('+values+')\n')
    parts.extend([f'[node name="{name}" type="Node3D"]\n',
                  '[node name="Visual" parent="." instance=ExtResource("1")]\n',
                  '[node name="BuildingBody" type="StaticBody3D" parent="."]\ncollision_layer = 1\ncollision_mask = 0\n'])
    for i,(at,_) in enumerate(colliders):
        node="Collision" if i==0 else f"Collision{i}"
        parts.append(f'[node name="{node}" type="CollisionShape3D" parent="BuildingBody"]\nposition = Vector3({at[0]}, {at[1]}, {at[2]})\nshape = SubResource("Body{i}")\n')
    if hull:
        parts.append('[node name="CornerCollision" type="CollisionShape3D" parent="BuildingBody"]\nshape = SubResource("CornerHull")\n')
    (scene_dir/(slug+".tscn")).write_text('\n'.join(parts))
    import_path=a.ASSET/(slug+".glb.import")
    if not import_path.exists():
        template=(a.PROJECT/"assets/models/buildings/batch_01/corner_cafe.glb.import").read_text()
        resource_path="res://assets/models/buildings/batch_23/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_23_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":23,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 23\n\nCourtyard Shopping Centre (092), Neighborhood Bank (093), Corner Clinic (094), Hardware Superstore (095). Approved pastel French Quarter style, chunky cream trim, recessed blue glass, broad neighborhood proportions.\n\nPlacement scenes: `scenes/buildings/batch_23/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Three body boxes keep the shopping courtyard open; clinic collision follows the chamfer with two boxes and a triangular convex prism. Bank piers collide, and the hardware shed and office have separate boxes. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_23.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_23.py`.\n')
