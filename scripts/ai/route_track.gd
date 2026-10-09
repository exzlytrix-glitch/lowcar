class_name RouteTrack
extends RefCounted
## A road route as a polyline with distance along it, so "how far along the route am I" and
## "where is the road 30 m ahead" are cheap. Progress along the route is the main training reward,
## the same idea Gran Turismo Sophy used with its track centreline.

var points := PackedVector2Array()
var distances := PackedFloat32Array()
## Sideways distance from the route at the last projection.
var offset: float = 0.0
var _segment: int = 0


func setup(route_points: PackedVector2Array) -> void:
	points = PackedVector2Array()
	for point: Vector2 in route_points:
		if points.is_empty() or points[points.size() - 1].distance_to(point) > 0.5:
			points.append(point)
	if points.size() == 1:
		points.append(points[0] + Vector2(0.0, -1.0))
	distances = PackedFloat32Array([0.0])
	for index: int in range(1, points.size()):
		distances.append(distances[index - 1] + points[index - 1].distance_to(points[index]))
	_segment = 0
	offset = 0.0


func length() -> float:
	return distances[distances.size() - 1] if not distances.is_empty() else 0.0


## Distance along the route of the closest point to `at`. Searches near the last answer, so it
## follows the car forward and does not jump to a far part of the route that passes close by.
func project(at: Vector2) -> float:
	var best: float = INF
	var best_s: float = 0.0
	var best_segment: int = _segment
	var low: int = maxi(0, _segment - 2)
	var high: int = mini(points.size() - 2, _segment + 12)
	for index: int in range(low, high + 1):
		var a: Vector2 = points[index]
		var b: Vector2 = points[index + 1]
		var closest: Vector2 = Geometry2D.get_closest_point_to_segment(at, a, b)
		var gap: float = closest.distance_to(at)
		if gap < best:
			best = gap
			best_segment = index
			best_s = distances[index] + a.distance_to(closest)
	_segment = best_segment
	offset = best
	return best_s


func point_at(s: float) -> Vector2:
	if points.is_empty():
		return Vector2.ZERO
	s = clampf(s, 0.0, length())
	var index: int = _segment
	while index > 0 and distances[index] > s:
		index -= 1
	while index < points.size() - 2 and distances[index + 1] < s:
		index += 1
	var span: float = maxf(distances[index + 1] - distances[index], 0.001)
	return points[index].lerp(points[index + 1], (s - distances[index]) / span)
