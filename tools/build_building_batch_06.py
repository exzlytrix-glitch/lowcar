"""Four neighborhood-scale Lowcar buildings using the approved architectural kit."""
from pathlib import Path
import importlib.util
import json
import hashlib

spec=importlib.util.spec_from_file_location("lowcar_batch_parts",Path(__file__).with_name("build_building_batch_01.py"))
b=importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
a=b.a
box,rod,mesh=a.box,a.rod,a.mesh
a.ASSET=a.PROJECT/"assets/models/buildings/batch_06"
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


def tailor_shop():
    w,d,h=6.4,8.8,3.10
    front=b.frame(w,d,3,"lilac",height=h)[0]
    front.row(.15,h-.09,[(2.00,2.60,.59,2.67,"shop"),(5.07,1.07,.15,2.67,"door")],"lilac")
    front.row(h+.15,2*h-.09,[(w/2,2.06,h+.56,2*h-.54,"window")],"lilac")
    front.row(2*h+.15,3*h-.09,[(u,1.27,2*h+.51,3*h-.55,"window") for u in (1.48,4.92)],"lilac")
    for u in (1.48,4.92):
        b.shutters(front,u,2*h+.51,1.27,3*h-.55-(2*h+.51),"blue_dark")
    # Small rectangular projecting window box, rather than a large upper bay.
    sill,head=h+.56,2*h-.54
    panel=a.Wall("Projecting_window",(-1.19,-d/2-.53),(1.19,-d/2-.53),(0,-1),.16)
    panel.row(sill-.06,head+.06,[(1.19,1.96,sill,head,"window")],"lilac")
    for x in (-1.19,1.19):
        box("Window_box_side",(x,-d/2-.26,(sill+head)/2),(.18,.52,head-sill+.15),"cream",.018)
    for z in (sill-.13,head+.15):
        box("Window_box_cap",(0,-d/2-.29,z),(2.65,.78,.18),"cream",.025)
    # Compact sloping entry canopy with a white front lip.
    points=[front.point(u,z,out) for out,z in ((.03,2.88),(.72,2.69),(.72,2.60),(.03,2.79)) for u in (4.33,5.81)]
    mesh("Angled_entry_canopy",points,[(0,1,3,2),(2,3,5,4),(4,5,7,6),(6,7,1,0),(0,2,4,6),(1,7,5,3)],"roof")
    front.part("Canopy_white_lip",5.07,2.65,1.55,.13,"cream",.08,.74)
    sign(front,2.37,3.24,3.62,"TAILOR",.35)
    for u in (.17,w-.17):
        front.part("White_corner_trim",u,4.70,.24,9.03,"cream",.19,.075)
    b.cornice(w,d,3*h,True)
    a.parapet("Tailor_parapet",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],3*h+.14,"lilac",.39)
    a.ac_unit("Roof_AC",(1.27,2.35,3*h+.11))


def shoe_shop():
    w,d,h=9.6,7.8,3.20
    front,right,rear,left=rectangle(w,d,"Shoes")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    for level in (1,2):
        box("Floor_plate",(0,0,level*h),(w,d,.18),"cream")
    for wall in (front,right,rear,left):
        if wall is front:
            ground=[(2.81,3.74,.53,2.74,"shop"),(7.84,1.16,.15,2.74,"door")]
            upper=[(u,1.76,h+.61,2*h-.55,"window") for u in (2.43,6.82)]
        elif wall is right:
            ground=[(u,2.39,.53,2.74,"shop") for u in (2.00,5.80)]
            upper=[(u,1.45,h+.61,2*h-.55,"window") for u in (2.00,5.80)]
        else:
            ground=[(wall.length*.62,1.05,.15 if wall is rear else 1.02,2.67,"door" if wall is rear else "window")]
            upper=[(wall.length*f,1.23,h+.63,2*h-.55,"window") for f in (.30,.70)]
        wall.row(.15,h-.09,ground,"coral")
        wall.row(h+.15,2*h-.09,upper,"coral")
        wall.part("Plinth",wall.length/2,.30,wall.length,.28,"cream",.19,.015)
    front.part("Shop_window_canopy",2.81,2.97,4.18,.19,"cream",1.00,.33,.025)
    front.part("Door_lintel",7.84,2.92,1.55,.18,"cream",.39,.14,.018)
    sign(front,4.72,3.42,4.54,"SHOES",.40)
    for wall,u in ((front,w-.24),(right,.24)):
        wall.part("Thick_corner_pier",u,3.24,.47,6.12,"cream",.27,.10)
    b.cornice(w,d,2*h,False)
    box("Flat_blue_roof_cap",(0,0,2*h+.23),(w+.49,d+.49,.29),"roof",.04)
    box("Rear_roof_vent",(2.86,2.28,2*h+.62),(.79,.83,.44),"metal",.03)
    box("Vent_cap",(2.86,2.28,2*h+.87),(1.05,1.09,.13),"cream",.025)


def newsstand():
    w,d,h=4.5,3.8,2.60
    front,right,rear,left=rectangle(w,d,"News")
    box("Foundation",(0,0,.06),(w,d,.12),"stone",.02)
    # Open serving recess: dark backing, chunky shutter frame, no painted glass.
    opening=3.32
    pier=(w-opening)/2
    for u in (pier/2,w-pier/2):
        front.part("Front_pier",u,1.34,pier,2.44,"cream",.38,-.19)
    front.part("Below_counter",w/2,.48,opening,.72,"cream",.38,-.19)
    front.part("Shutter_header",w/2,2.43,opening,.34,"cream",.38,-.19)
    front.part("Counter_backing",w/2,1.56,opening,1.39,"ink",.08,-.48)
    front.part("White_counter",w/2,.88,opening+.27,.20,"cream",.56,.15,.025)
    for u in (.55,w-.55):
        front.part("Shutter_guide",u,1.61,.11,1.48,"teal",.14,.04)
    for z in (2.32,2.42,2.52):
        front.part("Rolled_shutter_slat",w/2,z,opening-.12,.055,"metal",.08,.02)
    for index,color in enumerate(("blue","coral","yellow","mint")):
        u=.99+index*.84
        front.part("Magazine_pages",u,1.32,.53,.69,"cream",.12,-.10,.012)
        front.part("Magazine_cover",u,1.34,.44,.55,color,.022,-.02)
        front.part("Cover_title",u,1.48,.29,.07,"cream",.015,-.004)
        front.part("Paper_stack",u,1.02,.60,.13,"cream",.29,-.08,.008)
    right.row(.12,h-.09,[(2.23,.95,.12,2.19,"door")],"cream")
    rear.row(.12,h-.09,[(2.25,1.09,1.22,2.18,"window")],"cream")
    left.row(.12,h-.09,[],"cream")
    box("Roof_white_edge",(0,0,h+.01),(w+1.18,d+.69,.17),"cream",.025)
    box("Deep_teal_canopy",(0,-.20,h+.15),(w+1.22,d+1.11,.19),"teal",.035)
    front.part("News_roof_fascia",w/2,2.75,w+1.14,.33,"teal",.13,.75,.018)
    a.text("News_letters","NEWS",front.point(w/2,2.76,.827),.40)


def terrace_bungalow():
    w,d,h=12.0,8.4,3.05
    front=b.frame(w,d,1,"cream",height=h)[0]
    front.row(.15,h-.09,[(2.55,2.74,.75,2.66,"window"),(6.0,1.25,.15,2.66,"door"),(9.45,2.74,.75,2.66,"window")],"cream")
    for u in (2.55,9.45):
        b.shutters(front,u,.75,2.74,1.91,"teal")
    box("Wide_terrace_slab",(0,-d/2-.76,.08),(w+.35,1.83,.16),"stone",.025)
    for u in (.40,4.35,7.65,11.60):
        front.part("Terrace_column",u,1.63,.18,3.10,"cream",.18,1.34)
        front.part("Column_foot",u,.21,.33,.27,"cream",.33,1.34)
        front.part("Column_capital",u,3.02,.34,.20,"cream",.34,1.34)
        rod("Porch_bracket",front.point(u,2.58,1.34),front.point(u,3.09,.83),.09,"cream")
    front.part("White_terrace_beam",w/2,3.17,w+.13,.22,"cream",.24,1.34)
    box("Entry_step",(0,-d/2-1.91,.045),(2.57,.54,.09),"cream",.02)
    # A low broad hip extends forward over the terrace, with no tall attic mass.
    low,peak=h+.20,4.35
    half=w/2+.24
    yfront,yrear=-d/2-1.72,d/2+.25
    vertices=[(-half,yfront,low),(half,yfront,low),(half,yrear,low),(-half,yrear,low),
              (0,yfront+1.66,peak),(0,yrear-1.66,peak)]
    mesh("Broad_blue_hip",vertices,[(0,1,4),(1,2,5,4),(2,3,5),(3,0,4,5),(3,2,1,0)],"roof")
    rod("White_roof_ridge",vertices[4],vertices[5],.16,"cream")
    outline=vertices[:4]
    for p,q in zip(outline,outline[1:]+outline[:1]):
        rod("White_roof_fascia",p,q,.16,"cream")
    a.planter("Terrace_pot",front.point(10.81,.16,1.08),.29,.41)


models=[("tailor_shop","TailorShop",15,(6.4,8.8,9.3),"Lilac three-story shop house; small projecting window box; blue shutters; compact angled door canopy.",tailor_shop),
        ("shoe_shop","ShoeShop",16,(9.6,7.8,6.4),"Coral two-story corner shop; deep display windows; thick cream corner pier; flat blue roof cap.",shoe_shop),
        ("newsstand","Newsstand",17,(4.5,3.8,2.6),"Tiny cream kiosk; open newspaper counter; partly rolled shutter; deep teal overhang; side door.",newsstand),
        ("terrace_bungalow","TerraceBungalow",48,(12.0,8.4,3.05),"Broad cream bungalow; low blue hipped roof over a shallow terrace; white porch columns; teal shutters.",terrace_bungalow)]

scene_dir=a.PROJECT/"scenes/buildings/batch_06"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_06/"+slug+".tscn")
    entries.append(entry)
    (scene_dir/(slug+".tscn")).write_text(f'''[gd_scene load_steps=3 format=3]

[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_06/{slug}.glb" id="1"]

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
        resource_path="res://assets/models/buildings/batch_06/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text("\n".join(line for line in template.split("\n") if not line.startswith("uid=")))
    print("BATCH_06_BUILT",slug,entry["triangles"],"triangles",flush=True)
(a.ASSET/"manifest.json").write_text(json.dumps({"batch":6,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+"\n")
(a.ASSET/"README.md").write_text('# Lowcar — building batch 06\n\nTailor Shop (015), Shoe Shop (016), Newsstand (017), Terrace Bungalow (048). The approved clean pastels, cream trim, and recessed blue glazing at neighborhood scale: three, two, one, and one stories respectively.\n\nPlacement scenes: `scenes/buildings/batch_06/`. One shared static visual mesh and simple main-body collider per building. Meters, ground-center origin, Godot +Z front. Roof overhangs, window boxes, and porch trim extend beyond the main-body collider. Editable Blender files: `source/`.\n\nAll four appear in the driving city after relaunch. Review scene: `scenes/review/building_batch_06.tscn` (F6). 0 for all, 1–4 select, drag to orbit, wheel to zoom. Overview: `previews/lineup.png`.\n\nRebuild with Blender and `tools/build_building_batch_06.py`.\n')
