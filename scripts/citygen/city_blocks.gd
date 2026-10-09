class_name CityBlocks
extends RefCounted
## Finds the land enclosed by roads (the faces of the road network) and shapes each one
## into a curbed block: road widths cut away, rounded street corners, and buildable ground
## inside the sidewalk ring.

const PARK_BIAS: PackedFloat32Array = [0.8, 0.7, 1.6, 0.3]


class Block:
	var curb := PackedVector2Array()
	var ground: Array[PackedVector2Array] = []
	var style: int = 0
	var park: bool = false
	var centroid := Vector2.ZERO
	var area: float = 0.0


static func build(graph: RoadGraph, generator: RoadGenerator, settings: CityGenSettings) -> Array[Block]:
	var rng := RandomNumberGenerator.new()
	rng.seed = settings.city_seed * 31 + 5
	var dangling: Dictionary = _dangling_edges(graph)
	var sorted: Dictionary = _sorted_edges(graph, dangling)
	var visited: Dictionary = {}
	var capsules: Dictionary = {}
	var dead_ends: Array = _dead_end_cutters(graph, dangling)
	var blocks: Array[Block] = []
	var largest: float = PI * pow(settings.city_radius * 1.6, 2.0) * 0.5
	for id: int in graph.alive_edges():
		if dangling.has(id):
			continue
		for from: int in [graph.edge_a[id], graph.edge_b[id]]:
			if visited.has(_half_key(graph, id, from)):
				continue
			var face: Dictionary = _trace(graph, sorted, visited, id, from)
			if face.is_empty():
				continue
			var outline: PackedVector2Array = face["outline"]
			var area: float = signed_area(outline)
			# The outside of the city traces with negative area; skip it and slivers.
			if area < 60.0 or area > largest:
				continue
			var face_edges: PackedInt32Array = face["edges"]
			for curb: PackedVector2Array in _shape(graph, outline, face_edges, dead_ends, capsules, settings):
				var block := Block.new()
				block.curb = curb
				block.area = signed_area(curb)
				block.centroid = centroid(curb)
				block.style = generator.style_at(block.centroid)
				block.ground = outer(Geometry2D.offset_polygon(curb, -settings.sidewalk_width, Geometry2D.JOIN_MITER))
				var usable: float = 0.0
				for ground: PackedVector2Array in block.ground:
					usable += signed_area(ground)
				block.park = usable < 140.0 or rng.randf() < settings.park_chance * PARK_BIAS[block.style]
				blocks.append(block)
	return blocks


static func signed_area(polygon: PackedVector2Array) -> float:
	var total: float = 0.0
	for index: int in polygon.size():
		var a: Vector2 = polygon[index]
		var b: Vector2 = polygon[(index + 1) % polygon.size()]
		total += a.x * b.y - b.x * a.y
	return total * 0.5


static func centroid(polygon: PackedVector2Array) -> Vector2:
	var area: float = signed_area(polygon)
	if absf(area) < 0.001:
		return polygon[0]
	var sum := Vector2.ZERO
	for index: int in polygon.size():
		var a: Vector2 = polygon[index]
		var b: Vector2 = polygon[(index + 1) % polygon.size()]
		var cross: float = a.x * b.y - b.x * a.y
		sum += (a + b) * cross
	return sum / (6.0 * area)


## Clipper returns outer shapes with positive area and holes with negative area.
static func outer(polygons: Array[PackedVector2Array]) -> Array[PackedVector2Array]:
	var result: Array[PackedVector2Array] = []
	for polygon: PackedVector2Array in polygons:
		if polygon.size() >= 3 and signed_area(polygon) > 0.0:
			result.append(polygon)
	return result


static func _half_key(graph: RoadGraph, id: int, from: int) -> int:
	return id * 2 + (0 if from == graph.edge_a[id] else 1)


## Dead-end branches don't enclose land; peel them off so faces trace cleanly.
static func _dangling_edges(graph: RoadGraph) -> Dictionary:
	var degrees := PackedInt32Array()
	degrees.resize(graph.node_count())
	var stack: Array[int] = []
	for node: int in graph.node_count():
		degrees[node] = graph.degree(node)
		if degrees[node] == 1:
			stack.append(node)
	var dangling: Dictionary = {}
	while not stack.is_empty():
		var node: int = stack.pop_back()
		for id: int in graph.node_edges[node]:
			if dangling.has(id):
				continue
			dangling[id] = true
			var other: int = graph.other(id, node)
			degrees[node] -= 1
			degrees[other] -= 1
			if degrees[other] == 1:
				stack.append(other)
	return dangling


static func _sorted_edges(graph: RoadGraph, dangling: Dictionary) -> Dictionary:
	var sorted: Dictionary = {}
	for node: int in graph.node_count():
		var list: Array = []
		for id: int in graph.node_edges[node]:
			if not dangling.has(id):
				list.append(id)
		if list.size() < 2:
			continue
		list.sort_custom(func(x: int, y: int) -> bool: return graph.direction_from(node, x) < graph.direction_from(node, y))
		sorted[node] = list
	return sorted


## Walks one face keeping it on the left: at each junction take the next road clockwise.
static func _trace(graph: RoadGraph, sorted: Dictionary, visited: Dictionary, start_edge: int, start_from: int) -> Dictionary:
	var outline := PackedVector2Array()
	var edges := PackedInt32Array()
	var edge: int = start_edge
	var from: int = start_from
	for step: int in 6000:
		var key: int = _half_key(graph, edge, from)
		if visited.has(key):
			return {}
		visited[key] = true
		outline.append(graph.positions[from])
		edges.append(edge)
		var to: int = graph.other(edge, from)
		if not sorted.has(to):
			return {}
		var list: Array = sorted[to]
		var index: int = list.find(edge)
		edge = list[(index - 1 + list.size()) % list.size()]
		from = to
		if edge == start_edge and from == start_from:
			return {"outline": outline, "edges": edges}
	return {}


static func _shape(graph: RoadGraph, outline: PackedVector2Array, face_edges: PackedInt32Array, dead_ends: Array, capsules: Dictionary, settings: CityGenSettings) -> Array[PackedVector2Array]:
	var pieces: Array[PackedVector2Array] = [outline]
	var bounds := Rect2(outline[0], Vector2.ZERO)
	for point: Vector2 in outline:
		bounds = bounds.expand(point)
	var shapes: Array[PackedVector2Array] = []
	for id: int in face_edges:
		shapes.append(_capsule(graph, id, capsules))
	# Dead-end streets are cut as one shape from their junction to the tip. Cut piece by piece,
	# the inner pieces would sit fully inside the block and come back as holes instead of cuts.
	var reach: Rect2 = bounds.grow(settings.arterial_width)
	for cutter: Array in dead_ends:
		if (cutter[1] as Rect2).intersects(reach):
			shapes.append_array(cutter[0] as Array[PackedVector2Array])
	for shape: PackedVector2Array in shapes:
		if shape.is_empty():
			continue
		var next: Array[PackedVector2Array] = []
		for piece: PackedVector2Array in pieces:
			next.append_array(outer(Geometry2D.clip_polygons(piece, shape)))
		pieces = next
		if pieces.is_empty():
			return pieces
	# Opening (shrink then grow) rounds the street corners and drops slivers too thin to use.
	if settings.corner_radius > 0.05:
		var rounded: Array[PackedVector2Array] = []
		for piece: PackedVector2Array in pieces:
			for shrunk: PackedVector2Array in outer(Geometry2D.offset_polygon(piece, -settings.corner_radius, Geometry2D.JOIN_ROUND)):
				rounded.append_array(outer(Geometry2D.offset_polygon(shrunk, settings.corner_radius, Geometry2D.JOIN_ROUND)))
		pieces = rounded
	var result: Array[PackedVector2Array] = []
	for piece: PackedVector2Array in pieces:
		if signed_area(piece) >= 80.0:
			result.append(piece)
	return result


## Each dead-end branch becomes [road shapes, bounds], traced from the junction it hangs off.
static func _dead_end_cutters(graph: RoadGraph, dangling: Dictionary) -> Array:
	var paths: Array = []
	var walked: Dictionary = {}
	for id: int in dangling:
		for root: int in [graph.edge_a[id], graph.edge_b[id]]:
			if walked.has(id) or not _on_core(graph, root, dangling):
				continue
			_walk_dead_end(graph, dangling, walked, root, id, PackedVector2Array([graph.positions[root]]), 0.0, paths)
	var cutters: Array = []
	for path: Array in paths:
		var line: PackedVector2Array = path[0]
		var shapes: Array[PackedVector2Array] = Geometry2D.offset_polyline(line, float(path[1]) * 0.5,
			Geometry2D.JOIN_ROUND, Geometry2D.END_ROUND)
		var bounds := Rect2(line[0], Vector2.ZERO)
		for point: Vector2 in line:
			bounds = bounds.expand(point)
		cutters.append([shapes, bounds.grow(float(path[1]))])
	return cutters


static func _on_core(graph: RoadGraph, node: int, dangling: Dictionary) -> bool:
	for id: int in graph.node_edges[node]:
		if not dangling.has(id):
			return true
	return false


static func _walk_dead_end(graph: RoadGraph, dangling: Dictionary, walked: Dictionary, from: int, id: int,
		path: PackedVector2Array, width: float, paths: Array) -> void:
	walked[id] = true
	var to: int = graph.other(id, from)
	var line: PackedVector2Array = path.duplicate()
	line.append(graph.positions[to])
	var widest: float = maxf(width, graph.edge_width[id])
	var extended: bool = false
	for next: int in graph.node_edges[to]:
		if next == id or not dangling.has(next) or walked.has(next):
			continue
		extended = true
		_walk_dead_end(graph, dangling, walked, to, next, line, widest, paths)
	if not extended:
		paths.append([line, widest])


static func _capsule(graph: RoadGraph, id: int, cache: Dictionary) -> PackedVector2Array:
	if not cache.has(id):
		var line := PackedVector2Array([graph.positions[graph.edge_a[id]], graph.positions[graph.edge_b[id]]])
		var shapes: Array[PackedVector2Array] = Geometry2D.offset_polyline(line, graph.edge_width[id] * 0.5,
			Geometry2D.JOIN_ROUND, Geometry2D.END_ROUND)
		cache[id] = shapes[0] if not shapes.is_empty() else PackedVector2Array()
	return cache[id]
