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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_09"
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


def noodle_kitchen():
    w,d,h=7.8,9.0,3.1
    front=b.frame(w,d,3,"cream",ground_color="mint_dark",height=h)[0]
    front.row(.15,h-.09,[(2.77,3.85,.42,2.62,"shop"),(6.40,1.13,.15,2.62,"door")],"mint_dark")
    for level,centers in ((1,(1.91,5.57)),(2,(2.24,5.91))):
        sill,head=level*h+.64,(level+1)*h-.55
        front.row(level*h+.15,(level+1)*h-.09,[(u,1.49,sill,head,"window") for u in centers],"cream")
        for u in centers:
            b.shutters(front,u,sill,1.49,head-sill,"teal")
    # A solid teal sloped awning keeps the storefront darker beneath white trim.
    reach,width=.97,w-.30
    verts=[front.point(u,z,out) for out,z in ((.05,2.98),(reach,2.64),(reach,2.55),(.05,2.89)) for u in ((w-width)/2,(w+width)/2)]
    mesh("Solid_teal_awning",verts,[(0,1,3,2),(2,3,5,4),(4,5,7,6),(6,7,1,0),(0,2,4,6),(1,7,5,3)],"teal")
    front.part("Awning_cream_edge",w/2,2.56,width+.12,.13,"cream",.12,reach,.015)
    for u in (.60,w-.60):
        rod("Awning_bracket",front.point(u,2.06,.05),front.point(u,2.60,.84),.08,"cream")
    sign(front,w/2,3.35,5.05,"NOODLE KITCHEN",.37)
    for u in (.19,w-.19):
        front.part("Cream_corner_pier",u,4.70,.30,9.03,"cream",.21,.06)
    for level in (1,2):
        front.part("Cream_floor_band",w/2,level*h,w+.11,.21,"cream",.21,.03)
    flat_roof(w,d,3*h,"cream",.39)
    box("Rear_kitchen_chimney",(2.45,3.01,3*h+.58),(.67,.77,.98),"mint_dark",.025)
    box("Chimney_cap",(2.45,3.01,3*h+1.13),(.89,.99,.15),"cream",.025)
    a.ac_unit("Roof_AC",(-2.25,2.31,3*h+.11),(.93,.70,.53))


def ice_cream_shop():
    w,d,h=7.6,7.4,3.0
    # Three broad corner facets approximate a rounded pavilion without smooth curves.
    outline=[(-3.8,-1.75),(-3.56,-2.80),(-2.65,-3.56),(-1.75,-3.7),(3.8,-3.7),(3.8,3.7),(-3.8,3.7)]
    a.prism("Pavilion_foundation",outline,0,.15,"stone",.025)
    a.prism("Ceiling_plate",outline,h-.09,h+.09,"cream",.025)
    front=a.Wall("IceCream_front",outline[3],outline[4],(0,-1))
    right=a.Wall("IceCream_right",outline[4],outline[5],(1,0))
    rear=a.Wall("IceCream_rear",outline[5],outline[6],(0,1))
    left=a.Wall("IceCream_left",outline[6],outline[0],(-1,0))
    front.row(.15,h-.09,[(2.66,4.15,.94,2.56,"shop")],"blue")
    front.part("Serving_counter",2.66,.94,4.54,.19,"cream",.63,.18,.025)
    front.part("Counter_blue_front",2.66,.76,4.18,.21,"teal",.14,.23)
    right.row(.15,h-.09,[(1.56,1.14,.15,2.56,"door"),(4.88,1.73,.94,2.56,"window")],"blue")
    rear.row(.15,h-.09,[(3.65,1.10,.15,2.50,"door")],"blue")
    left.row(.15,h-.09,[(left.length*.52,1.37,1.08,2.50,"window")],"blue")
    for i in range(3):
        p,q=outline[i],outline[i+1]
        normal=(q[1]-p[1],p[0]-q[0])
        wall=a.Wall("IceCream_corner_%d"%i,p,q,normal)
        wall.row(.15,h-.09,[],"blue")
        wall.part("Corner_white_panel",wall.length/2,1.66,wall.length*.65,1.29,"cream",.055,.025,.018)
        wall.part("Inset_pastel_panel",wall.length/2,1.66,wall.length*.49,1.02,"coral",.025,.061,.01)
    for wall in (front,right,rear,left):
        wall.part("Cream_base_band",wall.length/2,.32,wall.length,.31,"cream",.17,.03)
    # The generous flat canopy follows the same clipped silhouette.
    roof_outline=[(x*1.13,y*1.13) for x,y in outline]
    a.prism("Cream_flat_roof_canopy",roof_outline,h+.01,h+.29,"cream",.04)
    a.prism("Powder_blue_roof_cap",[(x*1.09,y*1.09) for x,y in outline],h+.29,h+.38,"roof",.015)
    front.part("Blue_fascia_sign",2.71,h+.07,4.03,.45,"blue_dark",.14,.47,.025)
    a.text("IceCream_letters","ICE CREAM",front.point(2.71,h+.07,.56),.37)
    for u in (.15,right.length-.15):
        right.part("Cream_corner_trim",u,1.59,.22,2.80,"cream",.16,.03)
    box("Rear_roof_hatch",(1.65,2.10,h+.58),(1.55,1.40,.39),"blue",.03)
    box("Hatch_cap",(1.65,2.10,h+.81),(1.75,1.60,.12),"cream",.02)


def fresh_produce_shop():
    w,d,h=11.8,8.6,3.25
    front=b.frame(w,d,1,"mint",height=h)[0]
    front.row(.15,h-.09,[(2.42,3.16,.63,2.69,"shop"),(5.90,1.35,.15,2.69,"door"),(9.38,3.16,.63,2.69,"shop")],"mint")
    front.awning(w/2,w-.38,3.05,1.09)
    front.part("Butter_yellow_sign_band",w/2,3.42,6.85,.52,"yellow",.20,.10,.02)
    a.text("Produce_letters","FRESH PRODUCE",front.point(w/2,3.42,.22),.39,"ink")
    for u in (.19,4.50,7.30,w-.19):
        front.part("Cream_front_pier",u,1.67,.30,3.07,"cream",.20,.06)
    front.part("Butter_yellow_plinth",w/2,.32,w,.30,"yellow",.21,.015)
    b.cornice(w,d,h,False)
    b.hip_roof(w,d,h+.17,h+1.11)
    # Low painted display boxes remain tucked against the two shop panes.
    for u in (2.42,9.38):
        front.part("Produce_display_box",u,.63,2.25,.34,"yellow_dark",.47,.25,.025)
        front.part("Display_cream_lip",u,.84,2.39,.09,"cream",.51,.25,.015)
        for offset in (-.62,0,.62):
            center=front.point(u+offset,.91,.25)
            a.shrub("Produce_bundle",center,(.27,.19,.19),"green" if offset else "coral")
    box("Rear_roof_vent",(3.56,2.92,h+.90),(.49,.60,.52),"metal",.025)
    box("Vent_cap",(3.56,2.92,h+1.19),(.70,.80,.13),"cream",.02)


def butcher_shop():
    w,d,h=7.3,8.8,3.15
    front,right,rear,left=rectangle(w,d,"Butcher")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    for level in (1,2):
        box("Floor_plate",(0,0,level*h),(w,d,.18),"cream")
    for wall in (front,right,rear,left):
        if wall is front:
            ground=[(2.66,3.63,.52,2.73,"shop"),(6.03,1.13,.15,2.73,"door")]
            upper=[(u,1.05,h+.96,2*h-.64,"window") for u in (1.52,3.65,5.78)]
        elif wall is right:
            ground=[(2.08,1.28,1.13,2.73,"window"),(6.33,1.96,.15,2.80,"door")]
            upper=[(u,1.04,h+.83,2*h-.64,"window") for u in (2.32,6.55)]
        else:
            ground=[(wall.length*.54,1.03,.15 if wall is rear else 1.12,2.69,"door" if wall is rear else "window")]
            upper=[(wall.length*f,1.02,h+.87,2*h-.64,"window") for f in (.28,.70)]
        wall.row(.15,h-.09,ground,"coral_dark")
        wall.row(h+.15,2*h-.09,upper,"coral_dark")
        wall.part("Cream_plinth",wall.length/2,.31,wall.length,.29,"cream",.20,.015)
    for u in (.24,5.14,w-.24):
        front.part("Thick_storefront_pier",u,1.66,.38,3.00,"cream",.30,.105,.018)
    front.part("Cream_storefront_header",w/2,2.97,w+.14,.26,"cream",.35,.10,.02)
    front.part("Cream_storefront_canopy",w/2,3.20,w+.21,.19,"cream",.73,.22,.025)
    sign(front,w/2,3.58,4.72,"BUTCHER",.43)
    for u in (1.52,5.78):
        b.shutters(front,u,h+.96,1.05,2*h-.64-(h+.96),"blue_dark")
    right.part("Delivery_door_panel",6.33,1.48,1.80,2.52,"blue_dark",.06,-.09)
    for u in (5.85,6.81):
        right.part("Delivery_door_stile",u,1.48,.09,2.38,"cream",.045,-.04)
    right.part("Delivery_canopy",6.33,2.99,2.32,.16,"roof",.83,.25,.025)
    for z in (.52,1.32,2.12):
        right.part("Delivery_door_band",6.33,z,1.69,.08,"cream",.04,-.045)
    flat_roof(w,d,2*h,"coral_dark",.43)
    a.ac_unit("Roof_AC",(1.83,2.90,2*h+.10),(1.5,.91,.78))


models=[("noodle_kitchen","NoodleKitchen",26,(7.8,9.0,9.3),"Cream three-story noodle kitchen; solid teal awning; staggered shuttered window pairs; rear chimney.",noodle_kitchen),
        ("ice_cream_shop","IceCreamShop",27,(7.6,7.4,3.0),"Powder-blue one-story pavilion; faceted rounded corner; broad serving window; generous flat canopy.",ice_cream_shop),
        ("fresh_produce_shop","FreshProduceShop",28,(11.8,8.6,3.25),"Wide mint produce shop; three front bays; long striped awning; yellow trim; shallow hipped roof.",fresh_produce_shop),
        ("butcher_shop","ButcherShop",29,(7.3,8.8,6.3),"Terracotta two-story butcher; thick cream shop frame; small upper windows; side delivery door.",butcher_shop)]

scene_dir=a.PROJECT/"scenes/buildings/batch_09"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_09/"+slug+".tscn")
    entries.append(entry)
    (scene_dir/(slug+".tscn")).write_text(f'''[gd_scene load_steps=3 format=3]

[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_09/{slug}.glb" id="1"]

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
        resource_path="res://assets/models/buildings/batch_09/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text("\n".join(line for line in template.split("\n") if not line.startswith("uid=")))
    print("BATCH_09_BUILT",slug,entry["triangles"],"triangles",flush=True)
(a.ASSET/"manifest.json").write_text(json.dumps({"batch":9,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+"\n")
(a.ASSET/"README.md").write_text('# Lowcar — building batch 09\n\nNoodle Kitchen (026), Ice Cream Shop (027), Fresh Produce Shop (028), Butcher Shop (029). Approved pastel French Quarter styling, thick cream trim, recessed painted glazing, and neighborhood scale.\n\nPlacement scenes: `scenes/buildings/batch_09/`. Meters, ground-center origins, Godot +Z front, shared static meshes, and simple main-body collision. Canopies and roof details extend beyond the body collider. The ice cream shop uses a simple bounding box around its clipped corner. Editable Blender sources: `source/`.\n\nIncluded in the driving city after relaunch. Review: `scenes/review/building_batch_09.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_09.py`.\n')
