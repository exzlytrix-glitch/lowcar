extends Node3D
## Headless training world for the chase: learned cops vs a learned runner (training/train_chase.py).
## Several chases (scripts/ai/chase_match.gd) run at once in one random city, each on its own
## collision layer. The city is swapped every few minutes so nobody memorises streets.
##
## Args after "--": --port=N --matches=6 --seed=1 --repeat=6 --city-steps=3000 --radius=450
## --selftest=STEPS drives every slot with simple scripted driving (no Python) and prints a report.
## --eval=STEPS does the same with trained brains driving exactly as in the game (their best guess, no
## randomness): --cop-brain=PATH --runner-brain=PATH, default resources/ai/chase_*_brain.json.
##
## Wire format (little endian): on connect one JSON line describing the sizes. Then per decision Godot
## sends int32 byte count + float32[obs S*O, priv S*P, parts S*C, flags S*5 (done, active, truncated,
## navigation choice used, cop just wrecked), stats T] for S = matches * 6 slots (slot 0 of each match is
## the runner), and Python answers with float32[S*5] actions in ChaseAgent's wire order; a navigation
## value of -1 means "drive this slot with the scripted autopilot" (the fixed exam opponent).

var port: int = 0
var matches: int = 6
var seed_value: int = 1
var repeat: int = 6
var city_steps: int = 3000
var radius: float = 450.0
var selftest: int = 0
var cop_brain_path: String = "res://resources/ai/chase_cop_brain.json"
var runner_brain_path: String = "res://resources/ai/chase_runner_brain.json"
var _cop_net: PolicyNet
var _runner_net: PolicyNet
var _peer: StreamPeerTCP
var _rng := RandomNumberGenerator.new()
var _city: CityBuilder
var _nav: RoadNav
var _matches: Array[ChaseMatch] = []
var _actions := PackedFloat32Array()
var _frame: int = 0
var _decisions: int = 0
var _since_city: int = 0
var _started: int = 0
var _totals := PackedFloat32Array()


func _ready() -> void:
	for argument: String in OS.get_cmdline_user_args():
		var value: String = argument.get_slice("=", 1)
		match argument.get_slice("=", 0):
			"--port":
				port = int(value)
			"--matches":
				matches = clampi(int(value), 1, 27)
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
			"--eval":
				selftest = int(value)
				_cop_net = PolicyNet.new()
			"--cop-brain":
				cop_brain_path = value
			"--runner-brain":
				runner_brain_path = value
	if _cop_net != null:
		_cop_net = PolicyNet.load_file(cop_brain_path)
		_runner_net = PolicyNet.load_file(runner_brain_path)
		if _cop_net == null or _runner_net == null:
			printerr("CHASE_ARENA cannot load brains %s / %s" % [cop_brain_path, runner_brain_path])
			get_tree().quit(1)
			return
	_rng.seed = seed_value
	var built: int = Time.get_ticks_msec()
	_build_city()
	print("CHASE_ARENA city built in %d ms (%d buildings)" % [Time.get_ticks_msec() - built, _city.building_count])
	for index: int in matches:
		var chase := ChaseMatch.new()
		chase.setup(index, self, _nav, _rng)
		_matches.append(chase)
	_actions.resize(slots() * ChaseSenses.ACT_DIM)
	_totals.resize(ChaseMatch.STATS_DIM)
	if selftest == 0 and not _connect():
		get_tree().quit(1)
		return
	_started = Time.get_ticks_msec()


func slots() -> int:
	return matches * ChaseMatch.SLOTS


func _physics_process(_delta: float) -> void:
	if _matches.is_empty():
		return
	for chase: ChaseMatch in _matches:
		chase.physics_tick()
	_frame += 1
	if _frame % repeat != 0:
		return
	var dt: float = float(repeat) / float(Engine.physics_ticks_per_second)
	var packet: PackedFloat32Array = _collect(dt)
	_decisions += 1
	if selftest > 0:
		for index: int in matches:
			if _cop_net != null:
				_brain_actions(_matches[index], index * ChaseMatch.SLOTS * ChaseSenses.ACT_DIM)
			else:
				_matches[index].autopilot(_actions, index * ChaseMatch.SLOTS * ChaseSenses.ACT_DIM)
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
		for index: int in matches:
			_matches[index].autopilot(_actions, index * ChaseMatch.SLOTS * ChaseSenses.ACT_DIM, true)
	for index: int in matches:
		_matches[index].act(_actions, index * ChaseMatch.SLOTS * ChaseSenses.ACT_DIM)
	_since_city += 1
	if _since_city >= city_steps:
		_since_city = 0
		_new_city()


func _collect(dt: float) -> PackedFloat32Array:
	var s: int = slots()
	var o: int = ChaseSenses.OBS_DIM
	var p: int = ChaseMatch.PRIV_DIM
	var c: int = ChaseMatch.COMP_DIM
	var f: int = ChaseMatch.FLAG_DIM
	var t: int = ChaseMatch.STATS_DIM
	var packet := PackedFloat32Array()
	packet.resize(s * (o + p + c + f) + t)
	var priv_at: int = s * o
	var parts_at: int = priv_at + s * p
	var flags_at: int = parts_at + s * c
	var stats_at: int = flags_at + s * f
	for index: int in matches:
		var chase: ChaseMatch = _matches[index]
		chase.decide(dt)
		var first: int = index * ChaseMatch.SLOTS
		_put(packet, first * o, chase.obs)
		_put(packet, priv_at + first * p, chase.priv)
		_put(packet, parts_at + first * c, chase.parts)
		_put(packet, flags_at + first * f, chase.flags)
		for k: int in t:
			packet[stats_at + k] += chase.stats[k]
			_totals[k] += chase.stats[k]
		chase.stats.fill(0.0)
	return packet


func _brain_actions(chase: ChaseMatch, base: int) -> void:
	for slot: int in ChaseMatch.SLOTS:
		if not chase.active[slot]:
			continue
		var at: int = slot * ChaseSenses.OBS_DIM
		var net: PolicyNet = _runner_net if slot == 0 else _cop_net
		var action: PackedFloat32Array = net.decide(chase.obs.slice(at, at + ChaseSenses.OBS_DIM), _rng)
		for k: int in ChaseSenses.ACT_DIM:
			_actions[base + slot * ChaseSenses.ACT_DIM + k] = action[k]


static func _put(packet: PackedFloat32Array, at: int, values: PackedFloat32Array) -> void:
	for k: int in values.size():
		packet[at + k] = values[k]


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


## Swaps in a fresh random city; every match is cut short (no blame) at its next decision.
func _new_city() -> void:
	var old: CityBuilder = _city
	remove_child(old)
	old.queue_free()
	_build_city()
	for chase: ChaseMatch in _matches:
		chase.set_nav(_nav)


func _connect() -> bool:
	_peer = StreamPeerTCP.new()
	if _peer.connect_to_host("127.0.0.1", port) != OK:
		printerr("CHASE_ARENA cannot connect to port %d" % port)
		return false
	var waited: int = 0
	while _peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
		_peer.poll()
		OS.delay_msec(5)
		waited += 5
		if waited > 60000 or _peer.get_status() == StreamPeerTCP.STATUS_ERROR:
			printerr("CHASE_ARENA connection to port %d failed" % port)
			return false
	_peer.set_no_delay(true)
	var hello: Dictionary = {"mode": "chase", "slots": slots(), "matches": matches,
		"slots_per_match": ChaseMatch.SLOTS, "obs_dim": ChaseSenses.OBS_DIM, "cop_obs": ChaseSenses.COP_OBS,
		"runner_obs": ChaseSenses.RUNNER_OBS, "priv_dim": ChaseMatch.PRIV_DIM, "comp_dim": ChaseMatch.COMP_DIM,
		"flag_dim": ChaseMatch.FLAG_DIM, "act_dim": ChaseSenses.ACT_DIM, "stats_dim": ChaseMatch.STATS_DIM}
	_peer.put_data((JSON.stringify(hello) + "\n").to_utf8_buffer())
	return true


func _receive() -> bool:
	var needed: int = slots() * ChaseSenses.ACT_DIM * 4
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


func _report_selftest() -> void:
	var seconds: float = (Time.get_ticks_msec() - _started) / 1000.0
	var t := _totals
	var ended: float = maxf(t[0], 1.0)
	var runner_minutes: float = maxf(t[10] * 0.1 / 60.0, 0.001)
	var cop_minutes: float = maxf(t[11] * 0.1 / 60.0, 0.001)
	var active_slots: float = t[10] + t[11]
	print("CHASE_SELFTEST decisions=%d matches=%d wall=%.1fs slot_steps_per_s=%.0f sim_speed=%.1fx" % [
		_decisions, matches, seconds, active_slots / seconds, (_decisions * 0.1) / seconds])
	print("CHASE_SELFTEST ended=%d wrecked=%d survived=%d avg_match=%.0fs runner_kmh=%.0f cops_per_match=%.1f known=%.0f%%" % [
		t[0], t[1], t[2], t[13] / ended, t[9] / maxf(t[10], 1.0) * 3.6, t[11] / maxf(t[10], 1.0), t[12] / maxf(t[10], 1.0) * 100.0])
	print("CHASE_SELFTEST runner damage/min: total=%.1f from_cops=%.1f walls=%.1f damaging_hits=%d | cop wall dmg/cop-min=%.1f cop_wrecks=%d cop_on_cop=%.1f cop_kmh=%.0f" % [
		t[3] / runner_minutes, t[4] / runner_minutes, t[5] / runner_minutes, t[15], t[6] / cop_minutes, t[7], t[8],
		t[14] / maxf(t[11], 1.0) * 3.6])
	var runner_decisions: float = maxf(t[10], 1.0)
	var cop_decisions: float = maxf(t[11], 1.0)
	print("CHASE_SELFTEST abilities: cop bursts/cop-min=%.2f (landed a hit: %d) | runner boosts/min=%.2f (charging %.0f%% of the time, boost rams %d)" % [
		t[16] / cop_minutes, t[24], t[17] / runner_minutes, t[18] / runner_decisions * 100.0, t[25]])
	print("CHASE_SELFTEST controls: drifting cops %.1f%% runner %.1f%% | handbrake cops %.1f%% runner %.1f%% | cops reversing %.1f%%" % [
		t[19] / cop_decisions * 100.0, t[20] / runner_decisions * 100.0, t[21] / cop_decisions * 100.0,
		t[22] / runner_decisions * 100.0, t[23] / cop_decisions * 100.0])
