"""Four ordinary Lowcar storefronts using the approved pastel architectural kit."""
from pathlib import Path
import importlib.util
import json
import hashlib

spec=importlib.util.spec_from_file_location("lowcar_batch_parts",Path(__file__).with_name("build_building_batch_01.py"))
b=importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
a=b.a
box,rod,mesh=a.box,a.rod,a.mesh
a.ASSET=a.PROJECT/"assets/models/buildings/batch_07"
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


def furniture_shop():
    w,d,h=12.8,9.4,3.40
    front,right,rear,left=rectangle(w,d,"Furniture")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    for level in (1,2):
        box("Floor_plate",(0,0,level*h),(w,d,.18),"cream")
    for wall in (front,right,rear,left):
        if wall is front:
            ground=[(3.00,4.20,.40,2.98,"shop"),(6.40,1.43,.15,2.98,"door"),(10.02,3.48,.40,2.98,"shop")]
            upper=[(w/2,10.40,h+.68,2*h-.56,"window")]
        elif wall is right:
            ground=[(2.12,1.45,.83,2.94,"window"),(6.62,2.55,.15,3.02,"door")]
            upper=[(u,1.39,h+.66,2*h-.56,"window") for u in (2.35,6.85)]
        else:
            ground=[(wall.length*.57,1.12,.15 if wall is rear else 1.1,2.94,"door" if wall is rear else "window")]
            upper=[(wall.length*f,1.30,h+.72,2*h-.56,"window") for f in (.27,.51,.75)]
        wall.row(.15,h-.09,ground,"yellow")
        wall.row(h+.15,2*h-.09,upper,"yellow")
        wall.part("Plinth",wall.length/2,.29,wall.length,.27,"cream",.18,.015)
    for u in (3.21,9.59):
        front.part("Long_band_mullion",u,5.12,.12,1.90,"cream",.10,-.10)
    front.part("Continuous_shop_canopy",w/2,3.22,w+.10,.20,"cream",1.00,.36,.03)
    sign(front,w/2,3.71,6.08,"FURNITURE",.41)
    for u in (.20,w-.20):
        front.part("White_corner_pilaster",u,3.46,.31,6.40,"cream",.21,.085)
    right.part("Loading_shutter",6.62,1.60,2.36,2.67,"blue_dark",.08,-.08)
    for z in (.47,.89,1.31,1.73,2.15,2.57,2.95):
        right.part("Shutter_slat",6.62,z,2.33,.06,"cream",.04,-.03)
    right.part("Loading_header",6.62,3.17,2.91,.20,"cream",.29,.09)
    flat_roof(w,d,2*h,"yellow",.40)
    a.ac_unit("Roof_AC",(-3.3,2.75,2*h+.11))
    box("Roof_vent",(3.3,2.75,2*h+.37),(.92,.89,.47),"metal",.03)
    box("Vent_cap",(3.3,2.75,2*h+.64),(1.16,1.13,.13),"cream",.025)


def pet_supply_shop():
    w,d,h=10.8,8.2,3.35
    front=b.frame(w,d,1,"blue",height=h)[0]
    front.row(.15,h-.09,[(1.41,1.13,.15,2.60,"door"),(4.54,2.79,.50,2.60,"shop"),(8.43,3.28,.50,2.60,"shop")],"blue")
    front.part("Entry_canopy",1.41,2.84,1.73,.17,"cream",.81,.26,.025)
    sign(front,6.63,2.98,6.34,"PET SUPPLIES",.36)
    for u in (.19,w-.19):
        front.part("White_corner_trim",u,1.74,.29,3.19,"cream",.21,.08)
    b.cornice(w,d,h,False)
    box("Flat_blue_roof_lip",(0,0,h+.20),(w+.41,d+.41,.25),"roof",.03)
    box("Raised_entry_roof",(-3.78,-2.95,h+.62),(2.90,2.31,.79),"blue",.035)
    box("Raised_entry_cap",(-3.78,-2.95,h+1.08),(3.14,2.55,.14),"cream",.025)
    box("Rear_roof_vent",(3.30,2.15,h+.45),(.71,.81,.36),"metal",.025)
    box("Vent_cap",(3.30,2.15,h+.67),(.95,1.05,.13),"cream",.02)


def vintage_clothing():
    w,d,h=6.8,9.1,3.10
    front=b.frame(w,d,3,"mint",height=h)[0]
    inset=a.Wall("Recessed_shop",(-w/2,-d/2+.43),(w/2,-d/2+.43),(0,-1))
    inset.row(.15,h-.09,[(2.34,3.16,.48,2.65,"shop"),(5.50,1.10,.15,2.65,"door")],"mint_dark")
    for u in (.18,w-.18):
        front.part("Recess_return",u,1.56,.34,2.84,"cream",.54,-.22)
    front.part("Storefront_lintel",w/2,2.90,w+.12,.25,"cream",.75,-.13,.02)
    sign(front,4.74,3.32,3.36,"VINTAGE",.33)
    for level in (1,2):
        sill,head=level*h+.55,(level+1)*h-.55
        front.row(level*h+.15,(level+1)*h-.09,[(u,1.29,sill,head,"window") for u in (1.72,5.08)],"mint")
        for u in (1.72,5.08):
            b.shutters(front,u,sill,1.29,head-sill,"coral_dark")
    b.gallery(front,1.72,h+.13,2.32,.56,"diamond")
    for u in (.17,w-.17):
        front.part("White_corner_trim",u,4.72,.24,9.01,"cream",.20,.075)
    flat_roof(w,d,3*h,"mint",.40)
    box("Roof_stair_room",(1.33,2.26,3*h+.68),(2.41,2.55,1.02),"mint_dark",.035)
    box("Roof_stair_cap",(1.33,2.26,3*h+1.26),(2.65,2.79,.17),"cream",.025)
    box("Roof_access_door",(1.33,.96,3*h+.62),(.86,.05,.88),"teal")


def camera_shop():
    w,d,h=7.0,8.2,3.10
    front=b.frame(w,d,2,"cream",height=h)[0]
    front.row(.15,h-.09,[(2.40,3.35,.51,2.66,"shop"),(5.83,1.04,.15,2.66,"door")],"cream")
    front.row(h+.15,2*h-.09,[(u,1.36,h+.63,2*h-.55,"window") for u in (1.72,5.10)],"cream")
    for u in (1.72,5.10):
        b.shutters(front,u,h+.63,1.36,2*h-.55-(h+.63),"blue_dark")
    # Low rectangular display bay projects from the shopfront beside the door.
    bay=a.Wall("Display_bay",(-2.81,-d/2-.64),(.59,-d/2-.64),(0,-1),.18)
    bay.row(.49,2.74,[(1.70,3.02,.60,2.63,"shop")],"cream")
    for x in (-2.81,.59):
        box("Display_bay_side",(x,-d/2-.31,1.62),(.20,.64,2.26),"cream",.02)
    for z in (.43,2.83):
        box("Display_bay_cap",(-1.11,-d/2-.35,z),(3.73,.97,.19),"cream",.025)
    box("Bay_blue_lip",(-1.11,-d/2-.35,2.94),(3.77,1.01,.10),"roof",.018)
    front.part("Side_door_canopy",5.83,2.87,1.48,.16,"roof",.74,.23,.025)
    sign(front,2.40,3.24,3.72,"CAMERAS",.34)
    flat_roof(w,d,2*h,"cream",.38)
    for width,z in ((4.20,6.79),(2.50,7.04)):
        front.part("Stepped_roof_edge",w/2,z,width,.28,"cream",.25,-.07)
        front.part("Step_blue_cap",w/2,z+.17,width+.17,.12,"roof",.37,-.07,.018)
    a.ac_unit("Roof_AC",(1.59,2.20,2*h+.11))


models=[("furniture_shop","FurnitureShop",14,(12.8,9.4,6.8),"Broad butter-yellow two-story furniture shop; tall display panes; long upper window band; side loading shutter.",furniture_shop),
        ("pet_supply_shop","PetSupplyShop",18,(10.8,8.2,3.35),"Low powder-blue pet shop; offset entrance; two display windows; raised roof section over the door.",pet_supply_shop),
        ("vintage_clothing","VintageClothing",20,(6.8,9.1,9.3),"Mint three-story shop house; recessed shopfront; coral shutters; small diamond balcony; roof stair room.",vintage_clothing),
        ("camera_shop","CameraShop",21,(7.0,8.2,6.2),"Compact cream two-story camera shop; projecting ground-floor display bay; side door; stepped blue roof edge.",camera_shop)]

scene_dir=a.PROJECT/"scenes/buildings/batch_07"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_07/"+slug+".tscn")
    entries.append(entry)
    (scene_dir/(slug+".tscn")).write_text(f'''[gd_scene load_steps=3 format=3]

[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_07/{slug}.glb" id="1"]

[sub_resource type="BoxShape3D" id="BuildingBody"]
size = Vector3({w}, {h}, {d})

[node name="{name}" type="Node3D"]

[node name="Visual" parent="." instance=ExtResource("1")]

[node name="BuildingBody" type="StaticBody3D" parent="."]
collision_layer = 1
collision_mask = 0

[node name="Collision" type="CollisionShape3D" parent="BuildingBody"]
position = Vector3(0, {h/2}, 0)
shape = SubResource("BuildingBody")
''')
    import_path=a.ASSET/(slug+".glb.import")
    if not import_path.exists():
        template=(a.PROJECT/"assets/models/buildings/batch_01/corner_cafe.glb.import").read_text()
        resource_path="res://assets/models/buildings/batch_07/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text("\n".join(line for line in template.split("\n") if not line.startswith("uid=")))
    print("BATCH_07_BUILT",slug,entry["triangles"],"triangles",flush=True)
(a.ASSET/"manifest.json").write_text(json.dumps({"batch":7,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+"\n")
(a.ASSET/"README.md").write_text('# Lowcar — building batch 07\n\nFurniture Shop (014), Pet Supply Shop (018), Vintage Clothing (020), Camera Shop (021). Clean pastel French Quarter styling with cream trim, recessed blue glazing, and neighborhood proportions.\n\nPlacement scenes: `scenes/buildings/batch_07/`. Shared static visual meshes, meters, ground-center origins, Godot +Z front, and simple main-body collision. Canopies, display bays, balconies, and roof ornaments extend beyond the main-body colliders. Editable Blender sources: `source/`.\n\nIncluded in the driving city after relaunch. Review scene: `scenes/review/building_batch_07.tscn` (F6). 0 for all, 1–4 select, drag to orbit, wheel to zoom. Overview: `previews/lineup.png`.\n\nRebuild with Blender and `tools/build_building_batch_07.py`.\n')
