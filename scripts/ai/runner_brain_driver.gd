class_name RunnerBrainDriver
extends Node
## Lets the runner brain from chase training (training/train_chase.py) drive your car in the lab, so
## you can watch learned cops chase a learned runner. It sees what the arena's runner sees: a route to
## a random far destination it is free to ignore, the cops around it, and whether they have spotted it.
## Runs after the keyboard input each frame, so its controls win while it is on.

const DECISION_FRAMES: int = 6
const REPLAN_SECONDS: float = 2.0
const BRAIN_PATH: String = "res://resources/ai/chase_runner_brain.json"

var net: PolicyNet
var chase: LabChase
var car: LabVehicle
var senses := ChaseSenses.new()
var route := RouteTrack.new()
var _goal := Vector2.INF
var _replan: float = 0.0
var _frame: int = 0
var _rng := RandomNumberGenerator.new()
var _actions := PackedFloat32Array([0.0, 0.0, -1.0, -1.0])


func _ready() -> void:
	process_physics_priority = 10
	senses.setup(car, CopSenses.CAR_MASK)
	_rng.randomize()


func _physics_process(delta: float) -> void:
	if car == null or net == null or chase.nav == null or not car.controls_enabled:
		return
	_frame += 1
	if _frame % DECISION_FRAMES == 0:
		_decide(DECISION_FRAMES * delta)
	ChaseSenses.apply(car, _actions, 0, true)


func _decide(step: float) -> void:
	var here := Vector2(car.global_position.x, car.global_position.z)
	if _goal == Vector2.INF or here.distance_to(_goal) < 40.0:
		_pick_goal(here)
		_replan = 0.0
	_replan -= step
	if _replan <= 0.0 or route.points.is_empty():
		_replan = REPLAN_SECONDS
		var heading := Vector2(-car.global_basis.z.x, -car.global_basis.z.z).normalized()
		route.setup(chase.nav.route(here, heading, _goal))
	var progress: float = route.project(here)
	var cops: Array = []
	var bursting: Array = []
	for cop: LabVehicle in chase.cops:
		if is_instance_valid(cop):
			cops.append(cop)
			bursting.append(chase.bursting(cop))
	var cars: Array = cops.duplicate()
	cars.append(car)
	_actions = net.act(senses.observe_runner(route, progress, cars, step, cops, bursting, chase.intel))


func _pick_goal(here: Vector2) -> void:
	_goal = here
	for attempt: int in 12:
		var node: int = chase.nav.random_node(_rng)
		if node >= 0:
			_goal = chase.nav.graph.positions[node]
			if _goal.distance_to(here) > 300.0:
				return
