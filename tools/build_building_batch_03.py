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
a.ASSET = a.PROJECT / "assets/models/buildings/batch_03"
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


def bookshop():
    w,d,h=5.9,9.0,3.12
    front=b.frame(w,d,3,"blue",height=h)[0]
    front.row(.15,h-.09,[(1.07,1.28,.48,2.70,"shop"),(2.95,1.03,.15,2.70,"door"),(4.83,1.28,.48,2.70,"shop")],"blue")
    front.part("Entry_lintel",2.95,2.85,1.44,.18,"cream",.70,.23,.025)
    sign(front,w/2,3.37,4.33,"PAPERBACK",.33)
    for level in (1,2):
        sill=level*h+.61
        openings=[(u,1.20,sill,(level+1)*h-.55,"window") for u in (1.46,4.44)] if level == 1 else [(w/2,1.7,sill,(level+1)*h-.55,"window")]
        front.row(level*h+.15,(level+1)*h-.09,openings,"blue")
    for u in (1.46,4.44):
        b.shutters(front,u,h+.61,1.20,2*h-.55-(h+.61),"mint_dark")
    # A modest faceted projecting bay on the upper floor, with actual recesses.
    z=2*h+.61
    outline=[(-1.31,-d/2-.02),(-.94,-d/2-.61),(.94,-d/2-.61),(1.31,-d/2-.02)]
    a.prism("Bay_sill",outline,z-.15,z+.02,"cream",.022)
    a.prism("Bay_cap",[(x*1.04,y-.025) for x,y in outline],3*h-.52,3*h-.34,"cream",.022)
    baywalls=[a.Wall("Bay_left",outline[0],outline[1],(-.85,-.53),.13),
              a.Wall("Bay_front",outline[1],outline[2],(0,-1),.16),
              a.Wall("Bay_right",outline[2],outline[3],(.85,-.53),.13)]
    for wall in baywalls:
        if wall.name == "Bay_front":
            wall.row(z+.03,3*h-.52,[(wall.length/2,1.53,z+.12,3*h-.69,"window")],"blue")
        else:
            wall.part("Facet",wall.length/2,(z+3*h-.52)/2,wall.length,3*h-.52-z,"blue",.13,-.06)
    for u in (.16,w-.16):
        front.part("Corner_trim",u,4.70,.23,9.02,"cream",.17,.06)
    flat_roof(w,d,3*h,"blue",.38)
    for width,z in ((3.45,9.89),(2.15,10.17)):
        front.part("Stepped_crown",w/2,z,width,.30,"blue",.27,-.07)
        front.part("Stepped_cap",w/2,z+.17,width+.18,.12,"cream",.39,-.07)
    a.ac_unit("Roof_AC",(.94,2.20,9.47))


def pharmacy():
    w,d,h=10.0,8.0,3.20
    front=b.frame(w,d,2,"mint","cream",h)[0]
    front.row(.15,h-.09,[(1.36,1.23,.15,2.72,"door"),(4.36,2.77,.48,2.72,"shop"),(7.97,2.24,.48,2.72,"shop")],"cream")
    front.row(h+.15,2*h-.09,[(u,1.03,h+.68,2*h-.58,"window") for u in (2.12,3.64,6.36,7.88)],"mint")
    # A heavy sign band and square entry corner keep this shop broad and ordinary.
    front.part("Shop_sign_band",w/2,3.14,w+.16,.65,"mint_dark",.23,.16,.025)
    a.text("Pharmacy_letters","PHARMACY",front.point(5.0,3.15,.285),.39)
    front.part("Continuous_canopy",w/2,2.78,w+.10,.16,"cream",1.06,.41,.03)
    for u in (.19,w-.19):
        front.part("Corner_pilaster",u,3.28,.34,6.14,"cream",.23,.10)
    for u in (2.88,7.12):
        front.part("Paired_window_header",u,5.90,3.09,.19,"cream",.23,.085,.016)
    # Physical hanging sign, subdued colors from the existing palette.
    x=-w/2-.52
    box("Pharmacy_cross_board",(x,-d/2+.42,3.88),(.15,1.04,1.08),"teal",.055)
    for size in ((.06,.68,.20),(.06,.20,.68)):
        box("Pharmacy_cross",(x-.091,-d/2+.42,3.88),size,"cream")
    rod("Pharmacy_sign_bracket",(-w/2+.08,-d/2+.42,4.33),(x,-d/2+.42,4.33),.10,"cream")
    flat_roof(w,d,2*h,"mint",.42)
    box("Roof_service_room",(2.3,1.55,6.91),(2.42,2.2,.89),"mint_dark",.035)
    box("Roof_service_cap",(2.3,1.55,7.41),(2.64,2.42,.16),"roof",.025)
    a.ac_unit("Roof_AC",(-2.53,1.55,6.52))


def six_unit_apartments():
    w,d,h=10.20,9.20,3.10
    front=b.frame(w,d,3,"cream","mint_dark",h)[0]
    front.row(.15,h-.09,[(1.9,2.32,.78,2.66,"window"),(5.1,1.31,.15,2.66,"lobby"),(8.3,2.32,.78,2.66,"window")],"mint_dark")
    for level in (1,2):
        sill=level*h+.43
        centers=(1.27,2.55,4.46,5.74,7.65,8.93)
        front.row(level*h+.15,(level+1)*h-.09,[(u,.97,sill,(level+1)*h-.58,"window") for u in centers],"mint")
        b.gallery(front,5.1,level*h+.14,2.87,.91,"scroll")
        for u in (1.91,8.29):
            front.part("Paired_bay_header",u,(level+1)*h-.54,2.54,.17,"cream",.21,.07,.018)
    front.part("Entrance_canopy",5.1,2.85,2.19,.20,"cream",.98,.32,.028)
    for u in (.17,w-.17):
        front.part("Corner_trim",u,4.70,.24,9.04,"cream",.17,.06)
    flat_roof(w,d,3*h,"mint",.47)
    box("Roof_stair_room",(2.0,2.40,9.98),(2.55,2.45,1.09),"mint_dark",.038)
    box("Roof_stair_cap",(2.0,2.40,10.58),(2.79,2.69,.17),"cream",.025)
    box("Roof_stair_door",(2.0,1.15,9.94),(.87,.04,.94),"teal")
    a.ac_unit("Roof_AC",(-2.75,2.35,9.41))


def cream_city_office():
    w,d,h=11.8,8.8,3.15
    front=b.frame(w,d,3,"cream",height=h)[0]
    front.row(.15,h-.09,[(2.10,2.81,.66,2.73,"shop"),(5.90,1.52,.15,2.73,"lobby"),(9.70,2.81,.66,2.73,"shop")],"cream")
    for level in (1,2):
        sill,head=level*h+.55,(level+1)*h-.54
        front.row(level*h+.15,(level+1)*h-.09,[(u,.97,sill,head,"window") for u in (1.38,2.82,5.18,6.62,8.98,10.42)],"cream")
        for u in (2.10,5.90,9.70):
            front.part("Paired_window_header",u,head+.04,2.63,.19,"cream",.23,.08,.018)
    front.part("Lobby_canopy",5.9,2.96,3.30,.22,"roof",1.14,.42,.035)
    for u in (.20,w-.20):
        front.part("Corner_pilaster",u,4.78,.29,9.08,"cream",.21,.075)
    b.cornice(w,d,3*h,True)
    box("Broad_blue_roof_cap",(0,0,3*h+.22),(w+.45,d+.45,.28),"roof",.035)
    a.ac_unit("Roof_AC",(-3.55,2.30,3*h+.39))
    box("Roof_vent",(3.55,2.30,3*h+.58),(.86,.92,.42),"metal",.03)
    box("Vent_cap",(3.55,2.30,3*h+.83),(1.10,1.16,.13),"cream",.02)


models=[("paperback_bookshop","PaperbackBookshop",6,(5.9,9.0,9.36),"Powder-blue three-story bookshop; recessed central door; upper faceted bay; stepped parapet.",bookshop),
        ("neighborhood_pharmacy","NeighborhoodPharmacy",5,(10.0,8.0,6.4),"Broad mint and cream pharmacy; square entry corner; heavy sign band; paired upper windows.",pharmacy),
        ("six_unit_apartments","SixUnitApartments",57,(10.2,9.2,9.3),"Three-story cream and mint apartments; three paired front bays; central scrollwork balcony stack.",six_unit_apartments),
        ("slim_cream_tower","CreamCityOffice",69,(11.8,8.8,9.45),"Broad three-story cream office; paired upper windows; central lobby canopy; low blue roof cap.",cream_city_office)]
scene_dir=a.PROJECT/"scenes/buildings/batch_03"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=size[2],scene="res://scenes/buildings/batch_03/"+slug+".tscn")
    entries.append(entry)
    w,d,h=size
    (scene_dir/(slug+".tscn")).write_text(f'''[gd_scene load_steps=3 format=3]

[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_03/{slug}.glb" id="1"]

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
    template=(a.PROJECT/"assets/models/buildings/batch_01/corner_cafe.glb.import").read_text()
    resource_path="res://assets/models/buildings/batch_03/"+slug+".glb"
    template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
    template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
    template="\n".join(line for line in template.split("\n") if not line.startswith("uid="))
    (a.ASSET/(slug+".glb.import")).write_text(template)
    print("BATCH_03_BUILT",slug,entry["triangles"],"triangles",flush=True)
(a.ASSET/"manifest.json").write_text(json.dumps({"batch":3,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+"\n")
(a.ASSET/"README.md").write_text("""# Lowcar — building batch 03

Paperback Bookshop (006), Neighborhood Pharmacy (005), Six-Unit Apartments (057), Cream City Office (069). Same approved palette, recessed blue glazing, cream trim, and low-poly finish. The former tower asset path now contains a broad three-story office.

Placement scenes: `scenes/buildings/batch_03/`. One merged mesh and solid main-body collider per building. Meters, ground-center origin, Godot +Z front. Balconies, canopies, and roof ornaments extend beyond the body collider. No walkable interiors.

Editable sources: `source/*.blend`. Godot preview: `previews/lineup.png`. Open `scenes/review/building_batch_03.tscn` (F6) to inspect; 0 shows all, 1–4 select, drag to orbit, wheel to zoom.

Rebuild using Blender and `tools/build_building_batch_03.py`. All models are active in the driving city after relaunch.
""")
