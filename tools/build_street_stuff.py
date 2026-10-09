"""Lowcar sidewalk pieces first, followed by common street furniture. Texture-free, meter scale."""
from pathlib import Path
from math import sin, cos, pi
import json
import hashlib
import bpy
import bmesh
from mathutils import Vector

PROJECT = Path(__file__).resolve().parents[1]
ASSET = PROJECT / 'assets/models/streets/street_stuff'
SCENES = PROJECT / 'scenes/streets/street_stuff'
for folder in (ASSET, ASSET/'source', ASSET/'previews', SCENES):
    folder.mkdir(parents=True, exist_ok=True)
for folder in (ASSET/'source', ASSET/'previews'):
    (folder/'.gdignore').write_text('')
bpy.context.preferences.filepaths.save_version = 0
PALETTE = {'Cream':'F0E8D8','Stone':'DED8CB','Seam':'C8C2B7','Sage':'527A73',
           'Teal':'65978C','DarkTeal':'365C57','Wood':'C59270','WoodLight':'D5A17B',
           'Coral':'DC8469','Ink':'293D43','Glass':'FFF0C5','Brass':'CEAE71'}
entries = []
parts = []
materials = {}
root = None

def reset(name):
    global root,parts,materials
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    parts = []; materials = {}
    for label,color in PALETTE.items():
        rgb = [int(color[i:i+2],16)/255 for i in (0,2,4)]
        linear = [x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
        mat = bpy.data.materials.new(label)
        mat.diffuse_color=(*linear,1); mat.use_nodes=True
        node=mat.node_tree.nodes.get('Principled BSDF')
        node.inputs['Base Color'].default_value=(*linear,1)
        node.inputs['Roughness'].default_value=.86
        node.inputs['Specular IOR Level'].default_value=.22
        materials[label]=mat
    root=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(root)

def box(name,at,size,color,facet=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=at)
    obj=bpy.context.object; obj.name=name; obj.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(materials[color])
    if facet:
        mod=obj.modifiers.new('Broad edge facet','BEVEL'); mod.width=facet; mod.segments=1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.parent=root; parts.append(obj)
    return obj

def mesh(name,verts,faces,color):
    data=bpy.data.meshes.new(name); data.from_pydata(verts,[],faces); data.update()
    bm=bmesh.new(); bm.from_mesh(data); bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(data); bm.free()
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj)
    data.materials.append(materials[color]); obj.parent=root; parts.append(obj)
    return obj

def prism(name,outline,bottom,top,color):
    n=len(outline); verts=[(x,y,bottom) for x,y in outline]+[(x,y,top) for x,y in outline]
    return mesh(name,verts,[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],color)

def tube(name,at,radius,depth,color,top_radius=None,sides=10):
    bpy.ops.mesh.primitive_cone_add(vertices=sides,radius1=radius,radius2=radius if top_radius is None else top_radius,depth=depth,location=at)
    obj=bpy.context.object; obj.name=name; obj.data.materials.append(materials[color])
    obj.parent=root; parts.append(obj); return obj

def rod(name,a,b,width,color):
    direction=Vector(b)-Vector(a)
    obj=tube(name,(Vector(a)+Vector(b))/2,width,direction.length,color,sides=8)
    obj.rotation_euler=direction.to_track_quat('Z','Y').to_euler(); return obj

def ring(name,z,outer,inner,height,color,sides=12):
    verts=[]
    for radius,zz in [(outer,z-height/2),(outer,z+height/2),(inner,z-height/2),(inner,z+height/2)]:
        verts += [(cos(i*2*pi/sides)*radius,sin(i*2*pi/sides)*radius,zz) for i in range(sides)]
    faces=[]
    for i in range(sides):
        j=(i+1)%sides
        faces += [(i,j,j+sides,i+sides),(i+sides,j+sides,j+3*sides,i+3*sides),
                  (i+2*sides,i+3*sides,j+3*sides,j+2*sides),(i,j,j+2*sides,i+2*sides)]
    return mesh(name,verts,faces,color)

def curb(name,x0,x1,y=-1):
    # Front is Blender -Y / Godot +Z. Same 18 cm height and cream finish as the approved road.
    section=[(y,0),(y+.32,0),(y+.32,.18),(y+.09,.18),(y,.11)]
    n=len(section); verts=[(x0,yy,z) for yy,z in section]+[(x1,yy,z) for yy,z in section]
    mesh(name,verts,[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],'Cream')

def sidewalk_straight():
    box('Continuous_paving_subbase',(0,.16,.08),(4,1.68,.16),'Seam')
    box('Continuous_curb_subbase',(0,-.84,.04),(4,.32,.08),'Cream')
    for i in range(2):
        box('Broad_paving_slab',(-1+i*2,.16,.09),(1.982,1.68,.18),'Stone',.009)
        curb('Cream_curb_stone',-1.992+i*2,-.008+i*2)

def sidewalk_corner():
    outer=[(-2,2),(2,2),(2,-1.45),(1.958,-1.66),(1.839,-1.839),(1.66,-1.958),(1.45,-2),(-2,-2)]
    inner=[(-2,2),(1.68,2),(1.68,-1.45),(1.662,-1.538),(1.613,-1.613),(1.538,-1.662),(1.45,-1.68),(-2,-1.68)]
    prism('Faceted_corner_paving',inner,0,.18,'Stone')
    for i in range(1,7):
        a,b=outer[i],outer[i+1]; c,d=inner[i+1],inner[i]
        verts=[(*a,0),(*b,0),(*c,0),(*d,0),(*a,.11),(*b,.11),(*c,.18),(*d,.18)]
        mesh('Cream_corner_curb_%d'%i,verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'Cream')
    box('Quiet_paver_joint_X',(-.16,.15,.181),(3.68,.018,.0015),'Seam')
    box('Quiet_paver_joint_Y',(0,.15,.181),(.018,3.68,.0015),'Seam')

def sidewalk_ramp():
    box('Rear_paving', (0,.35,.09),(3,1.30,.18),'Stone')
    for side in (-1,1):
        box('Side_paving', (side*1.105,-.65,.09),(.79,.70,.18),'Stone')
        curb('Cream_curb_end',side*1.50 if side<0 else .70, -.70 if side<0 else 1.50)
    verts=[(-.70,-1,0),(.70,-1,0),(.70,-.30,0),(-.70,-.30,0),(-.70,-1,.004),(.70,-1,.004),(.70,-.30,.18),(-.70,-.30,.18)]
    mesh('Gentle_curb_ramp',verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'Stone')
    # A simple butter-colored tactile pad with deliberately oversized bumps.
    pad=box('Butter_tactile_pad',(0,-.64,.100),(1.18,.30,.012),'Brass',.008)
    pad.rotation_euler.x=.246
    for x in (-.40,-.20,0,.20,.40):
        for y in (-.73,-.58):
            z=.004+(y+1)/.70*.176+.014
            tube('Broad_tactile_dot',(x,y,z),.027,.014,'Cream',sides=8)

def streetlamp():
    tube('Broad_sage_foot',(0,0,.06),.24,.12,'Sage',.22)
    tube('Cream_base_collar',(0,0,.18),.17,.12,'Cream',.15)
    tube('Flared_pole_base',(0,0,.40),.14,.32,'Sage',.095)
    tube('Faceted_sage_pole',(0,0,2.00),.083,3.00,'Sage',.065)
    for height in (.62,3.35):
        tube('Cream_pole_band',(0,0,height),.105,.10,'Cream')
    tube('Lantern_neck',(0,0,3.55),.075,.20,'Sage')
    box('Cream_lantern_sill',(0,0,3.68),(.43,.43,.10),'Cream',.025)
    # Warm painted glazing and four chunky frame posts; no glow bloom or filigree noise.
    box('Warm_lantern_glass',(0,0,3.94),(.31,.31,.43),'Glass',.025)
    for x in (-.19,.19):
        for y in (-.19,.19):
            box('Sage_lantern_frame',(x,y,3.94),(.048,.048,.46),'Sage',.007)
    box('Cream_lantern_cornice',(0,0,4.21),(.49,.49,.10),'Cream',.023)
    prism('Sage_lantern_roof',[(-.28,-.28),(.28,-.28),(.28,.28),(-.28,.28)],4.26,4.29,'Sage')
    mesh('Four_roof_facets',[(-.28,-.28,4.29),(.28,-.28,4.29),(.28,.28,4.29),(-.28,.28,4.29),(0,0,4.43)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],'Sage')
    tube('Short_lantern_finial',(0,0,4.46),.045,.08,'Cream',.025,sides=8)

def trashcan():
    tube('Stable_bin_foot',(0,0,.065),.30,.13,'DarkTeal',.30,sides=12)
    ring('Hollow_teal_body',.50,.305,.264,.79,'Teal')
    tube('Dark_recessed_bin_bottom',(0,0,.52),.263,.035,'Ink',sides=12)
    ring('Chunky_cream_lip',.925,.338,.264,.09,'Cream')
    for i in range(12):
        angle=i*2*pi/12
        rod('Broad_vertical_bin_rib',(cos(angle)*.306,sin(angle)*.306,.19),(cos(angle)*.306,sin(angle)*.306,.86),.017,'Sage')
    for side in (-1,1):
        box('Bin_side_handle',(side*.336,0,.78),(.10,.21,.065),'DarkTeal',.022)
    box('Cream_bin_badge',(0,-.314,.58),(.19,.028,.19),'Cream',.022)
    box('Sage_badge_inset',(0,-.331,.58),(.105,.012,.105),'Sage',.012)

def bench():
    for i in range(3):
        box('Peach_seat_slat',(0,-.22+i*.20,.49),(2.06,.17,.085),'WoodLight' if i==1 else 'Wood',.017)
        obj=box('Peach_back_slat',(0,.30,.70+i*.115),(2.06,.075,.095),'WoodLight' if i==1 else 'Wood',.014)
        obj.rotation_euler.x=-.08
    for side in (-1,1):
        x=side*.82
        for y in (-.22,.25):
            box('Cream_bench_foot',(x,y,.035),(.21,.22,.07),'Cream',.018)
            rod('Cream_bench_leg',(x,y,.065),(x,y*.85,.45),.045,'Cream')
        rod('Cream_seat_frame',(x,-.34,.435),(x,.34,.435),.045,'Cream')
        rod('Cream_back_support',(x,.27,.43),(x,.34,1.02),.041,'Cream')
        # One simple polygonal arm loop carries the French Quarter ironwork rhythm.
        points=[(x,-.30,.47),(x,-.30,.65),(x,-.23,.70),(x,.18,.70),(x,.27,.64),(x,.27,.49)]
        for a,b in zip(points,points[1:]):
            rod('Cream_arm_loop',a,b,.035,'Cream')
    box('Lower_cream_crossbar',(0,.12,.22),(1.74,.065,.065),'Cream',.012)

def hydrant():
    tube('Cream_hydrant_foot',(0,0,.065),.245,.13,'Cream',sides=10)
    tube('Coral_hydrant_body',(0,0,.39),.175,.55,'Coral',.16,sides=10)
    tube('Cream_top_collar',(0,0,.685),.195,.07,'Cream',sides=10)
    tube('Faceted_coral_cap',(0,0,.775),.195,.13,'Coral',.095,sides=10)
    tube('Brass_top_nut',(0,0,.855),.055,.055,'Brass',sides=6)
    for side in (-1,1):
        rod('Coral_side_outlet',(side*.12,0,.49),(side*.31,0,.49),.10,'Coral')
        rod('Cream_side_cap',(side*.30,0,.49),(side*.36,0,.49),.112,'Cream')
        rod('Brass_side_nut',(side*.36,0,.49),(side*.385,0,.49),.037,'Brass')
    rod('Cream_front_outlet',(0,-.13,.43),(0,-.255,.43),.105,'Cream')
    rod('Brass_front_nut',(0,-.255,.43),(0,-.282,.43),.043,'Brass')

MODELS=[('sidewalk_straight','Straight sidewalk',sidewalk_straight,None),
        ('sidewalk_corner','Faceted sidewalk corner',sidewalk_corner,None),
        ('sidewalk_ramp','Curb ramp',sidewalk_ramp,None),
        ('streetlamp','Cream and sage lantern pole',streetlamp,('cylinder',.24,4.50)),
        ('trashcan','Open teal trash can',trashcan,('cylinder',.34,.97)),
        ('bench','Peach slat bench',bench,('box',(2.10,1.062,.74))),
        ('hydrant','Coral fire hydrant',hydrant,('box',(.78,.883,.46)))]

for slug,title,build,collider in MODELS:
    reset('Lowcar_'+slug); build(); root['description']=title
    bpy.ops.object.select_all(action='DESELECT'); root.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.wm.save_as_mainfile(filepath=str(ASSET/'source'/f'{slug}.blend'))
    copies=[]
    for obj in parts:
        clone=obj.copy(); clone.data=obj.data.copy(); bpy.context.collection.objects.link(clone); copies.append(clone)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in copies: obj.select_set(True)
    bpy.context.view_layer.objects.active=copies[0]; bpy.ops.object.join()
    merged=copies[0]; merged.name='ModelMesh'
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    merged.data.calc_loop_triangles()
    vertices=[merged.matrix_world@v.co for v in merged.data.vertices]
    bounds={'min':[round(min(v[i] for v in vertices),5) for i in range(3)],'max':[round(max(v[i] for v in vertices),5) for i in range(3)]}
    root.select_set(True)
    path=ASSET/f'{slug}.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_extras=True,export_cameras=False,export_lights=False)
    # Explicit Godot placement scenes keep the finished visual models reusable.
    shape=''; transform=''
    if collider is None:
        coords=[]
        for tri in merged.data.loop_triangles:
            for index in tri.vertices:
                v=vertices[index]; coords.extend((v.x,v.z,-v.y))
        shape='[sub_resource type="ConcavePolygonShape3D" id="Collision"]\nbackface_collision = true\ndata = PackedVector3Array('+', '.join(f'{v:.5f}' for v in coords)+')\n'
    elif collider[0]=='cylinder':
        radius,height=collider[1:]
        shape=f'[sub_resource type="CylinderShape3D" id="Collision"]\nradius = {radius}\nheight = {height}\n'
        transform=f'position = Vector3(0, {height/2}, 0)\n'
    else:
        width,height,depth=collider[1]
        shape=f'[sub_resource type="BoxShape3D" id="Collision"]\nsize = Vector3({width}, {height}, {depth})\n'
        transform=f'position = Vector3(0, {height/2}, 0)\n'
    scene=f'[gd_scene load_steps=3 format=3]\n\n[ext_resource type="PackedScene" path="res://assets/models/streets/street_stuff/{slug}.glb" id="1"]\n\n'+shape+f'\n[node name="{slug}" type="StaticBody3D"]\ncollision_layer = {1 if collider is None else 4}\ncollision_mask = 0\n\n[node name="Model" parent="." instance=ExtResource("1")]\n\n[node name="Collision" type="CollisionShape3D" parent="."]\n'+transform+'shape = SubResource("Collision")\n'
    (SCENES/f'{slug}.tscn').write_text(scene)
    entry={'id':slug,'name':title,'glb':path.name,'source':f'source/{slug}.blend','placement_scene':f'scenes/streets/street_stuff/{slug}.tscn',
           'triangles':len(merged.data.loop_triangles),'editable_parts':len(parts),'runtime_meshes':1,'blender_bounds_m':bounds,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    entries.append(entry)
    print('LOWCAR_STREET_MODEL_BUILT',slug,entry['triangles'],'triangles')
(ASSET/'manifest.json').write_text(json.dumps({'units':'meters','front':'Godot +Z','origin':'ground center','sidewalk_height_m':.18,'palette_srgb':PALETTE,'models':entries},indent=2)+'\n')
print('LOWCAR_STREET_STUFF_BUILT',len(entries),'models')
