"""Four neighborhood Lowcar offices using the approved pastel architectural kit."""
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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_20"
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


def wedge_office():
    h=3.15
    outline=[(-7.2,-3.0),(7.2,-5.0),(7.2,5.0),(-7.2,5.0)]
    a.prism("Wedge_foundation",outline,0,.15,"stone",.025)
    walls=[]
    for i,p in enumerate(outline):
        q=outline[(i+1)%len(outline)]
        walls.append(a.Wall("Wedge_face_%d"%i,p,q,(q[1]-p[1],p[0]-q[0])))
    for level in range(3):
        low,high=level*h+.15,(level+1)*h-.09
        a.prism("Wedge_floor_plate",outline,(level+1)*h-.09,(level+1)*h+.09,"cream",.015)
        for i,wall in enumerate(walls):
            if i==0:
                centers=(2.6,wall.length/2,wall.length-2.6)
                bays=[(u,3.0,level*h+.69,high-.46,"window") for u in centers]
                if level==0:
                    bays[1]=(wall.length/2,1.53,.15,2.73,"lobby")
            else:
                count=3 if wall.length>12 else 2
                bays=[(wall.length*(j+1)/(count+1),1.63,level*h+.73,high-.47,"window") for j in range(count)]
            wall.row(low,high,bays,"cream" if level==0 else "coral")
            wall.part("White_floor_band",wall.length/2,(level+1)*h,wall.length+.1,.21,"cream",.25,.055)
            if i==0 and level>0:
                for u in centers:
                    for du in (-.51,.51):
                        wall.part("Window_group_mullion",u+du,(level*h+.69+high-.46)/2,.072,high-.46-(level*h+.69)-.12,"ink",.06,-.13)
    for wall in walls:
        wall.part("Cream_base",wall.length/2,.29,wall.length,.28,"cream",.19,.02)
        for u in (.17,wall.length-.17):
            wall.part("Cream_corner_trim",u,4.78,.27,9.13,"cream",.22,.055)
        wall.part("Roof_cornice",wall.length/2,3*h+.03,wall.length+.19,.25,"cream",.37,.05,.025)
    front=walls[0]
    front.part("Angled_lobby_canopy",front.length/2,2.94,2.36,.18,"cream",.98,.30,.025)
    a.parapet("Wedge_roof_edge",outline,3*h+.17,"coral",.40)
    front.part("Raised_center_roof_step",front.length/2,10.15,5.0,.36,"coral",.22,-.045,.018)
    front.part("Step_cream_cap",front.length/2,10.38,5.20,.12,"cream",.34,-.025,.015)


def offset_core_office():
    w,d,h=10.9,9.0,3.05
    before={obj.name for obj in a.collection.objects}
    front=b.frame(w,d,4,"mint",height=h)[0]
    front.row(.15,h-.09,[(2.0,2.75,.76,2.59,"window"),(5.45,1.60,.15,2.59,"lobby"),
                        (8.9,2.75,.76,2.59,"window")],"mint")
    for level in (1,2,3):
        sill,head=level*h+.67,(level+1)*h-.47
        front.row(level*h+.15,(level+1)*h-.09,[(u,2.44,sill,head,"window") for u in (2.0,5.45,8.9)],"mint")
        front.part("White_floor_band",w/2,level*h,w+.12,.22,"cream",.24,.055)
        if level==2:
            for u in (2.0,8.9):
                b.shutters(front,u,sill,2.44,head-sill,"blue_dark")
    for u in (.18,w-.18):
        front.part("Cream_corner_trim",u,6.13,.27,11.78,"cream",.22,.055)
    front.part("Lobby_canopy",5.45,2.86,2.29,.18,"cream",.95,.28,.025)
    b.cornice(w,d,4*h,True)
    box("Main_blue_roof_cap",(0,0,4*h+.23),(w+.40,d+.40,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((1.55,.5,0))))
    before={obj.name for obj in a.collection.objects}
    sw,sd=3.1,10.0
    walls=rectangle(sw,sd,"Cream_stair_core")
    box("Core_foundation",(0,0,.075),(sw,sd,.15),"stone",.025)
    for level in range(4):
        box("Core_floor_plate",(0,0,(level+1)*h),(sw,sd,.18),"cream")
        for i,wall in enumerate(walls):
            bays=[(wall.length/2,1.10,level*h+.72,(level+1)*h-.49,"window")] if i in (0,2) else [(wall.length*f,1.17,level*h+.74,(level+1)*h-.49,"window") for f in (.28,.72)]
            wall.row(level*h+.15,(level+1)*h-.09,bays,"cream")
        walls[0].part("Blue_core_floor_accent",sw/2,(level+1)*h-.17,sw-.24,.13,"blue_dark",.08,.03)
    b.cornice(sw,sd,4*h,False)
    a.parapet("Cream_core_edge",[(-sw/2,-sd/2),(sw/2,-sd/2),(sw/2,sd/2),(-sw/2,sd/2)],4*h+.17,"cream",.37)
    move_new(before,Matrix.Translation(Vector((-5.45,0,0))))
    a.ac_unit("Offset_roof_equipment",(4.30,2.65,4*h+.36),(2.0,1.10,.65))


def double_setback_office():
    w,d,h=15.6,11.0,3.05
    front=b.frame(w,d,2,"cream",height=h)[0]
    front.row(.15,h-.09,[(2.8,3.50,.79,2.59,"window"),(7.8,2.60,.15,2.59,"lobby"),
                        (12.8,3.50,.79,2.59,"window")],"cream")
    front.row(h+.15,2*h-.09,[(u,2.65,h+.63,2*h-.47,"window") for u in (2.8,7.8,12.8)],"cream")
    for u in (2.8,7.8,12.8):
        for du in (-.45,.45):
            front.part("Lower_group_mullion",u+du,4.66,.072,1.83,"ink",.06,-.13)
    for u in (.18,w-.18):
        front.part("Cream_corner_pier",u,3.10,.28,5.88,"cream",.24,.06)
    front.part("Generous_lobby_canopy",7.8,2.87,3.50,.19,"roof",1.12,.37,.025)
    b.cornice(w,d,2*h,False)
    a.parapet("First_setback_edge",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],2*h+.17,"cream",.36)
    for uw,ud,cx,cy,z,color,centers,width in ((13.2,9.2,-.2,.6,2*h,"blue",(2.5,6.6,10.7),2.45),
                                           (10.6,7.4,-.65,1.4,3*h,"cream",(2.0,5.3,8.6),2.14)):
        before={obj.name for obj in a.collection.objects}
        upper=b.frame(uw,ud,1,color,height=h)[0]
        upper.row(.15,h-.09,[(u,width,.62,2.57,"window") for u in centers],color)
        b.cornice(uw,ud,h,False)
        if color=="blue":
            a.parapet("Second_setback_edge",[(-uw/2,-ud/2),(uw/2,-ud/2),(uw/2,ud/2),(-uw/2,ud/2)],h+.17,color,.36)
        else:
            box("Top_flat_blue_cap",(0,0,h+.23),(uw+.42,ud+.42,.26),"roof",.03)
        move_new(before,Matrix.Translation(Vector((cx,cy,z))))


def simple_city_office():
    w,d,h=13.2,8.8,3.15
    front=b.frame(w,d,3,"yellow",height=h)[0]
    front.row(.15,h-.09,[(2.2,1.35,.15,2.65,"door"),(6.6,1.64,.81,2.45,"window"),
                        (11.0,1.64,.81,2.45,"window")],"yellow")
    for level in (1,2):
        front.row(level*h+.15,(level+1)*h-.09,[(u,1.64,level*h+.81,level*h+2.45,"window") for u in (2.2,6.6,11.0)],"yellow")
        front.part("Cream_grid_band",w/2,level*h,w+.12,.22,"cream",.24,.055)
    for u in (.18,w-.18):
        front.part("Cream_corner_trim",u,4.78,.28,9.13,"cream",.23,.06)
    for u in (4.4,8.8):
        front.part("Upper_grid_pier",u,6.38,.22,5.89,"cream",.21,.055)
    front.part("Offset_door_canopy",2.2,2.90,2.09,.18,"cream",.83,.24,.025)
    b.cornice(w,d,3*h,False)
    box("Flat_blue_roof_lip",(0,0,3*h+.22),(w+.42,d+.42,.23),"roof",.03)


models=[("wedge_office","WedgeOffice",80,(14.4,10.0,9.45),"Broad coral three-story office; gently angled street frontage; regular blue windows; cream ground floor and stepped roof edge.",wedge_office),
    ("offset_core_office","OffsetCoreOffice",81,(14.0,10.0,12.2),"Broad mint four-story office; integrated cream stair core on one side; wide blue windows; offset roof equipment.",offset_core_office),
    ("double_setback_office","DoubleSetbackOffice",82,(15.6,11.0,12.2),"Broad cream four-story office with two shallow upper setbacks; powder-blue third floor; grouped windows and generous lobby.",double_setback_office),
    ("simple_city_office","SimpleCityOffice",83,(13.2,8.8,9.45),"Ordinary broad butter-yellow three-story office; square blue window grid; offset door; quiet cream cornice and flat blue lip.",simple_city_office)]

wedge_colliders=[((0,4.725,-1.0),(14.4,9.45,8.0))]
wedge_hull=[(-7.2,0,3.0),(7.2,0,5.0),(7.2,0,3.0),(-7.2,9.45,3.0),(7.2,9.45,5.0),(7.2,9.45,3.0)]
core_colliders=[((1.55,6.1,-.5),(10.9,12.2,9.0)),((-5.45,6.1,0),(3.1,12.2,10.0))]
setback_colliders=[((0,3.05,0),(15.6,6.1,11.0)),((-.2,7.625,-.6),(13.2,3.05,9.2)),((-.65,10.675,-1.4),(10.6,3.05,7.4))]

scene_dir=a.PROJECT/"scenes/buildings/batch_20"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=wedge_colliders if slug=="wedge_office" else core_colliders if slug=="offset_core_office" else setback_colliders if slug=="double_setback_office" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_20/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    hull=wedge_hull if slug=="wedge_office" else []
    if hull:
        entry["collision_hull_godot_m"]=hull
    parts=[f'[gd_scene load_steps={len(colliders)+2+(1 if hull else 0)} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_20/{slug}.glb" id="1"]\n']
    for i,(_,dim) in enumerate(colliders):
        parts.append(f'[sub_resource type="BoxShape3D" id="Body{i}"]\nsize = Vector3({dim[0]}, {dim[1]}, {dim[2]})\n')
    if hull:
        values=", ".join(str(value) for point in hull for value in point)
        parts.append('[sub_resource type="ConvexPolygonShape3D" id="FrontHull"]\npoints = PackedVector3Array('+values+')\n')
    parts.extend([f'[node name="{name}" type="Node3D"]\n',
                  '[node name="Visual" parent="." instance=ExtResource("1")]\n',
                  '[node name="BuildingBody" type="StaticBody3D" parent="."]\ncollision_layer = 1\ncollision_mask = 0\n'])
    for i,(at,_) in enumerate(colliders):
        node="Collision" if i==0 else f"Collision{i}"
        parts.append(f'[node name="{node}" type="CollisionShape3D" parent="BuildingBody"]\nposition = Vector3({at[0]}, {at[1]}, {at[2]})\nshape = SubResource("Body{i}")\n')
    if hull:
        parts.append('[node name="FrontCollision" type="CollisionShape3D" parent="BuildingBody"]\nshape = SubResource("FrontHull")\n')
    (scene_dir/(slug+".tscn")).write_text('\n'.join(parts))
    import_path=a.ASSET/(slug+".glb.import")
    if not import_path.exists():
        template=(a.PROJECT/"assets/models/buildings/batch_01/corner_cafe.glb.import").read_text()
        resource_path="res://assets/models/buildings/batch_20/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_20_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":20,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 20\n\nWedge Office (080), Offset-Core Office (081), Double-Setback Office (082), Simple City Office (083). Approved bright pastel French Quarter style, substantial cream trim, recessed painted blue glazing, broad three- and four-story proportions.\n\nPlacement scenes: `scenes/buildings/batch_20/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Simple body boxes follow the cream stair core and upper setbacks. The wedge has a body box plus a triangular convex prism matching its angled street front. Trim, canopies, and roof details remain visual. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_20.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_20.py`.\n')
