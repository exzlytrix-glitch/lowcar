class_name CellBuilder
extends CityBuilder
## One cell of the infinite city (WorldGen) for WorldStreamer: the usual CityBuilder city without its
## own land (the streamer lays one endless ground), and lane paint only on the roads this cell owns.
## Main roads are shared by two cells, so each is painted once; paint stops short of junctions the
## neighbouring cells complete (trim_extra adds their roads to the junction's count and width).

## Per edge of the cell's graph: 1 = paint it here (WorldGen.cell_roads "owned").
var owned := PackedByteArray()
## Node → [extra roads meeting there from neighbouring cells, the widest of them].
var trim_extra: Dictionary = {}
## Buildings touching these polygons are left out (WorldStreamer.clear_areas).
var clear_areas: Array[PackedVector2Array] = []


func build(config: CityGenSettings, road_graph: RoadGraph, road_generator: RoadGenerator, city_blocks: Array[CityBlocks.Block]) -> void:
	super.build(config, road_graph, road_generator, city_blocks)
	_clear_areas()
	_merge_bodies()


func _clear_areas() -> void:
	if clear_areas.is_empty():
		return
	for tile_root: Node in get_children():
		for child: Node in tile_root.get_children():
			var building := child as Node3D
			if building == null or not building.has_meta("local_bounds"):
				continue
			var bounds: AABB = building.get_meta("local_bounds")
			var outline := PackedVector2Array()
			for corner: Vector3 in [bounds.position, Vector3(bounds.end.x, 0.0, bounds.position.z), bounds.end, Vector3(bounds.position.x, 0.0, bounds.end.z)]:
				var at: Vector3 = building.transform * Vector3(corner.x, 0.0, corner.z)
				outline.append(Vector2(at.x, at.z))
			for area: PackedVector2Array in clear_areas:
				if not Geometry2D.intersect_polygons(outline, area).is_empty():
					tile_root.remove_child(building)
					building.free()
					building_count -= 1
					break


func _build_land() -> void:
	pass


## One collision body per tile instead of one per building: with a city's worth of cells loaded, a body
## per building runs past the physics engine's body limit. Runs before the cell enters the scene tree.
func _merge_bodies() -> void:
	for tile_root: Node in get_children():
		var merged: StaticBody3D = null
		for found: Node in tile_root.find_children("*", "StaticBody3D", true, false):
			var body := found as StaticBody3D
			if body.get_script() != null or body.collision_layer != 1 or body.physics_material_override != null:
				continue
			if merged == null:
				merged = StaticBody3D.new()
				merged.name = "Solid"
				merged.collision_layer = 1
				merged.collision_mask = 0
			var base: Transform3D = _relative_transform(body, tile_root)
			for child: Node in body.get_children():
				var holder := child as CollisionShape3D
				if holder == null or holder.disabled or holder.shape == null:
					continue
				var copy := CollisionShape3D.new()
				copy.shape = holder.shape
				copy.transform = base * holder.transform
				merged.add_child(copy)
			body.get_parent().remove_child(body)
			body.free()
		if merged != null:
			tile_root.add_child(merged)


## Transform of `node` relative to `ancestor`, without the scene tree (the cell is built outside it).
static func _relative_transform(node: Node3D, ancestor: Node) -> Transform3D:
	var result: Transform3D = node.transform
	var parent: Node = node.get_parent()
	while parent != null and parent != ancestor:
		if parent is Node3D:
			result = (parent as Node3D).transform * result
		parent = parent.get_parent()
	return result


func _build_markings() -> void:
	for id: int in graph.alive_edges():
		if id < owned.size() and owned[id] == 0:
			continue
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


func _trim(node: int) -> float:
	var extra: Array = trim_extra.get(node, [0, 0.0])
	var degree: int = graph.degree(node) + int(extra[0])
	if degree == 2:
		return 0.0
	if degree == 1:
		return 1.5
	var widest: float = extra[1]
	for id: int in graph.node_edges[node]:
		widest = maxf(widest, graph.edge_width[id])
	return widest * 0.5 + settings.corner_radius + 1.0
