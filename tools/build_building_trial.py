"""Author Lowcar's three building trials. Blender 5.x, no add-ons or textures.

Run: Blender --background --python tools/build_building_trial.py
Blender -Y is the street/front; glTF converts this to Godot +Z. Units: meters.
The .blend files keep named parts; the GLBs merge static export copies.
"""
from pathlib import Path
from math import atan2, cos, sin, pi
import hashlib
import json
import bpy
import bmesh
from mathutils import Vector

PROJECT = Path(__file__).resolve().parents[1]
ASSET = PROJECT / "assets/models/buildings/style_trial"
SOURCE = ASSET / "source"
PREVIEWS = ASSET / "previews"
for directory in (ASSET, SOURCE, PREVIEWS):
    directory.mkdir(parents=True, exist_ok=True)
for directory in (SOURCE, PREVIEWS):
    (directory / ".gdignore").write_text("")
bpy.context.preferences.filepaths.save_version = 0

PALETTE = {
    "cream": "F5E7CD", "stone": "D7C8AC", "coral": "E9967C",
    "coral_dark": "CC715D", "mint": "83B9A8", "mint_dark": "62978F",
    "yellow": "EBC567", "yellow_dark": "C99B46", "roof": "52738C",
    "teal": "328D89", "ink": "24394B", "glass": "34576B",
    "reflection": "739BAC", "green": "7BAA67", "green_dark": "527B53",
    "pot": "BE7659", "metal": "8A9B9E",
}
materials = {}
collection = None
root = None


def srgb(c):
    return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4


def reset_scene(name):
    global collection, root, materials
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    collection = bpy.data.collections.new("MODEL — editable architectural parts")
    bpy.context.scene.collection.children.link(collection)
    root = bpy.data.objects.new(name, None)
    collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = .5
    root["front"] = "Blender -Y; Godot +Z"
    root["units"] = "meters; origin at ground center"
    materials = {}
    for key, hex_value in PALETTE.items():
        mat = bpy.data.materials.new(key.title() + " — " + hex_value)
        rgb = tuple(srgb(int(hex_value[i:i+2], 16) / 255) for i in (0, 2, 4))
        mat.diffuse_color = (*rgb, 1)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*rgb, 1)
        bsdf.inputs["Roughness"].default_value = .84 if key not in ("glass", "reflection") else .56
        bsdf.inputs["Metallic"].default_value = 0
        bsdf.inputs["Specular IOR Level"].default_value = .2
        materials[key] = mat
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1


def relink(obj):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)
    obj.parent = root
    return obj


def mesh(name, vertices, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.parent = root
    obj.data.materials.append(materials[mat])
    return obj


def bevel(obj, width):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("Single broad edge facet", "BEVEL")
    mod.width = width
    mod.segments = 1
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)
    return obj


def box(name, at, size, mat="cream", edge=0, angle=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=at)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler.z = angle
    relink(obj)
    obj.data.materials.append(materials[mat])
    if edge:
        bevel(obj, edge)
    return obj


def prism(name, outline, bottom, top, mat="cream", edge=0):
    n = len(outline)
    vertices = [(x, y, z) for z in (bottom, top) for x, y in outline]
    faces = [tuple(range(n-1, -1, -1)), tuple(range(n, n*2))]
    faces += [(i, (i+1) % n, (i+1) % n+n, i+n) for i in range(n)]
    obj = mesh(name, vertices, faces, mat)
    if edge:
        bevel(obj, edge)
    return obj


def cylinder(name, at, radius, height, mat, vertices=8):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=height, location=at)
    obj = bpy.context.object
    obj.name = name
    relink(obj)
    obj.data.materials.append(materials[mat])
    return obj


def rod(name, a, b, width, mat="ink"):
    a, b = Vector(a), Vector(b)
    direction = b-a
    obj = box(name, (a+b)/2, (width, width, direction.length), mat)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


class Wall:
    """A facade with real openings rather than glass pasted over a solid cube."""
    def __init__(self, name, start, end, normal, depth=.38):
        self.name = name
        self.start = Vector((*start, 0))
        self.end = Vector((*end, 0))
        self.t = (self.end-self.start).normalized()
        self.n = Vector((*normal, 0)).normalized()
        self.length = (self.end-self.start).length
        self.angle = atan2(self.t.y, self.t.x)
        self.depth = depth

    def point(self, u, z, outward=0):
        p = self.start + self.t*u + self.n*outward
        p.z = z
        return p

    def part(self, label, u, z, width, height, mat="cream", depth=.08, outward=0, edge=0):
        return box(self.name+"_"+label, self.point(u, z, outward),
                   (width, depth, height), mat, edge, self.angle)

    def row(self, low, high, openings, mat):
        """openings: (center, width, sill height, head height, kind)."""
        cursor = 0
        for u, width, sill, head, kind in sorted(openings):
            left, right = u-width/2, u+width/2
            if left > cursor:
                self.part("Pier", (cursor+left)/2, (low+high)/2, left-cursor,
                          high-low, mat, self.depth, -self.depth/2)
            if sill > low:
                self.part("Below_opening", u, (low+sill)/2, width,
                          sill-low, mat, self.depth, -self.depth/2)
            if high > head:
                self.part("Above_opening", u, (head+high)/2, width,
                          high-head, mat, self.depth, -self.depth/2)
            self.window(u, sill, width, head-sill, kind)
            cursor = right
        if cursor < self.length:
            self.part("End_pier", (cursor+self.length)/2, (low+high)/2,
                      self.length-cursor, high-low, mat, self.depth, -self.depth/2)

    def window(self, u, sill, width, height, kind="window"):
        z = sill+height/2
        inset = -.19
        self.part("Recess", u, z, width+.015, height+.015, "ink", .06, inset-.03)
        pane_width = width-.18
        # Partition the actual glazing face into three non-overlapping color planes.
        # A floating reflection overlay would create tiny self-shadow artifacts.
        left, right = -pane_width/2, pane_width/2
        bottom, top = -height/2+.09, height/2-.09
        stripe_left_top, stripe_right_top = -pane_width*.45, -pane_width*.12
        stripe_left_bottom, stripe_right_bottom = pane_width*.12, pane_width*.45
        regions = [((left, bottom), (stripe_left_bottom, bottom), (stripe_left_top, top), (left, top)),
                   ((stripe_left_bottom, bottom), (stripe_right_bottom, bottom), (stripe_right_top, top), (stripe_left_top, top)),
                   ((stripe_right_bottom, bottom), (right, bottom), (right, top), (stripe_right_top, top))]
        vertices = [self.point(u+dx, z+dz, inset+.047) for region in regions for dx, dz in region]
        glazing = mesh(self.name+"_Painted_blue_glazing", vertices, [(0, 1, 2, 3), (4, 5, 6, 7), (8, 9, 10, 11)], "glass")
        glazing.data.materials.append(materials["reflection"])
        glazing.data.polygons[1].material_index = 1
        for du in (-width/2, width/2):
            self.part("Jamb", u+du, z, .11, height+.17, "cream", .14, .035)
        for h in (sill, sill+height):
            self.part("Lintel", u, h, width+.13, .11, "cream", .14, .035)
        self.part("Sill", u, sill-.045, width+.28, .14, "stone", .3, .085, .018)
        if kind in ("shop", "door", "lobby"):
            self.part("Central_mullion", u, z, .09, height-.10, "teal" if kind != "lobby" else "ink", .07, inset+.07)
            self.part("Door_or_shop_transom", u, sill+height*.74, width-.1, .08, "teal", .06, inset+.07)
            if kind in ("door", "lobby"):
                self.part("Door_handle", u+.19, sill+1.03, .07, .32, "cream", .09, inset+.13)
        else:
            self.part("Central_mullion", u, z, .065, height-.1, "ink", .045, inset+.065)

    def awning(self, u, width, height, reach=1.0):
        # Physical sloping panels and a straight hanging valance.
        count = max(4, round(width/.42))
        strip = width/count
        for i in range(count):
            left = u-width/2+i*strip
            mat = "teal" if i % 2 == 0 else "cream"
            vertices = [self.point(uu, zz, out) for out, zz in (
                (.04, height), (reach, height-.36), (reach, height-.43), (.04, height-.07))
                for uu in (left, left+strip)]
            mesh(self.name+"_Awning_stripe", vertices,
                 [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 7, 6), (6, 7, 1, 0), (0, 2, 4, 6), (1, 7, 5, 3)], mat)
            self.part("Awning_valance", left+strip/2, height-.50, strip, .18, mat, .09, reach)
        for side in (-1, 1):
            rod(self.name+"_Awning_brace", self.point(u+side*width*.43, height-.9, .04),
                self.point(u+side*width*.43, height-.43, reach-.08), .055, "ink")

    def balcony(self, u, sill, width, reach=.85, planted=False):
        floor = sill-.08
        self.part("Balcony_slab", u, floor, width+.3, .20, "cream", reach+.32, reach/2, .035)
        self.part("Balcony_front", u, floor+.54, width+.24, .88, "mint_dark", .13, reach+.10)
        self.part("Balcony_top_rail", u, floor+1.01, width+.33, .09, "cream", .19, reach+.10)
        for side in (-1, 1):
            self.part("Balcony_side", u+side*(width/2+.055), floor+.54, .13, .88, "mint_dark", reach+.1, reach/2+.04)
            self.part("Balcony_side_top", u+side*(width/2+.055), floor+1.01, .19, .09, "cream", reach+.25, reach/2+.04)
        if planted:
            planter(self.name+"_Balcony_planter", self.point(u+width*.29, floor+.12, reach*.55), .27, .46)


def text(name, body, at, size, mat="cream", angle=0):
    bpy.ops.object.text_add(location=at)
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = .008
    obj.data.resolution_u = 2
    obj.rotation_euler = (pi/2, 0, angle)
    obj.data.materials.append(materials[mat])
    relink(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return obj


def shrub(name, at, scale, mat="green"):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1, location=at)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    relink(obj)
    obj.data.materials.append(materials[mat])
    return obj


def planter(name, at, radius=.35, height=.55):
    x, y, z = at
    n = 8
    verts = [(x+cos(i*2*pi/n)*r, y+sin(i*2*pi/n)*r, z+h)
             for h, r in ((0, radius*.72), (height, radius)) for i in range(n)]
    mesh(name+"_Tapered_pot", verts, [tuple(range(n-1, -1, -1)), tuple(range(n, n*2))]+
         [(i, (i+1) % n, (i+1) % n+n, i+n) for i in range(n)], "pot")
    cylinder(name+"_Rim", (x, y, z+height-.04), radius*1.07, .12, "cream")
    cylinder(name+"_Soil", (x, y, z+height+.025), radius*.88, .015, "ink")
    shrub(name+"_Leaf_mass", (x, y, z+height+radius*.82), (radius*1.1, radius*1.03, radius*1.3))


def parapet(name, outline, z, mat="cream", height=.5):
    for i, start in enumerate(outline):
        end = outline[(i+1) % len(outline)]
        mid = (Vector(start)+Vector(end))/2
        length = (Vector(end)-Vector(start)).length
        angle = atan2(end[1]-start[1], end[0]-start[0])
        box(name+"_Wall", (*mid, z+height/2), (length, .18, height), mat, .024, angle)
        box(name+"_Cap", (*mid, z+height), (length+.10, .27, .12), "cream", .018, angle)


def ac_unit(name, at, size=(1.3, .8, .75)):
    x, y, z = at
    box(name+"_Housing", (x, y, z+size[2]/2), size, "metal", .07)
    box(name+"_Fan_inset", (x, y-.02, z+size[2]+.008), (size[0]*.6, size[1]*.66, .02), "ink", .045)
    for i in (-1, 0, 1):
        box(name+"_Vent_slat", (x+i*.18, y-.02, z+size[2]+.027), (.055, size[1]*.59, .026), "cream")


def corner_market():
    outline = [(-5.4, -3.55), (-4.2, -4.75), (5.4, -4.75), (5.4, 4.75), (-5.4, 4.75)]
    prism("Foundation", outline, 0, .14, "stone", .04)
    prism("Ground_floor_ceiling", outline, 3.04, 3.22, "cream", .035)
    prism("Second_floor_band", outline, 6.24, 6.39, "cream", .025)
    prism("Roof_cornice_lower", [(x*1.015, y*1.015) for x, y in outline], 9.34, 9.58, "cream", .04)
    prism("Flat_roof", outline, 9.56, 9.64, "stone")
    walls = [Wall("Market_front", (-4.2, -4.75), (5.4, -4.75), (0, -1)),
             Wall("Market_left", (-5.4, 4.75), (-5.4, -3.55), (-1, 0)),
             Wall("Market_rear", (5.4, 4.75), (-5.4, 4.75), (0, 1)),
             Wall("Market_right", (5.4, -4.75), (5.4, 4.75), (1, 0)),
             Wall("Market_corner", (-5.4, -3.55), (-4.2, -4.75), (-1, -1))]
    for wall in walls:
        if wall.name.endswith("corner"):
            wall.row(.14, 3.04, [(wall.length/2, 1.27, .17, 2.78, "door")], "cream")
            for low, high in ((3.22, 6.24), (6.39, 9.34)):
                wall.row(low, high, [(wall.length/2, .93, low+.65, high-.51, "window")], "coral_dark")
        elif wall.name.endswith(("front", "left")):
            storefronts = [(wall.length*.30, 2.58, .42, 2.73, "shop"),
                           (wall.length*.73, 2.58, .42, 2.73, "shop")]
            wall.row(.14, 3.04, storefronts, "cream")
            for u, width, *_ in storefronts:
                wall.awning(u, width+.46, 2.93, 1.03)
            for low, high in ((3.22, 6.24), (6.39, 9.34)):
                bays = [(wall.length*f, 1.43, low+.68, high-.5, "window") for f in (.19, .51, .82)]
                wall.row(low, high, bays, "coral")
            if wall.name.endswith("front"):
                wall.part("Store_sign_board", wall.length*.52, 3.38, 5.32, .68, "teal", .17, .19, .035)
                text("CORNER_MARKET_letters", "CORNER MARKET", wall.point(wall.length*.52, 3.38, .29), .44)
                # One broad balcony breaks the regular window rhythm.
                u = wall.length*.51
                wall.part("Upper_balcony_floor", u, 6.99, 2.14, .18, "cream", .94, .33, .026)
                for du in (-1.0, 1.0):
                    wall.part("Upper_balcony_post", u+du, 7.43, .09, .78, "teal", .11, .79)
                wall.part("Upper_balcony_rail", u, 7.83, 2.17, .10, "teal", .11, .79)
                for du in (-.65, -.32, 0, .32, .65):
                    wall.part("Upper_balcony_spindle", u+du, 7.43, .05, .72, "teal", .08, .79)
                for du in (-1.0, 1.0):
                    rod("Market_balcony_side", wall.point(u+du, 7.83, .1), wall.point(u+du, 7.83, .79), .09, "teal")
                planter("Market_balcony", wall.point(u+.64, 7.10, .36), .23, .33)
        else:
            door = [(wall.length*.5, 1.08, .16, 2.51, "door")] if wall.name.endswith("rear") else []
            wall.row(.14, 3.04, door, "cream")
            for low, high in ((3.22, 6.24), (6.39, 9.34)):
                wall.row(low, high, [(wall.length*f, 1.34, low+.68, high-.51, "window") for f in (.23, .55, .82)], "coral")
        # A broad base strip makes the building feel planted in the street.
        wall.part("Plinth", wall.length/2, .30, wall.length, .28, "stone", .19, .015)
    parapet("Market_roof_parapet", outline, 9.63, height=.47)
    box("Market_roof_access", (2.5, 1.5, 10.17), (2.8, 2.6, 1.08), "coral_dark", .06)
    box("Market_roof_access_cap", (2.5, 1.5, 10.76), (3.05, 2.85, .17), "roof", .045)
    box("Roof_access_door", (2.5, .18, 10.12), (.90, .045, .89), "teal", .025)
    ac_unit("Market_roof_AC", (-2.0, 2.2, 9.65))
    for x in (-3.7, -2.9):
        planter("Market_roof_garden", (x, -2.6, 9.66), .34, .45)
    # A rainpipe and external vent finish the otherwise simpler service facade.
    rod("Market_downpipe", (5.49, 3.9, .3), (5.49, 3.9, 9.34), .10, "coral_dark")
    box("Market_service_vent", (3.92, 4.79, 2.1), (1.03, .09, .55), "metal", .025)
    for h in (-.16, 0, .16):
        box("Market_service_vent_slat", (3.92, 4.847, 2.1+h), (.88, .04, .055), "ink")
    planter("Market_entry_left", (-5.87, -3.05, .14), .40, .60)
    planter("Market_entry_right", (-3.63, -5.31, .14), .40, .60)
    # Compact pavement board, readable only at close range.
    box("Market_street_board_frame", (.7, -6.04, .86), (.83, .13, 1.32), "cream", .045)
    box("Market_street_board_face", (.7, -6.12, .90), (.68, .02, 1.08), "teal")
    text("Market_street_board", "OPEN", (.7, -6.145, 1.01), .23)
    for x in (.38, 1.02):
        rod("Market_board_leg", (x, -6.02, .12), (x, -5.65, .9), .055, "stone")


def terrace_apartments():
    outline = [(-4.6, -4.5), (4.6, -4.5), (4.6, 4.5), (-4.6, 4.5)]
    prism("Apartment_foundation", outline, 0, .16, "stone", .05)
    walls = [Wall("Apartment_front", (-4.6, -4.5), (2.7, -4.5), (0, -1)),
             Wall("Apartment_left", (-4.6, 4.5), (-4.6, -4.5), (-1, 0)),
             Wall("Apartment_rear", (4.6, 4.5), (-4.6, 4.5), (0, 1)),
             Wall("Apartment_right", (4.6, -4.5), (4.6, 4.5), (1, 0))]
    for wall in walls:
        for floor in range(4):
            low = .16+floor*3.05
            high = low+2.91
            if floor == 0 and wall.name.endswith("front"):
                openings = [(wall.length*.27, 1.7, .22, 2.7, "lobby"),
                            (wall.length*.74, 2.0, .86, 2.50, "window")]
            else:
                openings = [(wall.length*f, 1.65, low+.46, high-.38, "window") for f in (.24, .73)]
            wall.row(low, high, openings, "mint" if not wall.name.endswith("right") else "cream")
            wall.part("Floor_band", wall.length/2, high+.07, wall.length+.12, .14, "cream", .49, -.10)
            if floor > 0 and wall.name.endswith("front"):
                u = wall.length*(.24 if floor % 2 else .73)
                wall.balcony(u, low+.46, 2.48, 1.04, True)
                # The other bay has a smaller Juliet rail; a different silhouette.
                u2 = wall.length*(.73 if floor % 2 else .24)
                wall.part("Juliet_bottom", u2, low+.52, 1.95, .15, "cream", .26, .08)
                wall.part("Juliet_rail", u2, low+1.43, 1.96, .09, "ink", .09, .20)
                for offset in (-.84, -.42, 0, .42, .84):
                    wall.part("Juliet_spindle", u2+offset, low+.99, .055, .88, "ink", .06, .20)
            if floor == 2 and wall.name.endswith("left"):
                wall.balcony(wall.length*.73, low+.46, 2.6, .9, True)
        wall.part("Plinth", wall.length/2, .31, wall.length, .28, "stone", .18, .01)
    stair = Wall("Apartment_stair_front", (2.7, -4.5), (4.6, -4.5), (0, -1))
    stair.row(.16, 13.1, [(stair.length/2, .74, .55, 12.7, "window")], "coral_dark")
    for z in (3.05, 6.10, 9.15, 12.1):
        stair.part("Stair_window_crossbar", stair.length/2, z, .74, .13, "cream", .12, -.08)
    box("Stair_tower_cap", (3.66, -.85, 13.16), (2.13, 7.52, .21), "cream", .035)
    box("Stair_tower_roof", (3.66, -.80, 12.70), (1.89, 7.40, .70), "coral_dark")
    prism("Apartment_roof_deck", outline, 12.22, 12.39, "stone", .03)
    parapet("Apartment_roof_parapet", outline, 12.39, height=.45)
    # Setback upper room makes a genuinely stepped roofline.
    box("Apartment_penthouse_rear", (-.8, 3.66, 13.25), (5.7, .38, 1.7), "mint_dark", .035)
    for x in (-3.46, 1.86):
        box("Apartment_penthouse_side", (x, 2.15, 13.25), (.38, 3.4, 1.7), "mint_dark", .035)
    box("Apartment_penthouse_cap", (-.8, 2.15, 14.17), (5.94, 3.65, .20), "cream", .04)
    roof_front = Wall("Apartment_roof_room", (-3.65, .45), (2.05, .45), (0, -1))
    roof_front.row(12.4, 14.1, [(1.45, 1.67, 12.63, 13.77, "window"),
                              (4.05, 1.67, 12.63, 13.77, "window")], "mint_dark")
    # Roof terrace pergola: a few thick slats, legible in a jump camera.
    for x in (-3.6, -.9):
        for y in (-3.2, -.45):
            box("Terrace_pergola_post", (x, y, 13.31), (.13, .13, 1.85), "cream", .015)
    for x in (-3.6, -.9):
        box("Terrace_pergola_beam", (x, -1.82, 14.30), (.19, 3.18, .18), "cream", .015)
    for y in (-3.05, -2.4, -1.75, -1.1, -.45):
        box("Terrace_pergola_slat", (-2.25, y, 14.43), (3.0, .23, .12), "roof", .018)
    for x, y in ((1.72, -3.0), (1.72, -1.55), (-3.6, 3.65)):
        planter("Terrace_garden", (x, y, 12.43), .39, .55)
    box("Lobby_canopy", (-2.64, -5.06, 2.87), (2.56, 1.26, .19), "roof", .045)
    text("Apartment_number", "24", (3.66, -4.72, 2.05), .53)
    box("Apartment_entry_step", (-2.64, -4.95, .12), (2.24, .89, .24), "cream", .04)
    planter("Apartment_front_planter", (-.33, -5.08, .16), .35, .53)
    ac_unit("Apartment_roof_AC", (.20, 2.75, 14.29), (1.05, .7, .62))
    rod("Apartment_rear_rainpipe", (3.95, 4.59, .32), (3.95, 4.59, 12.15), .10, "mint_dark")


def auto_garage():
    # Wide footprint, real open bays, and three crisp sawtooth roof volumes.
    outline = [(-6.9, -4.5), (6.9, -4.5), (6.9, 4.5), (-6.9, 4.5)]
    prism("Garage_floor", outline, 0, .13, "stone", .04)
    rear = Wall("Garage_rear", (6.9, 4.5), (-6.9, 4.5), (0, 1))
    rear.row(.13, 4.91, [(3.1, 2.6, 2.37, 3.41, "window"),
                        (10.6, 2.6, 2.37, 3.41, "window")], "yellow")
    office_wall = Wall("Garage_office_side", (-6.9, 4.5), (-6.9, -4.5), (-1, 0))
    office_wall.row(.13, 4.91, [(2.2, 2.13, 1.48, 2.86, "window"),
                        (6.38, 1.10, .19, 2.73, "door")], "yellow")
    box("Garage_right_wall", (6.71, 0, 2.52), (.38, 9.0, 4.78), "yellow", .045)
    centers = (-4.6, 0, 4.6)
    for x in (-6.64, -2.3, 2.3, 6.64):
        box("Garage_front_pier", (x, -4.31, 1.94), (.55, .38, 3.62), "cream", .025)
        box("Garage_pier_foot", (x, -4.43, .49), (.66, .60, .74), "stone", .03)
    box("Garage_header", (0, -4.31, 4.28), (13.8, .42, 1.06), "yellow", .035)
    box("Garage_cream_belt", (0, -4.57, 3.84), (14.01, .15, .17), "cream", .02)
    for idx, x in enumerate(centers):
        # Reveal the bay thickness with jambs and a dark inner lintel.
        for side in (-1, 1):
            box("Garage_bay_reveal", (x+side*1.83, -4.1, 1.92), (.16, .68, 3.60), "ink")
        box("Garage_bay_inner_lintel", (x, -4.07, 3.62), (3.8, .66, .18), "ink")
        if idx == 2:
            box("Garage_closed_shutter", (x, -4.05, 1.89), (3.57, .15, 3.50), "roof", .025)
            for z in (.40, .91, 1.42, 1.93, 2.44, 2.95, 3.46):
                box("Garage_shutter_slat", (x, -4.16, z), (3.48, .08, .085), "reflection")
            box("Garage_shutter_handle", (x, -4.225, .87), (.46, .07, .095), "cream", .014)
        else:
            box("Garage_open_bay_floor", (x, 0, .14), (3.59, 8.3, .024), "roof")
            for side in (-1, 1):
                box("Garage_lift_rail", (x+side*.84, .8, .24), (.18, 4.9, .22), "yellow_dark", .02)
                box("Garage_lift_column", (x+side*1.35, 1.18, 1.33), (.23, .29, 2.45), "teal", .025)
                box("Garage_lift_arm", (x+side*.98, 1.18, .7), (.90, .19, .15), "teal", .02)
            box("Garage_tool_cabinet", (x, 3.79, .76), (2.07, .69, 1.28), "teal", .055)
            box("Garage_worktop", (x, 3.76, 1.45), (2.21, .79, .12), "cream", .025)
            for z in (.43, .78, 1.12):
                box("Garage_cabinet_drawer", (x, 3.425, z), (1.85, .025, .04), "cream")
            box("Garage_ceiling_light", (x, 0, 4.69), (2.01, .36, .1), "cream", .015)
        text("Garage_bay_number", f"0{idx+1}", (x, -4.565, 4.33), .43, "ink")
    # Roof peaks repeat across width; rising slopes, blue vertical clerestories.
    for i in range(3):
        left, right = -6.9+i*4.6, -6.9+(i+1)*4.6
        front, rear = -4.5, 4.5
        low, high = 4.86, 6.45
        verts = [(left, front, low), (right, front, high), (right, rear, high), (left, rear, low),
                 (left, front, low+.16), (right, front, high+.16), (right, rear, high+.16), (left, rear, low+.16)]
        mesh("Garage_sawtooth_roof", verts, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], "roof")
        mesh("Garage_front_roof_gable", [(left, front, low), (right, front, low), (right, front, high)], [(0, 1, 2)], "yellow")
        mesh("Garage_rear_roof_gable", [(left, rear, low), (right, rear, low), (right, rear, high)], [(2, 1, 0)], "yellow")
        # A thick front/rear fascia reveals the zigzag even at street height.
        for y in (front-.07, rear+.07):
            rod("Garage_sloping_cream_fascia", (left-.08, y, low+.15), (right+.08, y, high+.15), .16, "cream")
        for y in (-3, 0, 3):
            box("Garage_clerestory_glass", (right-.065, y, 5.69), (.12, 2.76, 1.40), "glass")
            box("Garage_clerestory_reflection", (right+.001, y-.15, 5.95), (.008, 2.2, .28), "reflection")
        for y in (-4.42, -1.5, 1.5, 4.42):
            box("Garage_clerestory_mullion", (right, y, 5.70), (.16, .13, 1.59), "cream")
        box("Garage_clerestory_bottom", (right, 0, 4.96), (.18, 9, .13), "cream")
        box("Garage_clerestory_top", (right, 0, 6.45), (.18, 9, .12), "cream")
    # Side office windows and a service door face the neighboring street.
    office_wall.awning(2.2, 2.51, 3.11, .68)
    box("Garage_front_sign", (0, -4.75, 5.08), (6.20, .18, .83), "teal", .045)
    text("REDLINE_AUTO_letters", "REDLINE AUTO", (0, -4.858, 5.08), .56)
    # A low roadside pylon echoes the angled roof without adding neon.
    box("Garage_sign_post", (-6.05, -5.62, 1.4), (.18, .18, 2.8), "teal", .02)
    box("Garage_pylon_sign", (-6.05, -5.62, 3.01), (1.54, .18, 1.22), "teal", .065)
    text("Garage_pylon_AUTO", "AUTO", (-6.05, -5.725, 3.23), .36)
    text("Garage_pylon_24", "24 H", (-6.05, -5.725, 2.78), .27)
    for x in (-2.31, 2.31, 6.56):
        cylinder("Garage_bollard", (x, -5.07, .44), .115, .88, "yellow_dark")
        cylinder("Garage_bollard_cap", (x, -5.07, .89), .13, .08, "cream")
    # Thick spare tires and a small bench, all part of the exported asset.
    for z in (.27, .55, .83):
        bpy.ops.mesh.primitive_torus_add(major_segments=12, minor_segments=4, location=(6.05, -5.32, z),
                                       major_radius=.28, minor_radius=.13)
        obj = bpy.context.object
        obj.name = "Garage_spare_tire"
        relink(obj)
        obj.data.materials.append(materials["ink"])
    rod("Garage_rear_downpipe", (-6.96, 3.65, .13), (-6.96, 3.65, 4.81), .10, "yellow_dark")


def save_model(slug, name, description, author):
    reset_scene(name)
    author()
    bpy.context.view_layer.update()
    parts = [o for o in collection.objects if o.type == "MESH"]
    for obj in parts:
        for polygon in obj.data.polygons:
            polygon.use_smooth = False
    # Preserve editable source. Export joins copies to one static runtime mesh.
    bpy.ops.object.select_all(action="DESELECT")
    copies = []
    for original in parts:
        duplicate = original.copy()
        duplicate.data = original.data.copy()
        collection.objects.link(duplicate)
        duplicate.select_set(True)
        copies.append(duplicate)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    merged = bpy.context.object
    merged.name = name+"_StaticMesh"
    # Bake object transform and set the export object's origin to ground center.
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    triangles = sum(len(p.vertices)-2 for p in merged.data.polygons)
    coordinates = [merged.matrix_world @ v.co for v in merged.data.vertices]
    bounds = {"min": [round(min(v[i] for v in coordinates), 4) for i in range(3)],
              "max": [round(max(v[i] for v in coordinates), 4) for i in range(3)]}
    used_materials = sorted({merged.data.materials[p.material_index].name for p in merged.data.polygons})
    root.select_set(True)
    root["building_id"] = slug
    root["description"] = description
    path = ASSET / (slug+".glb")
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                             export_yup=True, export_apply=True, export_extras=True,
                             export_cameras=False, export_lights=False)
    bpy.data.objects.remove(merged, do_unlink=True)
    # A neutral studio is handy when editing the .blend; it is excluded from GLB.
    studio = bpy.data.collections.new("STUDIO — excluded from GLB")
    bpy.context.scene.collection.children.link(studio)
    bpy.ops.object.camera_add(location=(-18, -23, 17))
    camera = bpy.context.object
    camera.name = "StudioCamera"
    for col in list(camera.users_collection):
        col.objects.unlink(camera)
    studio.objects.link(camera)
    camera.rotation_euler = (Vector((0, 0, bounds["max"][2]*.43))-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 24
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(-12, -16, 23))
    lamp = bpy.context.object
    for col in list(lamp.users_collection):
        col.objects.unlink(lamp)
    studio.objects.link(lamp)
    lamp.name = "StudioKey"
    lamp.rotation_euler = (Vector((0, 0, 4))-lamp.location).to_track_quat("-Z", "Y").to_euler()
    lamp.data.energy = 2000
    lamp.data.shape = "DISK"
    lamp.data.size = 10
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.world.color = (.35, .42, .48)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_distance = 24
                area.spaces.active.region_3d.view_location = (0, 0, 5)
                area.spaces.active.shading.type = "MATERIAL"
    source_path = SOURCE / (slug+".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(source_path))
    return {"id": slug, "name": name, "description": description, "glb": path.name,
            "source": "source/"+source_path.name, "triangles": triangles, "runtime_meshes": 1,
            "editable_mesh_parts": len(parts), "materials": used_materials,
            "blender_bounds_m": bounds, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


if __name__ == "__main__":
    entries = [save_model("corner_market", "CornerMarket", "Coral three-story corner market with a chamfered entrance, striped awnings, real recessed windows, and a roof garden.", corner_market),
               save_model("terrace_apartments", "TerraceApartments", "Mint four-story apartments with alternating deep balconies, a coral stair tower, a setback roof room, and a pergola terrace.", terrace_apartments),
               save_model("redline_garage", "RedlineGarage", "Butter-yellow three-bay auto garage with a triple sawtooth roof, clerestory glass, two open service bays, and one closed shutter.", auto_garage)]
    (ASSET / "manifest.json").write_text(json.dumps({"units": "meters", "godot_front": "+Z", "origin": "ground center",
        "palette_srgb": PALETTE, "models": entries}, indent=2)+"\n")
    for entry in entries:
        print("BUILDING_BUILT", entry["id"], entry["triangles"], "triangles", entry["editable_mesh_parts"], "parts")
