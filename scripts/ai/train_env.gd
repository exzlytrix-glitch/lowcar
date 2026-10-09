extends Node3D
## Headless training world for learning cops. The Python trainer (training/train.py) launches this
## scene, connects over TCP, and every decision (6 physics frames = 0.1 s) gets back what each cop
## sees, its reward and whether its episode ended, then sends the cops' controls.
## The city is regenerated every few minutes so cops learn to drive, not to memorise streets.
##
## Args after "--": --port=N --agents=16 --seed=1 --repeat=6 --city-steps=3000 --radius=450
## --selftest=STEPS runs without Python (random driving) and prints throughput, for local checks.
##
## Wire format (little endian): on connect one JSON line {"obs_dim","act_dim","agents","info_dim"}.
## Then per decision Godot sends int32 byte count + float32[obs A*D, reward A, done A, info A*I],
## and Python answers with float32[A*3] actions.

const POLICE_TUNING: String = "res://resources/vehicles/patrol_car.tres"
const COP_TOP_SPEED: float = 34.0

var port: int = 0
var agents: int = 16
var seed_value: int = 1
var repeat: int = 6
var city_steps: int = 3000
var radius: float = 450.0
var selftest: int = 0
var _peer: StreamPeerTCP
var _rng := RandomNumberGenerator.new()
var _city: CityBuilder
var _nav: RoadNav
var _agents: Array[TrainAgent] = []
var _cars: Array[LabVehicle] = []
var _actions := PackedFloat32Array()
var _frame: int = 0
var _decisions: int = 0
var _since_city: int = 0
var _started: int = 0
var _reward_sum: float = 0.0
var _speed_sum: float = 0.0
var _wall_sum: float = 0.0
var _episodes: int = 0


func _ready() -> void:
	for argument: String in OS.get_cmdline_user_args():
		var value: String = argument.get_slice("=", 1)
		match argument.get_slice("=", 0):
			"--port":
				port = int(value)
			"--agents":
				agents = int(value)
			"--seed":
				seed_value = int(value)
			"--repeat":
				repeat = int(value)
			"--city-steps":
				city_steps = int(value)
			"--radius":
				radius = float(value)
			"--selftest":
				selftest = int(value)
	_rng.seed = seed_value
	var built: int = Time.get_ticks_msec()
	_build_city()
	print("TRAIN_ENV city built in %d ms (%d buildings)" % [Time.get_ticks_msec() - built, _city.building_count])
	for index: int in agents:
		var car: LabVehicle = _make_car()
		_cars.append(car)
		_agents.append(TrainAgent.new(car, _nav, _rng))
	for agent: TrainAgent in _agents:
		agent.reset()
	_actions.resize(agents * CopSenses.ACT_DIM)
	if selftest == 0 and not _connect():
		get_tree().quit(1)
		return
	_started = Time.get_ticks_msec()


func _physics_process(_delta: float) -> void:
	if _agents.is_empty():
		return
	_frame += 1
	if _frame % repeat != 0:
		return
	var dt: float = float(repeat) / float(Engine.physics_ticks_per_second)
	var packet: PackedFloat32Array = _collect(dt)
	_decisions += 1
	if selftest > 0:
		_random_actions()
		if _decisions >= selftest:
			_report_selftest()
			get_tree().quit()
			return
	else:
		_peer.put_32(packet.size() * 4)
		_peer.put_data(packet.to_byte_array())
		if not _receive():
			get_tree().quit()
			return
	for index: int in agents:
		CopSenses.apply(_cars[index], _actions, index * CopSenses.ACT_DIM)
	_since_city += 1
	if _since_city >= city_steps:
		_since_city = 0
		_new_city()


func _collect(dt: float) -> PackedFloat32Array:
	var obs_size: int = agents * CopSenses.OBS_DIM
	var packet := PackedFloat32Array()
	packet.resize(obs_size + agents * 2 + agents * TrainAgent.INFO_DIM)
	for index: int in agents:
		var result: Dictionary = _agents[index].step(dt, _cars)
		var obs: PackedFloat32Array = result["obs"]
		var base: int = index * CopSenses.OBS_DIM
		for k: int in CopSenses.OBS_DIM:
			packet[base + k] = obs[k]
		var reward: float = result["reward"]
		var done: bool = result["done"]
		packet[obs_size + index] = reward
		packet[obs_size + agents + index] = 1.0 if done else 0.0
		var info: PackedFloat32Array = result["info"]
		for k: int in TrainAgent.INFO_DIM:
			packet[obs_size + agents * 2 + index * TrainAgent.INFO_DIM + k] = info[k]
		_reward_sum += reward
		_speed_sum += info[1]
		_wall_sum += info[2]
		if done:
			_episodes += 1
	return packet


func _build_city() -> void:
	var settings := CityGenSettings.new()
	settings.city_seed = _rng.randi_range(1, 999999)
	settings.city_radius = radius
	var generator := RoadGenerator.new()
	var graph: RoadGraph = generator.generate(settings)
	var blocks: Array[CityBlocks.Block] = CityBlocks.build(graph, generator, settings)
	_city = CityBuilder.new()
	_city.name = "City"
	_city.collision_only = true
	add_child(_city)
	_city.build(settings, graph, generator, blocks)
	_nav = RoadNav.new(graph)


## Swaps in a fresh random city and restarts every cop on it; their current episodes are cut.
func _new_city() -> void:
	var old: CityBuilder = _city
	remove_child(old)
	old.queue_free()
	_build_city()
	for agent: TrainAgent in _agents:
		agent.nav = _nav
		agent.reset()
		agent.forced_end = true


func _make_car() -> LabVehicle:
	var car := LabVehicle.new()
	car.collision_layer = 4
	car.collision_mask = 15
	car.floor_snap_length = 0.5
	var shape := BoxShape3D.new()
	shape.size = Vector3(2.25, 1.6, 4.7)
	var holder := CollisionShape3D.new()
	holder.shape = shape
	holder.position.y = 0.8
	car.add_child(holder)
	car.tuning = (load(POLICE_TUNING) as VehicleTuning).duplicate() as VehicleTuning
	car.tuning.maximum_speed_mps = COP_TOP_SPEED
	car.handling = CarHandling.new()
	car.max_health = 1.0e9
	car.takes_damage = true
	car.add_to_group("police")
	add_child(car)
	if not OS.get_cmdline_user_args().has("--box"):
		car.chamfer_collider()
	return car


func _connect() -> bool:
	_peer = StreamPeerTCP.new()
	if _peer.connect_to_host("127.0.0.1", port) != OK:
		printerr("TRAIN_ENV cannot connect to port %d" % port)
		return false
	var waited: int = 0
	while _peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
		_peer.poll()
		OS.delay_msec(5)
		waited += 5
		if waited > 60000 or _peer.get_status() == StreamPeerTCP.STATUS_ERROR:
			printerr("TRAIN_ENV connection to port %d failed" % port)
			return false
	_peer.set_no_delay(true)
	var hello: Dictionary = {"obs_dim": CopSenses.OBS_DIM, "act_dim": CopSenses.ACT_DIM, "agents": agents,
		"info_dim": TrainAgent.INFO_DIM}
	_peer.put_data((JSON.stringify(hello) + "\n").to_utf8_buffer())
	return true


func _receive() -> bool:
	var needed: int = agents * CopSenses.ACT_DIM * 4
	while _peer.get_available_bytes() < needed:
		_peer.poll()
		if _peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
			return false
		OS.delay_usec(20)
	var result: Array = _peer.get_data(needed)
	if result[0] != OK:
		return false
	_actions = (result[1] as PackedByteArray).to_float32_array()
	return true


func _random_actions() -> void:
	for index: int in agents:
		var base: int = index * CopSenses.ACT_DIM
		_actions[base] = clampf(_actions[base] + _rng.randf_range(-0.3, 0.3), -1.0, 1.0)
		_actions[base + 1] = 0.85
		_actions[base + 2] = 1.0 if _rng.randf() < 0.03 else -1.0


func _report_selftest() -> void:
	var seconds: float = (Time.get_ticks_msec() - _started) / 1000.0
	var samples: float = float(_decisions * agents)
	print("TRAIN_SELFTEST decisions=%d agents=%d wall=%.1fs agent_steps_per_s=%.0f sim_speed=%.1fx mean_reward=%.3f mean_speed=%.1f wall_damage=%.1f episodes=%d" % [
		_decisions, agents, seconds, samples / seconds, (_decisions * 0.1) / seconds,
		_reward_sum / samples, _speed_sum / samples, _wall_sum, _episodes])
