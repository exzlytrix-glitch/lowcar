"""Build Lowcar's editable muscle car, GLB, and studio previews in Blender.

Run with Blender --background --python tools/build_red_muscle_car.py.
Blender axes: X = width, +Y = forward, Z = up. glTF exports Godot -Z forward.
"""
from pathlib import Path
from math import cos, sin, pi
import json
import hashlib
import bpy
import bmesh
from mathutils import Vector

bpy.context.preferences.filepaths.save_version = 0

PROJECT = Path(__file__).resolve().parents[1]
ASSET = PROJECT / "assets/models/vehicles/red_muscle_car"
SOURCE = ASSET / "source"
PREVIEWS = ASSET / "previews"
for folder in (ASSET, SOURCE, PREVIEWS):
    folder.mkdir(parents=True, exist_ok=True)
for folder in (SOURCE, PREVIEWS):
    (folder / ".gdignore").write_text("")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for collection in list(bpy.data.collections):
    if collection.name != "Collection":
        bpy.data.collections.remove(collection)
model_collection = bpy.data.collections["Collection"]
model_collection.name = "LOWCAR — model"
studio_collection = bpy.data.collections.new("STUDIO — excluded from GLB")
bpy.context.scene.collection.children.link(studio_collection)


def srgb(channel):
    return channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4


def material(name, color, roughness=.52, metallic=0.0):
    mat = bpy.data.materials.new(name)
    rgb = tuple(srgb(int(color[i:i + 2], 16) / 255) for i in (0, 2, 4))
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*rgb, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Specular IOR Level"].default_value = .28
    return mat


paint = material("Paint — vermilion red", "E9171C", .48, .03)
paint_dark = material("Paint — lower red facets", "BE101A", .55, .03)
paint_light = material("Paint — shoulder facets", "F52929", .5, .03)
paint_seam = material("Panel seams — red shadow", "720E1A", .8)
dark = material("Trim — midnight charcoal", "18212B", .64)
rubber = material("Tires — graphite", "20242D", .92)
tire_edge = material("Tire sidewall facets", "2B313B", .87)
metal = material("Metal — soft silver", "AFBCC6", .38, .48)
metal_dark = material("Metal — dark inset", "596574", .5, .4)
glass = material("Glass — ink blue", "183345", .3, .1)
glass_reflection = material("Glass — painted sky reflection", "527F93", .4)
headlight = material("Headlights — warm ivory", "FFF0C1", .4)
tail = material("Taillights — bright scarlet", "FF3645", .38)
tail_dark = material("Taillights — deep red edge", "AE0E23", .5)
plate = material("Plate — warm cream", "EAE2CD", .7)


def move_collection(obj, target=model_collection):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    target.objects.link(obj)


def empty(name, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    model_collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    obj.empty_display_size = .2
    return obj


root = empty("Lowcar_Red_Muscle")
chassis = empty("Chassis", root)
wheels = empty("Wheels", root)
attachment_socket = empty("GroundPunchSocket", root, (0, -.2, .3))
trunk_hinge = empty("TrunkHinge", chassis, (0, -1.50, 1.0813))


def parent_keep_world(obj, parent):
    bpy.context.view_layer.update()
    transform = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = transform
    return obj


def mesh(name, verts, faces, mat=paint, parent=chassis):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    model_collection.objects.link(obj)
    data.materials.append(mat)
    obj.parent = parent
    return obj


def apply_modifier(obj, modifier):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)


def bevel(obj, amount=.025, segments=1):
    mod = obj.modifiers.new("Deliberate edge facets", "BEVEL")
    mod.width = amount
    mod.segments = segments
    apply_modifier(obj, mod)
    return obj


def box(name, location, size, mat=paint, parent=chassis, chamfer=.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    move_collection(obj)
    obj.data.materials.append(mat)
    obj.parent = parent
    if chamfer:
        bevel(obj, chamfer)
    return obj


def cylinder(name, location, radius, depth, mat, axis="X", sides=12, parent=chassis):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    if axis == "X":
        obj.rotation_euler.y = pi / 2
    elif axis == "Y":
        obj.rotation_euler.x = pi / 2
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    move_collection(obj)
    obj.data.materials.append(mat)
    obj.parent = parent
    return obj


def line(name, a, b, radius, mat, parent=chassis):
    direction = Vector(b) - Vector(a)
    obj = cylinder(name, (Vector(a) + Vector(b)) / 2, radius, direction.length,
                   mat, axis="Z", sides=4, parent=parent)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


# A shaped continuous shell, with actual polygonal wheel openings.
sections = [
    (2.39, .99, 1.03), (2.05, 1.04, 1.09), (1.44, 1.07, 1.11),
    (.60, 1.065, 1.045), (-.35, 1.075, 1.035), (-1.43, 1.09, 1.085),
    (-2.05, 1.06, 1.055), (-2.39, 1.025, .985),
]
verts = []
for y, width, top in sections:
    profile = [(-width * .82, top), (-width * .955, top - .055),
               (-width, top - .17), (-width, .43), (-width * .92, .355),
               (width * .92, .355), (width, .43), (width, top - .17),
               (width * .955, top - .055), (width * .82, top)]
    verts.extend((x, y, z) for x, z in profile)
faces = [tuple(range(9, -1, -1))]
for i in range(len(sections) - 1):
    for j in range(10):
        faces.append((i * 10 + j, i * 10 + (j + 1) % 10,
                      (i + 1) * 10 + (j + 1) % 10, (i + 1) * 10 + j))
faces.append(tuple(range((len(sections) - 1) * 10, len(sections) * 10)))
body = mesh("Body_shell_sculpted", verts, faces)


def body_section(y):
    for i in range(len(sections) - 1):
        high, low = sections[i], sections[i + 1]
        if low[0] <= y <= high[0]:
            t = (y - low[0]) / (high[0] - low[0])
            return low[1] + (high[1] - low[1]) * t, low[2] + (high[2] - low[2]) * t
    return sections[0][1], sections[0][2]


def body_surface_x(y, z):
    width, top = body_section(y)
    if z <= top - .17:
        return width
    if z <= top - .055:
        return width * (1.0 - .045 * ((z - top + .17) / .115))
    return width * (.955 - .135 * min(1.0, (z - top + .055) / .055))


for axle_y, radius, height in ((1.44, .505, .445), (-1.43, .545, .48)):
    cutter = cylinder("temporary_wheelwell", (0, axle_y, height), radius, 3.3,
                      paint_dark, sides=16)
    mod = body.modifiers.new("Open wheel arch", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    apply_modifier(body, mod)
    bpy.data.objects.remove(cutter, do_unlink=True)
# The rear deck has an actual opening rather than a second lid over a solid roof.
cutter = box("temporary_trunk_opening", (0, -1.91, 1.105), (1.66, .86, .39))
mod = body.modifiers.new("Open trunk cavity", "BOOLEAN")
mod.operation = "DIFFERENCE"
mod.solver = "EXACT"
mod.object = cutter
apply_modifier(body, mod)
bpy.data.objects.remove(cutter, do_unlink=True)
body.data.materials.append(paint_dark)
body.data.materials.append(paint_light)
for poly in body.data.polygons:
    if poly.normal.z < -.25 or poly.center.z < .52:
        poly.material_index = 1
    elif .1 < poly.normal.z < .9:
        poly.material_index = 2
box("Underbody", (0, 0, .37), (1.43, 3.83, .16), dark, chamfer=.035)
box("Trunk_cavity_floor", (0, -1.91, .921), (1.64, .84, .018), dark)
for x in (-.82, .82):
    box("Trunk_cavity_side_" + str(x), (x, -1.91, .968), (.018, .84, .09), dark)
for y in (-1.485, -2.335):
    box("Trunk_cavity_end_" + str(y), (0, y, .964), (1.64, .016, .082), dark)

# The full panel, its underside, and its lip travel together around a front hinge.
lid_verts = []
for thickness in (-.033, .010):
    for y in (-1.50, -2.05, -2.34):
        _, top = body_section(y)
        lid_verts.extend(((-.855, y, top + thickness), (.855, y, top + thickness)))
lid_faces = [(0, 1, 3, 2), (2, 3, 5, 4), (6, 8, 9, 7), (8, 10, 11, 9),
             (0, 6, 7, 1), (4, 5, 11, 10), (0, 2, 8, 6), (2, 4, 10, 8),
             (1, 7, 9, 3), (3, 9, 11, 5)]
lid = mesh("Trunk_lid", lid_verts, lid_faces)
parent_keep_world(lid, trunk_hinge)
underside = box("Trunk_lid_underside", (0, -1.92, 1.017), (1.56, .73, .022), dark, chamfer=.008)
parent_keep_world(underside, trunk_hinge)

# Each fender lip is a short faceted band, not a floating full circle.
for side in (-1, 1):
    for label, axle_y, radius, height, width in (
        ("Front", 1.44, .505, .445, 1.075),
        ("Rear", -1.43, .545, .48, 1.105),
    ):
        ring_verts = []
        for depth in (-.014, .024):
            for r in (radius, radius + .045):
                for i in range(9):
                    theta = i * pi / 8
                    y = axle_y + cos(theta) * r
                    z = height + sin(theta) * r
                    x = side * (body_surface_x(y, z) + depth)
                    ring_verts.append((x, y, z))
        ring_faces = []
        for i in range(8):
            ring_faces.extend(((i, i + 1, 9 + i + 1, 9 + i),
                               (18 + i, 27 + i, 27 + i + 1, 18 + i + 1),
                               (i, 18 + i, 18 + i + 1, i + 1),
                               (9 + i, 9 + i + 1, 27 + i + 1, 27 + i)))
        mesh(f"{label}_fender_lip_{'L' if side < 0 else 'R'}", ring_verts, ring_faces, paint)

# Sloping cabin and fastback glass. All windows sit on the actual cabin planes.
cab = [(-.92, .48, 1.04), (.92, .48, 1.04),
       (.96, -1.48, 1.04), (-.96, -1.48, 1.04),
       (-.77, -.10, 1.67), (.77, -.10, 1.67),
       (.79, -.84, 1.63), (-.79, -.84, 1.63)]
mesh("Cabin_fastback_frame", cab,
     [(0, 1, 5, 4), (3, 7, 6, 2), (1, 2, 6, 5), (0, 4, 7, 3), (4, 5, 6, 7)])


def lerp(a, b, t):
    return Vector(a).lerp(Vector(b), t)


def glass_quad(name, corners, outward, inset=.10):
    center = sum((Vector(c) for c in corners), Vector()) / 4
    points = [center + (Vector(c) - center) * (1 - inset) + Vector(outward) * .012
              for c in corners]
    mesh(name, points, [(0, 1, 2, 3)], glass)
    # One broad graphic reflection, kept sparse enough to read at game distance.
    patch = [lerp(points[0], points[3], .75), lerp(points[1], points[2], .75),
             lerp(points[1], points[2], .91), lerp(points[0], points[3], .91)]
    patch = [v + Vector(outward) * .002 for v in patch]
    mesh(name + "_sky_band", patch, [(0, 1, 2, 3)], glass_reflection)


glass_quad("Windshield", [cab[0], cab[1], cab[5], cab[4]], (0, .72, .68), .13)
glass_quad("Rear_window", [cab[2], cab[3], cab[7], cab[6]], (0, -.70, .72), .16)
for side, indices in ((-1, (0, 3, 7, 4)), (1, (1, 2, 6, 5))):
    a, b, c, d = [Vector(cab[i]) for i in indices]
    split_bottom = a.lerp(b, .66)
    split_top = d.lerp(c, .66)
    label = "L" if side < 0 else "R"
    glass_quad("Door_window_" + label, [a, split_bottom, split_top, d], (side, 0, .12), .15)
    glass_quad("Quarter_window_" + label, [split_bottom, b, c, split_top], (side, 0, .12), .23)
    # Beltline, recessed door perimeter, and one substantial handle.
    belt_points = []
    for y in (.71, .60, -.35, -1.01):
        width, top = body_section(y)
        belt_points.append((side * (width * .977 + .005), y, top - .11))
    for i in range(len(belt_points) - 1):
        line("Beltline_" + label + str(i), belt_points[i], belt_points[i + 1], .009, paint_seam)
    for suffix, aa, bb in (
        ("front", (side * 1.071, .68, .91), (side * 1.071, .77, .47)),
        ("rear", (side * 1.08, -.89, .925), (side * 1.08, -.98, .47)),
        ("bottom", (side * 1.075, .73, .46), (side * 1.08, -.94, .46)),
    ):
        line("Door_seam_" + suffix + "_" + label, aa, bb, .007, paint_seam)
    box("Door_handle_" + label, (side * 1.097, -.56, .945), (.036, .19, .045), metal_dark, chamfer=.008)
    mirror = box("Mirror_" + label, (side * 1.075, .26, 1.185), (.20, .23, .11), paint, chamfer=.026)
    box("Mirror_glass_" + label, (side * 1.075, .137, 1.188), (.15, .012, .065), glass)
    box("Rocker_" + label, (side * 1.055, -.03, .415), (.08, 1.68, .09), paint_dark, chamfer=.025)

# Raised cowl: wide hood, restrained dark stripes, functional-looking scoop.
scoop_verts = [(-.34, .68, 1.058), (.34, .68, 1.058),
               (.30, 1.58, 1.107), (-.30, 1.58, 1.107),
               (-.28, .80, 1.196), (.28, .80, 1.196),
               (.27, 1.54, 1.176), (-.27, 1.54, 1.176)]
mesh("Hood_power_cowl", scoop_verts,
     [(0, 1, 5, 4), (3, 7, 6, 2), (1, 2, 6, 5), (0, 4, 7, 3), (4, 5, 6, 7)])
box("Scoop_inlet", (0, 1.574, 1.145), (.47, .024, .047), dark, chamfer=.008)
for side in (-1, 1):
    x = side * .48
    stripe_points = []
    stripe_samples = (.65, 1.44, 2.05, 2.23)
    for y in stripe_samples:
        _, top = body_section(y)
        stripe_points.extend(((x - .06, y, top + .003), (x + .06, y, top + .003)))
    mesh("Hood_stripe_" + str(side),
         stripe_points, [(i * 2, i * 2 + 1, i * 2 + 3, i * 2 + 2)
                         for i in range(len(stripe_samples) - 1)], dark)
    seam_points = []
    for y in (.60, 1.44, 2.05, 2.23):
        width, top = body_section(y)
        seam_points.append((side * width * .80, y, top + .003))
    for i in range(len(seam_points) - 1):
        line("Hood_panel_seam_" + str(side) + str(i), seam_points[i], seam_points[i + 1], .003, paint_seam)

# Front: four round lamps framed by a deep charcoal fascia.
box("Front_fascia", (0, 2.406, .81), (1.96, .06, .35), dark, chamfer=.05)
box("Grille_inset", (0, 2.448, .81), (.70, .025, .27), metal_dark, chamfer=.02)
for z in (.73, .81, .89):
    box("Grille_slat_" + str(z), (0, 2.467, z), (.65, .018, .025), dark)
box("Grille_center_badge", (0, 2.479, .82), (.065, .018, .115), metal, chamfer=.009)
for x in (-.79, -.49, .49, .79):
    cylinder("Headlight_recess_" + str(x), (x, 2.448, .83), .139, .039, metal_dark, axis="Y", sides=12)
    cylinder("Headlight_lens_" + str(x), (x, 2.473, .83), .112, .019, headlight, axis="Y", sides=12)
    cylinder("Headlight_center_" + str(x), (x, 2.485, .83), .054, .008, plate, axis="Y", sides=8)
box("Front_bumper", (0, 2.429, .555), (2.05, .15, .14), metal, chamfer=.035)
box("Front_chin", (0, 2.385, .375), (2.075, .22, .125), dark, chamfer=.035)
for x in (-.9, .9):
    box("Amber_indicator_" + str(x), (x, 2.451, .615), (.18, .025, .045), plate, chamfer=.009)

# Rear: readable from the chase view, without spending detail on tiny texture noise.
box("Rear_fascia", (0, -2.407, .785), (1.985, .07, .33), dark, chamfer=.034)
for side in (-1, 1):
    x = side * .65
    box("Taillight_recess_" + str(side), (x, -2.454, .825), (.63, .023, .20), tail_dark, chamfer=.018)
    for i in (-1, 0, 1):
        box("Taillight_segment_" + str(side) + "_" + str(i),
            (x + i * .196, -2.47, .825), (.176, .014, .134), tail, chamfer=.012)
    cylinder("Exhaust_outer_" + str(side), (side * .76, -2.448, .363), .071, .19,
             metal, axis="Y", sides=8)
    cylinder("Exhaust_dark_opening_" + str(side), (side * .76, -2.547, .363), .051,
             .01, dark, axis="Y", sides=8)
box("Rear_plate", (0, -2.467, .745), (.43, .025, .185), plate, chamfer=.013)
box("Rear_bumper", (0, -2.435, .535), (2.09, .16, .13), metal, chamfer=.03)
box("Rear_valance", (0, -2.365, .39), (1.81, .20, .105), dark, chamfer=.025)
parent_keep_world(box("Trunk_lip", (0, -2.28, 1.045), (1.98, .15, .065), paint, chamfer=.023), trunk_hinge)
for x in (-.08, .08):
    badge = box("Rear_badge_" + str(x), (x, -2.424, .997), (.034, .014, .075), metal)
    badge.rotation_euler.y = -.25

# A small geometric LOWCAR plate inscription; no texture dependency.
bpy.ops.object.text_add(location=(0, -2.485, .749))
text_obj = bpy.context.object
text_obj.name = "LOWCAR_plate_letters"
text_obj.data.body = "LOWCAR"
text_obj.data.align_x = "CENTER"
text_obj.data.align_y = "CENTER"
text_obj.data.size = .058
text_obj.rotation_euler = (pi / 2, 0, 0)
text_obj.data.materials.append(dark)
move_collection(text_obj)
text_obj.parent = chassis
bpy.ops.object.convert(target="MESH")

# Wheels rotate around local X; separate pivots survive the GLB import.
def build_wheel(name, location, radius, width, side):
    pivot = empty(name, wheels, location)
    steer = empty(name + "Steer", pivot)
    spin = empty(name + "Spin", steer)
    n = 16
    wheel_verts = []
    rings = [(-width / 2, radius * .90), (-width * .35, radius),
             (width * .35, radius), (width / 2, radius * .90)]
    for x, r in rings:
        wheel_verts.extend((x, cos(i * 2 * pi / n) * r, sin(i * 2 * pi / n) * r)
                           for i in range(n))
    wheel_faces = []
    for ring in range(3):
        for i in range(n):
            wheel_faces.append((ring * n + i, ring * n + (i + 1) % n,
                                (ring + 1) * n + (i + 1) % n, (ring + 1) * n + i))
    wheel_faces.extend((tuple(range(n - 1, -1, -1)), tuple(range(n * 3, n * 4))))
    tire_obj = mesh(name + "_Tire", wheel_verts, wheel_faces, rubber, parent=spin)
    tire_obj.data.materials.append(tire_edge)
    for i, face in enumerate(tire_obj.data.polygons):
        face.material_index = 1 if i < n or i >= n * 2 else 0
    out_x = side * (width / 2 + .009)
    cylinder(name + "_Rim_inset", (out_x, 0, 0), radius * .64, .021,
             dark, sides=16, parent=spin)
    rim_verts = []
    for x, r in ((out_x + side * .006, radius * .65),
                 (out_x + side * .013, radius * .54)):
        rim_verts.extend((x, cos(i * 2 * pi / n) * r, sin(i * 2 * pi / n) * r)
                         for i in range(n))
    mesh(name + "_Rim_lip", rim_verts,
         [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)], metal, parent=spin)
    for i in range(5):
        angle = i * 2 * pi / 5
        a = Vector((out_x + side * .018, cos(angle) * radius * .13, sin(angle) * radius * .13))
        b = Vector((out_x + side * .018, cos(angle) * radius * .51, sin(angle) * radius * .51))
        line(name + "_Spoke_" + str(i), a, b, .045, metal, parent=spin)
    cylinder(name + "_Hub", (out_x + side * .025, 0, 0), radius * .17, .029,
             metal_dark, sides=10, parent=spin)
    cylinder(name + "_Hub_cap", (out_x + side * .043, 0, 0), radius * .105, .012,
             metal, sides=8, parent=spin)
    return pivot


build_wheel("FrontLeft", (-1.005, 1.44, .445), .445, .30, -1)
build_wheel("FrontRight", (1.005, 1.44, .445), .445, .30, 1)
build_wheel("RearLeft", (-1.005, -1.43, .48), .48, .36, -1)
build_wheel("RearRight", (1.005, -1.43, .48), .48, .36, 1)

# Flat surface normals preserve the broad plane changes; no triangulation noise.
for obj in model_collection.objects:
    if obj.type == "MESH":
        for poly in obj.data.polygons:
            poly.use_smooth = False

bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 1
root["forward"] = "Blender +Y; Godot -Z"
root["style"] = "Bright red, broad muscle silhouette, sparse faceted edges"
root["wheel_pivots"] = "X axis rotation; front radius .445m, rear radius .48m"

# Merge export copies by moving part. Source pieces stay individually editable.
source_meshes = [obj for obj in model_collection.objects if obj.type == "MESH"]
runtime_meshes = []
for parent in (chassis, trunk_hinge, *(wheel.children[0].children[0] for wheel in wheels.children)):
    bpy.ops.object.select_all(action="DESELECT")
    copies = []
    for original in source_meshes:
        if original.parent != parent:
            continue
        copy = original.copy()
        copy.data = original.data.copy()
        model_collection.objects.link(copy)
        copy.select_set(True)
        copies.append(copy)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    merged = bpy.context.object
    merged.name = "BodyMesh" if parent == chassis else ("TrunkLidMesh" if parent == trunk_hinge else parent.name.removesuffix("Spin") + "Mesh")
    runtime_meshes.append(merged)

# Export only the actual car and its pivots.
bpy.ops.object.select_all(action="DESELECT")
for obj in [*(obj for obj in model_collection.objects if obj.type == "EMPTY"), *runtime_meshes]:
    obj.select_set(True)
glb_path = ASSET / "red_muscle_car.glb"
bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", use_selection=True,
                          export_yup=True, export_apply=True, export_extras=True,
                          export_cameras=False, export_lights=False)
for obj in runtime_meshes:
    bpy.data.objects.remove(obj, do_unlink=True)

# Studio setup is saved in the editable source, but never exported into the game.
floor_mat = material("Studio floor", "DAE0E5", .9)
floor = box("STUDIO_floor", (0, 0, -.04), (200, 200, .08), floor_mat, parent=None)
move_collection(floor, studio_collection)


def area(name, location, power, size, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    studio_collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, .7)) - obj.location).to_track_quat("-Z", "Y").to_euler()


area("STUDIO_key", (4, 5, 8), 700, 5)
area("STUDIO_fill", (-4, 1, 5), 250, 5, (.78, .86, 1))
area("STUDIO_rim", (1, -5, 6), 480, 4)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1600
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.world.color = (.16, .16, .16)
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.65, .72, .8, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .28
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = -.2
camera_data = bpy.data.cameras.new("STUDIO_camera")
camera = bpy.data.objects.new("STUDIO_camera", camera_data)
studio_collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 7.4

for label, position in (("front_three_quarter", (6.4, 8.6, 5.0)),
                        ("rear_three_quarter", (6.4, -8.6, 4.8)),
                        ("side", (9, .3, 2.2))):
    camera.location = position
    target = Vector((0, 0, .75))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(PREVIEWS / (label + ".png"))
    bpy.ops.render.render(write_still=True)

camera.location = (6.4, 8.6, 5.0)
camera.rotation_euler = (Vector((0, 0, .75)) - camera.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE / "red_muscle_car.blend"))

triangles = sum(sum(len(p.vertices) - 2 for p in obj.data.polygons)
                for obj in model_collection.objects if obj.type == "MESH")
manifest = {"name": "Lowcar red muscle car", "triangles": triangles,
            "runtime_mesh_objects": 6, "editable_source_mesh_objects": len(source_meshes),
            "glb_sha256": hashlib.sha256(glb_path.read_bytes()).hexdigest(),
            "forward": "-Z in Godot", "units": "meters",
            "front_wheel_radius_m": .445, "rear_wheel_radius_m": .48,
            "wheel_paths": ["Wheels/FrontLeft", "Wheels/FrontRight", "Wheels/RearLeft", "Wheels/RearRight"],
            "wheel_spin_child": "{Wheel}Steer/{Wheel}Spin", "trunk_hinge": "Chassis/TrunkHinge"}
(ASSET / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("LOWCAR_MODEL_BUILT", json.dumps(manifest))
