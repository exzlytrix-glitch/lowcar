class_name BrainCopDriver
extends Node
## Drives a cop with a trained brain (PolicyNet) using exactly the senses it trained with: a road
## route toward the target, re-planned twice a second, and a goal 80 m along that route
## ("driving school" setup). Decides 10 times a second and holds the controls in between.

const DECISION_FRAMES: int = 6
const GOAL_AHEAD: float = 80.0
const REPLAN_SECONDS: float = 0.5

var net: PolicyNet
var chase: LabChase
var car: LabVehicle
var target: CharacterBody3D
var mode: String = "brain"
var senses := CopSenses.new()
var route := RouteTrack.new()
var _frame: int = 0
var _replan: float = 0.0
var _actions := PackedFloat32Array([0.0, 0.0, -1.0])


func _ready() -> void:
	senses.car = car


func _physics_process(delta: float) -> void:
	if car == null or net == null:
		return
	if not chase.active or not is_instance_valid(target) or not car.controls_enabled:
		car.set_driver_command(0.0, 0.0, true)
		return
	_frame += 1
	if _frame % DECISION_FRAMES != 0:
		return
	var step: float = DECISION_FRAMES * delta
	var here := Vector2(car.global_position.x, car.global_position.z)
	_replan -= step
	if _replan <= 0.0 or route.points.is_empty():
		_replan = REPLAN_SECONDS
		var heading := Vector2(-car.global_basis.z.x, -car.global_basis.z.z).normalized()
		var aim := Vector2(target.global_position.x, target.global_position.z) + Vector2(target.velocity.x, target.velocity.z)
		route.setup(chase.nav.route(here, heading, aim))
	var progress: float = route.project(here)
	var goal: Vector2 = route.point_at(progress + GOAL_AHEAD)
	var cars: Array = chase.cops.duplicate()
	cars.append(target)
	_actions = net.act(senses.observe(route, progress, goal, Vector2.ZERO, cars, step))
	CopSenses.apply(car, _actions, 0)
