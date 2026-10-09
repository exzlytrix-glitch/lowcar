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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_15"
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


def four_unit_walkup():
    w,d,h=12.4,8.8,3.1
    front=b.frame(w,d,2,"coral",height=h)[0]
    front.row(.15,h-.09,[(1.55,1.76,.78,2.64,"window"),(4.29,1.17,.15,2.64,"door"),
                        (7.71,1.17,.15,2.64,"door"),(10.45,1.76,.78,2.64,"window")],"coral")
    upper=[(u,1.76,h+.72,2*h-.50,"window") for u in (1.64,4.66,7.74,10.76)]
    front.row(h+.15,2*h-.09,upper,"coral")
    for u,width,sill,head,_ in upper:
        b.shutters(front,u,sill,width,head-sill,"blue_dark")
    for u in (4.29,7.71):
        front.part("Entrance_header",u,2.81,1.63,.20,"cream",.28,.08,.02)
        front.part("Entrance_canopy",u,2.98,1.95,.17,"roof",.92,.32,.02)
        box("Entry_step",(-w/2+u,-d/2-.31,.08),(1.63,.72,.16),"cream",.025)
    for u in (.18,w/2,w-.18):
        front.part("Cream_pilaster",u,3.15,.27,5.91,"cream",.21,.06)
    front.part("Upper_floor_band",w/2,h,w+.12,.18,"cream",.22,.06)
    b.cornice(w,d,2*h,True)
    box("Shallow_blue_roof_cap",(0,0,2*h+.23),(w+.45,d+.45,.25),"roof",.04)
    a.ac_unit("Rear_roof_AC",(2.75,2.22,2*h+.36))


def exterior_stair_apartments():
    w,d,h=10.0,9.0,3.1
    before={obj.name for obj in a.collection.objects}
    front,right,rear,left=rectangle(w,d,"StairBlock")
    box("Foundation",(0,0,.075),(w,d,.15),"stone",.025)
    for level in range(3):
        z=level*h
        box("Floor_plate",(0,0,(level+1)*h),(w,d,.18),"cream")
        front_bays=[(u,1.45,z+.73,(level+1)*h-.50,"window") for u in (1.67,5.0,8.33)]
        if level==0:
            front_bays[1]=(5.0,1.32,.15,2.64,"door")
        front.row(z+.15,(level+1)*h-.09,front_bays,"blue")
        for wall in (right,rear):
            wall.row(z+.15,(level+1)*h-.09,[(wall.length*.28,1.32,z+.77,(level+1)*h-.52,"window"),
                (wall.length*.72,1.32,z+.77,(level+1)*h-.52,"window")],"blue")
        # Landing doors are real openings on the access side, alternating with each flight.
        door_u=2.3 if level==1 else 8.15
        left.row(z+.15,(level+1)*h-.09,[(door_u,1.13,z+.15,(level+1)*h-.50,"door"),
                (4.15,1.37,z+.83,(level+1)*h-.52,"window")],"blue")
        front.part("White_floor_band",w/2,(level+1)*h,w+.12,.16,"cream",.24,.05)
    for wall in (front,right,rear,left):
        wall.part("Cream_base",wall.length/2,.29,wall.length,.28,"cream",.18,.02)
    for u in (.18,w-.18):
        front.part("Corner_trim",u,4.68,.28,8.95,"cream",.21,.06)
    front.part("Entry_canopy",5,2.84,1.90,.17,"cream",.75,.22,.02)
    b.shutters(front,1.67,h+.73,1.45,1.87,"mint_dark")
    b.shutters(front,8.33,2*h+.73,1.45,1.87,"mint_dark")
    flat_roof(w,d,3*h,"blue",.34)
    move_new(before,Matrix.Translation(Vector((1.5,0,0))))
    # Two open switchback flights, oversized treads and cream handrails.
    x=-4.75
    for flight in range(2):
        direction=1 if flight==0 else -1
        start_y=-3.90 if flight==0 else 2.10
        base=flight*h
        for i in range(12):
            y=start_y+direction*(i+.5)*.50
            z=base+(i+1)*h/12
            box("Stair_tread",(x,y,z-.08),(1.70,.52,.16),"cream",.012)
            box("Blue_riser",(x,y-direction*.25,z-.12),(1.65,.10,.24),"blue_dark")
        for side_x in (x-.74,x+.74):
            rod("Blue_stair_stringer",(side_x,start_y,base+.08),(side_x,start_y+direction*6,base+h-.10),.16,"blue_dark")
            rod("Cream_stair_handrail",(side_x,start_y,base+1.02),(side_x,start_y+direction*6,base+h+1.02),.09,"cream")
            for i in range(5):
                y=start_y+direction*i*1.5
                z=base+i*h/4
                rod("Stair_rail_post",(side_x,y,z+.10),(side_x,y,z+1.03),.08,"cream")
    for level,y in ((0,-4.20),(1,2.66),(2,-4.20)):
        z=level*h
        box("Access_landing",(-4.55,y,z+.08),(2.14,1.29,.16),"cream",.02)
        for edge_y in (y-.58,y+.58):
            rod("Landing_outer_rail",(-5.56,edge_y,z+.20),(-5.56,edge_y,z+1.12),.09,"cream")
        rod("Landing_cross_rail",(-5.56,y-.58,z+1.12),(-5.56,y+.58,z+1.12),.09,"cream")
        if level>0:
            for post_x in (-3.76,-5.40):
                box("Landing_support",(post_x,y,z/2),(.17,.17,z),"blue_dark",.014)
    box("Stair_side_paving",(-4.75,-.45,.025),(2.45,8.95,.05),"stone")


def faceted_corner_apartments():
    h=3.1
    outline=[(-6.3,-2.8),(-4.3,-4.8),(6.3,-4.8),(6.3,4.8),(-6.3,4.8)]
    a.prism("Chamfered_foundation",outline,0,.15,"stone",.025)
    walls=[a.Wall("Corner",outline[0],outline[1],(-1,-1)),
        a.Wall("Main_front",outline[1],outline[2],(0,-1)),
        a.Wall("Right",outline[2],outline[3],(1,0)),
        a.Wall("Rear",outline[3],outline[4],(0,1)),
        a.Wall("Left",outline[4],outline[0],(-1,0))]
    for level in range(4):
        low=level*h+.15
        high=(level+1)*h-.09
        a.prism("Chamfered_floor",outline,(level+1)*h-.09,(level+1)*h+.09,"cream")
        for i,wall in enumerate(walls):
            if i==0:
                bays=[(wall.length/2,1.76,level*h+.67,high-.48,"window")]
            elif i==1:
                bays=[(u,1.54,level*h+.76,high-.50,"window") for u in (1.77,5.30,8.83)]
                if level==0:
                    bays[1]=(5.30,1.39,.15,2.64,"door")
            else:
                bays=[(wall.length*f,1.35,level*h+.77,high-.50,"window") for f in (.24,.72)]
            wall.row(low,high,bays,"yellow")
            wall.part("Floor_trim",wall.length/2,(level+1)*h,wall.length,.17,"cream",.24,.055)
            if i==1 and level>0:
                u=1.77 if level!=2 else 8.83
                b.gallery(wall,u,level*h+.40,2.24,.78,"diamond")
            if i==4 and level in (1,3):
                for u,width,sill,head,_ in bays:
                    b.shutters(wall,u,sill,width,head-sill,"mint_dark")
    for wall in walls:
        wall.part("Cream_base",wall.length/2,.29,wall.length,.28,"cream",.19,.02)
        for u in (.13,wall.length-.13):
            wall.part("Corner_pilaster",u,6.22,.25,12.0,"cream",.21,.05)
        wall.part("Crown_lower",wall.length/2,4*h-.16,wall.length+.18,.20,"cream",.30,.03,.02)
        wall.part("Crown_cap",wall.length/2,4*h+.07,wall.length+.33,.23,"cream",.47,.05,.025)
    front=walls[1]
    front.part("Lobby_canopy",5.30,2.89,2.04,.18,"cream",.84,.24,.025)
    a.prism("Blue_chamfered_roof",[(x*1.02,y*1.025) for x,y in outline],4*h+.18,4*h+.44,"roof",.035)
    box("Modest_roof_hatch",(2.5,2.4,4*h+.68),(1.61,1.82,.48),"yellow",.025)
    box("Hatch_cap",(2.5,2.4,4*h+.97),(1.83,2.04,.13),"cream",.02)


def wide_window_apartments():
    w,d,h=14.8,8.8,3.1
    front=b.frame(w,d,4,"cream",height=h)[0]
    front.row(.15,h-.09,[(1.85,2.06,.15,2.65,"lobby"),(6.16,3.13,.91,2.51,"window"),
                        (11.48,3.13,.91,2.51,"window")],"cream")
    for level in (1,2,3):
        sill=level*h+.86
        head=(level+1)*h-.55
        bays=[(u,3.13,sill,head,"window") for u in (2.51,7.40,12.29)]
        front.row(level*h+.15,(level+1)*h-.09,bays,"cream")
        for u,_,_,_,_ in bays:
            for du in (-.53,.53):
                front.part("Horizontal_window_mullion",u+du,(sill+head)/2,.075,head-sill-.12,"ink",.06,-.13)
        front.part("Navy_spandrel_band",w/2,level*h+.38,w-.51,.41,"roof",.07,.035)
        if level in (1,3):
            b.gallery(front,7.40,level*h+.43,3.34,.69,"scroll")
    for u in (.17,4.96,9.87,w-.17):
        front.part("Cream_divider",u,6.22,.22,12.02,"cream",.22,.07)
    front.part("Offset_lobby_canopy",1.85,2.90,2.72,.19,"roof",1.07,.36,.025)
    front.part("Lobby_white_header",1.85,2.72,2.46,.18,"cream",.28,.06)
    b.cornice(w,d,4*h,False)
    box("Broad_navy_roof_cap",(0,0,4*h+.23),(w+.44,d+.44,.27),"roof",.03)
    a.ac_unit("Rear_roof_unit",(3.47,2.24,4*h+.38),(1.65,1.15,.64))


models=[("four_unit_walkup","FourUnitWalkup",56,(12.4,8.8,6.2),"Broad coral two-story walkup; paired cream entrances; four generous shuttered upstairs windows; shallow blue roof cap.",four_unit_walkup),
    ("exterior_stair_apartments","ExteriorStairApartments",59,(13.0,9.0,9.3),"Powder-blue three-story apartments; chunky open switchback stair; alternating access landings; cream rails; low flat roof.",exterior_stair_apartments),
    ("faceted_corner_apartments","FacetedCornerApartments",60,(12.6,9.6,12.4),"Broad butter-yellow four-story corner block; chamfered blue window column; staggered shallow balconies; blue roof cap.",faceted_corner_apartments),
    ("wide_window_apartments","WideWindowApartments",61,(14.8,8.8,12.4),"Long cream four-story apartments; recessed horizontal navy window groups; offset lobby; two shallow ornamental balconies.",wide_window_apartments)]

stair_colliders=[((1.5,4.65,0),(10.0,9.3,9.0)),((-4.75,.025,.45),(2.45,.05,8.95))]
for flight in range(2):
    direction=1 if flight==0 else -1
    start_y=-3.90 if flight==0 else 2.10
    for i in range(12):
        y=start_y+direction*(i+.5)*.50
        z=flight*3.1+(i+1)*3.1/12
        stair_colliders.append(((-4.75,z-.08,-y),(1.70,.16,.52)))
for level,y in ((0,-4.20),(1,2.66),(2,-4.20)):
    stair_colliders.append(((-4.55,level*3.1+.08,-y),(2.14,.16,1.29)))
corner_colliders=[((1.0,6.2,0),(10.6,12.4,9.6)),((-5.3,6.2,-1.0),(2.0,12.4,7.6)),
                  ((-4.8,6.2,3.3),(1.0,12.4,1.0))]

scene_dir=a.PROJECT/"scenes/buildings/batch_15"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=stair_colliders if slug=="exterior_stair_apartments" else corner_colliders if slug=="faceted_corner_apartments" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_15/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_15/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_15/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_15_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":15,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 15\n\nFour-Unit Walkup (056), Exterior-Stair Apartments (059), Faceted Corner Apartments (060), Wide Window Apartments (061). Bright pastel French Quarter finish, substantial cream trim, recessed painted blue glazing, broad neighborhood proportions.\n\nPlacement scenes: `scenes/buildings/batch_15/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Simple box collision includes the exterior stairs and open landings; corner collision follows the chamfer with overlapping body boxes. Decorative rails, canopies, and roof details remain visual. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_15.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_15.py`.\n')
