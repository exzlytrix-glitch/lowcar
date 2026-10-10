class_name RunnerBrainDriver
extends Node
## Lets the runner brain from chase training (training/train_chase.py) drive your car in the lab, so
## you can watch learned cops chase a learned runner. Runs through ChaseAgent, the same plumbing as
## training. Runs after the keyboard input each frame, so its controls win while it is on.

const DECISION_FRAMES: int = 6
const BRAIN_PATH: String = "res://resources/ai/chase_runner_brain.json"

var net: PolicyNet
var chase: LabChase
var car: LabVehicle
var agent := ChaseAgent.new()
var _rng := RandomNumberGenerator.new()
var _frame: int = 0
var _ready_to_drive: bool = false


func _ready() -> void:
	process_physics_priority = 10
	_rng.randomize()


func _physics_process(delta: float) -> void:
	if car == null or net == null or chase.nav == null or not car.controls_enabled:
		return
	if not _ready_to_drive or agent.nav != chase.nav:
		agent.setup(car, true, chase.nav, CopSenses.CAR_MASK, _rng)
		agent.reset()
		_ready_to_drive = true
		_frame = -1
	_frame += 1
	agent.physics_tick()
	if _frame % DECISION_FRAMES != 0:
		agent.reapply()
		return
	var cops: Array = []
	var bursting: Array = []
	for cop: LabVehicle in chase.cops:
		if is_instance_valid(cop):
			cops.append(cop)
			bursting.append(chase.bursting(cop))
	var cars: Array = cops.duplicate()
	cars.append(car)
	agent.apply(net.decide(agent.observe_runner(DECISION_FRAMES * delta, cars, cops, bursting, chase.intel), _rng), 0)
