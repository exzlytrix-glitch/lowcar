"""Dress the approved cube pedestrian in a small, simplified police gear set."""
from pathlib import Path
import hashlib
import json
import bpy
import bmesh
from mathutils import Vector

PROJECT = Path(__file__).resolve().parents[1]
BASE = PROJECT/'assets/models/characters/pastel_pedestrian'
ASSET = PROJECT/'assets/models/characters/police_officer'
for folder in (ASSET, ASSET/'source', ASSET/'previews'):
    folder.mkdir(parents=True,exist_ok=True)
for folder in (ASSET/'source', ASSET/'previews'):
    (folder/'.gdignore').write_text('')
bpy.ops.wm.open_mainfile(filepath=str(BASE/'source/pastel_pedestrian.blend'))
bpy.context.preferences.filepaths.save_version = 0
root = bpy.data.objects['Lowcar_Pastel_Pedestrian']
rig = bpy.data.objects['PedestrianRig']
root.name = 'Lowcar_Police_Officer'
rig.name = 'PoliceOfficerRig'
root['description'] = 'The approved lavender cube pedestrian with a navy cap, vest, belt and simple gold badges.'
parts = [obj for obj in bpy.context.scene.objects if obj.type=='MESH']
gear=[]

def material(name,color):
    rgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=(*linear,1); mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*linear,1)
    shader.inputs['Roughness'].default_value=.9
    shader.inputs['Specular IOR Level'].default_value=.18
    return mat

navy=material('Gear — soft navy','3D5878')
gold=material('Badge — butter gold','E9CA81')

def attach(obj,bone,mat):
    obj.data.materials.append(mat)
    obj.parent=rig
    group=obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Rigid gear attachment','ARMATURE'); mod.object=rig
    parts.append(obj); gear.append(obj.name)

def block(name,at,size,bone,mat=navy,bevel=.008):
    bpy.ops.mesh.primitive_cube_add(size=1,location=at)
    obj=bpy.context.object; obj.name=name; obj.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=obj.modifiers.new('Single edge facet','BEVEL'); mod.width=bevel; mod.segments=1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    attach(obj,bone,mat)

# Ordinary cap and vest. Keep the lavender head, arms, hands, legs and feet exposed.
block('Navy_cap_crown',(0,-.008,1.701),(.482,.422,.102),'Head',bevel=.014)
block('Short_cap_peak',(0,-.243,1.661),(.45,.184,.045),'Head',bevel=.010)
block('Gold_cap_badge',(0,-.225,1.702),(.073,.018,.067),'Head',gold,.006)
block('Vest_front',(0,-.151,1.02),(.43,.060,.40),'Torso',bevel=.011)
block('Vest_back',(0,.144,1.02),(.43,.044,.40),'Torso',bevel=.010)
for side in (-1,1):
    block('Vest_shoulder_strap_'+str(side),(side*.16,0,1.236),(.066,.328,.068),'Torso',bevel=.007)
block('Simple_duty_belt',(0,0,.771),(.492,.325,.084),'Hips',bevel=.008)
block('Gold_belt_buckle',(0,-.173,.771),(.083,.025,.054),'Hips',gold,.004)
for side in (-1,1):
    block('Belt_pouch_'+str(side),(side*.17,-.181,.770),(.080,.067,.104),'Hips',bevel=.006)
block('Small_shoulder_radio',(-.115,-.196,1.123),(.073,.040,.108),'Torso',bevel=.005)
block('Radio_antenna',(-.133,-.196,1.202),(.018,.026,.063),'Torso',bevel=.003)

# A five-sided, solid badge is readable without lettering or fine embossed detail.
outline=[(-.040,.047),(.040,.047),(.040,-.008),(0,-.049),(-.040,-.008)]
vertices=[(.114+x,y,1.109+z) for y in (-.182,-.204) for x,z in outline]
faces=[tuple(range(4,-1,-1)),tuple(range(5,10))]
faces += [(i,(i+1)%5,(i+1)%5+5,i+5) for i in range(5)]
data=bpy.data.meshes.new('Plain_shield_badge'); data.from_pydata(vertices,[],faces); data.update()
bm=bmesh.new(); bm.from_mesh(data); bmesh.ops.recalc_face_normals(bm,faces=bm.faces); bm.to_mesh(data); bm.free()
badge=bpy.data.objects.new('Plain_shield_badge',data); bpy.context.collection.objects.link(badge)
attach(badge,'Torso',gold)

bpy.context.view_layer.update()
points=[obj.matrix_world@Vector(corner) for obj in parts for corner in obj.bound_box]
bounds={'min':[round(min(p[i] for p in points),5) for i in range(3)],
        'max':[round(max(p[i] for p in points),5) for i in range(3)]}
bpy.ops.object.select_all(action='DESELECT')
root.select_set(True); bpy.context.view_layer.objects.active=root
bpy.ops.wm.save_as_mainfile(filepath=str(ASSET/'source/police_officer.blend'))

copies=[]
for obj in parts:
    clone=obj.copy(); clone.data=obj.data.copy(); bpy.context.collection.objects.link(clone); copies.append(clone)
bpy.ops.object.select_all(action='DESELECT')
for obj in copies:
    obj.select_set(True)
bpy.context.view_layer.objects.active=copies[0]; bpy.ops.object.join()
model=copies[0]; model.name='PoliceOfficerMesh'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
model.data.calc_loop_triangles()
root.select_set(True); rig.select_set(True)
glb=ASSET/'police_officer.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
    export_yup=True,export_apply=False,export_extras=True,export_animations=False,
    export_cameras=False,export_lights=False)
base_manifest=json.loads((BASE/'manifest.json').read_text())
(ASSET/'manifest.json').write_text(json.dumps({
    'id':'police_officer','name':'Cube police officer','units':'meters','front':'Godot +Z','origin':'ground center',
    'base_model':'pastel_pedestrian','base_glb_sha256':base_manifest['sha256'],
    'height_m':bounds['max'][2], 'palette_srgb':{'PastelLavender':'B7A5DB','SoftNavy':'3D5878','ButterGold':'E9CA81'},
    'materials':3,'textures':0,'runtime_meshes':1,'triangles':len(model.data.loop_triangles),
    'editable_parts':len(parts),'gear_parts':gear,'bones':[bone.name for bone in rig.data.bones],
    'glb':glb.name,'source':'source/police_officer.blend','blender_bounds_m':bounds,
    'sha256':hashlib.sha256(glb.read_bytes()).hexdigest(),
},indent=2)+'\n')
print('LOWCAR_POLICE_OFFICER_BUILT',len(model.data.loop_triangles),'triangles;',len(gear),'simple gear pieces; same 11-bone pedestrian')
