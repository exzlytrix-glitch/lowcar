"""A clean, texture-free Lowcar street tile. Blender +Y exports to Godot -Z."""
from pathlib import Path
import bpy
import bmesh
import json
import hashlib

PROJECT = Path(__file__).resolve().parents[1]
ASSET = PROJECT / 'assets/models/streets/road_straight'
for folder in (ASSET / 'source', ASSET / 'previews'):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / '.gdignore').write_text('')
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

PALETTE = {'Asphalt': '30373E', 'Gutter': '414950', 'Curb': 'F0E8D8',
           'Sidewalk': 'DED8CB', 'CenterPaint': 'EDD194', 'EdgePaint': 'F4EBDD'}
materials = {}
for name, color in PALETTE.items():
    rgb = [int(color[i:i+2], 16)/255 for i in (0,2,4)]
    linear = [x/12.92 if x <= .04045 else ((x+.055)/1.055)**2.4 for x in rgb]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*linear, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*linear, 1)
    shader.inputs['Roughness'].default_value = .93
    shader.inputs['Specular IOR Level'].default_value = .18
    materials[name] = mat
root = bpy.data.objects.new('Lowcar_Road_Straight', None)
bpy.context.collection.objects.link(root)
parts = []

def box(name, location, size, material, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(materials[material])
    if bevel:
        mod = obj.modifiers.new('Single clean edge facet', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.parent = root
    parts.append(obj)
    return obj

def prism(name, section, y0, y1, material):
    verts = [(x,y0,z) for x,z in section] + [(x,y1,z) for x,z in section]
    n = len(section)
    faces = [tuple(range(n-1,-1,-1)), tuple(range(n,n*2))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    bm = bmesh.new(); bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data); bm.free()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(materials[material])
    obj.parent = root
    parts.append(obj)

# Square ends share an exact plane, so repeating tiles have no rounded end seams.
prism('Charcoal_roadbed', [(-4,-.22),(4,-.22),(4,0),(-4,0)], -10,10,'Asphalt')
for side in (-1,1):
    box('Quiet_gutter', (side*3.87,0,.0015), (.26,20,.003),'Gutter')
    box('Cream_edge_line', (side*3.57,0,.005), (.095,20,.006),'EdgePaint')
    for i in range(10):
        at = -9 + i*2
        if side > 0:
            section = [(4,0),(4.32,0),(4.32,.18),(4.09,.18),(4,.11)]
        else:
            section = [(-x,z) for x,z in [(4,0),(4.32,0),(4.32,.18),(4.09,.18),(4,.11)]]
        prism('Curb_%s_%02d' % (side,i),section,at-.991,at+.991,'Curb')
        # Tiny seams and a single edge facet, with a quiet flat walking surface.
        box('Sidewalk_slab_%s_%02d' % (side,i), (side*5.16,at,.09), (1.68,1.978,.18),'Sidewalk',.012)
for at in (-7.5,-2.5,2.5,7.5):
    box('Butter_center_dash', (0,at,.005), (.18,2.35,.006),'CenterPaint',.008)
root['description'] = 'Soft charcoal asphalt, cream curbs, broad warm sidewalk slabs, butter center dashes.'
root['tile_length_m'] = 20.0
root['road_width_m'] = 8.0
root['total_width_m'] = 12.0
root['road_top_m'] = 0.0
root['sidewalk_top_m'] = .18
bpy.ops.object.select_all(action='DESELECT')
root.select_set(True)
bpy.context.view_layer.objects.active = root
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_distance = 24
            area.spaces.active.shading.type = 'MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(ASSET/'source/road_straight.blend'))
# Merge only a copy: source retains independently editable curb stones and paint.
copies = []
for obj in parts:
    clone = obj.copy(); clone.data = obj.data.copy()
    bpy.context.collection.objects.link(clone)
    copies.append(clone)
bpy.ops.object.select_all(action='DESELECT')
for obj in copies:
    obj.select_set(True)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join()
merged = copies[0]
merged.name = 'RoadMesh'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
triangles = sum(len(p.vertices)-2 for p in merged.data.polygons)
root.select_set(True)
path = ASSET/'road_straight.glb'
bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                         export_yup=True, export_apply=True, export_extras=True,
                         export_cameras=False, export_lights=False)
manifest = {'id':'road_straight','units':'meters','long_axis':'Godot Z',
            'road_width_m':8,'tile_length_m':20,'total_width_m':12,
            'road_top_m':0,'sidewalk_top_m':.18,'runtime_meshes':1,
            'triangles':triangles,'editable_parts':len(parts),'palette_srgb':PALETTE,
            'glb':'road_straight.glb','source':'source/road_straight.blend',
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(ASSET/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('LOWCAR_ROAD_BUILT',triangles,'triangles;',len(parts),'editable parts')
