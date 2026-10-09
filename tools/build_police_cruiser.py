"""Build Belle Rive's ordinary four-door police cruiser, GLB, and studio previews in Blender.

Run with Blender --background --python tools/build_police_cruiser.py.
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
ASSET = PROJECT / "assets/models/vehicles/police_cruiser"
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


paint = material("Paint — warm fleet white", "F1EEE3", .58)
paint_dark = material("Paint — lower cream facets", "C9CDC6", .63)
paint_light = material("Paint — cream shoulders", "FAF5E9", .56)
navy = material("Paint — municipal navy", "243D53", .54)
navy_light = material("Paint — navy edge facets", "36566D", .56)
paint_seam = material("Panel seams", "697A80", .86)
dark = material("Trim — deep graphite", "192B37", .72)
rubber = material("Tires — graphite", "202832", .94)
tire_edge = material("Tire sidewall facets", "343D47", .90)
metal = material("Metal — satin silver", "B9C5CB", .43, .30)
metal_dark = material("Metal — steel wheel dish", "647581", .58, .20)
glass = material("Glass — painted blue", "284D65", .48)
glass_reflection = material("Glass — sky bands", "739EB2", .54)
headlight = material("Headlights — ivory", "FFF2CD", .52)
tail = material("Taillights — scarlet", "E84A4F", .51)
tail_dark = material("Lamp surrounds", "9E343C", .61)
plate = material("Plate — warm cream", "F1E5C9", .76)
red_lens = material("Lightbar — red lens", "F04B52", .46)
blue_lens = material("Lightbar — blue lens", "3997DF", .46)
amber = material("Indicators — amber", "F3BA55", .55)
gold = material("Badge — muted brass", "C9AA62", .68, .08)


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


root = empty("Belle_Rive_Police_Cruiser")
chassis = empty("Chassis", root)
wheels = empty("Wheels", root)
red_light = empty("RedLight", chassis)
blue_light = empty("BlueLight", chassis)


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


# Ordinary fleet sedan: a broad hood, upright four-door cabin and separate trunk.
sections = [(2.35, .94, .96), (2.08, 1.005, 1.00), (1.42, 1.035, 1.035),
            (.70, 1.035, 1.02), (-.25, 1.035, 1.01), (-1.42, 1.035, 1.01),
            (-2.08, 1.00, .98), (-2.35, .95, .92)]
verts = []
for y, width, top in sections:
    profile = [(-width * .83, top), (-width * .965, top - .055),
               (-width, top - .16), (-width, .42), (-width * .94, .34),
               (width * .94, .34), (width, .42), (width, top - .16),
               (width * .965, top - .055), (width * .83, top)]
    verts.extend((x, y, z) for x, z in profile)
faces = [tuple(range(9, -1, -1))]
for ring in range(len(sections) - 1):
    for edge in range(10):
        faces.append((ring * 10 + edge, ring * 10 + (edge + 1) % 10,
                      (ring + 1) * 10 + (edge + 1) % 10, (ring + 1) * 10 + edge))
faces.append(tuple(range((len(sections) - 1) * 10, len(sections) * 10)))
body = mesh("Sculpted_sedan_shell", verts, faces)


def body_section(y):
    for high, low in zip(sections, sections[1:]):
        if low[0] <= y <= high[0]:
            t = (y - low[0]) / (high[0] - low[0])
            return low[1] + (high[1] - low[1]) * t, low[2] + (high[2] - low[2]) * t
    return sections[0][1], sections[0][2]


def body_surface_x(y, z):
    width, top = body_section(y)
    if z <= top - .16:
        return width
    if z <= top - .055:
        return width * (1 - .035 * (z - top + .16) / .105)
    return width * (.965 - .135 * min(1, (z - top + .055) / .055))


for axle in (1.42, -1.42):
    cutter = cylinder("temporary_wheelwell", (0, axle, .43), .485, 3.2, dark, sides=16)
    mod = body.modifiers.new("Actual wheel arch opening", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    apply_modifier(body, mod)
    bpy.data.objects.remove(cutter, do_unlink=True)
for mat in (paint_dark, paint_light, navy, navy_light):
    body.data.materials.append(mat)
for face in body.data.polygons:
    center = sum((body.data.vertices[i].co for i in face.vertices), Vector()) / len(face.vertices)
    if center.y > .72 or center.y < -1.48:
        face.material_index = body.data.materials.find((navy_light if .1 < face.normal.z < .9 else navy).name)
    elif center.z < .54:
        face.material_index = body.data.materials.find(paint_dark.name)
    elif .1 < face.normal.z < .9:
        face.material_index = body.data.materials.find(paint_light.name)
box("Underbody", (0, 0, .34), (1.60, 3.95, .13), dark, chamfer=.025)

# Short fender lip bands follow the shell rather than floating above it.
for side in (-1, 1):
    for axle in (1.42, -1.42):
        points = []
        for radius in (.485, .519):
            for index in range(9):
                angle = index * pi / 8
                y, z = axle + cos(angle) * radius, .43 + sin(angle) * radius
                points.append((side * (body_surface_x(y, z) + .006), y, z))
        mesh(f"Arch_trim_{side}_{axle}", points,
             [(i, i + 1, i + 10, i + 9) for i in range(8)], navy_light)

cab = [(-.92, .72, 1.017), (.92, .72, 1.017),
       (.93, -1.48, 1.004), (-.93, -1.48, 1.004),
       (-.79, .20, 1.565), (.79, .20, 1.565),
       (.79, -1.00, 1.55), (-.79, -1.00, 1.55)]
mesh("Upright_four_door_cabin", cab,
     [(0, 1, 5, 4), (3, 7, 6, 2), (1, 2, 6, 5), (0, 4, 7, 3), (4, 5, 6, 7)], paint)


def glass_quad(name, corners, outward, inset=.12):
    center = sum((Vector(c) for c in corners), Vector()) / 4
    normal = Vector(outward)
    border = [center + (Vector(c) - center) * (1 - inset) + normal * .008 for c in corners]
    mesh(name + "_rubber_surround", border, [(0, 1, 2, 3)], dark)
    points = [center + (v - center) * .965 + normal * .006 for v in border]
    mesh(name, points, [(0, 1, 2, 3)], glass)
    patch = [points[0].lerp(points[3], .75), points[1].lerp(points[2], .75),
             points[1].lerp(points[2], .88), points[0].lerp(points[3], .88)]
    mesh(name + "_painted_sky", [v + normal * .003 for v in patch], [(0, 1, 2, 3)], glass_reflection)


glass_quad("Windshield", [cab[0], cab[1], cab[5], cab[4]], (0, .73, .68), .13)
glass_quad("Rear_glass", [cab[2], cab[3], cab[7], cab[6]], (0, -.75, .66), .16)


def lettering(name, text, at, size, mat, rotation=(0, 0, 0)):
    bpy.ops.object.text_add(location=at)
    obj = bpy.context.object
    obj.name = name
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.resolution_u = 2
    obj.rotation_euler = rotation
    obj.data.materials.append(mat)
    move_collection(obj)
    obj.parent = chassis
    bpy.ops.object.convert(target="MESH")
    return obj


for side, indices in ((-1, (0, 3, 7, 4)), (1, (1, 2, 6, 5))):
    a, b, c, d = [Vector(cab[i]) for i in indices]
    split_bottom, split_top = a.lerp(b, .46), d.lerp(c, .46)
    glass_quad(f"Front_door_glass_{side}", [a, split_bottom, split_top, d], (side, 0, .23), .14)
    glass_quad(f"Rear_door_glass_{side}", [split_bottom, b, c, split_top], (side, 0, .23), .17)
    # Trim, four real door outlines, normal handles and a little fleet badge.
    for y, z, y2, z2 in ((.74, .845, .65, .47), (-.29, .845, -.29, .47),
                           (-1.43, .845, -1.30, .51), (.65, .47, -1.30, .47)):
        line(f"Door_cut_{side}_{y}_{z}", (side * 1.043, y, z),
             (side * 1.043, y2, z2), .005, paint_seam)
    box(f"Door_livery_{side}", (side * 1.042, -.33, .705), (.012, 2.0, .21), navy)
    box(f"Belt_molding_{side}", (side * 1.042, -.34, .854), (.018, 2.02, .025), dark)
    for y in (-.08, -1.11):
        box(f"Handle_recess_{side}_{y}", (side * 1.047, y, .893), (.02, .19, .044), dark, chamfer=.008)
        box(f"Handle_{side}_{y}", (side * 1.061, y, .899), (.022, .135, .024), metal, chamfer=.005)
    box(f"Rocker_molding_{side}", (side * 1.015, 0, .39), (.055, 1.95, .065), navy, chamfer=.014)
    box(f"Mirror_stalk_{side}", (side * 1.01, .55, 1.115), (.16, .075, .05), dark)
    box(f"Mirror_housing_{side}", (side * 1.125, .54, 1.155), (.17, .22, .115), navy, chamfer=.02)
    box(f"Mirror_blue_face_{side}", (side * 1.128, .423, 1.16), (.12, .008, .063), glass_reflection)
    # Side text faces outwards: +X local text runs toward the front; -X toward rear.
    rotation = (pi / 2, 0, side * pi / 2)
    lettering(f"Police_door_type_{side}", "POLICE", (side * 1.054, -.50, .703), .178, paint_light, rotation)
    lettering(f"City_door_type_{side}", "BELLE RIVE", (side * 1.054, -.50, .586), .074, navy, rotation)
    # Six-point brass municipal badge; simple geometry, no ornamental noise.
    badge_y = .43
    badge_verts = [(side * 1.055, badge_y, .70)]
    for i in range(12):
        r = .104 if i % 2 == 0 else .066
        badge_verts.append((side * 1.055, badge_y + cos(i * pi / 6) * r, .70 + sin(i * pi / 6) * r))
    mesh(f"Municipal_badge_{side}", badge_verts,
         [(0, i + 1, (i + 1) % 12 + 1) for i in range(12)], gold)
    cylinder(f"Badge_center_{side}", (side * 1.059, badge_y, .70), .045, .009, navy, sides=8)

# Subtle hood / trunk seams and wipers: restrained everyday sheet metal.
for side in (-1, 1):
    for first, last in ((.75, 2.24), (-1.51, -2.25)):
        points = []
        for i in range(4):
            y = first + (last - first) * i / 3
            width, top = body_section(y)
            points.append((side * width * .80, y, top + .005))
        for i in range(3):
            line(f"Deck_seam_{side}_{first}_{i}", points[i], points[i + 1], .004, dark)
    line(f"Wiper_{side}", (side * .72, .657, 1.083), (side * .13, .603, 1.136), .009, dark)

# Deep lamp pockets and a simple horizontal grille. No sports-car scoop or wing.
box("Front_fascia", (0, 2.366, .78), (1.88, .052, .29), dark, chamfer=.025)
box("Grille_dish", (0, 2.397, .795), (.73, .022, .24), metal_dark, chamfer=.018)
for z in (.718, .768, .818, .868):
    box("Grille_bar_" + str(z), (0, 2.415, z), (.675, .017, .018), metal)
box("Grille_badge", (0, 2.429, .79), (.075, .012, .043), navy, chamfer=.008)
for side in (-1, 1):
    box(f"Headlight_pocket_{side}", (side * .665, 2.403, .80), (.50, .025, .215), metal_dark, chamfer=.016)
    for i in (-1, 1):
        box(f"Headlight_{side}_{i}", (side * .665 + i * .12, 2.422, .817), (.212, .015, .139), headlight, chamfer=.01)
    box(f"Amber_front_{side}", (side * .665, 2.423, .715), (.453, .016, .038), amber, chamfer=.006)
box("Front_bumper", (0, 2.367, .523), (1.98, .18, .18), navy_light, chamfer=.035)
box("Front_bumper_rub_strip", (0, 2.465, .54), (1.76, .023, .063), dark, chamfer=.008)
box("Lower_air_inlet", (0, 2.443, .392), (.91, .025, .092), dark, chamfer=.012)
box("Front_plate", (0, 2.485, .526), (.38, .014, .142), plate, chamfer=.008)
lettering("Front_plate_type", "BR 021", (0, 2.496, .526), .048, dark, (pi / 2, 0, pi))
# A normal modest patrol pushbar, visibly mounted to the bumper.
for x in (-.44, .44):
    box("Pushbar_upright_" + str(x), (x, 2.54, .67), (.073, .093, .48), dark, chamfer=.016)
    box("Pushbar_mount_" + str(x), (x, 2.44, .47), (.09, .28, .075), dark, chamfer=.012)
box("Pushbar_crosspiece", (0, 2.565, .68), (.94, .063, .076), metal_dark, chamfer=.018)

box("Rear_fascia", (0, -2.361, .737), (1.90, .055, .27), navy_light, chamfer=.026)
for side in (-1, 1):
    box(f"Rear_lamp_pocket_{side}", (side * .66, -2.395, .773), (.48, .017, .18), tail_dark, chamfer=.019)
    box(f"Rear_stop_lens_{side}", (side * .70, -2.408, .786), (.36, .013, .116), tail, chamfer=.012)
    box(f"Reverse_lamp_{side}", (side * .46, -2.409, .783), (.082, .014, .115), headlight, chamfer=.007)
box("Rear_plate_pocket", (0, -2.396, .722), (.49, .018, .19), dark, chamfer=.014)
box("Rear_plate", (0, -2.411, .722), (.398, .016, .146), plate, chamfer=.009)
lettering("Rear_plate_type", "BR 021", (0, -2.422, .721), .051, dark, (pi / 2, 0, 0))
box("Rear_bumper", (0, -2.373, .491), (2.00, .16, .165), navy_light, chamfer=.03)
box("Rear_bumper_strip", (0, -2.465, .51), (1.77, .018, .057), dark, chamfer=.008)
lettering("Rear_fleet_id", "021", (.73, -2.358, .875), .065, paint, (pi / 2, 0, 0))
lettering("Trunk_POLICE", "POLICE", (0, -1.88, .995), .165, paint)
cylinder("Exhaust_tip", (.69, -2.37, .329), .048, .20, metal, axis="Y", sides=8)
cylinder("Exhaust_inset", (.69, -2.476, .329), .034, .009, dark, axis="Y", sides=8)

# Low-profile standard lightbar, with isolated lens meshes for per-instance flashes.
for x in (-.41, .41):
    box("Lightbar_foot_" + str(x), (x, -.36, 1.587), (.17, .15, .071), dark, chamfer=.01)
box("Lightbar_base", (0, -.36, 1.641), (1.21, .295, .072), dark, chamfer=.024)
box("Lightbar_center", (0, -.36, 1.719), (.26, .255, .125), paint, chamfer=.022)
box("Lightbar_center_grille", (0, -.494, 1.719), (.184, .012, .064), metal_dark, chamfer=.009)
for side, parent, mat in ((-1, red_light, red_lens), (1, blue_light, blue_lens)):
    box(f"Lightbar_lens_{side}", (side * .393, -.36, 1.720), (.486, .255, .13), mat, parent, chamfer=.025)
    # Dividers stay graphite and do not pulse with the colored lenses.
    for x in (side * .30, side * .47):
        box(f"Lightbar_divider_{x}", (x, -.36, 1.718), (.013, .266, .127), dark, chamfer=.004)
cylinder("Antenna_base", (.60, -.85, 1.565), .039, .023, dark, axis="Z", sides=8)
line("Short_radio_antenna", (.60, -.85, 1.57), (.60, -.92, 1.87), .007, dark)


def build_wheel(name, location, side):
    pivot = empty(name, wheels, location)
    steer = empty(name + "Steer", pivot)
    spin = empty(name + "Spin", steer)
    n, radius, width = 16, .43, .26
    wheel_verts = []
    for x, r in ((-.13, .385), (-.092, radius), (.092, radius), (.13, .385)):
        wheel_verts.extend((x, cos(i * 2 * pi / n) * r, sin(i * 2 * pi / n) * r) for i in range(n))
    wheel_faces = []
    for ring in range(3):
        wheel_faces.extend((ring * n + i, ring * n + (i + 1) % n,
                            (ring + 1) * n + (i + 1) % n, (ring + 1) * n + i) for i in range(n))
    wheel_faces.extend((tuple(range(n - 1, -1, -1)), tuple(range(3 * n, 4 * n))))
    tire = mesh(name + "_Tire", wheel_verts, wheel_faces, rubber, spin)
    tire.data.materials.append(tire_edge)
    for i, face in enumerate(tire.data.polygons):
        face.material_index = 1 if i < n or i >= 2 * n else 0
    out = side * .141
    cylinder(name + "_Steel_dish", (out, 0, 0), .271, .022, metal_dark, sides=16, parent=spin)
    # Ordinary pressed steel disk, silver lip and small dark ventilation slots.
    rim_verts = []
    for x, r in ((out + side * .007, .273), (out + side * .014, .248)):
        rim_verts.extend((x, cos(i * 2 * pi / n) * r, sin(i * 2 * pi / n) * r) for i in range(n))
    mesh(name + "_Rim_lip", rim_verts, [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)], metal, spin)
    for i in range(8):
        angle = i * 2 * pi / 8
        slot = box(name + "_Wheel_vent_" + str(i),
                   (out + side * .025, cos(angle) * .204, sin(angle) * .204),
                   (.008, .066, .035), dark, spin, chamfer=.007)
        slot.rotation_euler.x = angle
    cylinder(name + "_Fleet_hubcap", (out + side * .029, 0, 0), .142, .05, metal, sides=12, parent=spin)
    cylinder(name + "_Hub_center", (out + side * .057, 0, 0), .052, .006, navy, sides=8, parent=spin)
    for i in range(5):
        a = i * 2 * pi / 5
        cylinder(name + "_Lug_" + str(i), (out + side * .057, cos(a) * .095, sin(a) * .095),
                 .012, .012, metal_dark, sides=6, parent=spin)
    return spin


spins = [build_wheel(name, (side * .98, y, .43), side) for name, side, y in
         (("FrontLeft", -1, 1.42), ("FrontRight", 1, 1.42), ("RearLeft", -1, -1.42), ("RearRight", 1, -1.42))]
for obj in model_collection.objects:
    if obj.type == "MESH":
        for face in obj.data.polygons:
            face.use_smooth = False
bpy.context.scene.unit_settings.system = "METRIC"
root["city"] = "Belle Rive"
root["role"] = "Ordinary four-door municipal police cruiser; unit 021"
root["forward"] = "Blender +Y; Godot -Z"

# Preserve all authored parts in Blender; merge only export copies by moving part.
source_meshes = [obj for obj in model_collection.objects if obj.type == "MESH"]
runtime_meshes = []
for parent in (chassis, red_light, blue_light, *spins):
    bpy.ops.object.select_all(action="DESELECT")
    copies = []
    for original in source_meshes:
        if original.parent == parent:
            obj = original.copy()
            obj.data = original.data.copy()
            model_collection.objects.link(obj)
            obj.select_set(True)
            copies.append(obj)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    merged = bpy.context.object
    merged.name = "BodyMesh" if parent == chassis else (parent.name + "Mesh")
    runtime_meshes.append(merged)
bpy.ops.object.select_all(action="DESELECT")
for obj in [*(obj for obj in model_collection.objects if obj.type == "EMPTY"), *runtime_meshes]:
    obj.select_set(True)
glb_path = ASSET / "police_cruiser.glb"
bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", use_selection=True,
                          export_yup=True, export_apply=True, export_extras=True,
                          export_cameras=False, export_lights=False)
for obj in runtime_meshes:
    bpy.data.objects.remove(obj, do_unlink=True)

floor_mat = material("Studio floor", "DAE0E5", .9)
floor = box("STUDIO_floor", (0, 0, -.04), (200, 200, .08), floor_mat, parent=None)
move_collection(floor, studio_collection)


def area(name, location, power, size, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.shape, data.size, data.color = power, "DISK", size, color
    obj = bpy.data.objects.new(name, data)
    studio_collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, .7)) - obj.location).to_track_quat("-Z", "Y").to_euler()


area("STUDIO_key", (4, 5, 8), 700, 5)
area("STUDIO_fill", (-4, 1, 5), 250, 5, (.78, .86, 1))
area("STUDIO_rim", (1, -5, 6), 480, 4)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = 1600, 1100
scene.render.image_settings.file_format = "PNG"
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
camera_data.type, camera_data.ortho_scale = "ORTHO", 7.4
for label, position in (("front_three_quarter", (6.4, 8.6, 4.8)),
                        ("rear_three_quarter", (6.4, -8.6, 4.4)), ("side", (9, .15, 2.1))):
    camera.location = position
    camera.rotation_euler = (Vector((0, 0, .85)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(PREVIEWS / (label + ".png"))
    bpy.ops.render.render(write_still=True)
camera.location = (6.4, 8.6, 4.8)
camera.rotation_euler = (Vector((0, 0, .85)) - camera.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE / "police_cruiser.blend"))
triangles = sum(sum(len(p.vertices) - 2 for p in obj.data.polygons) for obj in source_meshes)
manifest = {"name": "Belle Rive police cruiser", "city": "Belle Rive", "unit": "021",
            "triangles": triangles, "runtime_mesh_objects": 7,
            "editable_source_mesh_objects": len(source_meshes),
            "glb_sha256": hashlib.sha256(glb_path.read_bytes()).hexdigest(),
            "forward": "-Z in Godot", "units": "meters", "wheel_radius_m": .43,
            "wheel_paths": ["Wheels/" + n for n in ("FrontLeft", "FrontRight", "RearLeft", "RearRight")],
            "wheel_spin_child": "{Wheel}Steer/{Wheel}Spin",
            "light_paths": ["Chassis/RedLight/RedLightMesh", "Chassis/BlueLight/BlueLightMesh"],
            "glb": "police_cruiser.glb", "source": "source/police_cruiser.blend"}
(ASSET / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("LOWCAR_CRUISER_BUILT", json.dumps(manifest))
