"""Four ordinary Lowcar storefronts using the approved pastel architectural kit."""
from pathlib import Path
import importlib.util
import json
import hashlib
from math import cos, sin, pi

spec=importlib.util.spec_from_file_location("lowcar_batch_parts",Path(__file__).with_name("build_building_batch_01.py"))
b=importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
a=b.a
box,rod,mesh=a.box,a.rod,a.mesh
a.ASSET=a.PROJECT/"assets/models/buildings/batch_08"
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


def clip_glass(points,threshold,keep_left):
    result=[]
    for p,q in zip(points,points[1:]+points[:1]):
        fp,fq=p[0]+.48*p[1]-threshold,q[0]+.48*q[1]-threshold
        inside_p=fp<=0 if keep_left else fp>=0
        inside_q=fq<=0 if keep_left else fq>=0
        if inside_p:
            result.append(p)
        if inside_p!=inside_q:
            t=fp/(fp-fq)
            result.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
    return result


def arched_shop(wall,u,sill,width,height,color):
    radius=width/2
    head=sill+height
    rise=1.10
    spring=head-rise
    arc=[(radius*cos(pi-i*pi/8),spring+rise*sin(pi-i*pi/8)) for i in range(9)]
    # Fill the wall above the arch, keeping the opening itself genuinely curved.
    for i,(p,q) in enumerate(zip(arc,arc[1:])):
        polygon=[p,q,(q[0],head),(p[0],head)]
        clean=[]
        for point in polygon:
            if not clean or abs(point[0]-clean[-1][0])+abs(point[1]-clean[-1][1])>.00001:
                clean.append(point)
        if len(clean)>1 and abs(clean[0][0]-clean[-1][0])+abs(clean[0][1]-clean[-1][1])<.00001:
            clean.pop()
        n=len(clean)
        vertices=[wall.point(u+x,z,out) for out in (0,-.38) for x,z in clean]
        faces=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]
        faces += [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        mesh("Arch_spandrel_%02d"%i,vertices,faces,color)
    outline=[(-radius,sill),(radius,sill)]+list(reversed(arc))
    relative=[(x,z-(sill+head)/2) for x,z in outline]
    band=width*.10
    regions=[(clip_glass(relative,-band,True),"glass"),
             (clip_glass(clip_glass(relative,-band,False),band,True),"reflection"),
             (clip_glass(relative,band,False),"glass")]
    for points,material in regions:
        vertices=[wall.point(u+x,z+(sill+head)/2,-.143) for x,z in points]
        mesh("Arched_blue_glazing",vertices,[tuple(range(len(vertices)))],material)
    trim=[wall.point(u+x,z,.05) for x,z in arc]
    for p,q in zip(trim,trim[1:]):
        rod("Faceted_white_arch",p,q,.22,"cream")
    for side in (-1,1):
        rod("Arch_jamb",wall.point(u+side*radius,sill,.05),wall.point(u+side*radius,spring,.05),.20,"cream")
    wall.part("Arch_sill",u,sill-.045,width+.28,.16,"stone",.31,.08,.02)
    wall.part("Shop_mullion",u,(sill+head)/2,.09,head-sill-.10,"teal",.07,-.10)
    wall.part("Shop_transom",u,spring-.05,width-.16,.08,"teal",.07,-.10)


def radio_shop():
    w,d,h=9.8,8.6,3.10
    front=b.frame(w,d,3,"cream","blue_dark",h)[0]
    front.row(.15,h-.09,[(2.30,3.06,.48,2.68,"shop"),(5.27,1.12,.15,2.68,"door"),(7.88,2.41,.48,2.68,"shop")],"blue_dark")
    for level in (1,2):
        front.row(level*h+.15,(level+1)*h-.09,[(u,2.68,level*h+.62,(level+1)*h-.54,"window") for u in (2.75,7.05)],"cream")
    front.part("Storefront_canopy",w/2,2.91,w+.12,.18,"cream",.92,.30,.025)
    sign(front,w/2,3.40,5.45,"RADIO & ELECTRIC",.32)
    for u in (.19,w-.19):
        front.part("White_corner_trim",u,4.73,.27,9.04,"cream",.20,.075)
    x,y=-w/2-.42,-d/2+.88
    box("Projecting_radio_sign",(x,y,4.43),(.15,1.12,1.00),"blue_dark",.03)
    rod("Sign_bracket",(-w/2+.03,y,4.88),(x,y,4.88),.10,"cream")
    a.text("Side_radio_letters","RADIO",(x-.087,y,4.43),.24,angle=-pi/2)
    flat_roof(w,d,3*h,"cream",.39)
    box("Offset_roof_housing",(2.20,2.16,3*h+.64),(3.00,2.70,.92),"blue_dark",.035)
    box("Housing_cap",(2.20,2.16,3*h+1.18),(3.24,2.94,.16),"cream",.025)
    a.ac_unit("Roof_AC",(-2.62,2.06,3*h+.11))


def ceramic_shop():
    w,d,h=7.4,8.4,3.20
    front=b.frame(w,d,2,"coral_dark",height=h)[0]
    standard_window=front.window
    front.window=lambda u,sill,width,height,kind="window": arched_shop(front,u,sill,width,height,"coral_dark") if kind=="arch" else standard_window(u,sill,width,height,kind)
    front.row(.15,h-.09,[(2.75,3.40,.44,2.87,"arch"),(5.97,1.05,.15,2.68,"door")],"coral_dark")
    front.row(h+.15,2*h-.09,[(u,1.31,h+.55,2*h-.55,"window") for u in (1.95,5.69)],"coral_dark")
    b.gallery(front,1.95,h+.13,2.87,.80,"scroll")
    sign(front,5.91,3.47,2.01,"CLAY",.32)
    for u in (1.95,5.69):
        b.shutters(front,u,h+.55,1.31,2*h-.55-(h+.55),"blue_dark")
    flat_roof(w,d,2*h,"coral_dark",.38)
    box("Courtyard_paving",(5.85,0,.04),(4.3,d,.08),"stone")
    for x,width in ((3.975,.55),(7.225,1.55)):
        box("Courtyard_front_wall",(x,-d/2,.42),(width,.18,.84),"cream",.015)
        box("Front_wall_cap",(x,-d/2,.89),(width+.10,.28,.12),"cream",.015)
    for name,at,size in (("Courtyard_right_wall",(8.0,0,.42),(.18,d,.84)),("Courtyard_rear_wall",(5.85,d/2,.42),(4.3,.18,.84))):
        box(name,at,size,"cream",.015)
        box(name+"_cap",(at[0],at[1],.89),(size[0]+.10,size[1]+.10,.12),"cream",.015)
    a.planter("Courtyard_pot",(7.30,2.70,.08),.35,.48)
    a.planter("Courtyard_pot",(4.38,2.70,.08),.29,.42)
    a.ac_unit("Roof_AC",(-1.85,2.15,2*h+.11))
    # Center the complete building and court footprint at the shared asset origin.
    for part in a.collection.objects:
        if part.type=="MESH":
            part.location.x-=2.15


def avenue_diner():
    w,d,h=13.0,7.0,3.10
    front,right,rear,left=rectangle(w,d,"Diner")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Roof_plate",(0,0,h),(w,d,.18),"cream")
    for wall in (front,right,rear,left):
        if wall is front:
            openings=[(1.74,2.55,.62,2.65,"shop"),(5.09,2.75,.62,2.65,"shop"),(8.18,1.12,.15,2.65,"door"),(11.21,2.56,.62,2.65,"shop")]
        elif wall is rear:
            openings=[(wall.length*.68,1.11,.15,2.65,"door")]
        else:
            openings=[(u,1.75,.62,2.65,"shop") for u in (2.0,5.0)]
        wall.row(.15,h-.09,openings,"cream")
        wall.part("Coral_base_band",wall.length/2,.36,wall.length,.41,"coral",.18,.015)
    box("White_roof_edge",(0,-.10,h+.11),(w+.94,d+.70,.18),"cream",.025)
    box("Broad_blue_overhang",(0,-.10,h+.25),(w+1.00,d+.76,.23),"roof",.035)
    front.part("Coral_diner_fascia",w/2,3.25,6.13,.38,"coral",.11,.57,.02)
    a.text("Diner_letters","AVENUE DINER",front.point(w/2,3.25,.634),.35)
    box("Rear_kitchen_block",(3.48,1.97,3.80),(4.15,2.62,1.02),"coral",.035)
    box("Kitchen_cap",(3.48,1.97,4.38),(4.39,2.86,.16),"cream",.025)
    box("Kitchen_vent",(3.48,1.97,4.65),(.66,.72,.39),"metal",.025)
    box("Vent_cap",(3.48,1.97,4.91),(.92,.98,.14),"cream",.02)


def pizza_shop():
    w,d,h=8.6,8.8,3.20
    front,right,rear,left=rectangle(w,d,"Pizza")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Roof_plate",(0,0,h),(w,d,.18),"cream")
    for wall in (front,right,rear,left):
        if wall is front:
            openings=[(2.42,3.41,.48,2.72,"shop"),(6.36,1.25,.15,2.72,"door")]
        elif wall is right:
            openings=[(d/2,4.22,.48,2.72,"shop")]
        else:
            openings=[(wall.length*.63,1.06,.15 if wall is rear else 1.04,2.68,"door" if wall is rear else "window")]
        wall.row(.15,h-.09,openings,"coral")
        wall.part("White_plinth",wall.length/2,.31,wall.length,.30,"cream",.19,.02)
    front.part("Square_entry_canopy",6.36,2.93,3.83,.22,"cream",1.16,.39,.03)
    right.part("Side_display_canopy",d/2,2.93,4.69,.18,"cream",.81,.26,.025)
    for wall,u in ((front,w-.20),(right,.20)):
        wall.part("Corner_white_pier",u,1.66,.34,2.97,"cream",.23,.08)
    flat_roof(w,d,h,"coral",.39)
    front.part("Raised_sign_crown",4.85,3.87,4.99,.61,"coral",.27,-.07)
    front.part("Crown_white_cap",4.85,4.23,5.20,.14,"cream",.39,-.07,.02)
    sign(front,4.85,3.87,3.84,"PIZZA",.41)
    a.ac_unit("Roof_AC",(-1.62,2.64,h+.11))


models=[("radio_shop","RadioShop",13,(9.8,8.6,9.3),"Broad cream three-story radio shop; stacked window groups; projecting sign slab; offset blue roof housing.",radio_shop),
        ("ceramic_shop","CeramicShop",19,(11.7,8.4,6.4),"Terracotta two-story ceramic shop; faceted white arch; scrollwork balcony; open side courtyard.",ceramic_shop),
        ("avenue_diner","AvenueDiner",22,(13.0,7.0,3.1),"Long cream and coral diner; broad windows; deep blue roof overhang; low rear kitchen block.",avenue_diner),
        ("pizza_shop","PizzaShop",25,(8.6,8.8,3.2),"Squat coral corner pizza shop; broad entrance canopy; two deep display panes; raised sign parapet.",pizza_shop)]


scene_dir=a.PROJECT/"scenes/buildings/batch_08"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    collision_boxes=[((0,h/2,0),(w,h,d))]
    if slug == "ceramic_shop":
        collision_boxes=[((-2.15,3.2,0),(7.4,6.4,8.4)),((3.7,.04,0),(4.3,.08,8.4)),
                         ((1.825,.42,4.2),(.55,.84,.18)),((5.075,.42,4.2),(1.55,.84,.18)),
                         ((5.85,.42,0),(.18,.84,8.4)),((3.7,.42,-4.2),(4.3,.84,.18))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_08/"+slug+".tscn",collision_boxes_m=collision_boxes)
    entries.append(entry)
    lines=[f'[gd_scene load_steps={len(collision_boxes)+2} format=3]\n',f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_08/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_08/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text("\n".join(line for line in template.split("\n") if not line.startswith("uid=")))
    print("BATCH_08_BUILT",slug,entry["triangles"],"triangles",flush=True)
(a.ASSET/"manifest.json").write_text(json.dumps({"batch":8,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+"\n")
(a.ASSET/"README.md").write_text('# Lowcar — building batch 08\n\nRadio Shop (013), Ceramic Shop (019), Avenue Diner (022), Pizza Shop (025). Approved clean pastels, cream trim, recessed painted glazing, and neighborhood scale.\n\nPlacement scenes: `scenes/buildings/batch_08/`. Shared static visual meshes, meters, ground-center origins, Godot +Z front. The ceramic shop uses six simple collision boxes so its side courtyard remains open; the other three use main-body boxes. Canopies, balconies and roof ornaments extend beyond the main bodies. Editable Blender sources: `source/`.\n\nIncluded in the driving city after relaunch. Review scene: `scenes/review/building_batch_08.tscn` (F6). 0 for all, 1–4 select, drag to orbit, wheel to zoom. Overview: `previews/lineup.png`.\n\nRebuild with Blender and `tools/build_building_batch_08.py`.\n')
