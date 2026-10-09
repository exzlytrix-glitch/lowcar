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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_10"
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
    vertices=[(cx-half,-d/2,z),(cx+half,-d/2,z),(cx,-d/2,peak),
              (cx-half,d/2,z),(cx+half,d/2,z),(cx,d/2,peak)]
    mesh("Cream_gable_end",vertices,[(0,1,2),(5,4,3),(0,3,4,1)],"cream")
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


def harbor_fish_market():
    w,d,h=13.8,9.0,3.4
    front,right,rear,left=rectangle(w,d,"FishMarket")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Hall_ceiling",(0,0,h),(w,d,.18),"cream")
    hall=a.Wall("Open_market_front",(-w/2,-d/2),(3.9,-d/2),(0,-1))
    glazing=hall.window
    hall.window=lambda u,sill,width,height,kind="window": None if kind=="open" else glazing(u,sill,width,height,kind)
    hall.row(.15,h-.09,[(u,2.70,.15,3.03,"open") for u in (1.8,5.4,9.0)],"cream")
    for u in (.25,3.60,7.20,10.55):
        hall.part("Cream_bay_pier",u,1.73,.34,3.15,"cream",.26,.04)
        hall.part("Blue_pier_base",u,.34,.40,.39,"blue_dark",.30,.04)
    for u in (1.8,5.4,9.0):
        hall.part("Blue_bay_header",u,3.20,2.81,.24,"blue_dark",.27,.04)
    office=a.Wall("FishMarket_office",(3.9,-d/2),(w/2,-d/2),(0,-1))
    office.row(.15,h-.09,[(.85,1.12,.95,2.62,"window"),(2.22,.92,.15,2.62,"door")],"blue")
    right.row(.15,h-.09,[(u,1.44,1.08,2.74,"window") for u in (2.01,6.35)],"cream")
    rear.row(.15,h-.09,[(3.00,1.08,.15,2.66,"door"),(8.57,1.34,1.16,2.66,"window")],"cream")
    left.row(.15,h-.09,[(u,1.28,1.10,2.66,"window") for u in (2.45,6.65)],"cream")
    box("Office_partition",(3.9,0,1.74),(.23,d-.37,3.17),"blue",.015)
    for wall in (right,rear,left):
        wall.part("Cream_plinth",wall.length/2,.29,wall.length,.27,"cream",.18,.015)
    # Simple interior counters sit back from the clear entrance bays.
    for x in (-5.1,-1.5,2.1):
        box("Market_counter",(x,.42,.54),(2.52,.91,.78),"blue_dark",.03)
        box("Counter_cream_top",(x,.42,.98),(2.70,1.06,.15),"cream",.025)
        box("Counter_display_inset",(x,.42,1.07),(2.26,.70,.025),"glass")
    for x in (-5.1,-1.5,2.1):
        gable(3.6,d,h+.12,h+1.24,x)
    box("Office_flat_roof",(5.4,0,h+.23),(3.22,d+.27,.21),"roof",.025)
    box("Office_cream_fascia",(5.4,-d/2-.11,h+.14),(3.25,.16,.25),"cream")
    office.part("Office_sign",1.5,3.04,2.75,.38,"teal",.12,.10,.02)
    a.text("Fish_market_letters","FISH MARKET",office.point(1.5,3.04,.18),.28)
    a.ac_unit("Office_roof_AC",(5.39,2.15,h+.35),(.96,.71,.54))


def tea_house():
    w,d,h=8.4,8.8,3.15
    front=b.frame(w,d,2,"lilac",height=h)[0]
    inset=a.Wall("Tea_recess",(-w/2,-d/2+.40),(w/2,-d/2+.40),(0,-1))
    inset.row(.15,h-.09,[(1.85,2.25,.67,2.69,"shop"),(4.20,1.15,.15,2.69,"door"),(6.55,2.25,.67,2.69,"shop")],"lilac")
    for u in (.17,w-.17):
        front.part("Cream_recess_return",u,1.61,.30,2.91,"cream",.49,-.18,.015)
    front.part("Cream_recess_lintel",w/2,2.96,w+.06,.26,"cream",.62,-.14,.02)
    front.part("Recess_canopy",w/2,3.14,w+.10,.18,"cream",.92,.23,.025)
    sign(front,4.20,2.90,2.57,"TEA HOUSE",.30)
    sill,head=h+.54,2*h-.58
    front.row(h+.15,2*h-.09,[(u,1.07,sill,head,"window") for u in (1.78,4.20,6.62)],"lilac")
    for u in (1.78,6.62):
        b.shutters(front,u,sill,1.07,head-sill,"teal")
    b.gallery(front,4.20,h+.16,2.38,.79,"scroll")
    for u in (.18,w-.18):
        front.part("Cream_corner_trim",u,3.22,.28,6.03,"cream",.20,.045)
    flat_roof(w,d,2*h,"lilac",.44)
    box("Rear_stair_hatch",(2.35,2.88,2*h+.39),(1.97,1.82,.43),"lilac",.03)
    box("Hatch_cap",(2.35,2.88,2*h+.66),(2.16,2.01,.14),"cream",.02)
    a.planter("Tea_entry_planter",(-3.48,-d/2-.37,.15),.28,.43)


def sandwich_shop():
    w,d,h=6.8,8.0,3.10
    front=b.frame(w,d,1,"yellow",height=h)[0]
    front.row(.15,h-.09,[(2.50,3.61,.51,2.63,"shop"),(5.73,1.05,.15,2.63,"door")],"yellow")
    for u in (.20,4.62,w-.20):
        front.part("Cream_shop_pier",u,1.65,.30,2.96,"cream",.21,.06)
    front.part("Thick_flat_canopy",w/2,2.88,w+.35,.25,"cream",1.10,.38,.035)
    front.part("Canopy_teal_edge",w/2,3.04,w+.40,.09,"teal",1.15,.38,.015)
    sign(front,w/2,3.32,5.00,"SANDWICHES",.36)
    flat_roof(w,d,h,"yellow",.24)
    box("Rear_kitchen_volume",(.78,2.33,h+.57),(3.11,2.95,.85),"yellow_dark",.035)
    box("Kitchen_white_cap",(.78,2.33,h+1.06),(3.35,3.19,.16),"cream",.025)
    box("Kitchen_vent",(.78,2.46,h+1.32),(.72,.84,.39),"metal",.025)
    box("Vent_cap",(.78,2.46,h+1.56),(.97,1.09,.13),"cream",.02)
    front.part("Cream_front_base",w/2,.29,w,.27,"cream",.18,.015)


def burger_stand():
    w,d,h=7.4,7.4,3.05
    front,right,rear,left=rectangle(w,d,"Burger")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Ceiling",(0,0,h),(w,d,.18),"cream")
    front.row(.15,h-.09,[(2.55,3.88,.83,2.62,"shop"),(6.13,1.08,.15,2.62,"door")],"cream")
    right.row(.15,h-.09,[(3.65,4.88,.83,2.62,"shop")],"cream")
    rear.row(.15,h-.09,[(3.82,1.04,.15,2.61,"door")],"cream")
    left.row(.15,h-.09,[(3.80,1.43,1.08,2.61,"window")],"cream")
    for wall in (front,right,rear,left):
        wall.part("Coral_base_band",wall.length/2,.34,wall.length,.37,"coral",.21,.025)
    front.part("Serving_counter",2.55,.83,4.20,.17,"cream",.50,.17,.025)
    right.part("Side_serving_counter",3.65,.83,5.16,.17,"cream",.50,.17,.025)
    # The roof canopy wraps the street corner; a low blue hip roof sits above it.
    for wall in (front,right):
        wall.part("Deep_corner_canopy",wall.length/2,2.92,wall.length+1.30,.22,"cream",1.12,.37,.03)
        wall.part("Coral_canopy_fascia",wall.length/2,3.00,wall.length+1.31,.33,"coral",.16,.94,.018)
    front.part("Burger_sign",w/2,3.00,4.18,.38,"teal",.09,1.04,.02)
    a.text("Burger_letters","BURGERS",front.point(w/2,3.00,1.10),.37)
    b.cornice(w,d,h,False)
    b.hip_roof(w,d,h+.20,h+1.38)
    box("Rear_vent",(1.86,2.13,h+1.14),(.54,.66,.50),"metal",.025)
    box("Vent_cap",(1.86,2.13,h+1.43),(.76,.88,.13),"cream",.02)


models=[("harbor_fish_market","HarborFishMarket",30,(13.8,9.0,3.4),"Low cream fish market; three blue gables; open front bays; enclosed powder-blue side office.",harbor_fish_market),
        ("tea_house","TeaHouse",31,(8.4,8.8,6.3),"Compact lilac tea house; recessed frontage; small scrollwork balcony; shuttered upper windows.",tea_house),
        ("sandwich_shop","SandwichShop",32,(6.8,8.0,3.1),"Butter-yellow one-story sandwich shop; broad pane; offset door; thick canopy; raised rear kitchen.",sandwich_shop),
        ("burger_stand","BurgerStand",33,(7.4,7.4,3.05),"Square cream burger stand; coral banding; broad serving panes; corner canopy; blue hip roof.",burger_stand)]

fish_colliders=[((0,.075,0),(13.8,.15,9.0)),
                ((0,1.74,-4.31),(13.8,3.18,.38)),
                ((-6.71,1.74,0),(.38,3.18,9.0)),
                ((5.4,1.7,0),(3.0,3.4,9.0)),
                ((-6.675,1.59,4.31),(.45,2.88,.38)),
                ((-3.30,1.59,4.31),(.90,2.88,.38)),
                ((.30,1.59,4.31),(.90,2.88,.38)),
                ((3.675,1.59,4.31),(.45,2.88,.38))]

scene_dir=a.PROJECT/"scenes/buildings/batch_10"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=fish_colliders if slug=="harbor_fish_market" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_10/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_10/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_10/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_10_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":10,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 10\n\nHarbor Fish Market (030), Tea House (031), Sandwich Shop (032), Burger Stand (033). Approved clean pastel French Quarter finish, cream trim, recessed blue glazing, and neighborhood scale.\n\nPlacement scenes: `scenes/buildings/batch_10/`. Meters, ground-center origins, Godot +Z front, one shared static visual mesh per building, and simple world collision. The market uses eight box colliders for its floor, walls, piers, and closed office, preserving its three open front bays. Interior counters are visual; roof, balcony, and canopy details extend beyond the body collider. Editable sources: `source/`.\n\nIncluded in the driving city after relaunch. Review: `scenes/review/building_batch_10.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_10.py`.\n')
