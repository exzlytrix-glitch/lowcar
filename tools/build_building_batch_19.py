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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_19"
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


def terrace_office_block():
    w,d,h=15.2,10.8,3.05
    front=b.frame(w,d,3,"cream",ground_color="mint",height=h)[0]
    front.row(.15,h-.09,[(4.3,1.71,.15,2.59,"lobby"),(10.46,5.40,.80,2.59,"window")],"mint")
    for du in (-1.8,-.9,0,.9,1.8):
        front.part("Ground_group_mullion",10.46+du,1.70,.072,1.67,"ink",.06,-.13)
    for level in (1,2):
        sill,head=level*h+.69,(level+1)*h-.47
        centers=(2.61,7.60,12.59)
        front.row(level*h+.15,(level+1)*h-.09,[(u,3.20,sill,head,"window") for u in centers],"cream")
        for u in centers:
            for du in (-.54,.54):
                front.part("Long_window_mullion",u+du,(sill+head)/2,.074,head-sill-.12,"ink",.06,-.13)
        front.part("Mint_floor_accent",w/2,level*h-.10,w-.22,.18,"mint",.14,.035)
    for u in (.18,w-.18):
        front.part("Cream_corner_trim",u,4.62,.28,8.76,"cream",.24,.065)
    front.part("Lobby_canopy",4.3,2.86,2.41,.18,"cream",.93,.29,.025)
    b.cornice(w,d,3*h,True)
    a.parapet("Mint_terrace_border",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],3*h+.17,"mint",.57)
    before={obj.name for obj in a.collection.objects}
    uw,ud=12.2,6.4
    upper=b.frame(uw,ud,1,"cream",height=h)[0]
    upper.row(.15,h-.09,[(2.2,3.0,.62,2.57,"window"),(6.1,1.32,.15,2.57,"door"),
                        (10.0,3.0,.62,2.57,"window")],"cream")
    for u in (2.2,10.0):
        for du in (-.51,.51):
            upper.part("Top_window_mullion",u+du,1.60,.073,1.82,"ink",.06,-.13)
    b.cornice(uw,ud,h,False)
    box("Upper_blue_cap",(0,0,h+.23),(uw+.42,ud+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((0,2.2,3*h))))
    box("Front_terrace_planter",(0,-4.90,3*h+.53),(11.20,.58,.50),"mint_dark",.025)
    box("Planter_white_lip",(0,-4.90,3*h+.83),(11.38,.70,.12),"cream",.02)
    for x in (-4.2,0,4.2):
        a.shrub("Terrace_green",(x,-4.90,3*h+1.09),(.72,.24,.30))
    box("Short_rear_roof_room",(3.4,3.6,4*h+.70),(2.10,1.8,.62),"mint",.025)
    box("Roof_room_cap",(3.4,3.6,4*h+1.08),(2.32,2.02,.14),"cream",.02)


def narrow_window_office():
    w,d,h=13.8,9.0,3.15
    front=b.frame(w,d,3,"yellow",ground_color="cream",height=h)[0]
    front.row(.15,h-.09,[(2.6,3.14,.83,2.75,"window"),(6.9,1.50,.15,2.75,"lobby"),
                        (11.2,3.14,.83,2.75,"window")],"cream")
    for level in (1,2):
        sill,head=level*h+.62,(level+1)*h-.46
        bays=[(center+offset,.78,sill,head,"window") for center in (2.55,6.9,11.25) for offset in (-1.0,0,1.0)]
        front.row(level*h+.15,(level+1)*h-.09,bays,"yellow")
        front.part("Broad_white_floor_band",w/2,level*h,w+.14,.24,"cream",.26,.06)
    for u in (.18,w-.18):
        front.part("Cream_corner_pier",u,4.78,.28,9.13,"cream",.23,.06)
    front.part("Lobby_canopy",6.9,2.96,2.37,.19,"roof",1.0,.32,.025)
    flat_roof(w,d,3*h,"yellow",.35)


def faceted_corner_office():
    h=3.05
    outline=[(-7.0,-2.3),(-3.7,-5.3),(7,-5.3),(7,5.3),(-7,5.3)]
    a.prism("Faceted_foundation",outline,0,.15,"stone",.025)
    walls=[]
    for i,p in enumerate(outline):
        q=outline[(i+1)%len(outline)]
        walls.append(a.Wall("Office_facet_%d"%i,p,q,(q[1]-p[1],p[0]-q[0])))
    for level in range(4):
        low,high=level*h+.15,(level+1)*h-.09
        a.prism("Faceted_floor",outline,(level+1)*h-.09,(level+1)*h+.09,"cream",.015)
        for i,wall in enumerate(walls):
            if i==0:
                bays=[(wall.length/2,1.67 if level==0 else 2.90,.15 if level==0 else level*h+.62,high-.47,"lobby" if level==0 else "window")]
            elif i==1:
                bays=[(u,2.24,level*h+.68,high-.47,"window") for u in (2.0,5.35,8.70)]
            else:
                count=2 if wall.length<9 else 3
                bays=[(wall.length*(j+1)/(count+1),2.01,level*h+.69,high-.47,"window") for j in range(count)]
            wall.row(low,high,bays,"cream" if level==0 else "blue")
            wall.part("White_floor_band",wall.length/2,(level+1)*h,wall.length+.08,.23,"cream",.28,.055)
    for wall in walls:
        wall.part("Cream_plinth",wall.length/2,.29,wall.length,.28,"cream",.20,.02)
        for u in (.14,wall.length-.14):
            wall.part("Cream_facet_edge",u,6.13,.27,11.81,"cream",.24,.055)
        wall.part("Broad_top_cornice",wall.length/2,4*h+.04,wall.length+.20,.28,"cream",.43,.06,.025)
    corner=walls[0]
    corner.part("Angled_lobby_canopy",corner.length/2,2.87,2.37,.18,"cream",.97,.30,.025)
    a.prism("Flat_faceted_blue_cap",[(x*1.015,y*1.015) for x,y in outline],4*h+.20,4*h+.44,"roof",.035)


def broad_finance_office():
    w,d,h=17.6,10.2,3.2
    front=b.frame(w,d,3,"cream",height=h)[0]
    inset=a.Wall("Deep_finance_glazing",(-w/2,-d/2+.25),(w/2,-d/2+.25),(0,-1))
    def deep_window(u,sill,width,height,kind="window"):
        inset.window(u,sill,width,height,kind)
        for du in (-width/2,width/2):
            front.part("Deep_cream_jamb",u+du,sill+height/2,.13,height+.17,"cream",.48,-.19)
        for z in (sill,sill+height):
            front.part("Deep_cream_lintel",u,z,width+.13,.12,"cream",.48,-.19)
        front.part("Deep_window_sill",u,sill-.06,width+.27,.15,"stone",.52,-.15,.015)
    front.window=deep_window
    front.row(.15,h-.09,[(3.3,4.8,.78,2.76,"window"),(8.8,2.03,.15,2.76,"lobby"),
                        (14.3,4.8,.78,2.76,"window")],"cream")
    for level in (1,2):
        sill,head=level*h+.69,(level+1)*h-.46
        centers=(3.3,8.8,14.3)
        front.row(level*h+.15,(level+1)*h-.09,[(u,4.15,sill,head,"window") for u in centers],"cream")
        for u in centers:
            for du in (-.70,.70):
                front.part("Deep_group_mullion",u+du,(sill+head)/2,.074,head-sill-.12,"ink",.06,-.37)
        front.part("Teal_floor_accent",w/2,level*h-.08,w-.28,.20,"teal",.08,.025)
    for u in (7.52,10.08):
        front.part("Central_entry_pier",u,1.60,.31,2.79,"cream",.32,.055)
    for u in (.18,w-.18):
        front.part("Cream_corner_trim",u,4.84,.29,9.31,"cream",.25,.065)
    front.part("Central_teal_canopy",8.8,2.97,3.24,.20,"teal",1.36,.44,.025)
    b.cornice(w,d,3*h,True)
    box("Broad_blue_roof",(0,0,3*h+.23),(w+.42,d+.42,.26),"roof",.035)
    box("Small_teal_roof_room",(2.97,2.24,10.13),(3.25,2.71,.68),"teal",.035)
    box("Roof_room_cream_cap",(2.97,2.24,10.52),(3.47,2.93,.14),"cream",.025)


models=[("terrace_office_block","TerraceOfficeBlock",76,(15.2,10.8,12.2),"Broad cream four-story office; mint ground floor and terrace wall; long window groups; smaller top floor and short rear roof room.",terrace_office_block),
    ("narrow_window_office","NarrowWindowOffice",77,(13.8,9.0,9.45),"Broad butter-yellow three-story office; three groups of slender navy-blue windows; cream ground floor; shallow parapet.",narrow_window_office),
    ("faceted_corner_office","FacetedCornerOffice",78,(14.0,10.6,12.2),"Broad powder-blue four-story corner office; large chamfered street face; wrapping recessed blue windows; cream base and flat blue cap.",faceted_corner_office),
    ("broad_finance_office","BroadFinanceOffice",79,(17.6,10.2,9.6),"Wide cream three-story finance office; deeper painted blue window recesses; central teal canopy and entry bay; small rear roof room.",broad_finance_office)]

terrace_colliders=[((0,4.575,0),(15.2,9.15,10.8)),((0,10.675,-2.2),(12.2,3.05,6.4))]
corner_colliders=[((1.65,6.1,0),(10.7,12.2,10.6)),((-5.35,6.1,-1.5),(3.3,12.2,7.6))]
corner_hull=[(-7,0,2.3),(-3.7,0,5.3),(-3.7,0,2.3),(-7,12.2,2.3),(-3.7,12.2,5.3),(-3.7,12.2,2.3)]

scene_dir=a.PROJECT/"scenes/buildings/batch_19"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=terrace_colliders if slug=="terrace_office_block" else corner_colliders if slug=="faceted_corner_office" else [((0,h/2,0),(w,h,d))]
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_19/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    hull=corner_hull if slug=="faceted_corner_office" else []
    if hull:
        entry["collision_hull_godot_m"]=hull
    parts=[f'[gd_scene load_steps={len(colliders)+2+(1 if hull else 0)} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_19/{slug}.glb" id="1"]\n']
    for i,(_,dim) in enumerate(colliders):
        parts.append(f'[sub_resource type="BoxShape3D" id="Body{i}"]\nsize = Vector3({dim[0]}, {dim[1]}, {dim[2]})\n')
    if hull:
        values=", ".join(str(value) for point in hull for value in point)
        parts.append('[sub_resource type="ConvexPolygonShape3D" id="CornerHull"]\npoints = PackedVector3Array('+values+')\n')
    parts.extend([f'[node name="{name}" type="Node3D"]\n',
                  '[node name="Visual" parent="." instance=ExtResource("1")]\n',
                  '[node name="BuildingBody" type="StaticBody3D" parent="."]\ncollision_layer = 1\ncollision_mask = 0\n'])
    for i,(at,_) in enumerate(colliders):
        node="Collision" if i==0 else f"Collision{i}"
        parts.append(f'[node name="{node}" type="CollisionShape3D" parent="BuildingBody"]\nposition = Vector3({at[0]}, {at[1]}, {at[2]})\nshape = SubResource("Body{i}")\n')
    if hull:
        parts.append('[node name="CornerCollision" type="CollisionShape3D" parent="BuildingBody"]\nshape = SubResource("CornerHull")\n')
    (scene_dir/(slug+".tscn")).write_text('\n'.join(parts))
    import_path=a.ASSET/(slug+".glb.import")
    if not import_path.exists():
        template=(a.PROJECT/"assets/models/buildings/batch_01/corner_cafe.glb.import").read_text()
        resource_path="res://assets/models/buildings/batch_19/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_19_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":19,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 19\n\nTerrace Office Block (076), Narrow-Window Office (077), Faceted Corner Office (078), Broad Finance Office (079). Approved bright pastel French Quarter style, substantial cream trim, recessed painted blue glazing, broad three- and four-story proportions.\n\nPlacement scenes: `scenes/buildings/batch_19/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Simple body boxes follow the upper setback. The faceted corner uses two boxes and a triangular convex prism to preserve its angled street edge. Trim, canopies, terrace planting, and roof rooms remain visual. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_19.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_19.py`.\n')
