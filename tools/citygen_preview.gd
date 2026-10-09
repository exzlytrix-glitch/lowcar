extends SceneTree
## Renders a generated road network to a top-down PNG without opening a window.
## Usage: Godot --headless --path . --script res://tools/citygen_preview.gd -- --out=/tmp/city.png [--seed=7] [--blocks]

const SIZE: int = 1400
const DISTRICT_TINTS: Array[Color] = [Color("#EED9C4"), Color("#DCE3EC"), Color("#D5E8C8"), Color("#DDD8D0")]
const ROAD_COLORS: Array[Color] = [Color("#5C6670"), Color("#7A848E"), Color("#9A8F86"), Color("#46505A")]


func _initialize() -> void:
	var out_path: String = "user://citygen_preview.png"
	var settings: CityGenSettings = _load_settings()
	var draw_blocks: bool = false
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with("--out="):
			out_path = argument.trim_prefix("--out=")
		elif argument.begins_with("--seed="):
			settings.city_seed = int(argument.trim_prefix("--seed="))
		elif argument == "--blocks":
			draw_blocks = true
	var started: int = Time.get_ticks_msec()
	var generator := RoadGenerator.new()
	var graph: RoadGraph = generator.generate(settings)
	var road_ms: int = Time.get_ticks_msec() - started
	var image := Image.create(SIZE, SIZE, false, Image.FORMAT_RGB8)
	var scale: float = float(SIZE) / (settings.city_radius * 2.0 * 1.45)
	var half := Vector2(SIZE, SIZE) * 0.5
	for y: int in range(0, SIZE, 7):
		for x: int in range(0, SIZE, 7):
			var world: Vector2 = (Vector2(x, y) - half) / scale
			var tint: Color = Color("#B9D3A5")
			if world.length() <= generator.boundary_radius(world.angle()):
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
	print("CITYGEN road_ms=%d" % road_ms)
	quit()


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
