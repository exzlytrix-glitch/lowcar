"""Four neighborhood Lowcar houses using the approved pastel architectural kit."""
from pathlib import Path
import importlib.util
import json
import hashlib
from math import pi
from mathutils import Matrix, Vector

spec=importlib.util.spec_from_file_location("lowcar_batch_parts",Path(__file__).with_name("build_building_batch_01.py"))
b=importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
a=b.a
box,rod,mesh=a.box,a.rod,a.mesh
a.ASSET=a.PROJECT/"assets/models/buildings/batch_13"
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
    # Closed triangular end slabs preserve stable outward normals at both ends.
    for end in (-1,1):
        tri=[(cx-half,end*d/2,z),(cx+half,end*d/2,z),(cx,end*d/2,peak)]
        tri += [(x,y-end*.12,zz) for x,y,zz in tri]
        mesh("Cream_gable_end",tri,[(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)],"cream")
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


def move_new(before,transform):
    a.bpy.context.view_layer.update()
    for obj in a.collection.objects:
        if obj.name not in before and obj.type=="MESH":
            obj.matrix_world=transform @ obj.matrix_world


def peach_flat_roof_home():
    w,d,h=9.2,9.0,3.10
    front=b.frame(w,d,2,"coral",height=h)[0]
    front.row(.15,h-.09,[(2.02,1.16,.15,2.68,"door"),(6.13,3.34,.78,2.68,"window")],"coral")
    sill,head=h+.47,2*h-.55
    front.row(h+.15,2*h-.09,[(u,1.51,sill,head,"window") for u in (1.83,4.60,7.37)],"coral")
    for u in (1.83,7.37):
        b.shutters(front,u,sill,1.51,head-sill,"blue_dark")
    b.gallery(front,w/2,h+.14,w-.67,.95,"scroll")
    front.part("Door_canopy",2.02,2.86,1.79,.18,"cream",.78,.23,.025)
    for u in (.18,w-.18):
        front.part("Cream_corner_trim",u,3.18,.28,5.93,"cream",.20,.045)
    flat_roof(w,d,2*h,"coral",.42)
    box("Rear_roof_hatch",(2.21,2.70,2*h+.39),(1.71,1.62,.43),"coral_dark",.03)
    box("Hatch_cap",(2.21,2.70,2*h+.65),(1.93,1.84,.12),"cream",.02)
    box("Entry_step",(-w/2+2.02,-d/2-.29,.075),(1.57,.67,.15),"cream",.02)


def split_level_home():
    h=3.10
    before={obj.name for obj in a.collection.objects}
    w,d=7.1,9.2
    front=b.frame(w,d,2,"blue",height=h)[0]
    front.row(.15,h-.09,[(u,1.57,.80,2.67,"window") for u in (1.78,5.32)],"blue")
    sill,head=h+.63,2*h-.56
    front.row(h+.15,2*h-.09,[(u,1.17,sill,head,"window") for u in (1.49,3.55,5.61)],"blue")
    for u in (1.49,5.61):
        b.shutters(front,u,sill,1.17,head-sill,"teal")
    for u in (.17,w-.17):
        front.part("Cream_corner_trim",u,3.18,.25,5.94,"cream",.20,.045)
    flat_roof(w,d,2*h,"blue",.38)
    box("Small_roof_vent",(-1.62,2.50,2*h+.40),(.60,.72,.47),"metal",.02)
    box("Vent_cap",(-1.62,2.50,2*h+.69),(.79,.91,.13),"cream",.02)
    move_new(before,Matrix.Translation(Vector((-2.35,0,0))))
    before={obj.name for obj in a.collection.objects}
    w,d=4.7,7.7
    front=b.frame(w,d,1,"blue_dark",height=h)[0]
    front.row(.15,h-.09,[(1.36,1.46,.82,2.67,"window"),(3.60,1.10,.15,2.67,"door")],"blue_dark")
    front.part("Entry_canopy",3.60,2.87,1.65,.18,"cream",.80,.25,.025)
    for u in (.17,w-.17):
        front.part("Cream_corner_trim",u,1.62,.25,2.90,"cream",.20,.045)
    flat_roof(w,d,h,"blue_dark",.30)
    box("Entry_step",(-w/2+3.60,-d/2-.28,.075),(1.48,.63,.15),"cream",.02)
    move_new(before,Matrix.Translation(Vector((3.55,-.75,0))))


def roof_garden_house():
    w,d,h=8.8,9.3,3.10
    front=b.frame(w,d,2,"cream",height=h)[0]
    front.row(.15,h-.09,[(2.08,1.77,.76,2.67,"window"),(4.40,1.14,.15,2.67,"door"),(6.72,1.77,.76,2.67,"window")],"cream")
    sill,head=h+.65,2*h-.56
    front.row(h+.15,2*h-.09,[(u,1.06,sill,head,"window") for u in (1.89,3.24,5.56,6.91)],"cream")
    for u in (1.89,6.91):
        b.shutters(front,u,sill,1.06,head-sill,"mint_dark")
    front.part("Cream_entry_canopy",4.40,2.87,1.91,.18,"cream",.85,.25,.025)
    for u in (.17,w-.17):
        front.part("Cream_corner_trim",u,3.18,.25,5.94,"cream",.21,.04)
    b.cornice(w,d,2*h,True)
    # Third floor is a smaller setback volume, leaving a planted terrace in front.
    before={obj.name for obj in a.collection.objects}
    uw,ud=7.2,6.5
    upper=b.frame(uw,ud,1,"cream",height=h)[0]
    upper.row(.15,h-.09,[(u,1.01,.77,2.66,"window") for u in (1.22,2.57,4.63,5.98)],"cream")
    for u in (1.22,5.98):
        b.shutters(upper,u,.77,1.01,1.89,"mint_dark")
    flat_roof(uw,ud,h,"cream",.41)
    move_new(before,Matrix.Translation(Vector((-.05,1.0,2*h))))
    box("Chunky_front_planter_wall",(0,-4.09,2*h+.40),(7.94,.61,.58),"mint_dark",.025)
    box("Planter_cream_lip",(0,-4.09,2*h+.73),(8.09,.74,.14),"cream",.02)
    box("Planter_soil",(0,-4.09,2*h+.80),(7.72,.47,.03),"ink")
    for x in (-3.03,-1.82,-.61,.61,1.82,3.03):
        a.shrub("Roof_planting",(x,-4.09,2*h+1.04),(.53,.27,.31))
    for x in (-2.82,2.82):
        box("Upper_roof_planter",(x,2.70,3*h+.41),(1.36,.74,.51),"mint_dark",.025)
        box("Upper_planter_cap",(x,2.70,3*h+.70),(1.50,.86,.12),"cream",.02)
        a.shrub("Upper_roof_green",(x,2.70,3*h+.96),(.57,.29,.32))


def wrap_balcony_house():
    w,d,h=9.0,9.0,3.10
    outline=[(-4.5,-4.5),(3.45,-4.5),(4.5,-3.45),(4.5,4.5),(-4.5,4.5)]
    a.prism("Corner_foundation",outline,0,.15,"stone",.025)
    for level in (1,2):
        a.prism("Corner_floor_plate",outline,level*h-.09,level*h+.09,"cream",.015)
    front=a.Wall("Wrap_front",outline[0],outline[1],(0,-1))
    corner=a.Wall("Recessed_corner",outline[1],outline[2],(1,-1))
    right=a.Wall("Wrap_right",outline[2],outline[3],(1,0))
    rear=a.Wall("Wrap_rear",outline[3],outline[4],(0,1))
    left=a.Wall("Wrap_left",outline[4],outline[0],(-1,0))
    for wall in (front,corner,right,rear,left):
        if wall is corner:
            ground=[(wall.length/2,1.08,.15,2.67,"door")]
            upper=[(wall.length/2,.83,h+.66,2*h-.60,"window")]
        elif wall in (front,right):
            ground=[(wall.length*f,1.65,.79,2.67,"window") for f in (.25,.73)]
            upper=[(wall.length*f,1.21,h+.50,2*h-.56,"window") for f in (.20,.50,.80)]
        else:
            ground=[(wall.length*.53,1.08,.15 if wall is rear else 1.03,2.65,"door" if wall is rear else "window")]
            upper=[(wall.length*f,1.21,h+.68,2*h-.59,"window") for f in (.28,.70)]
        wall.row(.15,h-.09,ground,"yellow")
        wall.row(h+.15,2*h-.09,upper,"yellow")
        wall.part("Cream_base",wall.length/2,.30,wall.length,.28,"cream",.19,.015)
    for wall in (front,right):
        b.gallery(wall,wall.length/2,h+.15,wall.length-.37,.97,"scroll",True)
        for u in (wall.length*.20,wall.length*.80):
            b.shutters(wall,u,h+.50,1.21,2*h-.56-(h+.50),"blue_dark")
    corner.part("Corner_entry_header",corner.length/2,2.84,1.39,.19,"cream",.41,.10,.015)
    b.cornice(w,d,2*h,False)
    gable(w+.28,d+.22,2*h+.18,7.82)


models=[("peach_flat_roof_home","PeachFlatRoofHome",47,(9.2,9.0,6.2),"Coral two-story square home; long cream scrollwork balcony; broad ground window; full-width flat parapet.",peach_flat_roof_home),
        ("split_level_home","SplitLevelHome",49,(11.8,9.2,6.2),"Powder-blue home with a two-story main block and a lower one-story entrance wing; offset flat roofs.",split_level_home),
        ("roof_garden_house","RoofGardenHouse",50,(8.8,9.3,9.3),"Cream three-story home with a partial upper setback; chunky mint planter walls; paired narrow front windows.",roof_garden_house),
        ("wrap_balcony_house","WrapBalconyHouse",51,(9.0,9.0,6.2),"Butter-yellow two-story corner home; L-shaped white galleries; recessed corner door; broad blue pitched roof.",wrap_balcony_house)]

split_colliders=[((-2.35,3.1,0),(7.1,6.2,9.2)),((3.55,1.55,.75),(4.7,3.1,7.7))]
garden_colliders=[((0,3.1,0),(8.8,6.2,9.3)),((-.05,7.75,-1.0),(7.2,3.1,6.5))]

scene_dir=a.PROJECT/"scenes/buildings/batch_13"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=split_colliders if slug=="split_level_home" else garden_colliders if slug=="roof_garden_house" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_13/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_13/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_13/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_13_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":13,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 13\n\nPeach Flat-Roof Home (047), Split-Level Home (049), Roof-Garden House (050), Wrap-Balcony House (051). Approved pastel French Quarter finish, thick cream trim, recessed painted blue glazing, shutters, and occasional ornamental galleries.\n\nPlacement scenes: `scenes/buildings/batch_13/`. Meters, ground-center origins, Godot +Z front, and one static visual mesh per building. Split-level and roof-garden homes use two body boxes matching their different heights; the other homes use a simple body box. Roof ornaments, canopies, and balconies remain visual details. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_13.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_13.py`.\n')
