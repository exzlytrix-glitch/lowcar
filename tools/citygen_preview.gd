extends SceneTree
## Renders a generated road network to a top-down PNG without opening a window.
## Usage: Godot --headless --path . --script res://tools/citygen_preview.gd -- --out=/tmp/city.png [--seed=7] [--blocks]
##   [--world=2]  draw the infinite world instead (WorldGen): the cells within 2 of the origin

const SIZE: int = 1400
const DISTRICT_TINTS: Array[Color] = [Color("#EED9C4"), Color("#DCE3EC"), Color("#D5E8C8"), Color("#DDD8D0")]
const ROAD_COLORS: Array[Color] = [Color("#5C6670"), Color("#7A848E"), Color("#9A8F86"), Color("#46505A")]


func _initialize() -> void:
	var out_path: String = "user://citygen_preview.png"
	var settings: CityGenSettings = _load_settings()
	var draw_blocks: bool = false
	var world_radius: int = -1
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with("--out="):
			out_path = argument.trim_prefix("--out=")
		elif argument.begins_with("--seed="):
			settings.city_seed = int(argument.trim_prefix("--seed="))
		elif argument == "--blocks":
			draw_blocks = true
		elif argument.begins_with("--world="):
			world_radius = int(argument.trim_prefix("--world="))
	var started: int = Time.get_ticks_msec()
	var generator: RoadGenerator
	var graph: RoadGraph
	var view_size: float = settings.city_radius * 2.0 * 1.45
	var center := Vector2.ZERO
	if world_radius >= 0:
		var world_gen := WorldGen.new()
		world_gen.setup(settings)
		graph = world_gen.window(0, 0, world_radius)
		generator = world_gen
		view_size = (world_radius * 2 + 1) * WorldGen.CELL
		center = Vector2(WorldGen.CELL * 0.5, WorldGen.CELL * 0.5)
		settings.city_radius = view_size
	else:
		generator = RoadGenerator.new()
		graph = generator.generate(settings)
	var road_ms: int = Time.get_ticks_msec() - started
	var image := Image.create(SIZE, SIZE, false, Image.FORMAT_RGB8)
	var scale: float = float(SIZE) / view_size
	var half := Vector2(SIZE, SIZE) * 0.5 - center * scale
	for y: int in range(0, SIZE, 7):
		for x: int in range(0, SIZE, 7):
			var world: Vector2 = (Vector2(x, y) - half) / scale
			var tint: Color = Color("#B9D3A5")
			if world_radius >= 0 or world.length() <= generator.boundary_radius(world.angle()):
				tint = DISTRICT_TINTS[generator.style_at(world)]
			image.fill_rect(Rect2i(x, y, 7, 7), tint)
	var block_count: int = 0
	if draw_blocks:
		var blocks: Array = CityBlocks.build(graph, generator, settings)
		block_count = blocks.size()
		for block: CityBlocks.Block in blocks:
			_fill_polygon(image, block.curb, scale, half, Color("#F4EFE4"))
			for ground: PackedVector2Array in block.ground:
				_fill_polygon(image, ground, scale, half, Color("#A9CF96") if block.park else Color("#E6D3BD"))
	for id: int in graph.alive_edges():
		var a: Vector2 = graph.positions[graph.edge_a[id]] * scale + half
		var b: Vector2 = graph.positions[graph.edge_b[id]] * scale + half
		var radius: float = maxf(1.0, graph.edge_width[id] * 0.5 * scale) if not draw_blocks else 0.6
		_line(image, a, b, radius, ROAD_COLORS[graph.edge_kind[id]])
	image.save_png(out_path)
	var length: float = 0.0
	var dead_ends: int = 0
	var junctions: int = 0
	for id: int in graph.alive_edges():
		length += graph.edge_length(id)
	for node: int in graph.node_count():
		if graph.degree(node) == 1:
			dead_ends += 1
		elif graph.degree(node) >= 3:
			junctions += 1
	print("CITYGEN seed=%d roads=%d length=%.1fkm junctions=%d dead_ends=%d blocks=%d time=%dms -> %s" % [
		settings.city_seed, graph.alive_edges().size(), length / 1000.0, junctions, dead_ends, block_count,
		Time.get_ticks_msec() - started, out_path])
	print("CITYGEN road_ms=%d crossings_without_junction=%d" % [road_ms, _crossings(graph)])
	quit()


## Roads that cross without a junction (should be 0; non-zero means cells or streets overlap).
func _crossings(graph: RoadGraph) -> int:
	var count: int = 0
	for id: int in graph.alive_edges():
		var a: Vector2 = graph.positions[graph.edge_a[id]]
		var b: Vector2 = graph.positions[graph.edge_b[id]]
		for other: int in graph.edges_in(Rect2(a, Vector2.ZERO).expand(b).grow(1.0)):
			if other <= id:
				continue
			var shared: bool = graph.edge_a[other] == graph.edge_a[id] or graph.edge_a[other] == graph.edge_b[id] \
				or graph.edge_b[other] == graph.edge_a[id] or graph.edge_b[other] == graph.edge_b[id]
			if shared:
				continue
			if Geometry2D.segment_intersects_segment(a, b, graph.positions[graph.edge_a[other]], graph.positions[graph.edge_b[other]]) != null:
				count += 1
	return count


func _load_settings() -> CityGenSettings:
	var path: String = "res://resources/citygen/city_lab_settings.tres"
	if ResourceLoader.exists(path):
		return (load(path) as CityGenSettings).duplicate() as CityGenSettings
	return CityGenSettings.new()


func _line(image: Image, a: Vector2, b: Vector2, radius: float, color: Color) -> void:
	var steps: int = maxi(1, int(a.distance_to(b) * 2.0))
	var size: int = maxi(1, int(radius * 2.0))
	for step: int in steps + 1:
		var point: Vector2 = a.lerp(b, float(step) / float(steps))
		var rect := Rect2i(int(point.x - radius), int(point.y - radius), size, size)
		image.fill_rect(rect.intersection(Rect2i(0, 0, SIZE, SIZE)), color)


func _fill_polygon(image: Image, polygon: PackedVector2Array, scale: float, half: Vector2, color: Color) -> void:
	var points := PackedVector2Array()
	for point: Vector2 in polygon:
		points.append(point * scale + half)
	var bounds := Rect2(points[0], Vector2.ZERO)
	for point: Vector2 in points:
		bounds = bounds.expand(point)
	for y: int in range(maxi(0, int(bounds.position.y)), mini(SIZE, int(bounds.end.y) + 1)):
		for x: int in range(maxi(0, int(bounds.position.x)), mini(SIZE, int(bounds.end.x) + 1)):
			if Geometry2D.is_point_in_polygon(Vector2(x, y), points):
				image.set_pixel(x, y, color)
