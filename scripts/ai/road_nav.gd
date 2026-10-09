class_name RoadNav
extends RefCounted
## Navigation over the generated road network, shared by training and in-game cops:
## A* routes between road points, junction lookup, and random far destinations.

var graph: RoadGraph
var astar := AStar2D.new()
var _ids := PackedInt64Array()
## The last next_junction() / exits() answers: cops of one chase all ask about the same runner.
var _junction_key: Array = []
var _junction_answer: Dictionary = {}
var _exits_key := Vector2i(-1, -1)
var _exits_answer: Array = []


func _init(road_graph: RoadGraph) -> void:
	graph = road_graph
	for node: int in graph.node_count():
		if graph.degree(node) > 0:
			astar.add_point(node, graph.positions[node])
	for id: int in graph.alive_edges():
		astar.connect_points(graph.edge_a[id], graph.edge_b[id])
	_ids = astar.get_point_ids()


## Closest junction to a point on the roads, preferring the end of the road that lies ahead.
func node_near(at: Vector2, heading: Vector2) -> int:
	var found: Dictionary = _road_point(at)
	if found.is_empty():
		return -1
	var id: int = found["edge"]
	var a: int = graph.edge_a[id]
	var b: int = graph.edge_b[id]
	if heading != Vector2.ZERO:
		return a if heading.dot(graph.positions[a] - at) > heading.dot(graph.positions[b] - at) else b
	return a if graph.positions[a].distance_to(at) < graph.positions[b].distance_to(at) else b


## Road route from a car to a destination: the car's own position, then junctions, then the destination.
func route(from: Vector2, heading: Vector2, to: Vector2) -> PackedVector2Array:
	var points := PackedVector2Array([from])
	var start: int = node_near(from, heading)
	var finish: int = node_near(to, Vector2.ZERO)
	if start >= 0 and finish >= 0:
		for id: int in astar.get_id_path(start, finish):
			points.append(graph.positions[id])
	points.append(to)
	return points


func random_node(rng: RandomNumberGenerator) -> int:
	return _ids[rng.randi() % _ids.size()] if not _ids.is_empty() else -1


## A random point in the middle of a random road, with the road's direction.
func random_road_spot(rng: RandomNumberGenerator) -> Dictionary:
	var edges: PackedInt32Array = graph.alive_edges()
	for attempt: int in 20:
		var id: int = edges[rng.randi() % edges.size()]
		var a: Vector2 = graph.positions[graph.edge_a[id]]
		var b: Vector2 = graph.positions[graph.edge_b[id]]
		if a.distance_to(b) < 12.0:
			continue
		var dir: Vector2 = (b - a).normalized()
		if rng.randf() < 0.5:
			dir = -dir
		return {"point": a.lerp(b, rng.randf_range(0.25, 0.75)), "dir": dir}
	return {}


## The junction a car on the road at `at` reaches next driving along `heading` (bends are skipped):
## {"node", "edge" (the road it arrives on), "distance" (metres along the road)}, or {} off the roads.
func next_junction(at: Vector2, heading: Vector2) -> Dictionary:
	if _junction_key == [at, heading]:
		return _junction_answer
	_junction_key = [at, heading]
	_junction_answer = {}
	var found: Dictionary = graph.closest_road_point(at, 60.0)
	if found.is_empty():
		return {}
	var edge: int = found["edge"]
	var a: int = graph.edge_a[edge]
	var b: int = graph.edge_b[edge]
	var node: int = a if heading.dot(graph.positions[a] - at) > heading.dot(graph.positions[b] - at) else b
	var walked: Dictionary = _through_bends(node, edge, at.distance_to(graph.positions[node]))
	_junction_answer = {"node": walked["node"], "edge": walked["edge"], "distance": walked["distance"]}
	return _junction_answer


## The roads leaving `node` other than `arrived` (the one a car came in on), left to right:
## [{"edge", "turn" (radians, negative = left), "end" (junction at its far end), "length" (to there)}].
func exits(node: int, arrived: int) -> Array:
	if _exits_key == Vector2i(node, arrived):
		return _exits_answer
	var came_from: Vector2 = graph.positions[graph.other(arrived, node)]
	var in_dir: Vector2 = (graph.positions[node] - came_from).normalized()
	var result: Array = []
	for id: int in graph.node_edges[node]:
		if id == arrived:
			continue
		var out_dir: Vector2 = (graph.positions[graph.other(id, node)] - graph.positions[node]).normalized()
		var far: int = graph.other(id, node)
		var walked: Dictionary = _through_bends(far, id, graph.edge_length(id))
		result.append({"edge": id, "turn": in_dir.angle_to(out_dir), "end": walked["node"], "length": walked["distance"]})
	result.sort_custom(func(x: Dictionary, y: Dictionary) -> bool: return x["turn"] < y["turn"])
	_exits_key = Vector2i(node, arrived)
	_exits_answer = result
	return result


## A point `metres` along an exit road from `node` (stops at the road's far junction).
func along_exit(node: int, exit: Dictionary, metres: float) -> Vector2:
	var start: Vector2 = graph.positions[node]
	var next: Vector2 = graph.positions[graph.other(exit["edge"], node)]
	if start.distance_to(next) >= metres:
		return start + (next - start).normalized() * metres
	return graph.positions[exit["end"]] if exit["length"] <= metres else next


## Closest road point, searching near first (a full 400 m search is slow and almost never needed).
func _road_point(at: Vector2) -> Dictionary:
	for radius: float in [30.0, 120.0, 400.0]:
		var found: Dictionary = graph.closest_road_point(at, radius)
		if not found.is_empty():
			return found
	return {}


func route_length(points: PackedVector2Array) -> float:
	var total: float = 0.0
	for index: int in range(1, points.size()):
		total += points[index - 1].distance_to(points[index])
	return total


## Follows a road through bend nodes (exactly two roads) until a real junction or dead end.
func _through_bends(node: int, edge: int, distance: float) -> Dictionary:
	for step: int in 16:
		if graph.degree(node) != 2:
			break
		var onward: int = graph.node_edges[node][0] if graph.node_edges[node][0] != edge else graph.node_edges[node][1]
		distance += graph.edge_length(onward)
		edge = onward
		node = graph.other(onward, node)
	return {"node": node, "edge": edge, "distance": distance}
