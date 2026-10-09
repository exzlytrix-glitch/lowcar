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
a.ASSET = a.PROJECT / "assets/models/buildings/batch_02"
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


def bodega():
    w,d,h=7.4,8.8,3.2
    front=b.frame(w,d,2,"yellow",height=h)[0]
    front.row(.15,h-.09,[(1.44,1.80,.50,2.75,"shop"),(3.74,1.80,.50,2.75,"shop"),(6.14,1.08,.15,2.75,"door")],"yellow")
    front.row(h+.15,2*h-.09,[(u,1.08,h+.74,2*h-.58,"window") for u in (1.34,3.70,6.06)],"yellow")
    for u in (1.34,3.70,6.06):
        b.shutters(front,u,h+.74,1.08,2*h-.58-(h+.74),"mint_dark")
    front.awning(w/2,w-.30,2.98,1.10)
    sign(front,w/2,3.53,4.12,"BODEGA",.39)
    for u in (.16,w-.16):
        front.part("Corner_trim",u,3.26,.24,6.02,"cream",.17,.05)
    flat_roof(w,d,2*h,"yellow")
    box("Roof_store_room",(1.4,2.35,6.90),(2.35,2.15,.91),"yellow_dark",.035)
    box("Roof_store_cap",(1.4,2.35,7.39),(2.57,2.37,.14),"roof",.025)
    a.ac_unit("Roof_AC",(-1.85,2.45,6.50))


def barber_pole(wall, u, z):
    center=wall.point(u,z,.35)
    pole=a.cylinder("Barber_pole",center,.14,1.20,"cream",12)
    x,y,cz=center
    # A low-poly spiral ribbon around the opaque cylinder, in the existing coral.
    vertices=[]
    steps=24
    for i in range(steps+1):
        angle=i*2*pi/12
        height=-.58+i*1.16/steps
        for offset in (0,.12):
            vertices.append((x+cos(angle)*.146,y+sin(angle)*.146,cz+height+offset))
    mesh("Barber_spiral",vertices,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(steps)],"coral_dark")
    for height in (-.68,.73):
        a.cylinder("Barber_pole_cap",(x,y,cz+height),.185,.12,"teal",8)
    rod("Barber_pole_mount",wall.point(u,z,.03),center,.11,"teal")


def barber():
    w,d,h=4.85,7.65,3.15
    front=b.frame(w,d,2,"cream",height=h)[0]
    front.row(.15,h-.09,[(1.57,1.94,.59,2.71,"shop"),(3.72,1.04,.15,2.71,"door")],"mint_dark")
    front.row(h+.15,2*h-.09,[(u,1.12,h+.31,2*h-.56,"window") for u in (1.27,3.57)],"cream")
    for u in (1.27,3.57):
        b.shutters(front,u,h+.31,1.12,2*h-.56-(h+.31),"teal")
    b.gallery(front,w/2,h+.12,w-.43,.77,"diamond")
    sign(front,w/2,2.99,3.39,"BARBER",.35)
    barber_pole(front,.28,1.96)
    front.part("Door_canopy",3.72,2.74,1.36,.14,"roof",.68,.20,.025)
    flat_roof(w,d,2*h,"mint_dark",.46)
    # Tiny upper roof setback, without turning the shop into a landmark.
    box("Roof_hatch",(.72,1.7,6.64),(1.62,1.9,.36),"roof",.03)
    box("Roof_hatch_cap",(.72,1.7,6.86),(1.82,2.1,.12),"cream",.02)


def gable_roof(w, d, z, peak):
    # Solid yellow gable ends; two broad blue roof planes and chunky white fascia.
    half=w/2
    outline=[(-half,-d/2,z),(half,-d/2,z),(0,-d/2,peak),
             (-half,d/2,z),(half,d/2,z),(0,d/2,peak)]
    mesh("Gable_volume",outline,[(0,1,2),(5,4,3),(0,3,4,1),(0,2,5,3),(1,4,5,2)],"yellow")
    over=.29
    for side in (-1,1):
        vertices=[(side*(half+over),-d/2-over,z+.02),(0,-d/2-over,peak+.07),
                  (0,d/2+over,peak+.07),(side*(half+over),d/2+over,z+.02)]
        mesh("Blue_roof_plane",vertices,[(0,1,2,3) if side < 0 else (3,2,1,0)],"roof")
        for y in (-d/2-over,d/2+over):
            rod("White_gable_fascia",(side*(half+over),y,z+.03),(0,y,peak+.08),.15,"cream")
        rod("Roof_eave",(side*(half+over),-d/2-over,z),(side*(half+over),d/2+over,z),.17,"cream")
    rod("Roof_ridge",(0,-d/2-over,peak+.09),(0,d/2+over,peak+.09),.15,"cream")


def bakery():
    w,d,h=6.8,9.2,3.15
    front=b.frame(w,d,2,"yellow",height=h)[0]
    front.row(.15,h-.09,[(2.37,3.26,.48,2.71,"shop"),(5.70,1.07,.15,2.71,"door")],"yellow")
    front.row(h+.15,2*h-.09,[(u,1.17,h+.58,2*h-.57,"window") for u in (1.39,3.40,5.41)],"yellow")
    front.awning(2.37,3.64,2.95,.89)
    front.part("Door_canopy",5.70,2.91,1.43,.17,"roof",.91,.33,.025)
    sign(front,w/2,3.37,3.80,"BAKERY",.38)
    for u in (1.39,5.41):
        b.shutters(front,u,h+.58,1.17,2*h-.57-(h+.58),"blue_dark")
    b.cornice(w,d,2*h,False)
    gable_roof(w,d,2*h+.19,8.09)
    # Faceted round attic window: a painted blue pane in a solid cream ring.
    z,y=7.14,-d/2-.045
    ring=[]
    for radius in (.36,.25):
        ring += [(cos(i*2*pi/12)*radius,y,z+sin(i*2*pi/12)*radius) for i in range(12)]
    mesh("Attic_window_ring",ring,[(i,(i+1)%12,(i+1)%12+12,i+12) for i in range(12)],"cream")
    mesh("Attic_window_blue",[(cos(i*2*pi/12)*.25,y+.016,z+sin(i*2*pi/12)*.25) for i in range(12)],[tuple(range(12))],"glass")
    rod("Attic_window_mullion",(0,y-.015,z-.25),(0,y-.015,z+.25),.05,"cream")
    box("Rear_kitchen_chimney",(1.85,2.9,7.83),(.61,.69,1.19),"yellow_dark",.025)
    box("Chimney_cap",(1.85,2.9,8.46),(.80,.88,.13),"cream",.02)


def wide_row_house():
    w,d,h=8.8,8.4,3.05
    front=b.frame(w,d,2,"mint",height=h)[0]
    front.row(.15,h-.09,[(1.81,1.58,.69,2.62,"window"),(4.40,1.24,.15,2.62,"door"),(6.99,1.58,.69,2.62,"window")],"mint")
    front.row(h+.15,2*h-.09,[(u,1.34,h+.54,2*h-.56,"window") for u in (1.77,4.4,7.03)],"mint")
    for u in (1.77,4.4,7.03):
        b.shutters(front,u,h+.54,1.34,2*h-.56-(h+.54),"blue_dark")
    # A modest portico and orderly windows make this the quieter residential facade.
    front.part("Entry_canopy",4.4,2.86,2.21,.20,"cream",1.15,.40,.025)
    for u in (3.48,5.32):
        front.part("Entry_column",u,1.38,.15,2.69,"cream",.15,.86)
        front.part("Column_foot",u,.16,.27,.21,"cream",.27,.86)
    box("Entry_step",(0,-d/2-.60,.075),(2.30,1.30,.15),"cream",.025)
    for u in (.17,w-.17):
        front.part("Corner_pilaster",u,3.10,.24,5.72,"cream",.17,.06)
    flat_roof(w,d,2*h,"mint",.46)
    box("Roof_access",(2.2,2.0,6.72),(2.15,2.1,.95),"mint_dark",.04)
    box("Roof_access_cap",(2.2,2.0,7.25),(2.37,2.32,.16),"cream",.025)
    box("Roof_access_door",(2.2,.92,6.66),(.84,.04,.83),"teal")


models=[("everyday_bodega","EverydayBodega",4,(7.4,8.8,6.4),"Butter-yellow bodega; full-width striped canopy; three shuttered upper windows.",bodega),
        ("neighborhood_barber","NeighborhoodBarber",10,(4.85,7.65,6.3),"Skinny cream barber shop; teal shutters; diamond balcony; faceted barber pole.",barber),
        ("neighborhood_bakery","NeighborhoodBakery",24,(6.8,9.2,6.3),"Butter-yellow bakery; broad display window; blue gable; round attic window.",bakery),
        ("wide_row_house","WideRowHouse",38,(8.8,8.4,6.1),"Ordinary mint row house; symmetrical windows; white entrance portico; flat cornice.",wide_row_house)]
scene_dir=a.PROJECT/"scenes/buildings/batch_02"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=size[2],scene="res://scenes/buildings/batch_02/"+slug+".tscn")
    entries.append(entry)
    w,d,h=size
    (scene_dir/(slug+".tscn")).write_text(f'''[gd_scene load_steps=3 format=3]

[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_02/{slug}.glb" id="1"]

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
    resource_path="res://assets/models/buildings/batch_02/"+slug+".glb"
    template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
    template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
    template="\n".join(line for line in template.split("\n") if not line.startswith("uid="))
    (a.ASSET/(slug+".glb.import")).write_text(template)
    print("BATCH_02_BUILT",slug,entry["triangles"],"triangles",flush=True)
(a.ASSET/"manifest.json").write_text(json.dumps({"batch":2,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+"\n")
(a.ASSET/"README.md").write_text("""# Lowcar — building batch 02

Everyday Bodega (004), Neighborhood Barber (010), Neighborhood Bakery (024), Wide Row House (038). Same palette, recessed painted glazing, white trim, and low-poly finish as the approved buildings.

Placement scenes: `scenes/buildings/batch_02/`. One merged visual mesh and simple solid body collider per building. Meters; ground-center origin; Godot +Z front. Canopies, balconies, and roof details extend beyond the main collider. Exterior models; no walkable interiors.

Editable sources: `source/*.blend`. Godot lineup: `previews/lineup.png`. Review with `scenes/review/building_batch_02.tscn` (F6); 0 for all, 1–4 select, drag to orbit, wheel to zoom.

Rebuild with Blender: `tools/build_building_batch_02.py`. Ready for city placement; not yet added to the gameplay city generator.
""")
