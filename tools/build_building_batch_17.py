"""Four neighborhood Lowcar residential blocks using the approved pastel architectural kit."""
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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_17"
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


def twin_stair_apartments():
    w,d,h=11.0,8.7,3.1
    before={obj.name for obj in a.collection.objects}
    front=b.frame(w,d,4,"yellow",height=h)[0]
    front.row(.15,h-.09,[(2.0,2.10,.77,2.64,"window"),(5.5,1.50,.15,2.64,"lobby"),
                        (9.0,2.10,.77,2.64,"window")],"yellow")
    for level in (1,2,3):
        sill,head=level*h+.69,(level+1)*h-.50
        front.row(level*h+.15,(level+1)*h-.09,[(u,1.54,sill,head,"window") for u in (1.55,4.15,6.85,9.45)],"yellow")
        front.part("Cream_window_grid_band",w/2,level*h,w+.12,.24,"cream",.24,.065)
    for u in (.17,2.85,5.5,8.15,w-.17):
        front.part("Upper_grid_pier",u,7.76,.20,8.85,"cream",.22,.06)
    front.part("Lobby_canopy",5.5,2.90,2.17,.18,"cream",1.17,.39,.025)
    b.cornice(w,d,4*h,False)
    box("Main_blue_roof",(0,0,4*h+.23),(w+.36,d+.36,.25),"roof",.025)
    box("Shallow_central_setback",(0,1.51,4*h+.59),(4.7,3.9,.66),"yellow",.03)
    box("Setback_cream_cap",(0,1.51,4*h+.98),(4.93,4.13,.13),"cream",.025)
    move_new(before,Matrix.Translation(Vector((0,.50,0))))
    for cx in (-6.7,6.7):
        before={obj.name for obj in a.collection.objects}
        sw,sd=2.4,9.7
        walls=rectangle(sw,sd,"Coral_stair_spine")
        box("Stair_spine_foundation",(0,0,.075),(sw,sd,.15),"stone",.025)
        for level in range(4):
            low,high=level*h+.15,(level+1)*h-.09
            box("Stair_floor",(0,0,(level+1)*h),(sw,sd,.18),"cream")
            for i,wall in enumerate(walls):
                bays=[(wall.length/2,.84,level*h+.73,high-.47,"window")] if i in (0,2) else [(wall.length*f,1.17,level*h+.75,high-.47,"window") for f in (.28,.72)]
                wall.row(low,high,bays,"coral")
            walls[0].part("Cream_floor_band",sw/2,(level+1)*h,sw+.10,.18,"cream",.24,.05)
        for u in (.12,sw-.12):
            walls[0].part("Stair_corner_trim",u,6.24,.23,12.02,"cream",.20,.05)
        walls[0].part("Cream_plinth",sw/2,.29,sw,.28,"cream",.19,.02)
        b.cornice(sw,sd,4*h,False)
        box("Stair_spine_roof_cap",(0,0,4*h+.29),(sw+.39,sd+.39,.31),"coral_dark",.025)
        move_new(before,Matrix.Translation(Vector((cx,0,0))))


def shopfront_apartments():
    w,d,h=13.4,9.2,3.1
    front=b.frame(w,d,4,"mint",ground_color="cream",height=h)[0]
    bays=[(2.00,2.40,.36,2.70,"shop"),(4.25,1.20,.15,2.70,"door"),(6.70,1.28,.15,2.70,"lobby"),
          (9.15,1.20,.15,2.70,"door"),(11.40,2.40,.36,2.70,"shop")]
    front.row(.15,h-.09,bays,"cream")
    front.part("Shared_shop_canopy",w/2,3.18,w-.30,.17,"cream",1.16,.49,.025)
    front.part("Canopy_teal_valance",w/2,3.05,w-.35,.14,"teal",.10,1.04)
    for u,words in ((2.95,"MARKET"),(10.45,"BAKERY")):
        front.part("Shop_sign_board",u,2.90,3.59,.32,"teal",.10,.115,.015)
        a.text("Shop_sign_letters",words,front.point(u,2.90,.185),.24)
    for level in (1,2,3):
        sill,head=level*h+.65,(level+1)*h-.50
        centers=(1.67,5.0,8.40,11.73)
        front.row(level*h+.15,(level+1)*h-.09,[(u,1.54,sill,head,"window") for u in centers],"mint")
        for u in centers[::2] if level!=2 else centers[1::2]:
            for z in (sill+.09,sill+.98):
                front.part("Juliet_horizontal_rail",u,z,1.80,.08,"cream",.085,.23)
            for du in (-.78,-.39,0,.39,.78):
                front.part("Juliet_rail_spindle",u+du,sill+.53,.055,.87,"cream",.06,.23)
        if level in (1,3):
            for u in (1.67,11.73):
                b.shutters(front,u,sill,1.54,head-sill,"blue_dark")
        front.part("Cream_floor_trim",w/2,level*h,w+.1,.18,"cream",.22,.04)
    for u in (.17,w-.17):
        front.part("Cream_corner_trim",u,6.22,.28,12.02,"cream",.21,.06)
    flat_roof(w,d,4*h,"mint",.38)


def vertical_pier_apartments():
    w,d,h=14.2,10.0,3.1
    front=b.frame(w,d,3,"coral_dark",height=h)[0]
    for level in range(3):
        sill,head=level*h+.49,(level+1)*h-.44
        bays=[(u,1.80,sill,head,"window") for u in (1.6,4.55,7.55)]+[(u,1.25,sill,head,"window") for u in (10.4,12.75)]
        if level==0:
            bays[1]=(4.55,1.36,.15,2.66,"door")
        front.row(level*h+.15,(level+1)*h-.09,bays,"coral_dark")
        front.part("Broad_cream_band",w/2,(level+1)*h,w+.15,.22,"cream",.27,.065)
    for u in (.2,3.1,6.15,9.1):
        front.part("Tall_cream_vertical_pier",u,6.24,.40,12.02,"cream",.31,.085)
    for u in (11.5,14.0):
        front.part("Lower_cream_vertical_pier",u,4.67,.40,8.89,"cream",.31,.085)
    front.part("Entrance_canopy",4.55,2.91,1.89,.18,"cream",.83,.25,.025)
    b.cornice(w,d,3*h,False)
    outline=[(-7.1,-5),(2.0,-5),(2.0,-2.2),(7.1,-2.2),(7.1,5),(-7.1,5)]
    a.prism("L_shaped_upper_floor",outline,3*h-.02,3*h+.16,"cream",.015)
    a.prism("L_shaped_roof_plate",outline,4*h-.09,4*h+.09,"cream",.015)
    for i,p in enumerate(outline):
        q=outline[(i+1)%len(outline)]
        wall=a.Wall("Upper_L_facade",p,q,(q[1]-p[1],p[0]-q[0]))
        if i==0:
            bays=[(u,1.80,3*h+.49,4*h-.44,"window") for u in (1.6,4.55,7.55)]
        elif i==2:
            bays=[(wall.length/2,2.80,3*h+.68,4*h-.48,"window")]
        else:
            count=1 if wall.length<4 else 2 if wall.length<11 else 3
            bays=[(wall.length*(j+1)/(count+1),1.42,3*h+.65,4*h-.48,"window") for j in range(count)]
        wall.row(3*h+.15,4*h-.09,bays,"coral_dark")
        wall.part("Cream_crown",wall.length/2,4*h+.04,wall.length+.19,.26,"cream",.39,.055,.025)
    a.prism("Blue_L_roof_cap",outline,4*h+.18,4*h+.39,"roof",.025)
    a.parapet("Small_corner_terrace",[(2.15,-4.85),(6.92,-4.85),(6.92,-2.27),(2.15,-2.27)],3*h+.17,"coral_dark",.49)
    a.planter("Terrace_pot",(6.26,-3.69,3*h+.11),.32,.45)


def stepped_city_office():
    w,d,h=14.8,10.0,3.05
    front=b.frame(w,d,3,"blue",ground_color="cream",height=h)[0]
    front.row(.15,h-.09,[(3.0,1.93,.15,2.59,"lobby"),(9.29,6.18,.83,2.59,"window")],"cream")
    for du in (-2.03,-1.015,0,1.015,2.03):
        front.part("Ground_glazing_mullion",9.29+du,1.71,.073,1.64,"ink",.06,-.13)
    for level in (1,2):
        sill,head=level*h+.73,(level+1)*h-.47
        centers=(3.08,7.40,11.72)
        front.row(level*h+.15,(level+1)*h-.09,[(u,3.05,sill,head,"window") for u in centers],"blue")
        for u in centers:
            for du in (-.51,.51):
                front.part("Office_group_mullion",u+du,(sill+head)/2,.073,head-sill-.12,"ink",.06,-.13)
        front.part("Broad_white_floor_band",w/2,level*h,w+.17,.30,"cream",.28,.065)
    for u in (.18,w-.18):
        front.part("Cream_corner_pier",u,4.62,.32,8.75,"cream",.24,.06)
    front.part("Broad_lobby_canopy",3.0,2.85,3.04,.20,"cream",1.03,.35,.025)
    b.cornice(w,d,3*h,False)
    a.parapet("Base_terrace_edge",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],3*h+.17,"blue",.40)
    before={obj.name for obj in a.collection.objects}
    uw,ud=9.8,6.8
    upper=b.frame(uw,ud,1,"blue",height=h)[0]
    upper.row(.15,h-.09,[(u,2.30,.69,2.57,"window") for u in (1.8,4.9,8.0)],"blue")
    for u in (1.8,4.9,8.0):
        upper.part("Top_group_mullion",u,1.63,.072,1.74,"ink",.06,-.13)
    b.cornice(uw,ud,h,False)
    box("Upper_flat_blue_cap",(0,0,h+.24),(uw+.42,ud+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((-.75,1.2,3*h))))
    a.ac_unit("Small_rear_roof_AC",(1.98,2.79,4*h+.37),(1.50,.89,.60))


models=[("twin_stair_apartments","TwinStairApartments",66,(15.8,9.7,12.4),"Broad butter-yellow four-story apartments; two integrated coral stair spines; cream window grid; shallow central roof setback.",twin_stair_apartments),
    ("shopfront_apartments","ShopfrontApartments",67,(13.4,9.2,12.4),"Mint four-story mixed-use block; two ground-floor shops and a separate apartment entrance; shared cream canopy; shallow Juliet rails.",shopfront_apartments),
    ("vertical_pier_apartments","VerticalPierApartments",68,(14.2,10.0,12.4),"Broad terracotta four-story apartments; thick cream vertical piers; tall recessed blue windows; L-shaped upper floor and small corner terrace.",vertical_pier_apartments),
    ("stepped_city_office","SteppedCityOffice",71,(14.8,10.0,12.2),"Broad powder-blue four-story office; smaller top floor; grouped horizontal blue glazing; cream ground lobby and floor bands.",stepped_city_office)]

twin_colliders=[((0,6.2,-.5),(11.0,12.4,8.7)),((-6.7,6.2,0),(2.4,12.4,9.7)),((6.7,6.2,0),(2.4,12.4,9.7))]
pier_colliders=[((0,4.65,0),(14.2,9.3,10.0)),((-2.55,10.85,0),(9.1,3.1,10.0)),((4.55,10.85,-1.4),(5.1,3.1,7.2))]
office_colliders=[((0,4.575,0),(14.8,9.15,10.0)),((-.75,10.675,-1.2),(9.8,3.05,6.8))]

scene_dir=a.PROJECT/"scenes/buildings/batch_17"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=twin_colliders if slug=="twin_stair_apartments" else pier_colliders if slug=="vertical_pier_apartments" else office_colliders if slug=="stepped_city_office" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_17/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_17/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_17/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_17_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":17,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 17\n\nTwin-Stair Apartments (066), Shopfront Apartments (067), Vertical-Pier Apartments (068), Stepped City Office (071). Approved bright pastel French Quarter style, cream trim, recessed painted blue glazing, broad four-story proportions. The older tall roster suggestions for 066 and 068 have been reduced to four stories.\n\nPlacement scenes: `scenes/buildings/batch_17/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Simple body boxes follow the stair spines and upper setbacks; shopfront apartments use one body box. Rails, canopies, ornamental piers, and roof details remain visual. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_17.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_17.py`.\n')
