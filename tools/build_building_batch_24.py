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
a.ASSET=a.PROJECT/"assets/models/buildings/batch_24"
a.SOURCE=a.ASSET/"source"
a.PREVIEWS=a.ASSET/"previews"
for folder in (a.ASSET,a.SOURCE,a.PREVIEWS):
    folder.mkdir(parents=True,exist_ok=True)
for folder in (a.SOURCE,a.PREVIEWS):
    (folder/".gdignore").write_text("")


def move_new(before,transform):
    a.bpy.context.view_layer.update()
    for obj in a.collection.objects:
        if obj.name not in before and obj.type=="MESH":
            obj.matrix_world=transform @ obj.matrix_world


def inset_lobby(front,depth=.48):
    original=front.window
    back=a.Wall("Recessed_lobby",(front.start.x,front.start.y+depth),(front.end.x,front.end.y+depth),(0,-1))
    def glazing(u,sill,width,height,kind="window"):
        if kind not in ("door","lobby"):
            return original(u,sill,width,height,kind)
        back.window(u,sill,width,height,kind)
        for du in (-width/2,width/2):
            front.part("Lobby_reveal_jamb",u+du,sill+height/2,.15,height+.17,"cream",depth+.22,-depth/2,.015)
        for z in (sill,sill+height):
            front.part("Lobby_reveal_lintel",u,z,width+.16,.14,"cream",depth+.22,-depth/2,.015)
    front.window=glazing


def rectangle(w,d,label):
    return [a.Wall(label+"_front",(-w/2,-d/2),(w/2,-d/2),(0,-1)),
            a.Wall(label+"_right",(w/2,-d/2),(w/2,d/2),(1,0)),
            a.Wall(label+"_rear",(w/2,d/2),(-w/2,d/2),(0,1)),
            a.Wall(label+"_left",(-w/2,d/2),(-w/2,-d/2),(-1,0))]


def shutter_bays(wall):
    original=wall.window
    def window(u,sill,width,height,kind="window"):
        if kind!="loading":
            return original(u,sill,width,height,kind)
        wall.part("Closed_loading_shutter",u,sill+height/2,width,height,"roof",.14,-.14,.025)
        for i in range(6):
            wall.part("Loading_shutter_slat",u,sill+.24+i*(height-.48)/5,width-.14,.065,"reflection",.06,-.035)
        for du in (-width/2,width/2):
            wall.part("Loading_cream_jamb",u+du,sill+height/2,.16,height+.14,"cream",.22,.025)
        wall.part("Loading_cream_header",u,sill+height,width+.25,.17,"cream",.22,.025)
        wall.part("Shutter_handle",u,sill+.87,.53,.095,"cream",.08,-.005,.015)
    wall.window=window


def postal_sorting_building():
    w,d,h=18.8,12.0,3.2
    walls=rectangle(w,d,"Postal")
    box("Postal_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    for level in range(2):
        box("Postal_floor_plate",(0,0,(level+1)*h),(w,d,.18),"cream")
        for i,wall in enumerate(walls):
            if level==0 and i==0:
                bays=[(4.6,1.62,.15,2.72,"lobby"),(12.3,5.6,1.27,2.72,"window")]
            elif level==0 and i==2:
                shutter_bays(wall)
                bays=[(u,3.45,.15,2.87,"loading") for u in (3.15,9.4,15.65)]
            elif level==0:
                bays=[(wall.length*.30,1.50,1.84,2.75,"window"),(wall.length*.72,1.16,.15,2.65,"door")]
            else:
                count=5 if i==0 else 3
                bays=[(wall.length*(j+.5)/count,2.19,level*h+1.22,level*h+2.40,"window") for j in range(count)]
            wall.row(level*h+.15,(level+1)*h-.09,bays,"coral_dark")
            wall.part("Postal_cream_band",wall.length/2,(level+1)*h,wall.length+.13,.25,"cream",.26,.055)
    front=walls[0]
    front.part("Front_office_canopy",4.6,3.00,3.3,.20,"roof",1.10,.37,.025)
    front.part("Postal_name_panel",w/2,3.51,5.2,.44,"teal",.15,.12,.02)
    a.text("Postal_name","POST",front.point(w/2,3.51,.21),.39)
    for wall in walls:
        wall.part("Postal_cream_base",wall.length/2,.29,wall.length,.28,"cream",.20,.02)
        for u in (.19,wall.length-.19):
            wall.part("Postal_corner_trim",u,3.25,.31,6.17,"cream",.24,.06)
    b.cornice(w,d,2*h,False)
    box("Postal_flat_blue_roof",(0,0,2*h+.23),(w+.42,d+.42,.26),"roof",.03)


def design_studio():
    w,d,h=15.0,11.0,3.1
    front=b.frame(w,d,2,"cream",height=h)[0]
    front.row(.15,h-.09,[(u,2.66,.71,2.65,"window") for u in (3.0,7.5,12.0)],"cream")
    front.row(h+.15,2*h-.09,[(u,3.00,h+.66,2*h-.46,"window") for u in (3.0,7.5,12.0)],"cream")
    front.part("Lilac_lower_floor_accent",w/2,h-.06,w-.20,.19,"lilac",.14,.025)
    for u in (.18,w-.18):
        front.part("Studio_base_corner_trim",u,3.15,.29,5.91,"cream",.23,.055)
    b.cornice(w,d,2*h,False)
    a.parapet("Cream_studio_terrace_edge",[(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)],2*h+.17,"cream",.49)
    before={obj.name for obj in a.collection.objects}
    uw,ud=11.8,7.8
    upper=b.frame(uw,ud,1,"lilac",height=h)[0]
    upper.row(.15,h-.09,[(u,4.16,.49,2.67,"window") for u in (2.55,9.25)],"lilac")
    for u in (2.55,9.25):
        for du in (-.72,.72):
            upper.part("Oversized_studio_glass_bar",u+du,1.59,.074,2.02,"ink",.06,-.12)
    b.cornice(uw,ud,h,False)
    box("Studio_top_blue_cap",(0,0,h+.23),(uw+.42,ud+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((-.4,1.2,2*h))))
    before={obj.name for obj in a.collection.objects}
    ew,ed=4.2,2.6
    entrance=b.frame(ew,ed,1,"lilac",height=h)[0]
    entrance.row(.15,h-.09,[(ew/2,1.65,.15,2.62,"lobby")],"lilac")
    entrance.part("Studio_entry_panel",ew/2,2.89,2.47,.33,"teal",.12,.10,.018)
    a.text("Studio_letters","STUDIO",entrance.point(ew/2,2.89,.18),.27)
    b.cornice(ew,ed,h,False)
    box("Low_entry_blue_cap",(0,0,h+.23),(ew+.42,ed+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((4.5,-5.9,0))))
    a.planter("Studio_terrace_pot",(-5.83,-3.77,2*h+.18),.34,.48)


def publishing_office():
    w,d,h=13.8,12.4,3.1
    walls=rectangle(w,d,"Publisher")
    box("Publisher_foundation",(0,0,.075),(w,d,.15),"stone",.025)
    # The first floor stops behind the double-height street lobby.
    box("Rear_first_floor_plate",(0,2.7,h),(w,7.0,.18),"cream")
    for level in (2,3,4):
        box("Publisher_floor_plate",(0,0,level*h),(w,d,.18),"cream")
    front=walls[0]
    front.row(.15,2*h-.09,[(4.0,3.10,.15,5.77,"lobby"),(10.0,3.10,.66,5.77,"window")],"blue")
    front.part("Lobby_door_transom",4.0,2.76,3.00,.10,"ink",.07,-.105)
    front.part("Double_height_window_bar",10.0,2.76,3.00,.10,"ink",.07,-.105)
    for wall in walls[1:]:
        if wall is walls[2]:
            bays=[(wall.length*.30,1.17,.15,2.65,"door"),(wall.length*.70,2.2,3.75,5.60,"window")]
        else:
            bays=[(wall.length*f,1.50,2.25,5.52,"window") for f in (.27,.73)]
        wall.row(.15,2*h-.09,bays,"blue")
    for level in (2,3):
        for i,wall in enumerate(walls):
            count=3 if i==0 else 2
            bays=[(wall.length*(j+.5)/count,2.34 if i==0 else 1.53,level*h+.69,(level+1)*h-.47,"window") for j in range(count)]
            wall.row(level*h+.15,(level+1)*h-.09,bays,"blue")
            wall.part("Publisher_cream_band",wall.length/2,level*h,wall.length+.13,.25,"cream",.26,.055)
    front.part("Publishing_name_panel",w/2,6.43,5.32,.44,"teal",.14,.11,.02)
    a.text("Publishing_letters","PUBLISH",front.point(w/2,6.43,.20),.36)
    for wall in walls:
        wall.part("Publisher_base",wall.length/2,.29,wall.length,.28,"cream",.20,.02)
        for u in (.19,wall.length-.19):
            wall.part("Publisher_corner_trim",u,6.25,.31,12.10,"cream",.24,.06)
    b.cornice(w,d,4*h,True)
    box("Publisher_flat_blue_cap",(0,0,4*h+.23),(w+.42,d+.42,.26),"roof",.03)
    box("Publisher_rear_service_room",(2.9,4.1,4*h+.67),(4.2,3.4,.85),"cream",.035)
    box("Rear_service_blue_cap",(2.9,4.1,4*h+1.16),(4.44,3.64,.17),"roof",.025)


def car_showroom():
    w,d,h=19.0,8.6,4.5
    before={obj.name for obj in a.collection.objects}
    front=b.frame(w,d,1,"cream",height=h)[0]
    front.row(.15,h-.09,[(4.45,6.38,.28,3.97,"shop"),(9.5,2.10,.15,3.97,"lobby"),
                        (14.55,6.38,.28,3.97,"shop")],"cream")
    for u in (4.45,14.55):
        for du in (-1.10,1.10):
            front.part("Showroom_glass_bar",u+du,2.15,.11,3.55,"ink",.075,-.11)
    for u in (.21,w-.21):
        front.part("Showroom_corner_pier",u,2.30,.36,4.12,"cream",.29,.065)
    b.cornice(w,d,h,False)
    box("Deep_projecting_showroom_roof",(0,-.48,h+.29),(w+.94,d+1.80,.40),"cream",.035)
    box("Showroom_blue_roof_surface",(0,-.48,h+.59),(w+1.00,d+1.86,.18),"roof",.025)
    box("Showroom_roof_name_panel",(0,-5.49,h+.27),(4.0,.13,.32),"teal",.018)
    a.text("Showroom_letters","AUTO",(0,-5.57,h+.27),.28)
    move_new(before,Matrix.Translation(Vector((0,-1.7,0))))
    before={obj.name for obj in a.collection.objects}
    rw,rd,rh=19.0,3.4,3.05
    walls=rectangle(rw,rd,"Showroom_service")
    box("Rear_service_foundation",(0,0,.075),(rw,rd,.15),"stone",.025)
    for i,wall in enumerate(walls):
        if i==2:
            shutter_bays(wall)
            bays=[(4.0,1.30,.15,2.64,"door"),(14.5,3.50,.15,2.64,"loading")]
        elif i in (1,3):
            bays=[(wall.length/2,1.5,1.25,2.64,"window")]
        else:
            bays=[]
        wall.row(.15,rh-.09,bays,"blue")
    b.cornice(rw,rd,rh,False)
    box("Lower_service_blue_cap",(0,0,rh+.23),(rw+.42,rd+.42,.26),"roof",.03)
    move_new(before,Matrix.Translation(Vector((0,4.3,0))))


models=[
    ("postal_sorting_building","PostalSortingBuilding",96,(18.8,12.0,6.4),"Broad terracotta two-story postal building with closed rear loading bays, narrow high windows and a front office canopy.",postal_sorting_building),
    ("design_studio","DesignStudio",97,(15.0,11.0,9.3),"Cream and muted-lilac three-story studio with oversized top-floor windows, small terrace and offset lower entrance.",design_studio),
    ("publishing_office","PublishingOffice",98,(13.8,12.4,12.4),"Broad powder-blue four-story publishing office with double-height front lobby, paired upper glazing and rear roof service enclosure.",publishing_office),
    ("car_showroom","CarShowroom",99,(19.0,12.0,4.5),"Wide cream one-story showroom with two tall blue glazing bays, deep projecting roof slab and lower rear service wing.",car_showroom)]

extra_colliders={
    "design_studio":[((0,3.1,0),(15.0,6.2,11.0)),((-.4,7.75,-1.2),(11.8,3.1,7.8)),((4.5,1.55,5.9),(4.2,3.1,2.6))],
    "car_showroom":[((0,2.25,1.7),(19.0,4.5,8.6)),((0,1.525,-4.3),(19.0,3.05,3.4))]}

scene_dir=a.PROJECT/"scenes/buildings/batch_24"
scene_dir.mkdir(parents=True,exist_ok=True)
entries=[]
for slug,name,roster_id,size,description,author in models:
    entry=a.save_model(slug,name,description,author)
    w,d,h=size
    colliders=extra_colliders.get(slug,[((0,h/2,0),(w,h,d))])
    entry.update(roster_id=roster_id,footprint_m=list(size[:2]),body_height_m=h,scene="res://scenes/buildings/batch_24/"+slug+".tscn",
                 collision_boxes=[{"center":list(at),"size":list(dim)} for at,dim in colliders])
    entries.append(entry)
    parts=[f'[gd_scene load_steps={len(colliders)+2} format=3]\n',
           f'[ext_resource type="PackedScene" path="res://assets/models/buildings/batch_24/{slug}.glb" id="1"]\n']
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
        resource_path="res://assets/models/buildings/batch_24/"+slug+".glb"
        template=template.replace("res://assets/models/buildings/batch_01/corner_cafe.glb",resource_path)
        template=template.replace("corner_cafe.glb-ca2d60216d655181a29847542da4bc48.scn",slug+".glb-"+hashlib.md5(resource_path.encode()).hexdigest()+".scn")
        import_path.write_text('\n'.join(line for line in template.split('\n') if not line.startswith('uid=')))
    print("BATCH_24_BUILT",slug,entry['triangles'],"triangles",flush=True)
(a.ASSET/'manifest.json').write_text(json.dumps({"batch":24,"units":"meters","godot_front":"+Z","origin":"ground center","style":"Pastel French Quarter / New Orleans Creole","palette_srgb":a.PALETTE,"models":entries},indent=2)+'\n')
(a.ASSET/'README.md').write_text('# Lowcar — building batch 24\n\nPostal Sorting Building (096), Design Studio (097), Publishing Office (098), Car Showroom (099). Approved pastel French Quarter style, cream trim, recessed painted blue glazing, broad one- to four-story proportions. Publishing Office replaces the older narrow five-story roster suggestion with a broad four-story building.\n\nPlacement scenes: `scenes/buildings/batch_24/`. Meters, ground-center origins, Godot +Z front, one static visual mesh per building. Separate body boxes follow the studio terrace and offset entry, and the showroom sales floor and lower rear service wing. Loading shutters are closed. Editable Blender sources: `source/`.\n\nIncluded in the city after relaunch. Review: `scenes/review/building_batch_24.tscn`; 0 for all, 1–4 select, drag to orbit, wheel to zoom. Preview: `previews/lineup.png`. Rebuild: `tools/build_building_batch_24.py`.\n')
