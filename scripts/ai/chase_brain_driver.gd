class_name ChaseBrainDriver
extends Node
## Drives a lab cop with a brain from chase training (training/train_chase.py), using exactly the
## arena's senses: a road route toward where the team thinks you are, the team's shared knowledge of
## you (ChaseIntel, kept by LabChase), the nearest teammates, and its burst. Decides 10 times a second;
## a burst fired near you shows the "!" warning.

const DECISION_FRAMES: int = 6
const REPLAN_SECONDS: float = 0.5
const WARNING_RANGE: float = 45.0

var net: PolicyNet
var chase: LabChase
var car: LabVehicle
var target: LabVehicle
var mode: String = "brain"
var burst := CopBurst.new()
var senses := ChaseSenses.new()
var route := RouteTrack.new()
var _frame: int = 0
var _replan: float = 0.0
var _actions := PackedFloat32Array([0.0, 0.0, -1.0, -1.0])
var _warning: Label3D


func _ready() -> void:
	senses.setup(car, CopSenses.CAR_MASK)
	# Spread the cops' decisions over the six frames so no single frame runs them all.
	_frame = int(car.get_instance_id() % DECISION_FRAMES)
	_warning = Label3D.new()
	_warning.text = "!"
	_warning.font_size = 160
	_warning.pixel_size = 0.012
	_warning.outline_size = 36
	_warning.modulate = Color("#FFD400")
	_warning.outline_modulate = Color("#24394B")
	_warning.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_warning.no_depth_test = true
	_warning.position = Vector3(0.0, 3.4, 0.0)
	_warning.visible = false
	car.add_child.call_deferred(_warning)


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
		route.setup(chase.nav.route(here, heading, chase.intel.believed_position()))
	var progress: float = route.project(here)
	var team: Array = []
	for cop: LabVehicle in chase.cops:
		if cop != car and is_instance_valid(cop):
			team.append(cop)
	var cars: Array = team.duplicate()
	cars.append(target)
	var obs: PackedFloat32Array = senses.observe_cop(route, progress, cars, step, chase.intel, chase.sees(car), target,
		team, team.size() + 1, burst)
	_actions = net.act(obs)
	burst.cooldown = CopBurst.cooldown_at(chase.minute())
	burst.tick(step, _actions[3] > 0.0)
	ChaseSenses.apply(car, _actions, 0, false)
	mode = "burst" if burst.active() else "brain"
	var gap: float = car.global_position.distance_to(target.global_position)
	_warning.visible = burst.active() and gap < WARNING_RANGE
