class_name RoadGraph
extends RefCounted
## Planar street network: junction points joined by straight road pieces.
## Curved roads are chains of short pieces. Every crossing is a shared junction.

enum Kind { ARTERIAL, STREET, LANE, RING }

const CELL: float = 48.0

var positions := PackedVector2Array()
var node_edges: Array[Array] = []
var edge_a := PackedInt32Array()
var edge_b := PackedInt32Array()
var edge_kind := PackedInt32Array()
var edge_width := PackedFloat32Array()
var edge_style := PackedInt32Array()
var edge_alive := PackedByteArray()
var _cells: Dictionary = {}


func node_count() -> int:
	return positions.size()


func edge_count() -> int:
	return edge_a.size()


func add_node(at: Vector2) -> int:
	positions.append(at)
	node_edges.append([])
	return positions.size() - 1


func add_edge(a: int, b: int, kind: int, width: float, style: int) -> int:
	var id: int = edge_a.size()
	edge_a.append(a)
	edge_b.append(b)
	edge_kind.append(kind)
	edge_width.append(width)
	edge_style.append(style)
	edge_alive.append(1)
	node_edges[a].append(id)
	node_edges[b].append(id)
	_index(id, true)
	return id


func remove_edge(id: int) -> void:
	if edge_alive[id] == 0:
		return
	edge_alive[id] = 0
	node_edges[edge_a[id]].erase(id)
	node_edges[edge_b[id]].erase(id)
	_index(id, false)


func split_edge(id: int, at: Vector2) -> int:
	var a: int = edge_a[id]
	var b: int = edge_b[id]
	var kind: int = edge_kind[id]
	var width: float = edge_width[id]
	var style: int = edge_style[id]
	remove_edge(id)
	var middle: int = add_node(at)
	add_edge(a, middle, kind, width, style)
	add_edge(middle, b, kind, width, style)
	return middle


func other(id: int, node: int) -> int:
	return edge_b[id] if edge_a[id] == node else edge_a[id]


func degree(node: int) -> int:
	return node_edges[node].size()


func edge_length(id: int) -> float:
	return positions[edge_a[id]].distance_to(positions[edge_b[id]])


func direction_from(node: int, id: int) -> float:
	return (positions[other(id, node)] - positions[node]).angle()


func connected(a: int, b: int) -> bool:
	for id: int in node_edges[a]:
		if other(id, a) == b:
			return true
	return false


func alive_edges() -> PackedInt32Array:
	var result := PackedInt32Array()
	for id: int in edge_count():
		if edge_alive[id] == 1:
			result.append(id)
	return result


func edges_in(area: Rect2) -> PackedInt32Array:
	var found: Dictionary = {}
	var low := Vector2i(floori(area.position.x / CELL), floori(area.position.y / CELL))
	var high := Vector2i(floori(area.end.x / CELL), floori(area.end.y / CELL))
	for x: int in range(low.x, high.x + 1):
		for y: int in range(low.y, high.y + 1):
			var key := Vector2i(x, y)
			if _cells.has(key):
				for id: int in _cells[key]:
					found[id] = true
	var result := PackedInt32Array()
	for id: int in found:
		result.append(id)
	return result


## Nearest place where from→to crosses an existing road, ignoring roads touching ignore_node.
func first_crossing(from: Vector2, to: Vector2, ignore_node: int) -> Dictionary:
	var best: Dictionary = {}
	var best_distance: float = INF
	for id: int in edges_in(Rect2(from, Vector2.ZERO).expand(to).grow(1.0)):
		if edge_a[id] == ignore_node or edge_b[id] == ignore_node:
			continue
		var hit: Variant = Geometry2D.segment_intersects_segment(from, to, positions[edge_a[id]], positions[edge_b[id]])
		if hit == null:
			continue
		var point: Vector2 = hit
		var distance: float = from.distance_to(point)
		if distance < best_distance:
			best_distance = distance
			best = {"edge": id, "point": point, "distance": distance}
	return best


## True when from→to would cross a road that touches neither end node.
func crosses(from: Vector2, to: Vector2, node_a: int, node_b: int) -> bool:
	for id: int in edges_in(Rect2(from, Vector2.ZERO).expand(to).grow(1.0)):
		var a: int = edge_a[id]
		var b: int = edge_b[id]
		if a == node_a or b == node_a or a == node_b or b == node_b:
			continue
		if Geometry2D.segment_intersects_segment(from, to, positions[a], positions[b]) != null:
			return true
	return false


func nearest_node(at: Vector2, radius: float, exclude: int) -> int:
	var best: int = -1
	var best_distance: float = radius
	for id: int in edges_in(Rect2(at, Vector2.ZERO).grow(radius)):
		for node: int in [edge_a[id], edge_b[id]]:
			if node == exclude:
				continue
			var distance: float = positions[node].distance_to(at)
			if distance < best_distance:
				best_distance = distance
				best = node
	return best


func distance_to_edge(at: Vector2, id: int) -> float:
	return at.distance_to(Geometry2D.get_closest_point_to_segment(at, positions[edge_a[id]], positions[edge_b[id]]))


## Closest point on any road within radius: {"edge", "point"} or empty.
func closest_road_point(at: Vector2, radius: float) -> Dictionary:
	var best: Dictionary = {}
	var best_distance: float = radius
	for id: int in edges_in(Rect2(at, Vector2.ZERO).grow(radius)):
		var point: Vector2 = Geometry2D.get_closest_point_to_segment(at, positions[edge_a[id]], positions[edge_b[id]])
		var distance: float = point.distance_to(at)
		if distance < best_distance:
			best_distance = distance
			best = {"edge": id, "point": point}
	return best


func _index(id: int, add: bool) -> void:
	var a: Vector2 = positions[edge_a[id]]
	var b: Vector2 = positions[edge_b[id]]
	var low := Vector2i(floori(minf(a.x, b.x) / CELL), floori(minf(a.y, b.y) / CELL))
	var high := Vector2i(floori(maxf(a.x, b.x) / CELL), floori(maxf(a.y, b.y) / CELL))
	for x: int in range(low.x, high.x + 1):
		for y: int in range(low.y, high.y + 1):
			var key := Vector2i(x, y)
			if add:
				if not _cells.has(key):
					_cells[key] = []
				_cells[key].append(id)
			elif _cells.has(key):
				_cells[key].erase(id)
