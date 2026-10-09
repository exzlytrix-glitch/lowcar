"""Build one monochrome cube pedestrian, with rigid limb weights for future animation."""
from pathlib import Path
from math import atan2
import hashlib
import json
import bpy
from mathutils import Vector

PROJECT = Path(__file__).resolve().parents[1]
ASSET = PROJECT / 'assets/models/characters/pastel_pedestrian'
for folder in (ASSET, ASSET/'source', ASSET/'previews'):
    folder.mkdir(parents=True, exist_ok=True)
for folder in (ASSET/'source', ASSET/'previews'):
    (folder/'.gdignore').write_text('')
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

color = 'B7A5DB'
rgb = [int(color[i:i+2],16)/255 for i in (0,2,4)]
linear = [x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb]
material = bpy.data.materials.new('Pastel lavender — single color')
material.diffuse_color = (*linear,1)
material.use_nodes = True
shader = material.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = (*linear,1)
shader.inputs['Roughness'].default_value = .9
shader.inputs['Specular IOR Level'].default_value = .18

root = bpy.data.objects.new('Lowcar_Pastel_Pedestrian',None)
bpy.context.collection.objects.link(root)
root['description'] = 'Friendly cube humanoid, one pastel lavender material, blank cube face.'
root['front'] = 'Blender -Y / Godot +Z'

rig_data = bpy.data.armatures.new('CubeHumanoid')
rig = bpy.data.objects.new('PedestrianRig',rig_data)
bpy.context.collection.objects.link(rig)
rig.parent = root
rig.show_in_front = True
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')

bone_specs = [
    ('Hips',None,(0,0,.62),(0,0,.76)),
    ('Torso','Hips',(0,0,.76),(0,0,1.24)),
    ('Head','Torso',(0,0,1.24),(0,0,1.66)),
]
for side,sign in [('L',1),('R',-1)]:
    bone_specs += [
        ('Arm_'+side,'Torso',(sign*.30,0,1.19),(sign*.37,0,.72)),
        ('Hand_'+side,'Arm_'+side,(sign*.37,0,.72),(sign*.39,0,.57)),
        ('Leg_'+side,'Hips',(sign*.125,0,.65),(sign*.125,0,.125)),
        ('Foot_'+side,'Leg_'+side,(sign*.125,0,.125),(sign*.125,-.16,.065)),
    ]
for name,parent,head,tail in bone_specs:
    bone = rig_data.edit_bones.new(name)
    bone.head = head; bone.tail = tail
    if parent:
        bone.parent = rig_data.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
rig.select_set(False)

parts = []
def block(name,at,size,bone,bevel=.012,angle=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=at)
    obj=bpy.context.object; obj.name=name; obj.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(material)
    mod=obj.modifiers.new('One soft edge facet','BEVEL')
    mod.width=bevel; mod.segments=1
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.rotation_euler.y=angle
    obj.parent=rig
    group=obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    skin=obj.modifiers.new('Rigid block limb','ARMATURE'); skin.object=rig
    parts.append(obj)

block('Cube_head',(0,-.008,1.475),(.45,.39,.41),'Head',.018)
block('Little_neck',(0,0,1.248),(.16,.17,.065),'Head',.008)
block('Broad_torso',(0,0,1.008),(.46,.27,.49),'Torso',.017)
block('Compact_hips',(0,0,.694),(.36,.245,.17),'Hips',.012)
for side,sign in [('L',1),('R',-1)]:
    block('Relaxed_arm_'+side,(sign*.335,0,.955),(.165,.19,.49),'Arm_'+side,.011,-sign*atan2(.07,.47))
    block('Block_hand_'+side,(sign*.386,-.006,.646),(.18,.205,.165),'Hand_'+side,.014)
    block('Block_leg_'+side,(sign*.125,0,.390),(.17,.215,.53),'Leg_'+side,.010)
    block('Block_foot_'+side,(sign*.125,-.065,.0625),(.20,.32,.125),'Foot_'+side,.012)

bpy.context.view_layer.update()
points = [obj.matrix_world @ Vector(corner) for obj in parts for corner in obj.bound_box]
bounds = {'min':[round(min(p[i] for p in points),5) for i in range(3)],
          'max':[round(max(p[i] for p in points),5) for i in range(3)]}
bpy.ops.object.select_all(action='DESELECT')
root.select_set(True); bpy.context.view_layer.objects.active=root
bpy.ops.wm.save_as_mainfile(filepath=str(ASSET/'source/pastel_pedestrian.blend'))

# Keep editable blocks in the source; export one skinned mesh and one material.
copies=[]
for obj in parts:
    clone=obj.copy(); clone.data=obj.data.copy()
    bpy.context.collection.objects.link(clone)
    copies.append(clone)
bpy.ops.object.select_all(action='DESELECT')
for obj in copies:
    obj.select_set(True)
bpy.context.view_layer.objects.active=copies[0]
bpy.ops.object.join()
model=copies[0]; model.name='PedestrianMesh'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
model.data.calc_loop_triangles()
root.select_set(True); rig.select_set(True)
glb = ASSET/'pastel_pedestrian.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
    export_yup=True,export_apply=False,export_extras=True,export_animations=False,
    export_cameras=False,export_lights=False)
(ASSET/'manifest.json').write_text(json.dumps({
    'id':'pastel_pedestrian','name':'Pastel cube pedestrian','units':'meters',
    'front':'Godot +Z','origin':'ground center','height_m':bounds['max'][2],
    'palette_srgb':{'PastelLavender':color},'materials':1,'textures':0,
    'triangles':len(model.data.loop_triangles),'editable_parts':len(parts),
    'runtime_meshes':1,'bones':[s[0] for s in bone_specs],
    'glb':glb.name,'source':'source/pastel_pedestrian.blend',
    'blender_bounds_m':bounds,'sha256':hashlib.sha256(glb.read_bytes()).hexdigest(),
},indent=2)+'\n')
print('LOWCAR_PEDESTRIAN_BUILT',len(parts),'editable blocks;',len(model.data.loop_triangles),'triangles;',len(bone_specs),'bones; one material')
