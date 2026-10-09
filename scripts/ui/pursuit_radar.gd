class_name PursuitRadar
extends Control
## Player-facing street radar: the red triangle is you; blue/red dots are real patrols.
var vehicle: ArcadeVehicle
const RANGE_M: float = 115.0

func _process(_delta: float) -> void:
	queue_redraw()

func _draw() -> void:
	if not is_instance_valid(vehicle):
		return
	var center: Vector2 = size * 0.5
	var scale: float = minf(size.x, size.y) * 0.46 / RANGE_M
	draw_rect(Rect2(Vector2.ZERO, size), Color("162735"))
	var nearest_x: int = roundi(vehicle.global_position.x / ChaseRoads.SPACING)
	var nearest_z: int = roundi(vehicle.global_position.z / ChaseRoads.SPACING)
	for offset: int in range(-3, 4):
		var x: float = (nearest_x + offset) * ChaseRoads.SPACING
		var z: float = (nearest_z + offset) * ChaseRoads.SPACING
		draw_line(_point(Vector3(x, 0, vehicle.global_position.z - 300), center, scale), _point(Vector3(x, 0, vehicle.global_position.z + 300), center, scale), Color("40596a"), 9.0, true)
		draw_line(_point(Vector3(vehicle.global_position.x - 300, 0, z), center, scale), _point(Vector3(vehicle.global_position.x + 300, 0, z), center, scale), Color("40596a"), 9.0, true)
	for unit: Node in get_tree().get_nodes_in_group("police"):
		if not unit is PoliceVehicle:
			continue
		var dot: Vector2 = _point(unit.global_position, center, scale)
		# Close units remain visible beside the player's marker instead of hiding under it.
		var separation: Vector2 = dot - center
		if separation.length() < 13.0:
			dot = center + (separation.normalized() if separation.length() > 0.01 else Vector2.DOWN) * 13.0
		dot = dot.clamp(Vector2(7, 7), size - Vector2(7, 7))
		draw_circle(dot, 5.0, Color("62b4f0") if unit.unit_id % 2 == 0 else Color("ff856e"))
	var triangle := PackedVector2Array([center + Vector2(0, -8), center + Vector2(-6, 6), center + Vector2(6, 6)])
	draw_colored_polygon(triangle, Color("f85448"))
	draw_rect(Rect2(Vector2.ONE, size - Vector2.ONE * 2), Color("627681"), false, 1.0)

func _point(at: Vector3, center: Vector2, scale: float) -> Vector2:
	var local: Vector3 = (at - vehicle.global_position).rotated(Vector3.UP, -vehicle.rotation.y)
	return center + Vector2(local.x, local.z) * scale
