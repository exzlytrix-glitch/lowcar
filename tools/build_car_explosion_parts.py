"""Split the approved red car into recognizable, editable explosion pieces.

The intact hero model is preserved. Run with Blender --background --python.
"""
from pathlib import Path
from collections import defaultdict
import json
import hashlib
import bpy
from mathutils import Vector

PROJECT = Path(__file__).resolve().parents[1]
ASSET = PROJECT / "assets/models/vehicles/red_muscle_car"
bpy.ops.wm.open_mainfile(filepath=str(ASSET / "source/red_muscle_car.blend"))
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
original_collection = bpy.data.collections["LOWCAR — model"]
originals = list(original_collection.objects)
collection = bpy.data.collections.new("EXPLOSION — editable pieces")
bpy.context.scene.collection.children.link(collection)
groups = defaultdict(list)


def region(center):
    x, y, z = center
    if y > .60:
        return "Hood" if z > 1.025 else "Nose"
    if y < -1.48:
        return "RearBody"
    if z > 1.13:
        return "Cabin"
    if abs(x) > .73:
        return "LeftDoor" if x < 0 else "RightDoor"
    return "Underbody"


def copy_piece(obj, name):
    clone = obj.copy()
    clone.data = obj.data.copy()
    clone.animation_data_clear()
    collection.objects.link(clone)
    world = obj.matrix_world.copy()
    clone.parent = None
    clone.matrix_world = world
    groups[name].append(clone)


for obj in originals:
    if obj.type != "MESH":
        continue
    if obj.name == "Body_shell_sculpted":
        # Separate the continuous shell by polygon region; no fake generic debris cubes.
        faces = defaultdict(list)
        for face in obj.data.polygons:
            center = sum((obj.matrix_world @ obj.data.vertices[i].co for i in face.vertices), Vector()) / len(face.vertices)
            faces[region(center)].append(face)
        for label, polygons in faces.items():
            vertices, indices, new_faces = [], {}, []
            for face in polygons:
                corners = []
                for i in face.vertices:
                    if i not in indices:
                        indices[i] = len(vertices)
                        vertices.append(obj.matrix_world @ obj.data.vertices[i].co)
                    corners.append(indices[i])
                new_faces.append(corners)
            data = bpy.data.meshes.new(label + "_shell")
            data.from_pydata(vertices, [], new_faces)
            for mat in obj.data.materials:
                data.materials.append(mat)
            for face, old in zip(data.polygons, polygons):
                face.material_index = old.material_index
            data.update()
            clone = bpy.data.objects.new(label + "_shell", data)
            collection.objects.link(clone)
            groups[label].append(clone)
    else:
        parent = obj.parent
        if parent and parent.name.endswith("Spin"):
            label = parent.name.removesuffix("Spin")
        elif parent and parent.name == "TrunkHinge":
            label = "Trunk"
        elif "Cabin" in obj.name or "window" in obj.name.lower() or "Windshield" in obj.name:
            label = "Cabin"
        elif "power_cowl" in obj.name or "Scoop" in obj.name or "Hood_" in obj.name:
            label = "Hood"
        else:
            center = sum((obj.matrix_world @ v.co for v in obj.data.vertices), Vector()) / len(obj.data.vertices)
            label = region(center)
        copy_piece(obj, label)

root = bpy.data.objects.new("CarExplosionParts", None)
collection.objects.link(root)
for label, objects in groups.items():
    points = [obj.matrix_world @ v.co for obj in objects for v in obj.data.vertices]
    center = sum(points, Vector()) / len(points)
    pivot = bpy.data.objects.new(label, None)
    collection.objects.link(pivot)
    pivot.parent = root
    pivot.location = center
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        world = obj.matrix_world.copy()
        obj.parent = pivot
        obj.matrix_world = world
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    mesh = bpy.context.object
    world = mesh.matrix_world.copy()
    # Mesh vertices become pivot-relative, with the local object transform at identity.
    mesh.data.transform(pivot.matrix_world.inverted() @ world)
    mesh.matrix_basis.identity()
    mesh.name = label + "Mesh"
    for face in mesh.data.polygons:
        face.use_smooth = False

bpy.ops.object.select_all(action="DESELECT")
for obj in collection.objects:
    obj.select_set(True)
glb = ASSET / "explosion_parts.glb"
bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True,
                          export_yup=True, export_apply=True, export_extras=True,
                          export_animations=False, export_cameras=False, export_lights=False)
for obj in originals:
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(ASSET / "source/explosion_parts.blend"))
manifest = {"pieces": list(groups), "piece_count": len(groups), "source": "source/explosion_parts.blend",
            "glb": "explosion_parts.glb", "forward": "Godot -Z", "units": "meters",
            "sha256": hashlib.sha256(glb.read_bytes()).hexdigest()}
(ASSET / "explosion_parts_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("LOWCAR_EXPLOSION_PARTS_BUILT", json.dumps(manifest))
