class_name ChaseBrainDriver
extends Node
## Drives a lab cop with a brain from chase training (training/train_chase.py) through ChaseAgent, the
## same plumbing training uses: senses, the team's shared knowledge of you (ChaseIntel, kept by
## LabChase), its navigation choice and its burst. Decides 10 times a second; a burst fired near you
## shows the "!" warning.

const DECISION_FRAMES: int = 6
const WARNING_RANGE: float = 45.0

var net: PolicyNet
var chase: LabChase
var car: LabVehicle
var target: LabVehicle
var mode: String = "brain"
var agent := ChaseAgent.new()
var _rng := RandomNumberGenerator.new()
var _frame: int = 0
var _warning: Label3D


func _ready() -> void:
	_rng.randomize()
	agent.setup(car, false, chase.nav, CopSenses.CAR_MASK, _rng)
	agent.reset()
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
	var team: Array = []
	for cop: LabVehicle in chase.cops:
		if cop != car and is_instance_valid(cop):
			team.append(cop)
	var cars: Array = team.duplicate()
	cars.append(target)
	var obs: PackedFloat32Array = agent.observe_cop(DECISION_FRAMES * delta, cars, chase.intel, chase.sees(car), target,
		team, team.size() + 1)
	agent.burst.cooldown = CopBurst.cooldown_at(chase.minute())
	agent.apply(net.decide(obs, _rng), 0)
	mode = "burst" if agent.burst.active() else "brain"
	_warning.visible = agent.burst.active() and car.global_position.distance_to(target.global_position) < WARNING_RANGE
