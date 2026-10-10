class_name ScriptedDriver
extends Node
## Drives a car along a list of points for cutscenes (the breakout): steers toward a point a little
## ahead on the path and holds each point's speed. Runs after the player's input, so it wins.

signal arrived

var car: ArcadeVehicle
## [Vector2 point, float speed m/s] pairs, in order.
var path: Array = []
var look_ahead: float = 6.0
var _index: int = 0


func _ready() -> void:
	process_physics_priority = 10


func _physics_process(_delta: float) -> void:
	if not is_instance_valid(car) or path.is_empty():
		return
	var here := Vector2(car.global_position.x, car.global_position.z)
	while _index < path.size() - 1 and here.distance_to(path[_index][0]) < look_ahead:
		_index += 1
	var target: Vector2 = path[_index][0]
	var speed: float = path[_index][1]
	if _index == path.size() - 1 and here.distance_to(target) < look_ahead:
		car.set_driver_command(0.0, 0.0, false)
		arrived.emit()
		path = []
		return
	var forward := Vector2(-car.global_basis.z.x, -car.global_basis.z.z).normalized()
	var turn: float = forward.angle_to((target - here).normalized())
	var steer: float = clampf(turn * 2.2, -1.0, 1.0)
	var gap: float = speed - car.forward_speed
	car.set_driver_command(clampf(gap * 0.35 + 0.15, -1.0, 1.0), steer, false)
