"""Lowcar batch 01: four pastel French Quarter-inspired exterior models.
Reuses the approved building palette, recessed glazing and static GLB exporter.
"""
from pathlib import Path
from math import sin, cos, pi
import importlib.util
import json

spec = importlib.util.spec_from_file_location("lowcar_architecture", Path(__file__).with_name("build_building_trial.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
a.ASSET = a.PROJECT / "assets/models/buildings/batch_01"
a.SOURCE = a.ASSET / "source"
a.PREVIEWS = a.ASSET / "previews"
for folder in (a.ASSET, a.SOURCE, a.PREVIEWS):
    folder.mkdir(parents=True, exist_ok=True)
for folder in (a.SOURCE, a.PREVIEWS):
    (folder / ".gdignore").write_text("")
a.PALETTE.update(blue="96BFD4", blue_dark="648FA9", lilac="B7A8CF")
box, rod, mesh, Wall = a.box, a.rod, a.mesh, a.Wall


def frame(width, depth, floors, color, ground_color=None, height=3.12):
    """Solid floor plates, recessed wall openings, sparse service-side windows."""
    walls = [Wall("Front", (-width/2, -depth/2), (width/2, -depth/2), (0, -1)),
             Wall("Right", (width/2, -depth/2), (width/2, depth/2), (1, 0)),
             Wall("Rear", (width/2, depth/2), (-width/2, depth/2), (0, 1)),
             Wall("Left", (-width/2, depth/2), (-width/2, -depth/2), (-1, 0))]
    box("Foundation", (0, 0, .075), (width, depth, .15), "stone", .025)
    for level in range(1, floors+1):
        z = level*height
        box("Floor_%02d" % level, (0, 0, z), (width, depth, .18), "cream")
    for wall in walls:
        wall.part("Plinth", wall.length/2, .30, wall.length, .28, "cream", .20, .01)
        if wall is walls[0]:
            continue
        count = 2 if wall is walls[2] else 3
        for level in range(floors):
            low, high = .15+level*height, (level+1)*height-.09
            if level == 0:
                bays = [(wall.length*.48, 1.0, .15, 2.65, "door")] if wall is walls[2] else [(wall.length*.72, 1.25, 1.10, 2.63, "window")]
            else:
                bays = [(wall.length*(i+1)/(count+1), 1.15, low+.63, high-.50, "window") for i in range(count)]
            wall.row(low, high, bays, ground_color or color if level == 0 else color)
        wall.part("Roof_frieze", wall.length/2, floors*height-.26, wall.length+.13, .32, "cream", .21, .05)
    return walls


def cornice(width, depth, z, fancy=False):
    box("Cornice_lower", (0, 0, z-.17), (width+.22, depth+.22, .17), "cream", .025)
    box("Cornice_crown", (0, 0, z+.02), (width+.52, depth+.52, .23), "cream", .035)
    if fancy:
        for i in range(max(5, round(width/.55))):
            x = -width/2+.32+i*(width-.64)/(max(5, round(width/.55))-1)
            box("Cornice_dentil", (x, -depth/2-.13, z-.36), (.18, .22, .24), "cream")


def shutters(wall, u, sill, width, height, color="teal"):
    for side in (-1, 1):
        center = u+side*(width/2+.32)
        wall.part("Shutter_panel", center, sill+height/2, .43, height+.03, color, .09, .075, .018)
        for z in (sill+.22, sill+height-.22):
            wall.part("Shutter_crossbar", center, z, .39, .07, "cream", .04, .14)
        for fraction in (.36, .51, .66):
            wall.part("Shutter_louver", center, sill+height*fraction, .32, .065, color, .055, .15)


def scroll(wall, u, bottom, outward, mirror=1):
    # Broad polygonal C curls: geometric ironwork, visible at driving distance.
    points = [wall.point(u+mirror*cos(-pi*.65+i*pi*1.65/7)*.20,
                         bottom+.44+sin(-pi*.65+i*pi*1.65/7)*.31, outward) for i in range(8)]
    for p, q in zip(points, points[1:]):
        rod("Balcony_scroll", p, q, .055, "cream")


def gallery(wall, u, floor, width, reach=1.15, pattern="scroll", columns=False):
    wall.part("Gallery_slab", u, floor, width+.24, .19, "cream", reach+.25, reach/2, .025)
    front = reach+.08
    for z in (floor+.14, floor+1.08):
        wall.part("Gallery_rail", u, z, width+.20, .08, "cream", .09, front)
    count = max(2, round(width/.72))
    for i in range(count+1):
        x = u-width/2+i*width/count
        wall.part("Gallery_spindle", x, floor+.60, .065, .94, "cream", .07, front)
    for i in range(count):
        x = u-width/2+(i+.5)*width/count
        if pattern == "scroll":
            scroll(wall, x, floor+.08, front, -1 if i % 2 else 1)
        else:
            points = [(x-.25, floor+.60), (x, floor+.96), (x+.25, floor+.60), (x, floor+.24), (x-.25, floor+.60)]
            for p, q in zip(points, points[1:]):
                rod("Gallery_diamond", wall.point(*p, front), wall.point(*q, front), .055, "cream")
    for side in (-1, 1):
        x = u+side*width/2
        for z in (floor+.14, floor+1.08):
            rod("Gallery_side_rail", wall.point(x, z, .05), wall.point(x, z, front), .07, "cream")
        for outward in (.42, .81):
            wall.part("Gallery_side_spindle", x, floor+.61, .065, .92, "cream", .07, outward)
        if columns:
            wall.part("Gallery_support", x, floor/2, .16, floor, "cream", .16, front)
            wall.part("Gallery_column_foot", x, .19, .28, .30, "cream", .28, front)
            wall.part("Gallery_capital", x, floor-.25, .30, .18, "cream", .28, front)
        else:
            rod("Gallery_under_bracket", wall.point(x, floor-.60, .04), wall.point(x, floor-.10, reach*.65), .11, "cream")


def hip_roof(width, depth, low, high):
    w, d = width/2+.20, depth/2+.20
    vertices = [(-w,-d,low),(w,-d,low),(w,d,low),(-w,d,low),
                (0,-d+1.65,high),(0,d-1.65,high)]
    mesh("Faceted_hip_roof", vertices, [(0,1,4),(1,2,5,4),(2,3,5),(3,0,4,5),(3,2,1,0)], "roof")
    box("Roof_ridge", (0,0,high+.02), (.16, depth-3.0, .13), "cream", .02)


def corner_cafe():
    w,d,h = 8.8,8.8,3.35
    walls = frame(w,d,2,"yellow", "mint",h)
    front,right = walls[:2]
    front.row(.15,h-.09,[(1.65,2.05,.48,2.90,"shop"),(4.75,1.22,.15,2.90,"door"),(7.20,1.9,.48,2.90,"shop")],"mint")
    front.row(h+.15,2*h-.09,[(u,1.40,h+.29,2*h-.57,"window") for u in (1.6,4.4,7.2)],"yellow")
    # A wraparound upper gallery gives the corner its recognizable silhouette.
    gallery(front,w/2,h+.12,w-.35,1.10,"scroll",True)
    gallery(right,d/2,h+.12,d-.35,1.10,"scroll",True)
    for wall in (front,right):
        for u in (wall.length*.20, wall.length*.50, wall.length*.80):
            wall.awning(u,2.10,3.00,.72)
    front.part("Cafe_sign",w/2,3.03,3.5,.50,"teal",.12,.19,.02)
    a.text("Cafe_letters","CORNER CAFE",front.point(w/2,3.03,.265),.32)
    for u in (1.6,4.4,7.2):
        shutters(front,u,h+.29,1.40,2*h-.57-(h+.29),"mint_dark")
    cornice(w,d,2*h,True)
    a.parapet("Cafe_parapet",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],2*h+.14,"yellow",.49)
    box("Cafe_roof_kitchen",(-1.9,1.9,7.02),(2.0,2.4,.58),"yellow_dark",.04)
    box("Cafe_roof_kitchen_cap",(-1.9,1.9,7.37),(2.20,2.58,.16),"roof",.025)
    a.planter("Cafe_entry_pot",(1.45,-d/2-.62,.15),.31,.44)


def coral_row_house():
    w,d,h=5.9,9.1,3.10
    front=frame(w,d,2,"coral",height=h)[0]
    front.row(.15,h-.09,[(1.20,1.0,.15,2.69,"door"),(3.63,1.50,.73,2.69,"window")],"coral")
    upper_sill=h+.29
    front.row(h+.15,2*h-.09,[(u,1.25,upper_sill,2*h-.55,"window") for u in (1.48,4.32)],"coral")
    for u in (1.48,4.32):
        shutters(front,u,upper_sill,1.25,2*h-.55-upper_sill)
    shutters(front,3.63,.73,1.50,1.96)
    gallery(front,w/2,h+.12,w-.25,1.0,"scroll")
    for u in (.17,w-.17):
        front.part("Corner_pilaster",u,3.15,.21,5.80,"cream",.17,.065)
    front.part("Door_entablature",1.20,2.82,1.5,.17,"cream",.28,.12,.015)
    box("Entry_step",(-w/2+1.20,-d/2-.28,.075),(1.44,.65,.15),"cream",.025)
    cornice(w,d,2*h,True)
    hip_roof(w,d,2*h+.18,7.44)
    box("Rear_chimney",(1.76,2.3,7.19),(.51,.69,1.15),"coral_dark",.03)
    box("Chimney_cap",(1.76,2.3,7.80),(.71,.85,.15),"cream",.025)


def blue_townhouse():
    w,d,h=5.5,9.8,3.10
    front=frame(w,d,3,"blue",height=h)[0]
    front.row(.15,h-.09,[(1.36,1.30,.69,2.67,"window"),(3.88,1.14,.15,2.67,"door")],"blue")
    for level in (1,2):
        sill=level*h+.31
        front.row(level*h+.15,(level+1)*h-.09,[(u,1.16,sill,(level+1)*h-.55,"window") for u in (1.42,4.05)],"blue")
        for u in (1.42,4.05):
            shutters(front,u,sill,1.16,(level+1)*h-.55-sill,"coral_dark")
        gallery(front,w/2,level*h+.14,w-.62,.78,"diamond")
    for u in (.14,w-.14):
        front.part("Tall_corner_trim",u,4.65,.24,9.0,"cream",.17,.06)
    front.part("Entrance_canopy",3.88,2.82,1.58,.16,"cream",.73,.22,.03)
    cornice(w,d,3*h,True)
    a.parapet("Townhouse_roof",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],3*h+.14,"blue",.40)
    for width,z in ((3.1,9.85),(1.95,10.10)):
        front.part("Stepped_crown",w/2,z,width,.32,"blue",.25,-.07)
        front.part("Stepped_crown_cap",w/2,z+.17,width+.15,.12,"cream",.36,-.07)
    box("Roof_stair_room",(1.35,2.7,9.83),(2.0,2.8,1.03),"blue_dark",.04)
    box("Roof_stair_cap",(1.35,2.7,10.39),(2.2,3.0,.16),"cream",.025)
    box("Roof_access_door",(1.35,1.28,9.76),(.83,.05,.86),"teal")


def skinny_apartments():
    w,d,h=7.35,8.6,3.10
    front=frame(w,d,5,"mint", "mint_dark",h)[0]
    front.row(.15,h-.09,[(1.43,1.17,.15,2.66,"lobby"),(3.88,1.36,.83,2.66,"window"),(6.01,1.05,.83,2.66,"window")],"mint_dark")
    for level in range(1,5):
        sill=level*h+.36
        front.row(level*h+.15,(level+1)*h-.09,[(1.54,1.33,sill,(level+1)*h-.59,"window"),(3.93,1.30,sill+.13,(level+1)*h-.59,"window"),(6.10,1.12,sill+.13,(level+1)*h-.59,"window")],"mint")
        gallery(front,1.54,level*h+.14,2.35,1.04,"scroll")
        # A shallow keystone motif contrasts with the ornate balcony stack.
        for u in (3.93,6.10):
            front.part("Window_keystone",u,(level+1)*h-.54,.24,.26,"cream",.19,.085,.012)
    front.part("Balcony_stack_divider",2.85,7.84,.18,14.75,"cream",.17,.065)
    front.part("Entrance_canopy",1.43,2.83,1.84,.20,"cream",.90,.29,.025)
    cornice(w,d,5*h,True)
    a.parapet("Apartment_roof",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],5*h+.14,"mint",.52)
    box("Roof_access",(1.7,1.8,16.13),(2.45,2.50,.95),"mint_dark",.035)
    box("Roof_access_cap",(1.7,1.8,16.66),(2.67,2.72,.17),"cream",.025)
    box("Roof_access_door",(1.7,.52,16.08),(.83,.05,.85),"teal")
    a.ac_unit("Roof_AC",(-1.7,2.0,15.60))


models=[("corner_cafe", "CornerCafe", 23, (8.8,8.8,6.70), "Butter-yellow corner cafe; mint storefront; wraparound white scrollwork gallery.",corner_cafe),
        ("coral_row_house", "CoralRowHouse",37,(5.9,9.1,6.20),"Coral two-story row house; teal shutters; full-width gallery; low hipped roof.",coral_row_house),
        ("blue_townhouse", "BlueTownhouse",39,(5.5,9.8,9.30),"Powder-blue three-story townhouse; coral shutters; diamond balcony rails; stepped crown.",blue_townhouse),
        ("skinny_apartments", "SkinnyApartments",58,(7.35,8.6,15.50),"Skinny mint five-story apartments; one stack of white scrollwork balconies; flat cornice.",skinny_apartments)]
if __name__ == "__main__":
    entries=[]
    scene_dir=a.PROJECT/"scenes/buildings/batch_01"
    scene_dir.mkdir(parents=True,exist_ok=True)
    for slug,name,roster_id,size,description,author in models:
        entry=a.save_model(slug,name,description,author)
        entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=size[2],scene="res://scenes/buildings/batch_01/"+slug+".tscn")
        entries.append(entry)
        w,d,h=size
        # One inexpensive solid body collider; exterior recesses remain visual detail.
        (scene_dir/(slug+".tscn")).write_text(f'''[gd_scene load_steps=3 format=3]

    [ext_resource type="PackedScene" path="res://assets/models/buildings/batch_01/{slug}.glb" id="1"]

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
        print("BATCH_01_BUILT",slug,entry["triangles"],"triangles",flush=True)
    (a.ASSET/"manifest.json").write_text(json.dumps({"batch":1,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+"\n")
    (a.ASSET/"README.md").write_text("""# Lowcar — building batch 01

    Four French Quarter-inspired exteriors: Corner Café (023), Coral Row House (037), Blue Townhouse (039), and Skinny Apartments (058).

    Use the scenes in `scenes/buildings/batch_01/` for placement. Each has one merged visual mesh and a simple solid building-body collider on the World layer. Units are meters, origin is ground-center, and front faces Godot +Z. Balconies and roof ornaments extend beyond the body collider. These exterior models have no walkable interiors.

    Editable Blender sources are in `source/`; the manifest records bounds and export hashes. `previews/lineup.png` is rendered in Godot beside the actual red muscle car.

    Review scene: `scenes/review/building_batch_01.tscn` (F6). 0 shows all four; 1–4 select a building. Drag to orbit, wheel to zoom, G for street view, B for rear, I for overview, Tab to hide controls.

    Rebuild with Blender using `tools/build_building_batch_01.py`. This batch is ready for city placement; the gameplay city generator still uses its existing blockout buildings.
    """)
