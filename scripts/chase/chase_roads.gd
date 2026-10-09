class_name ChaseRoads
extends RefCounted
## Routes along the 64 m street grid that CityChunk builds, without a navmesh.
const SPACING: float = 64.0

static func project(at: Vector3) -> Vector3:
	var x: float = snappedf(at.x, SPACING)
	var z: float = snappedf(at.z, SPACING)
	return Vector3(x, 0.1, at.z) if absf(at.x - x) <= absf(at.z - z) else Vector3(at.x, 0.1, z)

static func route(from: Vector3, goal: Vector3, heading: Vector3, prefer_x: bool) -> Array[Vector3]:
	var start: Vector3 = project(from)
	var finish: Vector3 = project(goal)
	if (is_equal_approx(start.x, finish.x) and is_equal_approx(fmod(absf(start.x), SPACING), 0.0)) or (is_equal_approx(start.z, finish.z) and is_equal_approx(fmod(absf(start.z), SPACING), 0.0)):
		return [finish]
	var best: Array[Vector3] = []
	var best_cost: float = INF
	for a: Vector3 in _ends(start):
		for b: Vector3 in _ends(finish):
			for x_first: bool in [prefer_x, not prefer_x]:
				var candidate: Array[Vector3] = [a]
				var cursor: Vector3 = a
				while not cursor.is_equal_approx(b):
					if (x_first and not is_equal_approx(cursor.x, b.x)) or is_equal_approx(cursor.z, b.z):
						cursor.x += signf(b.x - cursor.x) * SPACING
					else:
						cursor.z += signf(b.z - cursor.z) * SPACING
					candidate.append(cursor)
				candidate.append(finish)
				var cost: float = start.distance_to(a) + absf(a.x - b.x) + absf(a.z - b.z) + b.distance_to(finish)
				var first: Vector3 = a - from
				first.y = 0.0
				if first.length() > 4.0:
					cost += (1.0 - heading.dot(first.normalized())) * 12.0
				if cost < best_cost:
					best_cost = cost
					best = candidate
	while best.size() > 1 and from.distance_to(best[0]) < 5.0:
		best.pop_front()
	return best

static func _ends(at: Vector3) -> Array[Vector3]:
	if is_equal_approx(at.x, snappedf(at.x, SPACING)):
		var z: float = floorf(at.z / SPACING) * SPACING
		return [Vector3(at.x, 0.1, z), Vector3(at.x, 0.1, z + SPACING)]
	var x: float = floorf(at.x / SPACING) * SPACING
	return [Vector3(x, 0.1, at.z), Vector3(x + SPACING, 0.1, at.z)]
