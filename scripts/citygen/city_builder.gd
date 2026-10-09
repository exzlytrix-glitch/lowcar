class_name CityBuilder
extends Node3D
## Turns a generated layout into the drivable city: asphalt, curbed sidewalks the car can bump
## up onto, lot ground, lane paint, buildings from the Lowcar kit, and street trees.
## Ground, paint, collision and trees are batched per tile so the whole city stays cheap to draw.

const TILE: float = 240.0
const OUTSKIRTS: float = 2600.0
const SIDEWALK := Color("#E8E2D4")
const CURB := Color("#D3CCBC")
const ROAD := Color("#7B848E")
const GRASS := Color("#B3D39F")
const PAINT := Color("#F7F1E6")
const CENTER_PAINT := Color("#F2C46B")
const PARK := Color("#A8CF93")
const TRUNK := Color("#8C6E57")
const LOT_COLORS: Array[Color] = [Color("#E3CDB2"), Color("#D3CCC1"), Color("#BCD8A4"), Color("#C9C4BB")]
const LEAVES: Array[Color] = [Color("#8FBF7A"), Color("#A3C98A"), Color("#7FB38A"), Color("#B5D38E")]
## Building mix per district style: old town, grid, residential, industrial.
const CATEGORY_WEIGHTS: Array[Dictionary] = [
	{"shop": 0.55, "home": 0.45},
	{"office": 0.5, "shop": 0.25, "home": 0.25},
	{"home": 0.85, "shop": 0.15},
	{"industrial": 0.8, "shop": 0.1, "office": 0.1},
]
const SETBACK: Array[Vector2] = [Vector2(0.0, 0.3), Vector2(0.0, 0.8), Vector2(2.5, 5.5), Vector2(1.5, 4.0)]
const GAP: Array[Vector2] = [Vector2(0.0, 0.4), Vector2(0.0, 1.5), Vector2(2.5, 6.0), Vector2(3.0, 9.0)]
const STREET_TREE_CHANCE: PackedFloat32Array = [0.35, 0.9, 1.0, 0.3]
const LOT_LIFT: float = 0.06
## Rows of buildings per block (old town, grid, residential, industrial) and how deep each row is.
const ROWS: PackedInt32Array = [4, 3, 1, 2]
const ROW_DEPTH: float = 15.0


class Tile:
	var ground := SurfaceTool.new()
	var paint := SurfaceTool.new()
	var faces := PackedVector3Array()
	var has_ground: bool = false
	var has_paint: bool = false
	var root: Node3D
	var trees: Array = []


var settings: CityGenSettings
var graph: RoadGraph
var generator: RoadGenerator
var blocks: Array[CityBlocks.Block] = []
var footprints: Array[PackedVector2Array] = []
var footprint_styles := PackedInt32Array()
## Training city: collision only (floor, curbs, building boxes). No meshes, paint or trees.
var collision_only: bool = false
var building_count: int = 0
var tree_count: int = 0
var _rng := RandomNumberGenerator.new()
var _material: StandardMaterial3D
var _tiles: Dictionary = {}
var _catalog: Dictionary = {}
static var _stand_ins: Dictionary = {}
static var _trunk_mesh: CylinderMesh
static var _leaf_mesh: SphereMesh


static func category_of(id: String) -> String:
	for word: String in ["warehouse", "factory", "workshop", "garage", "wholesaler", "storehouse", "sorting", "superstore", "showroom"]:
		if id.contains(word):
			return "industrial"
	for word: String in ["office", "studio", "tower", "civic", "bank", "clinic", "department", "mixed_use"]:
		if id.contains(word):
			return "office"
	if id == "tea_house":
		return "shop"
	for word: String in ["house", "home", "apartments", "bungalow", "duplex", "walkup", "semi_detached"]:
		if id.contains(word):
			return "home"
	return "shop"


func build(config: CityGenSettings, road_graph: RoadGraph, road_generator: RoadGenerator, city_blocks: Array[CityBlocks.Block]) -> void:
	settings = config
	graph = road_graph
	generator = road_generator
	blocks = city_blocks
	_rng.seed = config.city_seed * 7919 + 3
	_material = StandardMaterial3D.new()
	_material.vertex_color_use_as_albedo = true
	_material.roughness = 0.92
	_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	_sort_catalog()
	_build_land()
	for block: CityBlocks.Block in blocks:
		_build_block(block)
	if not collision_only:
		_build_markings()
	_commit_tiles()


# --- land, curbs and paint -------------------------------------------------

func _build_land() -> void:
	var land := SurfaceTool.new()
	land.begin(Mesh.PRIMITIVE_TRIANGLES)
	var margin: float = settings.arterial_width * 0.5 + 6.0 if settings.ring_road else 4.0
	var count: int = generator.boundary.size()
	var edge := PackedVector2Array()
	for point: Vector2 in generator.boundary:
		edge.append(point.normalized() * (point.length() + margin))
	for index: int in count:
		var a: Vector2 = edge[index]
		var b: Vector2 = edge[(index + 1) % count]
		_triangle(land, Vector3.ZERO, _v3(a, 0.0), _v3(b, 0.0), Vector3.UP, ROAD)
		var far_a: Vector2 = a.normalized() * OUTSKIRTS
		var far_b: Vector2 = b.normalized() * OUTSKIRTS
		_triangle(land, _v3(a, 0.0), _v3(far_a, 0.0), _v3(far_b, 0.0), Vector3.UP, GRASS)
		_triangle(land, _v3(a, 0.0), _v3(far_b, 0.0), _v3(b, 0.0), Vector3.UP, GRASS)
	if not collision_only:
		var visual := MeshInstance3D.new()
		visual.name = "Land"
		visual.mesh = land.commit()
		visual.material_override = _material
		visual.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(visual)
	var floor_body := StaticBody3D.new()
	floor_body.name = "Floor"
	floor_body.collision_layer = 1
	floor_body.collision_mask = 0
	var shape := BoxShape3D.new()
	shape.size = Vector3(OUTSKIRTS * 2.0, 1.0, OUTSKIRTS * 2.0)
	var collision := CollisionShape3D.new()
	collision.shape = shape
	collision.position.y = -0.5
	floor_body.add_child(collision)
	add_child(floor_body)


func _build_block(block: CityBlocks.Block) -> void:
	var tile: Tile = _tile_for(block.centroid)
	var height: float = settings.curb_height
	var lot_color: Color = PARK if block.park else LOT_COLORS[block.style]
	if not _add_block_surface(tile, block, height, lot_color):
		# Fallback for awkward shapes: full sidewalk top with the lots laid just above it.
		_add_curb(tile, block.curb, height)
		for ground: PackedVector2Array in block.ground:
			_add_flat(tile, ground, height + LOT_LIFT, lot_color)
	var placed: Array[PackedVector2Array] = []
	if collision_only:
		if not block.park:
			placed = _place_buildings(tile, block)
		for footprint: PackedVector2Array in placed:
			footprints.append(footprint)
			footprint_styles.append(block.style)
		return
	if block.park:
		_plant_park(tile, block)
	else:
		placed = _place_buildings(tile, block)
		if block.style == RoadGenerator.Style.RESIDENTIAL:
			_plant_yards(tile, block, placed)
	_plant_street_trees(tile, block)
	for footprint: PackedVector2Array in placed:
		footprints.append(footprint)
		footprint_styles.append(block.style)


## Ramp, sidewalk ring and lot as one level surface with no overlapping layers (no distant flicker).
## Works when the block has one simple inner area; returns false so the caller can fall back.
func _add_block_surface(tile: Tile, block: CityBlocks.Block, height: float, lot_color: Color) -> bool:
	if block.ground.size() != 1:
		return false
	var curb: PackedVector2Array = block.curb
	var top: PackedVector2Array = _inset(curb, settings.curb_ramp)
	var inner: PackedVector2Array = _inset(curb, settings.sidewalk_width)
	var expected: float = CityBlocks.signed_area(block.ground[0])
	if absf(CityBlocks.signed_area(inner) - expected) > expected * 0.06:
		return false
	var lot: PackedInt32Array = Geometry2D.triangulate_polygon(inner)
	if lot.is_empty():
		return false
	tile.has_ground = true
	for index: int in curb.size():
		var next: int = (index + 1) % curb.size()
		var b0: Vector3 = _v3(curb[index], 0.005)
		var b1: Vector3 = _v3(curb[next], 0.005)
		var t0: Vector3 = _v3(top[index], height)
		var t1: Vector3 = _v3(top[next], height)
		var i0: Vector3 = _v3(inner[index], height)
		var i1: Vector3 = _v3(inner[next], height)
		var normal: Vector3 = (b1 - b0).cross(t0 - b0).normalized()
		if normal.y < 0.0:
			normal = -normal
		_triangle(tile.ground, b0, b1, t1, normal, CURB)
		_triangle(tile.ground, b0, t1, t0, normal, CURB)
		_triangle(tile.ground, t0, t1, i1, Vector3.UP, SIDEWALK)
		_triangle(tile.ground, t0, i1, i0, Vector3.UP, SIDEWALK)
		var c0: Vector3 = _sunk(curb[index], top[index], height)
		var c1: Vector3 = _sunk(curb[next], top[next], height)
		tile.faces.append_array(PackedVector3Array([c0, c1, t1, c0, t1, t0, t0, t1, i1, t0, i1, i0]))
	for index: int in range(0, lot.size(), 3):
		var a: Vector3 = _v3(inner[lot[index]], height)
		var b: Vector3 = _v3(inner[lot[index + 1]], height)
		var c: Vector3 = _v3(inner[lot[index + 2]], height)
		_triangle(tile.ground, a, b, c, Vector3.UP, lot_color)
		tile.faces.append_array(PackedVector3Array([a, b, c]))
	return true


## Sidewalk top plus a shallow ramp down to the road, so curbs are climbable instead of walls.
func _add_curb(tile: Tile, curb: PackedVector2Array, height: float) -> void:
	var top: PackedVector2Array = _inset(curb, settings.curb_ramp)
	var indices: PackedInt32Array = Geometry2D.triangulate_polygon(top)
	var ramp: bool = true
	if indices.is_empty():
		top = curb
		ramp = false
		indices = Geometry2D.triangulate_polygon(curb)
		if indices.is_empty():
			return
	tile.has_ground = true
	for index: int in range(0, indices.size(), 3):
		var a: Vector3 = _v3(top[indices[index]], height)
		var b: Vector3 = _v3(top[indices[index + 1]], height)
		var c: Vector3 = _v3(top[indices[index + 2]], height)
		_triangle(tile.ground, a, b, c, Vector3.UP, SIDEWALK)
		tile.faces.append_array(PackedVector3Array([a, b, c]))
	if not ramp:
		return
	for index: int in curb.size():
		var next: int = (index + 1) % curb.size()
		var b0: Vector3 = _v3(curb[index], 0.005)
		var b1: Vector3 = _v3(curb[next], 0.005)
		var t0: Vector3 = _v3(top[index], height)
		var t1: Vector3 = _v3(top[next], height)
		var normal: Vector3 = (b1 - b0).cross(t0 - b0).normalized()
		if normal.y < 0.0:
			normal = -normal
		_triangle(tile.ground, b0, b1, t1, normal, CURB)
		_triangle(tile.ground, b0, t1, t0, normal, CURB)
		var c0: Vector3 = _sunk(curb[index], top[index], height)
		var c1: Vector3 = _sunk(curb[next], top[next], height)
		tile.faces.append_array(PackedVector3Array([c0, c1, t1, c0, t1, t0]))


## Collision for the ramp continues the slope a little below the road, so there is no edge at
## tire height for a car to snag on (a snag reads as a head-on wall hit).
func _sunk(curb_point: Vector2, top_point: Vector2, height: float) -> Vector3:
	var outward: Vector2 = curb_point - top_point
	var run: float = maxf(outward.length(), 0.01)
	var depth: float = 0.1
	return _v3(curb_point + outward / run * (depth * run / height), -depth)


func _add_flat(tile: Tile, polygon: PackedVector2Array, height: float, color: Color) -> void:
	var indices: PackedInt32Array = Geometry2D.triangulate_polygon(polygon)
	for index: int in range(0, indices.size(), 3):
		_triangle(tile.ground, _v3(polygon[indices[index]], height), _v3(polygon[indices[index + 1]], height),
			_v3(polygon[indices[index + 2]], height), Vector3.UP, color)
	tile.has_ground = tile.has_ground or not indices.is_empty()


func _build_markings() -> void:
	for id: int in graph.alive_edges():
		var kind: int = graph.edge_kind[id]
		if kind == RoadGraph.Kind.LANE:
			continue
		var a: Vector2 = graph.positions[graph.edge_a[id]]
		var b: Vector2 = graph.positions[graph.edge_b[id]]
		var length: float = a.distance_to(b)
		if length < 1.0:
			continue
		var dir: Vector2 = (b - a) / length
		var side := Vector2(-dir.y, dir.x)
		var start: float = _trim(graph.edge_a[id])
		var finish: float = length - _trim(graph.edge_b[id])
		if finish - start < 3.0:
			continue
		var tile: Tile = _tile_for((a + b) * 0.5)
		if kind == RoadGraph.Kind.ARTERIAL or kind == RoadGraph.Kind.RING:
			for offset: float in [-0.2, 0.2]:
				_paint_strip(tile, a, dir, side, start, finish, offset, 0.14, CENTER_PAINT, 0.0, 0.0)
			var lane: float = graph.edge_width[id] * 0.25
			for offset: float in [-lane, lane]:
				_paint_strip(tile, a, dir, side, start, finish, offset, 0.13, PAINT, 3.0, 6.0)
		else:
			_paint_strip(tile, a, dir, side, start, finish, 0.0, 0.13, PAINT, 3.0, 5.0)


## Paint stops short of junctions so crossings stay clean.
func _trim(node: int) -> float:
	var degree: int = graph.degree(node)
	if degree == 2:
		return 0.0
	if degree == 1:
		return 1.5
	var widest: float = 0.0
	for id: int in graph.node_edges[node]:
		widest = maxf(widest, graph.edge_width[id])
	return widest * 0.5 + settings.corner_radius + 1.0


func _paint_strip(tile: Tile, origin: Vector2, dir: Vector2, side: Vector2, start: float, finish: float,
		offset: float, width: float, color: Color, dash: float, gap: float) -> void:
	var cursor: float = start
	while cursor < finish:
		var end: float = finish if dash <= 0.0 else minf(cursor + dash, finish)
		var left: Vector2 = side * (offset - width * 0.5)
		var right: Vector2 = side * (offset + width * 0.5)
		var p0: Vector3 = _v3(origin + dir * cursor + left, 0.03)
		var p1: Vector3 = _v3(origin + dir * end + left, 0.03)
		var p2: Vector3 = _v3(origin + dir * end + right, 0.03)
		var p3: Vector3 = _v3(origin + dir * cursor + right, 0.03)
		_triangle(tile.paint, p0, p1, p2, Vector3.UP, color)
		_triangle(tile.paint, p0, p2, p3, Vector3.UP, color)
		tile.has_paint = true
		if dash <= 0.0:
			break
		cursor += dash + gap


# --- buildings ---------------------------------------------------------------

func _sort_catalog() -> void:
	_catalog.clear()
	for entry: Dictionary in CityBuildingKit.catalog():
		var category: String = category_of(entry["id"])
		if not _catalog.has(category):
			_catalog[category] = []
		_catalog[category].append(entry)


## Walks each street-facing edge of the buildable ground and lines it with buildings that face the road.
## Deep blocks get more rows behind the first, so interiors fill like real back-to-back city blocks.
func _place_buildings(tile: Tile, block: CityBlocks.Block) -> Array[PackedVector2Array]:
	var placed: Array[PackedVector2Array] = []
	for ground: PackedVector2Array in block.ground:
		var rows: Array[PackedVector2Array] = [ground]
		for row: int in ROWS[block.style]:
			for outline: PackedVector2Array in rows:
				_line_edges(tile, block.style, outline, ground, placed, row > 0)
			var inner: Array[PackedVector2Array] = []
			for outline: PackedVector2Array in rows:
				inner.append_array(CityBlocks.outer(Geometry2D.offset_polygon(outline, -ROW_DEPTH, Geometry2D.JOIN_MITER)))
			rows = inner
			if rows.is_empty():
				break
	return placed


func _line_edges(tile: Tile, style: int, outline_source: PackedVector2Array, ground: PackedVector2Array,
		placed: Array[PackedVector2Array], inner_row: bool) -> void:
	var weights: Dictionary = CATEGORY_WEIGHTS[style]
	var setback: Vector2 = Vector2(0.0, 0.6) if inner_row else SETBACK[style]
	var gap: Vector2 = GAP[style]
	var outline: PackedVector2Array = _simplify(outline_source, 1.5)
	for index: int in outline.size():
		var p: Vector2 = outline[index]
		var q: Vector2 = outline[(index + 1) % outline.size()]
		var edge_length: float = p.distance_to(q)
		if edge_length < 5.0:
			continue
		var along: Vector2 = (q - p) / edge_length
		var out := Vector2(along.y, -along.x)
		var cursor: float = _rng.randf_range(0.0, 1.5)
		while cursor < edge_length - 4.0:
			if _rng.randf() > settings.building_fill:
				cursor += _rng.randf_range(4.0, 9.0)
				continue
			var done: bool = false
			for attempt: int in 4:
				var entry: Dictionary = _pick(weights, edge_length - cursor)
				if entry.is_empty():
					break
				var bounds: AABB = entry["bounds"]
				var center: Vector2 = p + along * (cursor + bounds.size.x * 0.5) - out * (_rng.randf_range(setback.x, setback.y) + bounds.size.z * 0.5)
				var theta: float = atan2(out.x, out.y)
				var footprint: PackedVector2Array = _footprint(bounds, center, theta)
				if not _fits(footprint, ground, placed):
					continue
				_spawn(tile, entry, center, theta)
				placed.append(footprint)
				cursor += bounds.size.x + _rng.randf_range(gap.x, gap.y)
				done = true
				break
			if not done:
				cursor += 2.5


func _pick(weights: Dictionary, max_width: float) -> Dictionary:
	var roll: float = _rng.randf()
	var category: String = "shop"
	for key: String in weights:
		roll -= float(weights[key])
		if roll <= 0.0:
			category = key
			break
	var options: Array = _catalog.get(category, _catalog.get("shop", []))
	if options.is_empty():
		return {}
	for attempt: int in 6:
		var entry: Dictionary = options[_rng.randi() % options.size()]
		var bounds: AABB = entry["bounds"]
		if bounds.size.x <= max_width:
			return entry
	return {}


func _fits(footprint: PackedVector2Array, ground: PackedVector2Array, placed: Array[PackedVector2Array]) -> bool:
	for corner: Vector2 in footprint:
		if not Geometry2D.is_point_in_polygon(corner, ground):
			return false
	for point: Vector2 in ground:
		if Geometry2D.is_point_in_polygon(point, footprint):
			return false
	var box: Rect2 = _rect(footprint)
	var shrunk: PackedVector2Array = _shrink(footprint, 0.3)
	for other: PackedVector2Array in placed:
		if _rect(other).intersects(box) and not Geometry2D.intersect_polygons(shrunk, other).is_empty():
			return false
	return true


func _spawn(tile: Tile, entry: Dictionary, center: Vector2, theta: float) -> void:
	var bounds: AABB = entry["bounds"]
	if collision_only:
		var body := StaticBody3D.new()
		body.collision_layer = 1
		body.collision_mask = 0
		var shape := BoxShape3D.new()
		shape.size = bounds.size
		var holder := CollisionShape3D.new()
		holder.shape = shape
		body.add_child(holder)
		body.position = _v3(center, settings.curb_height + bounds.size.y * 0.5)
		body.rotation.y = theta
		tile.root.add_child(body)
		building_count += 1
		return
	var local_center := Vector2(bounds.get_center().x, bounds.get_center().z)
	var origin: Vector2 = center - _rotate(local_center, theta)
	var building: Node3D = CityBuildingKit.instantiate(entry)
	building.position = _v3(origin, settings.curb_height + LOT_LIFT)
	building.rotation.y = theta
	tile.root.add_child(building)
	# Full model up close; a two-colour block in the distance, drawn in one call instead of ~9.
	for visual: Node in building.find_children("*", "GeometryInstance3D", true, false):
		(visual as GeometryInstance3D).visibility_range_end = settings.detail_distance
		(visual as GeometryInstance3D).visibility_range_end_margin = 8.0
	var stand_in := MeshInstance3D.new()
	stand_in.name = "Distant"
	stand_in.mesh = _stand_in_mesh(entry)
	stand_in.material_override = _material
	stand_in.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	stand_in.visibility_range_begin = settings.detail_distance
	stand_in.visibility_range_begin_margin = 8.0
	stand_in.visibility_range_end = settings.view_distance
	building.add_child(stand_in)
	building_count += 1


## Box of the model's footprint and height, coloured with its own dominant wall and roof colours.
static func _stand_in_mesh(entry: Dictionary) -> ArrayMesh:
	var id: String = entry["id"]
	if _stand_ins.has(id):
		return _stand_ins[id]
	var bounds: AABB = entry["bounds"]
	var colors: Array[Color] = _model_colors(entry)
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var low: Vector3 = bounds.position
	var high: Vector3 = bounds.end
	var corners: Array[Vector3] = [Vector3(low.x, 0.0, low.z), Vector3(high.x, 0.0, low.z), Vector3(high.x, 0.0, high.z), Vector3(low.x, 0.0, high.z)]
	for index: int in 4:
		var a: Vector3 = corners[index]
		var b: Vector3 = corners[(index + 1) % 4]
		var normal: Vector3 = (b - a).cross(Vector3.UP).normalized()
		var top_a := Vector3(a.x, high.y, a.z)
		var top_b := Vector3(b.x, high.y, b.z)
		for vertex: Vector3 in [a, b, top_b, a, top_b, top_a]:
			surface.set_color(colors[0])
			surface.set_normal(normal)
			surface.add_vertex(vertex)
	for vertex: Vector3 in [corners[0], corners[1], corners[2], corners[0], corners[2], corners[3]]:
		surface.set_color(colors[1])
		surface.set_normal(Vector3.UP)
		surface.add_vertex(Vector3(vertex.x, high.y, vertex.z))
	var mesh: ArrayMesh = surface.commit()
	_stand_ins[id] = mesh
	return mesh


## Area-weighted colours of the model's walls (sideways faces) and roof (upward faces), in linear space.
static func _model_colors(entry: Dictionary) -> Array[Color]:
	var model: Node3D = CityBuildingKit.instantiate(entry)
	var wall := Vector4.ZERO
	var roof := Vector4.ZERO
	for visual: Node in model.find_children("*", "MeshInstance3D", true, false):
		var instance := visual as MeshInstance3D
		for surface_index: int in instance.mesh.get_surface_count():
			var material := instance.get_active_material(surface_index) as StandardMaterial3D
			if material == null:
				continue
			var tint: Color = material.albedo_color.srgb_to_linear()
			var arrays: Array = instance.mesh.surface_get_arrays(surface_index)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			var triangle_count: int = indices.size() / 3 if not indices.is_empty() else vertices.size() / 3
			for triangle: int in range(0, triangle_count, 2):
				var a: Vector3
				var b: Vector3
				var c: Vector3
				if indices.is_empty():
					a = vertices[triangle * 3]
					b = vertices[triangle * 3 + 1]
					c = vertices[triangle * 3 + 2]
				else:
					a = vertices[indices[triangle * 3]]
					b = vertices[indices[triangle * 3 + 1]]
					c = vertices[indices[triangle * 3 + 2]]
				var cross: Vector3 = (b - a).cross(c - a)
				var area: float = cross.length()
				if area < 0.0001:
					continue
				var upward: float = absf(cross.y) / area
				var weighted := Vector4(tint.r, tint.g, tint.b, 1.0) * area
				if upward > 0.7:
					roof += weighted
				elif upward < 0.4:
					wall += weighted
	model.free()
	# Windows and trim darken the average; lift it so distant blocks match the facades' overall read.
	var wall_color := Color(0.9, 0.85, 0.78) if wall.w <= 0.0 else Color(wall.x / wall.w, wall.y / wall.w, wall.z / wall.w).lightened(0.12)
	var roof_color := wall_color.darkened(0.25) if roof.w <= 0.0 else Color(roof.x / roof.w, roof.y / roof.w, roof.z / roof.w)
	return [wall_color, roof_color]


func _footprint(bounds: AABB, center: Vector2, theta: float) -> PackedVector2Array:
	var half := Vector2(bounds.size.x, bounds.size.z) * 0.5
	var result := PackedVector2Array()
	for corner: Vector2 in [Vector2(-half.x, -half.y), Vector2(half.x, -half.y), Vector2(half.x, half.y), Vector2(-half.x, half.y)]:
		result.append(center + _rotate(corner, theta))
	return result


# --- trees -------------------------------------------------------------------

func _plant_street_trees(tile: Tile, block: CityBlocks.Block) -> void:
	var chance: float = STREET_TREE_CHANCE[block.style]
	var outline: PackedVector2Array = _simplify(block.curb, 1.5)
	var inset: float = settings.curb_ramp + (settings.sidewalk_width - settings.curb_ramp) * 0.5
	for index: int in outline.size():
		var p: Vector2 = outline[index]
		var q: Vector2 = outline[(index + 1) % outline.size()]
		var edge_length: float = p.distance_to(q)
		var along: Vector2 = (q - p) / maxf(edge_length, 0.001)
		var inward := Vector2(-along.y, along.x)
		var cursor: float = 6.0
		while cursor < edge_length - 6.0:
			var point: Vector2 = p + along * cursor + inward * inset
			if _rng.randf() < chance and Geometry2D.is_point_in_polygon(point, block.curb):
				_add_tree(tile, point, _rng.randf_range(0.8, 1.05))
			cursor += settings.tree_spacing * _rng.randf_range(0.85, 1.15)


func _plant_park(tile: Tile, block: CityBlocks.Block) -> void:
	for ground: PackedVector2Array in block.ground:
		var box: Rect2 = _rect(ground)
		var step: float = 9.0
		var y: float = box.position.y + step * 0.5
		while y < box.end.y:
			var x: float = box.position.x + step * 0.5
			while x < box.end.x:
				var point := Vector2(x, y) + Vector2(_rng.randf_range(-3.0, 3.0), _rng.randf_range(-3.0, 3.0))
				if _rng.randf() < 0.6 and Geometry2D.is_point_in_polygon(point, ground):
					_add_tree(tile, point, _rng.randf_range(0.9, 1.4))
				x += step
			y += step


func _plant_yards(tile: Tile, block: CityBlocks.Block, placed: Array[PackedVector2Array]) -> void:
	for ground: PackedVector2Array in block.ground:
		var box: Rect2 = _rect(ground)
		var count: int = int(CityBlocks.signed_area(ground) / 420.0)
		for attempt: int in count:
			var point := Vector2(_rng.randf_range(box.position.x, box.end.x), _rng.randf_range(box.position.y, box.end.y))
			if not Geometry2D.is_point_in_polygon(point, ground):
				continue
			var clear: bool = true
			for footprint: PackedVector2Array in placed:
				if _rect(footprint).grow(2.0).has_point(point):
					clear = false
					break
			if clear:
				_add_tree(tile, point, _rng.randf_range(0.85, 1.3))


func _add_tree(tile: Tile, at: Vector2, size: float) -> void:
	var basis := Basis(Vector3.UP, _rng.randf() * TAU).scaled(Vector3.ONE * size)
	tile.trees.append([Transform3D(basis, _v3(at, settings.curb_height + LOT_LIFT)), LEAVES[_rng.randi() % LEAVES.size()]])
	tree_count += 1


# --- tiles -------------------------------------------------------------------

func _tile_for(at: Vector2) -> Tile:
	var key := Vector2i(floori(at.x / TILE), floori(at.y / TILE))
	if not _tiles.has(key):
		var tile := Tile.new()
		tile.ground.begin(Mesh.PRIMITIVE_TRIANGLES)
		tile.paint.begin(Mesh.PRIMITIVE_TRIANGLES)
		tile.root = Node3D.new()
		tile.root.name = "Tile_%d_%d" % [key.x, key.y]
		add_child(tile.root)
		_tiles[key] = tile
	return _tiles[key]


func _commit_tiles() -> void:
	for key: Vector2i in _tiles:
		var tile: Tile = _tiles[key]
		if tile.has_ground and not collision_only:
			var ground := MeshInstance3D.new()
			ground.name = "Ground"
			ground.mesh = tile.ground.commit()
			ground.material_override = _material
			tile.root.add_child(ground)
		if not tile.faces.is_empty():
			var body := StaticBody3D.new()
			body.name = "Curbs"
			body.collision_layer = 1
			body.collision_mask = 0
			var shape := ConcavePolygonShape3D.new()
			shape.backface_collision = true
			shape.set_faces(tile.faces)
			var collision := CollisionShape3D.new()
			collision.shape = shape
			body.add_child(collision)
			tile.root.add_child(body)
		if tile.has_paint and not collision_only:
			var paint := MeshInstance3D.new()
			paint.name = "Paint"
			paint.mesh = tile.paint.commit()
			paint.material_override = _material
			paint.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			paint.visibility_range_end = 320.0
			tile.root.add_child(paint)
		if not tile.trees.is_empty() and not collision_only:
			_commit_trees(tile)


func _commit_trees(tile: Tile) -> void:
	if _trunk_mesh == null:
		_trunk_mesh = CylinderMesh.new()
		_trunk_mesh.top_radius = 0.18
		_trunk_mesh.bottom_radius = 0.27
		_trunk_mesh.height = 2.6
		_trunk_mesh.radial_segments = 6
		_trunk_mesh.rings = 1
		var bark := StandardMaterial3D.new()
		bark.albedo_color = TRUNK.srgb_to_linear()
		bark.roughness = 0.9
		_trunk_mesh.material = bark
		_leaf_mesh = SphereMesh.new()
		_leaf_mesh.radius = 1.6
		_leaf_mesh.height = 2.7
		_leaf_mesh.radial_segments = 8
		_leaf_mesh.rings = 3
		var leaves := StandardMaterial3D.new()
		leaves.vertex_color_use_as_albedo = true
		leaves.roughness = 0.85
		_leaf_mesh.material = leaves
	var trunks := MultiMesh.new()
	trunks.transform_format = MultiMesh.TRANSFORM_3D
	trunks.mesh = _trunk_mesh
	trunks.instance_count = tile.trees.size()
	var crowns := MultiMesh.new()
	crowns.transform_format = MultiMesh.TRANSFORM_3D
	crowns.use_colors = true
	crowns.mesh = _leaf_mesh
	crowns.instance_count = tile.trees.size()
	for index: int in tile.trees.size():
		var base: Transform3D = tile.trees[index][0]
		trunks.set_instance_transform(index, base.translated_local(Vector3(0.0, 1.3, 0.0)))
		crowns.set_instance_transform(index, base.translated_local(Vector3(0.0, 3.1, 0.0)))
		crowns.set_instance_color(index, (tile.trees[index][1] as Color).srgb_to_linear())
	for multimesh: MultiMesh in [trunks, crowns]:
		var instance := MultiMeshInstance3D.new()
		instance.multimesh = multimesh
		instance.visibility_range_end = settings.view_distance + TILE
		tile.root.add_child(instance)


# --- geometry helpers --------------------------------------------------------

func _triangle(surface: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, normal: Vector3, color: Color) -> void:
	var linear: Color = color.srgb_to_linear()
	for vertex: Vector3 in [a, b, c]:
		surface.set_color(linear)
		surface.set_normal(normal)
		surface.add_vertex(vertex)


func _v3(at: Vector2, height: float) -> Vector3:
	return Vector3(at.x, height, at.y)


func _rotate(v: Vector2, theta: float) -> Vector2:
	return Vector2(v.x * cos(theta) + v.y * sin(theta), -v.x * sin(theta) + v.y * cos(theta))


func _rect(polygon: PackedVector2Array) -> Rect2:
	var box := Rect2(polygon[0], Vector2.ZERO)
	for point: Vector2 in polygon:
		box = box.expand(point)
	return box


func _shrink(polygon: PackedVector2Array, amount: float) -> PackedVector2Array:
	var middle := Vector2.ZERO
	for point: Vector2 in polygon:
		middle += point
	middle /= float(polygon.size())
	var result := PackedVector2Array()
	for point: Vector2 in polygon:
		result.append(point + (middle - point).normalized() * amount)
	return result


## Same-count inward offset (mitred) of a counter-clockwise polygon, so ramp quads pair up with the curb line.
func _inset(polygon: PackedVector2Array, distance: float) -> PackedVector2Array:
	var count: int = polygon.size()
	var result := PackedVector2Array()
	result.resize(count)
	for index: int in count:
		var previous: Vector2 = polygon[index - 1]
		var current: Vector2 = polygon[index]
		var next: Vector2 = polygon[(index + 1) % count]
		var e1: Vector2 = (current - previous).normalized()
		var e2: Vector2 = (next - current).normalized()
		var n1 := Vector2(-e1.y, e1.x)
		var n2 := Vector2(-e2.y, e2.x)
		var bisector: Vector2 = n1 + n2
		bisector = n1 if bisector.length() < 0.001 else bisector.normalized()
		result[index] = current + bisector * (distance / maxf(bisector.dot(n1), 0.4))
	return result


## Drops points that barely bend the outline, so street fronts become long straight runs.
func _simplify(polygon: PackedVector2Array, tolerance: float) -> PackedVector2Array:
	var result := PackedVector2Array(polygon)
	var changed: bool = true
	while changed and result.size() > 3:
		changed = false
		var index: int = 0
		while index < result.size() and result.size() > 3:
			var previous: Vector2 = result[index - 1]
			var next: Vector2 = result[(index + 1) % result.size()]
			var current: Vector2 = result[index]
			if current.distance_to(Geometry2D.get_closest_point_to_segment(current, previous, next)) < tolerance:
				result.remove_at(index)
				changed = true
			else:
				index += 1
	return result
