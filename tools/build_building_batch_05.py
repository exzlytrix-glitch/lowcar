"""Four more Lowcar exteriors, using the approved palette and architectural parts."""
from pathlib import Path
from math import pi
import importlib.util
import json
import hashlib

spec = importlib.util.spec_from_file_location("lowcar_batch_parts", Path(__file__).with_name("build_building_batch_01.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
a = b.a
box, rod, mesh = a.box, a.rod, a.mesh
a.ASSET = a.PROJECT / "assets/models/buildings/batch_05"
a.SOURCE = a.ASSET / "source"
a.PREVIEWS = a.ASSET / "previews"
for folder in (a.ASSET, a.SOURCE, a.PREVIEWS):
    folder.mkdir(parents=True, exist_ok=True)
for folder in (a.SOURCE, a.PREVIEWS):
    (folder / ".gdignore").write_text("")


def rectangle(w, d, label="Wall"):
    return [a.Wall(label+"_front",(-w/2,-d/2),(w/2,-d/2),(0,-1)),
            a.Wall(label+"_right",(w/2,-d/2),(w/2,d/2),(1,0)),
            a.Wall(label+"_rear",(w/2,d/2),(-w/2,d/2),(0,1)),
            a.Wall(label+"_left",(-w/2,d/2),(-w/2,-d/2),(-1,0))]


def flat_roof(w,d,z,color,height=.43):
    b.cornice(w,d,z,True)
    a.parapet("Roof_parapet",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],z+.14,color,height)


def sign(wall,u,z,width,words,size=.34):
    wall.part("Shop_sign",u,z,width,.52,"teal",.14,.14,.025)
    a.text("Shop_letters",words,wall.point(u,z,.22),size)


def gable_roof(w,d,z,peak,color="cream",attic=False):
    half=w/2
    # Broad gable end with a real window opening when the house has an attic.
    if attic:
        sill,head,width=z+.63,peak-.84,1.32
        points=[(-half,z),(half,z),(0,peak),(-width/2,sill),(width/2,sill),(-width/2,head),(width/2,head)]
        mesh("Front_gable",[(x,-d/2,h) for x,h in points],[(0,1,4,3),(0,3,5,2),(1,2,6,4),(5,6,2)],color)
        front=rectangle(w,d,"Attic")[0]
        front.window(w/2,sill,width,head-sill)
    else:
        mesh("Front_gable",[(-half,-d/2,z),(half,-d/2,z),(0,-d/2,peak)],[(0,1,2)],color)
    mesh("Rear_gable",[(-half,d/2,z),(half,d/2,z),(0,d/2,peak)],[(2,1,0)],color)
    for side in (-1,1):
        vertices=[(side*(half+.27),-d/2-.27,z+.02),(0,-d/2-.27,peak+.07),
                  (0,d/2+.27,peak+.07),(side*(half+.27),d/2+.27,z+.02)]
        mesh("Blue_roof_plane",vertices,[(0,1,2,3) if side<0 else (3,2,1,0)],"roof")
        for y in (-d/2-.27,d/2+.27):
            rod("White_gable_fascia",(side*(half+.27),y,z+.03),(0,y,peak+.08),.16,"cream")
        rod("White_eave",(side*(half+.27),-d/2-.27,z),(side*(half+.27),d/2+.27,z),.17,"cream")
    rod("Roof_ridge",(0,-d/2-.27,peak+.09),(0,d/2+.27,peak+.09),.16,"cream")


def junction_convenience():
    w,d,h=9.4,9.2,3.12
    front,right,rear,left=rectangle(w,d,"Junction")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    for level in range(1,5):
        box("Floor_plate",(0,0,level*h),(w,d,.18),"cream")
    for wall in (front,right,rear,left):
        if wall is front:
            ground=[(1.88,2.50,.49,2.71,"shop"),(5.05,2.49,.49,2.71,"shop"),(8.02,1.13,.15,2.71,"door")]
        elif wall is right:
            ground=[(u,2.20,.49,2.71,"shop") for u in (1.74,4.57,7.40)]
        elif wall is rear:
            ground=[(wall.length*.67,1.05,.15,2.65,"door")]
        else:
            ground=[(wall.length*.70,1.35,.91,2.65,"window")]
        wall.row(.15,h-.09,ground,"yellow")
        for level in (1,2,3):
            count=4 if wall in (front,right) else 3
            openings=[(wall.length*(i+1)/(count+1),1.03,level*h+.56,(level+1)*h-.51,"window") for i in range(count)]
            wall.row(level*h+.15,(level+1)*h-.09,openings,"blue")
        wall.part("Plinth",wall.length/2,.30,wall.length,.28,"cream",.19,.015)
    for wall in (front,right):
        wall.part("Wrap_canopy",wall.length/2,2.95,wall.length+.50,.19,"cream",1.0,.34,.03)
        wall.part("Canopy_blue_edge",wall.length/2,2.93,wall.length+.53,.16,"roof",.10,.81)
        wall.part("Shop_header_band",wall.length/2,3.38,wall.length,.52,"blue_dark",.17,.045)
        for u in (.18,wall.length-.18):
            wall.part("White_corner_pier",u,6.30,.29,12.11,"cream",.21,.08)
    sign(front,w/2,3.38,5.68,"JUNCTION",.42)
    flat_roof(w,d,4*h,"blue",.61)
    box("Setback_roof_room",(1.76,2.22,13.34),(3.31,3.04,1.54),"blue_dark",.035)
    box("Roof_room_cap",(1.76,2.22,14.19),(3.55,3.28,.16),"cream",.025)
    box("Roof_terrace_door",(1.76,.67,13.22),(.96,.05,1.15),"teal")
    for x in (-3.55,-1.42):
        box("Terrace_planter",(x,-2.89,12.85),(1.42,.62,.49),"cream",.025)
        a.shrub("Terrace_green",(x,-2.89,13.17),(.63,.27,.29))


def cycle_shop():
    w,d,h=8.6,8.2,3.35
    front,right,rear,left=rectangle(w,d,"Cycle")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Roof_plate",(0,0,h),(w,d,.18),"cream")
    for wall in (front,right,rear,left):
        if wall is front:
            openings=[(1.56,1.80,.57,2.75,"shop"),(4.30,2.85,.15,2.75,"door"),(7.04,1.80,.57,2.75,"shop")]
        elif wall is right:
            openings=[(2.07,1.04,.15,2.65,"door"),(5.52,1.46,.90,2.65,"window")]
        else:
            openings=[(wall.length*.58,1.29,1.15,2.65,"window")]
        wall.row(.15,h-.09,openings,"mint")
        wall.part("Plinth",wall.length/2,.30,wall.length,.28,"cream",.19,.015)
    for u in (.20,w-.20):
        front.part("White_entry_pier",u,1.75,.29,3.17,"cream",.20,.08)
    front.part("Double_door_canopy",w/2,2.95,3.55,.17,"cream",.87,.30,.025)
    b.cornice(w,d,h,False)
    gable_roof(w,d,h+.18,4.84,"mint")
    sign(front,w/2,4.01,3.10,"CYCLES",.36)
    right.part("Service_canopy",2.07,2.83,1.49,.15,"roof",.59,.19,.025)


def blue_gable_house():
    w,d,h=7.6,9.0,3.1
    front=b.frame(w,d,2,"cream",height=h)[0]
    front.row(.15,h-.09,[(1.54,1.59,.73,2.68,"window"),(3.80,1.14,.15,2.68,"door"),(6.06,1.59,.73,2.68,"window")],"cream")
    front.row(h+.15,2*h-.09,[(u,1.33,h+.55,2*h-.54,"window") for u in (1.54,3.80,6.06)],"cream")
    for u in (1.54,6.06):
        b.shutters(front,u,h+.55,1.33,2*h-.54-(h+.55),"blue_dark")
        b.shutters(front,u,.73,1.59,1.95,"blue_dark")
    front.part("Porch_roof",3.80,2.93,2.36,.21,"roof",1.31,.47,.03)
    for u in (2.80,4.80):
        front.part("Porch_column",u,1.48,.16,2.83,"cream",.16,1.05)
        front.part("Column_base",u,.18,.31,.26,"cream",.30,1.05)
        front.part("Column_capital",u,2.74,.31,.20,"cream",.30,1.05)
    box("Porch_step",(0,-d/2-.65,.075),(2.58,1.50,.15),"stone",.025)
    b.cornice(w,d,2*h,False)
    gable_roof(w,d,2*h+.19,8.85,"cream",True)
    box("Chimney",(2.06,2.26,8.05),(.54,.73,1.72),"blue_dark",.03)
    box("Chimney_cap",(2.06,2.26,8.97),(.76,.91,.16),"cream",.025)


def mint_office_block():
    w,d,h=12.0,9.0,3.10
    front=b.frame(w,d,4,"mint","cream",h)[0]
    front.row(.15,h-.09,[(2.16,2.79,.69,2.68,"shop"),(6.00,1.61,.15,2.68,"lobby"),(9.84,2.79,.69,2.68,"shop")],"cream")
    for level in (1,2,3):
        front.row(level*h+.15,(level+1)*h-.09,[(u,1.59,level*h+.53,(level+1)*h-.52,"window") for u in (1.95,4.65,7.35,10.05)],"mint")
    for u in (.24,w-.24):
        front.part("White_facade_frame",u,6.25,.36,12.13,"cream",.24,.09)
    front.part("Frame_header",w/2,4*h-.26,w-.12,.36,"cream",.24,.09)
    front.part("Lobby_canopy",w/2,2.87,3.31,.20,"cream",1.13,.39,.035)
    b.cornice(w,d,4*h,False)
    a.parapet("Mint_roof",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],4*h+.14,"mint",.40)
    box("Setback_roof_room",(2.60,2.55,4*h+.68),(2.39,2.47,.94),"mint_dark",.035)
    box("Roof_room_cap",(2.60,2.55,4*h+1.22),(2.63,2.71,.16),"cream",.025)
    box("Roof_room_door",(2.60,1.29,4*h+.65),(.86,.05,.83),"teal")
    a.ac_unit("Roof_AC",(-3.20,2.53,4*h+.11))


models=[("junction_convenience","JunctionConvenience",11,(9.4,9.2,12.48),"Four-story powder-blue corner shop; butter-yellow frontage; wraparound canopy; setback roof terrace.",junction_convenience),
        ("cycle_shop","CycleShop",12,(8.6,8.2,3.35),"Mint one-story cycle shop; extra-wide double doors; shallow blue gable; side service entry.",cycle_shop),
        ("blue_gable_house","BlueGableHouse",40,(7.6,9.0,6.2),"Cream two-story house; broad steep blue gable; recessed attic window; white-column entrance porch.",blue_gable_house),
        ("slim_mint_tower","MintOfficeBlock",70,(12.0,9.0,12.4),"Broad four-story mint office; white facade frame; four-window front rhythm; modest setback roof room.",mint_office_block)]
scene_dir=a.PROJECT/"scenes/buildings/batch_05"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_05/"+slug+".tscn")
    entries.append(entry)
    (scene_dir/(slug+".tscn")).write_text(f'''[gd_scene load_steps=3 format=3]

[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_05/{slug}.glb" id="1"]

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
        resource_path="res://assets/models/buildings/batch_05/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text("\n".join(line for line in template.split("\n") if not line.startswith("uid=")))
    print("BATCH_05_BUILT",slug,entry["triangles"],"triangles",flush=True)
(a.ASSET/"manifest.json").write_text(json.dumps({"batch":5,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+"\n")
(a.ASSET/"README.md").write_text("""# Lowcar — building batch 05

Junction Convenience (011), Cycle Shop (012), Blue Gable House (040), Mint Office Block (070). Same approved pastels, cream trim, recessed blue glazing, and clean low-poly finish. The former tower asset path now contains a broad four-story office.

Placement scenes: `scenes/buildings/batch_05/`. One shared static visual mesh and simple main-body collider per building. Meters, ground-center origin, Godot +Z front. Canopies, pitched roofs, and roof ornaments extend beyond the main-body collider. Editable Blender sources are in `source/`.

All four appear in the driving city after relaunch. Review scene: `scenes/review/building_batch_05.tscn` (F6). 0 for all, 1–4 select, drag to orbit, wheel to zoom. Native overview: `previews/lineup.png`.

Rebuild with Blender and `tools/build_building_batch_05.py`.
""")
