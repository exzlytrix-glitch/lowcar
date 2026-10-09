class_name RoadNav
extends RefCounted
## Navigation over the generated road network, shared by training and in-game cops:
## A* routes between road points, junction lookup, and random far destinations.

var graph: RoadGraph
var astar := AStar2D.new()
var _ids := PackedInt64Array()


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
	var found: Dictionary = graph.closest_road_point(at, 400.0)
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
