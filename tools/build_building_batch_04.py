"""Four everyday Lowcar buildings using the approved architectural parts."""
from pathlib import Path
from math import cos, sin, pi
import importlib.util
import json
import hashlib

spec = importlib.util.spec_from_file_location("lowcar_batch_parts", Path(__file__).with_name("build_building_batch_01.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
a = b.a
box, rod, mesh = a.box, a.rod, a.mesh
a.ASSET = a.PROJECT / "assets/models/buildings/batch_04"
a.SOURCE = a.ASSET / "source"
a.PREVIEWS = a.ASSET / "previews"
for folder in (a.ASSET, a.SOURCE, a.PREVIEWS):
    folder.mkdir(parents=True, exist_ok=True)
for folder in (a.SOURCE, a.PREVIEWS):
    (folder / ".gdignore").write_text("")


def flat_roof(w, d, z, color, height=.42):
    b.cornice(w, d, z, True)
    a.parapet("Roof_parapet", [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)], z+.14, color, height)


def sign(wall, u, z, width, words, size=.34):
    wall.part("Shop_sign",u,z,width,.52,"teal",.14,.14,.025)
    a.text("Shop_letters",words,wall.point(u,z,.22),size)


def flower_shop():
    w,d,h=7.0,7.8,3.20
    front=b.frame(w,d,1,"coral",height=h)[0]
    front.row(.15,h-.09,[(2.71,3.77,.49,2.73,"shop"),(5.77,1.08,.15,2.73,"door")],"coral")
    front.part("Blue_canopy",w/2,2.93,w-.35,.18,"roof",1.16,.45,.035)
    front.part("Canopy_white_lip",w/2,2.86,w-.29,.12,"cream",.10,1.04)
    b.cornice(w,d,h,False)
    b.hip_roof(w,d,h+.19,4.31)
    sign(front,w/2,3.45,3.40,"FLOWERS",.35)
    for x in (-2.58,2.58):
        y=-d/2-.48
        box("Flower_planter",(x,y,.38),(.81,.63,.61),"pot",.025)
        box("Planter_rim",(x,y,.70),(.88,.70,.11),"cream",.015)
        box("Planter_soil",(x,y,.75),(.72,.55,.03),"ink")
        a.shrub("Planter_leaves",(x,y,.88),(.34,.24,.23))
        for dx,height,color in ((-.20,1.12,"yellow"),(.03,1.20,"cream"),(.23,1.06,"coral_dark")):
            rod("Flower_stem",(x+dx,y,.79),(x+dx,y,height),.035,"green_dark")
            a.shrub("Faceted_flower",(x+dx,y,height),(.12,.12,.10),color)


def corner_hardware():
    w,d,h=11.6,8.6,3.35
    front=b.frame(w,d,2,"coral_dark","cream",h)[0]
    front.row(.15,h-.09,[(1.91,2.65,.59,2.83,"shop"),(5.80,1.97,.15,2.93,"door"),(9.69,2.65,.59,2.83,"shop")],"cream")
    front.row(h+.15,2*h-.09,[(u,1.35,h+.64,2*h-.59,"window") for u in (1.90,4.42,7.18,9.70)],"coral_dark")
    for u in (.22,3.57,8.03,w-.22):
        front.part("Chunky_pilaster",u,3.44,.30,6.29,"cream",.22,.095)
        front.part("Pilaster_capital",u,6.48,.48,.22,"cream",.28,.13,.015)
    front.part("Shop_canopy",w/2,3.13,w+.14,.18,"cream",.88,.30,.025)
    sign(front,w/2,3.57,5.48,"CORNER HARDWARE",.39)
    flat_roof(w,d,2*h,"coral_dark",.42)
    front.part("Raised_parapet",w/2,7.37,4.91,.68,"coral_dark",.27,-.07)
    front.part("Raised_parapet_cap",w/2,7.73,5.12,.16,"cream",.41,-.07,.02)
    a.ac_unit("Roof_AC",(-2.58,1.85,6.81))
    box("Roof_vent",(2.10,2.15,7.03),(.77,.80,.46),"metal",.035)
    box("Vent_cap",(2.10,2.15,7.30),(1.06,1.09,.13),"cream",.02)


def spin_laundry():
    w,d,h=11.8,7.2,3.35
    front=b.frame(w,d,1,"mint",height=h)[0]
    windows=[(u,1.66,.79,2.45,"window") for u in (1.38,3.69,6.00,8.31)]
    front.row(.15,h-.09,windows+[(10.49,1.08,.15,2.68,"door")],"mint")
    for u in (.17,w-.17):
        front.part("Shop_corner_trim",u,1.71,.26,3.08,"cream",.17,.065)
    front.part("Entry_canopy",10.49,2.85,1.63,.16,"cream",.74,.25,.025)
    sign(front,4.8,2.96,5.42,"SPIN LAUNDRY",.40)
    b.cornice(w,d,h,False)
    box("Low_blue_roof_lip",(0,0,h+.22),(w+.50,d+.50,.26),"roof",.035)
    a.ac_unit("Roof_AC",(3.05,1.65,h+.36))
    # Simple rear vent, deliberately quiet beside the neighboring storefronts.
    box("Rear_vent",(-3.15,d/2+.04,2.40),(1.18,.10,.46),"metal",.02)
    for z in (-.12,.12):
        box("Vent_slat",(-3.15,d/2+.10,2.40+z),(1.01,.05,.04),"ink")


def courtyard_duplex():
    w,d,h=10.6,9.4,3.15
    outline=[(-5.3,-4.7),(-1.1,-4.7),(-1.1,.5),(5.3,.5),(5.3,4.7),(-5.3,4.7)]
    a.prism("L_foundation",outline,0,.15,"stone",.018)
    for level in (1,2):
        a.prism("L_floor_plate",outline,level*h-.09,level*h+.08,"cream")
    walls=[a.Wall("Left_front",outline[0],outline[1],(0,-1)),
           a.Wall("Courtyard_left",outline[1],outline[2],(1,0)),
           a.Wall("Courtyard_back",outline[2],outline[3],(0,-1)),
           a.Wall("Right_outer",outline[3],outline[4],(1,0)),
           a.Wall("Rear",outline[4],outline[5],(0,1)),
           a.Wall("Left_outer",outline[5],outline[0],(-1,0))]
    for wall in walls:
        if wall.name == "Left_front":
            ground=[(1.09,1.06,.72,2.69,"window"),(2.94,1.03,.15,2.69,"door")]
            upper=[(u,1.08,h+.54,2*h-.56,"window") for u in (1.09,2.97)]
        elif wall.name == "Courtyard_back":
            ground=[(1.1,1.09,.72,2.69,"window"),(3.2,1.09,.15,2.69,"door"),(5.3,1.09,.72,2.69,"window")]
            upper=[(u,1.09,h+.44,2*h-.56,"window") for u in (1.1,3.2,5.3)]
        else:
            count=3 if wall.length > 7 else 2
            ground=[(wall.length*.56,1.3,.77,2.68,"window")]
            upper=[(wall.length*(i+1)/(count+1),1.08,h+.55,2*h-.56,"window") for i in range(count)]
        wall.row(.15,h-.09,ground,"yellow")
        wall.row(h+.15,2*h-.09,upper,"yellow")
        wall.part("Plinth",wall.length/2,.31,wall.length,.28,"cream",.18,.015)
        wall.part("Cornice_lower",wall.length/2,2*h-.11,wall.length+.10,.21,"cream",.22,.065)
        wall.part("Cornice_crown",wall.length/2,2*h+.13,wall.length+.22,.21,"cream",.35,.09,.02)
        if wall.name in ("Left_front","Courtyard_back"):
            for u,width,sill,head,kind in upper:
                b.shutters(wall,u,sill,width,head-sill,"blue_dark")
    b.gallery(walls[2],3.2,h+.13,2.86,.91,"scroll")
    a.parapet("L_roof_parapet",outline,2*h+.22,"yellow",.40)
    box("Courtyard_paving",(2.1,-2.1,.035),(6.4,5.2,.07),"stone")
    # Low courtyard walls leave a broad central opening. The collision matches it.
    for x,width in ((0.0,2.2),(4.6,1.4)):
        box("Front_courtyard_wall",(x,-4.7,.5),(width,.20,1.0),"cream",.018)
        box("Front_wall_cap",(x,-4.7,1.03),(width+.11,.30,.12),"cream",.018)
    box("Right_courtyard_wall",(5.3,-2.1,.5),(.20,5.2,1.0),"cream",.018)
    box("Right_wall_cap",(5.3,-2.1,1.03),(.30,5.3,.12),"cream",.018)
    a.planter("Courtyard_pot",(4.42,-.72,.07),.31,.43)
    a.ac_unit("Roof_AC",(-3.0,2.0,6.42))


models=[("flower_shop","FlowerShop",7,(7.0,7.8,3.2),"Coral single-story flower shop; broad blue canopy; low hipped roof; faceted flower planters.",flower_shop),
        ("corner_hardware","CornerHardware",8,(11.6,8.6,6.7),"Broad terracotta hardware shop; tall double doors; chunky white pilasters; raised parapet.",corner_hardware),
        ("spin_laundry","SpinLaundry",9,(11.8,7.2,3.35),"Long mint laundry; repeating square windows; low blue roof lip; offset entrance.",spin_laundry),
        ("courtyard_duplex","CourtyardDuplex",42,(10.6,9.4,6.3),"Butter-yellow L-shaped duplex; open entry courtyard; low white walls; inward-facing balcony.",courtyard_duplex)]
scene_dir=a.PROJECT/"scenes/buildings/batch_04"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    collision_boxes=[((0,h/2,0),(w,h,d))]
    if slug == "courtyard_duplex":
        collision_boxes=[((-3.2,3.15,0),(4.2,6.3,9.4)),((2.1,3.15,-2.6),(6.4,6.3,4.2)),
                         ((0,.5,4.7),(2.2,1,.20)),((4.6,.5,4.7),(1.4,1,.20)),
                         ((5.3,.5,2.1),(.20,1,5.2)),((2.1,.035,2.1),(6.4,.07,5.2))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_04/"+slug+".tscn",collision_boxes_m=collision_boxes)
    entries.append(entry)
    lines=[f'[gd_scene load_steps={len(collision_boxes)+2} format=3]\n',f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_04/{slug}.glb" id="1"]\n']
    for i,(center,shape_size) in enumerate(collision_boxes):
        lines += [f'[sub_resource type="BoxShape3D" id="Body_{i}"]',f'size = Vector3({shape_size[0]}, {shape_size[1]}, {shape_size[2]})\n']
    lines += [f'[node name="{name}" type="Node3D"]\n','[node name="Visual" parent="." instance=ExtResource("1")]\n','[node name="BuildingBody" type="StaticBody3D" parent="."]','collision_layer = 1','collision_mask = 0\n']
    for i,(center,shape_size) in enumerate(collision_boxes):
        label="Collision" if i == 0 else "Collision_%d" % i
        lines += [f'[node name="{label}" type="CollisionShape3D" parent="BuildingBody"]',f'position = Vector3({center[0]}, {center[1]}, {center[2]})',f'shape = SubResource("Body_{i}")\n']
    (scene_dir/(slug+".tscn")).write_text("\n".join(lines))
    import_path=a.ASSET/(slug+".glb.import")
    if not import_path.exists():
        template=(a.PROJECT/"assets/models/buildings/batch_01/corner_cafe.glb.import").read_text()
        resource_path="res://assets/models/buildings/batch_04/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text("\n".join(line for line in template.split("\n") if not line.startswith("uid=")))
    print("BATCH_04_BUILT",slug,entry["triangles"],"triangles",flush=True)
(a.ASSET/"manifest.json").write_text(json.dumps({"batch":4,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+"\n")
(a.ASSET/"README.md").write_text("""# Lowcar — building batch 04

Flower Shop (007), Corner Hardware (008), Spin Laundry (009), Courtyard Duplex (042). The same approved pastel palette, white trim, recessed blue glazing, and clean low-poly finish.

Placement scenes: `scenes/buildings/batch_04/`. Shared static meshes, meter scale, ground-center origins, and Godot +Z front. The duplex uses six simple collision boxes to preserve its L-shaped body and open courtyard; the other three use a main-body box. Editable Blender files are in `source/`.

All four are included in the driving city automatically after relaunch. Review scene: `scenes/review/building_batch_04.tscn` (F6). 0 for all, 1–4 select, drag to orbit, wheel to zoom. Native overview: `previews/lineup.png`.

Rebuild with Blender and `tools/build_building_batch_04.py`.
""")
