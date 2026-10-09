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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_14"
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


def small_courtyard_house():
    w,d,h=12.2,10.0,3.10
    outline=[(-6.1,-5),(-2.4,-5),(-2.4,.8),(2.4,.8),(2.4,-5),(6.1,-5),(6.1,5),(-6.1,5)]
    upper_outline=[(-6.1,-5),(-2.4,-5),(-2.4,.8),(6.1,.8),(6.1,5),(-6.1,5)]
    lower_outline=[(2.4,-5),(6.1,-5),(6.1,.8),(2.4,.8)]
    a.prism("U_foundation",outline,0,.15,"stone",.025)
    a.prism("First_floor_plate",outline,h-.09,h+.09,"cream",.015)
    a.prism("Upper_roof_plate",upper_outline,2*h-.09,2*h+.09,"cream",.02)
    walls=[(a.Wall("Courtyard_front_left",outline[0],outline[1],(0,-1)),2),
           (a.Wall("Courtyard_inner_left",outline[1],outline[2],(1,0)),2),
           (a.Wall("Courtyard_back",outline[2],outline[3],(0,-1)),2),
           (a.Wall("Courtyard_inner_right",outline[3],outline[4],(-1,0)),1),
           (a.Wall("Courtyard_front_right",outline[4],outline[5],(0,-1)),1),
           (a.Wall("Courtyard_right_low",outline[5],(6.1,.8),(1,0)),1),
           (a.Wall("Courtyard_right_rear",(6.1,.8),outline[6],(1,0)),2),
           (a.Wall("Courtyard_rear",outline[6],outline[7],(0,1)),2),
           (a.Wall("Courtyard_outer_left",outline[7],outline[0],(-1,0)),2)]
    for wall,floors in walls:
        for level in range(floors):
            if wall.name=="Courtyard_back" and level==0:
                bays=[(.85,1.03,.77,2.66,"window"),(2.40,1.10,.15,2.66,"door"),(3.95,1.03,.77,2.66,"window")]
            elif "front_" in wall.name:
                bays=[(wall.length/2,1.48,level*h+.78,(level+1)*h-.45,"window")]
            else:
                count=3 if wall.length>7 else 2
                bays=[(wall.length*(i+1)/(count+1),1.17,level*h+.81,(level+1)*h-.47,"window") for i in range(count)]
            wall.row(level*h+.15,(level+1)*h-.09,bays,"coral_dark")
            if level==1 and wall.name in ("Courtyard_front_left","Courtyard_back"):
                for u,width,sill,head,kind in bays:
                    b.shutters(wall,u,sill,width,head-sill,"blue_dark")
        wall.part("Cream_base",wall.length/2,.30,wall.length,.28,"cream",.18,.015)
        wall.part("Cream_cornice",wall.length/2,floors*h+.04,wall.length+.17,.24,"cream",.33,.06,.018)
    step_wall=a.Wall("Upper_wall_over_low_wing",(2.4,.8),(6.1,.8),(0,-1))
    step_wall.row(h+.15,2*h-.09,[(1.85,1.45,h+.79,2*h-.47,"window")],"coral_dark")
    step_wall.part("Cream_step_cornice",1.85,2*h+.04,3.87,.24,"cream",.33,.06,.018)
    a.parapet("Upper_L_parapet",upper_outline,2*h+.17,"coral_dark",.34)
    a.parapet("Lower_wing_parapet",lower_outline,h+.17,"coral_dark",.27)
    box("Courtyard_paving",(0,-2.1,.035),(4.8,5.8,.07),"stone")
    for x in (-1.75,1.75):
        box("Front_gate_wall",(x,-5,.425),(1.30,.18,.85),"cream",.02)
        box("Gate_wall_cap",(x,-5,.90),(1.40,.29,.12),"cream",.015)
    a.planter("Courtyard_pot",(1.55,-.07,.07),.33,.46)
    box("Upper_roof_hatch",(-4.32,2.29,2*h+.40),(1.59,1.79,.43),"coral_dark",.025)
    box("Hatch_cap",(-4.32,2.29,2*h+.66),(1.79,1.99,.12),"cream",.02)


def tile_roof_bungalow():
    w,d,h=10.8,9.0,3.0
    front=b.frame(w,d,1,"cream",height=h)[0]
    front.row(.15,h-.09,[(2.43,2.13,.74,2.65,"window"),(5.46,1.60,.74,2.65,"window"),(8.63,1.14,.15,2.65,"door")],"cream")
    for u,width in ((2.43,2.13),(5.46,1.60)):
        b.shutters(front,u,.74,width,1.91,"mint_dark")
    box("Porch_slab",(0,-d/2-.65,.075),(w+.22,1.53,.15),"stone",.025)
    for x in (-4.35,4.35):
        box("Thick_porch_column",(x,-d/2-1.06,1.54),(.27,.27,2.84),"cream",.02)
        box("Column_foot",(x,-d/2-1.06,.20),(.43,.43,.25),"cream",.025)
        box("Column_capital",(x,-d/2-1.06,2.90),(.43,.43,.22),"cream",.02)
    front.part("Cream_porch_beam",w/2,3.04,w+.18,.23,"cream",.28,1.07,.02)
    before={obj.name for obj in a.collection.objects}
    # Broad painted terracotta roof facets suggest tile without individual tile noise.
    a.materials['roof']=a.materials['coral_dark']
    b.hip_roof(w,10.1,h+.20,4.54)
    move_new(before,Matrix.Translation(Vector((0,-.55,0))))
    box("Rear_roof_vent",(-2.91,2.75,4.17),(.48,.59,.57),"coral_dark",.025)
    box("Vent_cap",(-2.91,2.75,4.51),(.69,.80,.13),"cream",.02)


def artists_townhouse():
    w,d,h=7.3,9.0,3.10
    front=b.frame(w,d,3,"lilac",height=h)[0]
    front.row(.15,h-.09,[(1.51,1.13,.15,2.68,"door"),(4.92,2.38,.78,2.68,"window")],"lilac")
    sill,head=h+.62,2*h-.56
    front.row(h+.15,2*h-.09,[(u,1.45,sill,head,"window") for u in (1.82,5.48)],"lilac")
    for u in (1.82,5.48):
        b.shutters(front,u,sill,1.45,head-sill,"blue_dark")
    front.row(2*h+.15,3*h-.09,[(w/2,4.58,2*h+.41,3*h-.46,"shop")],"lilac")
    for u in (2.50,4.80):
        front.part("Studio_white_mullion",u,7.73,.10,2.03,"cream",.085,-.07)
    front.part("Cream_entry_header",1.51,2.82,1.65,.22,"cream",.33,.08,.018)
    front.part("Small_entry_canopy",1.51,2.99,1.90,.17,"cream",.77,.23,.025)
    for u in (.18,w-.18):
        front.part("Cream_corner_trim",u,4.72,.28,9.02,"cream",.21,.045)
    flat_roof(w,d,3*h,"lilac",.35)
    box("Small_roof_setback",(1.28,2.42,3*h+.69),(2.62,2.51,1.06),"blue_dark",.035)
    box("Setback_cream_cap",(1.28,2.42,3*h+1.30),(2.86,2.75,.15),"cream",.025)
    box("Roof_access_door",(1.28,1.14,3*h+.59),(.81,.04,.84),"teal")


def annex_townhouse():
    w,h=7.8,3.10
    before={obj.name for obj in a.collection.objects}
    d=7.3
    front=b.frame(w,d,2,"mint",height=h)[0]
    front.row(.15,h-.09,[(1.63,1.14,.15,2.67,"door"),(5.03,2.34,.79,2.67,"window")],"mint")
    sill,head=h+.64,2*h-.56
    front.row(h+.15,2*h-.09,[(u,1.18,sill,head,"window") for u in (1.59,3.90,6.21)],"mint")
    for u in (1.59,6.21):
        b.shutters(front,u,sill,1.18,head-sill,"blue_dark")
    front.part("Front_entry_canopy",1.63,2.87,1.82,.18,"cream",.82,.25,.025)
    for u in (.18,w-.18):
        front.part("Cream_corner_trim",u,3.18,.26,5.94,"cream",.21,.045)
    flat_roof(w,d,2*h,"mint",.36)
    move_new(before,Matrix.Translation(Vector((0,-2.15,0))))
    before={obj.name for obj in a.collection.objects}
    d=4.3
    front,right,rear,left=rectangle(w,d,"Annex")
    box("Annex_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    box("Annex_ceiling",(0,0,h),(w,d,.18),"cream")
    for wall in (front,right,rear,left):
        if wall is left:
            bays=[(1.80,1.12,.15,2.64,"door")]
        elif wall is right:
            bays=[(2.20,1.20,1.00,2.64,"window")]
        elif wall is rear:
            bays=[(w/2,1.62,.86,2.64,"window")]
        else:
            bays=[]
        wall.row(.15,h-.09,bays,"mint_dark")
        wall.part("Cream_base",wall.length/2,.30,wall.length,.28,"cream",.18,.015)
    left.part("Side_service_canopy",1.80,2.83,1.64,.17,"cream",.72,.22,.025)
    b.cornice(w,d,h,False)
    box("Low_blue_roof_cap",(0,0,h+.20),(w+.42,d+.42,.22),"roof",.03)
    move_new(before,Matrix.Translation(Vector((0,3.65,0))))


models=[("small_courtyard_house","SmallCourtyardHouse",52,(12.2,10.0,6.2),"Terracotta U-shaped courtyard home; two-story left and rear wings; low right wing; open cream gate wall.",small_courtyard_house),
        ("tile_roof_bungalow","TileRoofBungalow",53,(10.8,9.0,3.0),"Cream one-story bungalow; broad terracotta roof planes; two thick porch columns; offset entrance.",tile_roof_bungalow),
        ("artists_townhouse","ArtistsTownhouse",54,(7.3,9.0,9.3),"Compact lilac three-story artist home; tall top-floor studio window; small blue roof setback; cream entry.",artists_townhouse),
        ("annex_townhouse","AnnexTownhouse",55,(7.8,11.6,6.2),"Mint two-story front home with a lower rear annex; stepped side silhouette; side service door; blue annex roof.",annex_townhouse)]

courtyard_colliders=[((-4.25,3.1,0),(3.7,6.2,10.0)),((1.85,3.1,-2.9),(8.5,6.2,4.2)),
                     ((4.25,1.55,2.1),(3.7,3.1,5.8)),((0,.035,2.1),(4.8,.07,5.8)),
                     ((-1.75,.425,5.0),(1.3,.85,.18)),((1.75,.425,5.0),(1.3,.85,.18))]
annex_colliders=[((0,3.1,2.15),(7.8,6.2,7.3)),((0,1.55,-3.65),(7.8,3.1,4.3))]

scene_dir=a.PROJECT/"scenes/buildings/batch_14"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=courtyard_colliders if slug=="small_courtyard_house" else annex_colliders if slug=="annex_townhouse" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_14/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_14/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_14/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_14_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":14,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 14\n\nSmall Courtyard House (052), Tile-Roof Bungalow (053), Artist’s Townhouse (054), Annex Townhouse (055). Approved pastel French Quarter finish, substantial cream trim, painted recessed blue glazing, and neighborhood scale.\n\nPlacement scenes: `scenes/buildings/batch_14/`. Meters, ground-center origins, Godot +Z front, one shared static visual mesh per building. The courtyard uses six boxes to preserve its open entrance and differently sized wings; the annex home uses two body boxes. Others use simple body boxes. Porch, canopy, planter, and roof details remain visual. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_14.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_14.py`.\n')
