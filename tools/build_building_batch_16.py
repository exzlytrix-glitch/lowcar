"""Four neighborhood Lowcar residential blocks using the approved pastel architectural kit."""
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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_16"
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


def blue_roof_apartments():
    w,d,h=12.8,9.2,2.95
    front=b.frame(w,d,4,"coral",height=h)[0]
    front.row(.15,h-.09,[(2.83,2.73,.74,2.49,"window"),(6.4,1.53,.15,2.49,"lobby"),
                        (9.97,2.73,.74,2.49,"window")],"coral")
    for level in (1,2,3):
        sill,head=level*h+.65,(level+1)*h-.46
        bays=[(u,1.44,sill,head,"window") for u in (2.15,4.35,8.45,10.65)]
        front.row(level*h+.15,(level+1)*h-.09,bays,"coral")
        for u in (2.15,10.65):
            b.shutters(front,u,sill,1.44,head-sill,"blue_dark")
        front.part("Cream_floor_trim",w/2,level*h,w+.1,.17,"cream",.23,.04)
    for u in (.18,w/2,w-.18):
        front.part("Cream_pilaster",u,5.96,.28,11.45,"cream",.21,.055)
    front.part("Portico_roof",6.4,2.71,2.88,.22,"cream",1.30,.43,.025)
    for x in (-1.17,1.17):
        box("Portico_column",(x,-d/2-.90,1.41),(.24,.24,2.38),"cream",.02)
        box("Portico_foot",(x,-d/2-.90,.23),(.40,.40,.22),"cream",.02)
        box("Portico_capital",(x,-d/2-.90,2.55),(.40,.40,.18),"cream",.02)
    box("Portico_step",(0,-d/2-.61,.08),(3.11,1.62,.16),"stone",.025)
    b.cornice(w,d,4*h,True)
    b.hip_roof(w,d,4*h+.18,13.50)
    for cx in (-3.10,3.10):
        y,low,top=-3.80,12.02,13.42
        dormer=a.Wall("Cream_dormer",(cx-.89,y-.80),(cx+.89,y-.80),(0,-1),.20)
        dormer.row(low,top,[(.89,1.16,12.28,13.25,"window")],"cream")
        for x in (cx-.82,cx+.82):
            box("Dormer_side",(x,y,(low+top)/2),(.14,1.6,top-low),"cream",.015)
        box("Dormer_rear",(cx,y+.72,(low+top)/2),(1.78,.16,top-low),"cream",.015)
        before={obj.name for obj in a.collection.objects}
        gable(2.02,1.78,13.46,13.84,cx)
        move_new(before,Matrix.Translation(Vector((0,y,0))))


def setback_apartments():
    w,d,h=13.8,10.2,3.10
    front=b.frame(w,d,3,"mint",height=h)[0]
    front.row(.15,h-.09,[(2.15,2.13,.78,2.64,"window"),(6.9,1.60,.15,2.64,"lobby"),
                        (11.1,2.13,.78,2.64,"window")],"mint")
    for level in (1,2):
        sill,head=level*h+.61,(level+1)*h-.50
        front.row(level*h+.15,(level+1)*h-.09,[(2.15,1.54,sill,head,"window"),
                         (6.9,2.64,sill,head,"window"),(11.1,1.54,sill,head,"window")],"mint")
        b.gallery(front,2.15,level*h+.39,2.43,.82,"scroll")
        b.shutters(front,11.1,sill,1.54,head-sill,"coral_dark")
    for u in (.17,w-.17):
        front.part("Cream_corner_trim",u,4.68,.28,8.96,"cream",.22,.05)
    front.part("Lobby_canopy",6.9,2.87,2.39,.19,"cream",.96,.29,.025)
    b.cornice(w,d,3*h,True)
    a.parapet("Terrace_border",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],3*h+.17,"mint",.50)
    before={obj.name for obj in a.collection.objects}
    uw,ud=8.8,7.2
    upper=b.frame(uw,ud,1,"mint",height=h)[0]
    upper.row(.15,h-.09,[(1.75,1.29,.72,2.64,"window"),(4.4,1.25,.15,2.64,"door"),
                        (7.05,1.29,.72,2.64,"window")],"mint")
    for u in (1.75,7.05):
        b.shutters(upper,u,.72,1.29,1.92,"blue_dark")
    flat_roof(uw,ud,h,"mint",.32)
    move_new(before,Matrix.Translation(Vector((1.2,.8,3*h))))
    for x in (-4.50,-2.83):
        a.planter("Terrace_planter",(x,-4.18,3*h+.12),.35,.48)
    box("Offset_roof_access",(3.13,2.79,4*h+.57),(1.72,1.50,.55),"mint_dark",.035)
    box("Roof_access_cap",(3.13,2.79,4*h+.91),(1.92,1.70,.13),"cream",.025)


def courtyard_apartments():
    h=3.1
    outline=[(-8.6,-6),(-3.1,-6),(-3.1,2.3),(3.1,2.3),(3.1,-6),(8.6,-6),(8.6,6),(-8.6,6)]
    a.prism("U_foundation",outline,0,.15,"stone",.025)
    walls=[a.Wall("Left_front",outline[0],outline[1],(0,-1)),
        a.Wall("Inner_left",outline[1],outline[2],(1,0)),
        a.Wall("Courtyard_rear",outline[2],outline[3],(0,-1)),
        a.Wall("Inner_right",outline[3],outline[4],(-1,0)),
        a.Wall("Right_front",outline[4],outline[5],(0,-1)),
        a.Wall("Outer_right",outline[5],outline[6],(1,0)),
        a.Wall("Rear",outline[6],outline[7],(0,1)),
        a.Wall("Outer_left",outline[7],outline[0],(-1,0))]
    portals={"Inner_left":4.0,"Outer_left":8.0}
    for level in range(1,5):
        a.prism("U_floor_plate",outline,level*h-.09,level*h+.09,"cream",.015)
    for wall in walls:
        original=wall.window
        wall.window=lambda u,sill,width,height,kind="window",base=original: None if kind=="passage" else base(u,sill,width,height,kind)
        for level in range(4):
            sill,head=level*h+.74,(level+1)*h-.49
            if level==0 and wall.name in portals:
                u=portals[wall.name]
                bay_u=6.77 if wall.name=="Inner_left" else 3.12
                bays=[(u,1.9,.15,2.55,"passage"),(bay_u,1.42,.84,2.61,"window")]
            elif wall.name=="Courtyard_rear" and level==0:
                bays=[(1.32,1.09,.79,2.64,"window"),(3.10,1.37,.15,2.64,"door"),(4.88,1.09,.79,2.64,"window")]
            else:
                count=2 if wall.length<8 else 3 if wall.length<15 else 4
                bays=[(wall.length*(i+1)/(count+1),1.43,sill,head,"window") for i in range(count)]
            wall.row(level*h+.15,(level+1)*h-.09,bays,"cream")
            wall.part("Terracotta_floor_accent",wall.length/2,(level+1)*h-.20,wall.length,.17,"coral_dark",.16,.035)
            if level in (1,3) and wall.name in ("Left_front","Right_front"):
                for u,width,sill,head,kind in bays:
                    b.shutters(wall,u,sill,width,head-sill,"mint_dark")
            if level==2 and wall.name=="Inner_right":
                b.gallery(wall,wall.length/2,level*h+.39,2.26,.63,"diamond")
        if wall.name in portals:
            u=portals[wall.name]
            for du in (-1.015,1.015):
                wall.part("Passage_cream_jamb",u+du,1.39,.18,2.47,"cream",.28,.025,.018)
            wall.part("Passage_cream_header",u,2.66,2.31,.22,"cream",.34,.04,.022)
            for left,right in ((0,u-.95),(u+.95,wall.length)):
                wall.part("Cream_base",(left+right)/2,.29,right-left,.28,"cream",.19,.02)
        else:
            wall.part("Cream_base",wall.length/2,.29,wall.length,.28,"cream",.19,.02)
        wall.part("Cream_cornice",wall.length/2,4*h+.03,wall.length+.18,.27,"cream",.37,.055,.025)
    for y in (-2.95,-1.05):
        box("Passage_side_return",(-5.85,y,1.40),(5.5,.18,2.5),"cream")
    box("Passage_ceiling",(-5.85,-2,2.64),(5.5,1.9,.18),"cream")
    box("Courtyard_paving",(0,-1.85,.035),(6.2,8.3,.07),"stone")
    a.parapet("Continuous_U_parapet",outline,4*h+.17,"coral_dark",.36)
    a.planter("Courtyard_corner_pot",(2.48,1.54,.07),.33,.47)


def long_balcony_apartments():
    w,d,h=16.2,8.6,3.10
    front=b.frame(w,d,3,"blue",height=h)[0]
    front.row(.15,h-.09,[(2.5,3.0,.77,2.64,"window"),(8.1,1.60,.15,2.64,"lobby"),
                        (13.7,3.0,.77,2.64,"window")],"blue")
    for level in (1,2):
        sill,head=level*h+.72,(level+1)*h-.49
        bays=[(u,1.70,sill,head,"window") for u in (1.80,4.90,11.30,14.40)]
        bays.append((8.10,1.48,level*h+.27,head,"door"))
        front.row(level*h+.15,(level+1)*h-.09,bays,"blue")
        for u in (1.80,14.40):
            b.shutters(front,u,sill,1.70,head-sill,"mint_dark")
        b.gallery(front,w/2,level*h+.14,w-.66,1.02,"scroll" if level==1 else "diamond",level==1)
    for u in (.17,w-.17):
        front.part("Cream_corner_trim",u,4.69,.28,8.98,"cream",.21,.055)
    front.part("Entry_canopy",8.10,2.87,2.21,.18,"roof",.87,.28,.025)
    front.part("Central_gallery_column",8.10,3.20,.20,6.09,"cream",.20,1.10,.015)
    for z in (.24,h-.03,2*h-.03):
        front.part("Column_cap",8.10,z,.35,.19,"cream",.35,1.10,.015)
    b.cornice(w,d,3*h,False)
    box("Flat_blue_roof_edge",(0,0,3*h+.23),(w+.44,d+.44,.26),"roof",.035)
    a.ac_unit("Rear_roof_AC",(4.17,2.24,3*h+.36),(1.55,.91,.61))


models=[("blue_roof_apartments","BlueRoofApartments",62,(12.8,9.2,11.8),"Broad coral four-story apartments; faceted blue pitched roof; two cream dormers; paired upper windows; chunky entrance portico.",blue_roof_apartments),
    ("setback_apartments","SetbackApartments",63,(13.8,10.2,12.4),"Broad mint three-story base with a smaller fourth floor; generous front and side terrace; corner balcony stack; offset roof access room.",setback_apartments),
    ("courtyard_apartments","CourtyardApartments",64,(17.2,12.0,12.4),"Broad cream four-story U-shaped apartments; terracotta floor accents and parapet; open central courtyard; real ground-level passage through left wing.",courtyard_apartments),
    ("long_balcony_apartments","LongBalconyApartments",65,(16.2,8.6,9.3),"Wide powder-blue three-story apartments; two full-width cream ornamental galleries; central entrance; flat blue roof edge.",long_balcony_apartments)]

setback_colliders=[((0,4.65,0),(13.8,9.3,10.2)),((1.2,10.85,-.8),(8.8,3.1,7.2))]
courtyard_colliders=[((-5.85,7.75,0),(5.5,9.3,12.0)),((-5.85,1.55,4.475),(5.5,3.1,3.05)),
    ((-5.85,1.55,-2.475),(5.5,3.1,7.05)),((5.85,6.2,0),(5.5,12.4,12.0)),
    ((0,6.2,-4.15),(6.2,12.4,3.7)),((-5.85,.075,2.0),(5.5,.15,1.9)),((0,.035,1.85),(6.2,.07,8.3))]

scene_dir=a.PROJECT/"scenes/buildings/batch_16"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=setback_colliders if slug=="setback_apartments" else courtyard_colliders if slug=="courtyard_apartments" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_16/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_16/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_16/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_16_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":16,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 16\n\nBlue-Roof Apartments (062), Setback Apartments (063), Courtyard Apartments (064), Long Balcony Apartments (065). Approved bright pastel French Quarter style, substantial cream trim, recessed blue glazing, broad neighborhood proportions, three or four stories.\n\nPlacement scenes: `scenes/buildings/batch_16/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. The setback uses two body boxes; courtyard collision preserves its open center and side passage. Other buildings use simple body boxes. Ornamental rails, columns, canopies, dormers, and roof details remain visual. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_16.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_16.py`.\n')
