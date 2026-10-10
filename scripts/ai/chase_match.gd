class_name ChaseMatch
extends RefCounted
## One chase in the training arena (scripts/ai/chase_arena.gd): a runner with the player's car
## (heavier, sharper handling, charge boost, 100 health) against 1-5 cops. Matches share the arena's
## city, but each has its own collision layer, so they drive through each other. A match ends when the
## runner explodes (cops win) or after MATCH_SECONDS (the runner survived). Cops join during a match
## (reinforcements) and leave when wrecked or left far behind, so squads change size mid-chase.
## Difficulty is a chase minute drawn per match: it sets cop top speed and burst recharge as in the lab.
##
## Slot 0 is the runner, slots 1-5 the cops. Every decision each slot reports its view, raw reward
## parts for what happened since its last action (training/train_chase.py weighs them), and flags
## (episode ended, slot active, ended by the clock not by anyone, navigation choice used this decision,
## this cop just wrecked: training lets it share the team's later result).
## How each car sees and acts is ChaseAgent (shared with the game).
##
## Reward parts, cop:    0 runner damage (team)  1 runner wrecked (team)  2 metres closed on the runner
##                       3 own wall damage  4 own damage from car hits  5 own wreck
##                       6 damage it dealt to the runner  7 damage it dealt to other cops
## Reward parts, runner: 0 alive (1 per decision)  1 damage taken  2 wrecked  3 damage dealt to cops
##                       4 cops wrecked  5 speed (m/s)  6 wall damage taken  7 survived to the end

const SLOTS: int = 6
const MAX_COPS: int = 5
const COMP_DIM: int = 8
const PRIV_DIM: int = 12
const FLAG_DIM: int = 5
const STATS_DIM: int = 26
## Stats summed over the arena between decisions (for training logs):
## 0 matches ended  1 runner wrecked  2 runner survived  3 runner damage  4 runner damage from cop hits
## 5 runner wall damage  6 cop wall damage  7 cop wrecks  8 cop-on-cop damage  9 runner speed sum
## 10 runner decisions  11 cop decisions  12 decisions the cops knew where the runner was
## 13 match seconds (summed at match end)  14 cop speed sum  15 damaging cop hits on the runner
## Abilities and controls (are they used, and do they work):
## 16 cop bursts fired  17 runner boosts fired  18 runner decisions spent charging  19 cop decisions drifting
## 20 runner decisions drifting  21 cop decisions on the handbrake  22 runner decisions on the handbrake
## 23 cop decisions reversing  24 damaging cop hits made during a burst  25 damaging runner hits on cops while boosting
const MATCH_SECONDS: float = 120.0
const RUNNER_TUNING: String = "res://resources/vehicles/red_muscle_car.tres"
const POLICE_TUNING: String = "res://resources/vehicles/patrol_car.tres"
const RUNNER_HEALTH: float = 100.0
const RUNNER_MASS: float = 1.6
const COP_HEALTH: float = 60.0
const BASE_TOP_SPEED: float = 34.0
const CATCH_UP_START: float = 25.0
const CATCH_UP_FULL: float = 85.0
const CATCH_UP_BOOST: float = 1.3
const RECYCLE_DISTANCE: float = 420.0
## Share of chases where the runner starts from a standstill (like the start of a real run) instead of
## already cruising, and share of cops that spawn parked and have to pull out.
const RUNNER_STANDING_START: float = 0.35
const COP_PARKED_START: float = 0.15
## Cop reaction delay, physics frames at 60 per second: 100-250 ms, drawn per cop (GT Sophy trained with
## similar delays and stayed superhuman; delayed cops have to predict instead of react).
const COP_DELAY_FRAMES := Vector2i(6, 15)
## Chance a match starts with 1, 2, 3, 4 or 5 cops.
const SQUAD_ODDS: PackedFloat32Array = [0.25, 0.25, 0.2, 0.15, 0.15]

var index: int = 0
var layer: int = 0
var nav: RoadNav
var rng: RandomNumberGenerator
var runner: LabVehicle
var cars: Array[LabVehicle] = []
var active: Array[bool] = []
var intel := ChaseIntel.new()
var minute: float = 0.0
var elapsed: float = 0.0
var target_cops: int = 1
## Ends the match at the next decision without blaming anyone (the arena swapped the city).
var abort: bool = false
## Filled by decide(): SLOTS rows each.
var obs := PackedFloat32Array()
var priv := PackedFloat32Array()
var parts := PackedFloat32Array()
var flags := PackedFloat32Array()
var stats := PackedFloat32Array()
var agents: Array[ChaseAgent] = []
var _respawn_wait := PackedFloat32Array()
var _last_gap := PackedFloat32Array()
var _pending := PackedFloat32Array()
var _accum := PackedFloat32Array()
var _sightings: Array[bool] = []
var _reinforce_clock: float = 0.0
var _burst_counts := PackedInt32Array()
var _dt: float = 0.1


func setup(match_index: int, parent: Node, road_nav: RoadNav, random: RandomNumberGenerator) -> void:
	index = match_index
	layer = 1 << (4 + match_index)
	nav = road_nav
	rng = random
	obs.resize(SLOTS * ChaseSenses.OBS_DIM)
	priv.resize(SLOTS * PRIV_DIM)
	parts.resize(SLOTS * COMP_DIM)
	flags.resize(SLOTS * FLAG_DIM)
	stats.resize(STATS_DIM)
	_accum.resize(SLOTS * COMP_DIM)
	_respawn_wait.resize(SLOTS)
	_last_gap.resize(SLOTS)
	_burst_counts.resize(SLOTS)
	_pending.resize(SLOTS)
	for slot: int in SLOTS:
		var car: LabVehicle = _make_car(slot == 0)
		parent.add_child(car)
		car.chamfer_collider()
		cars.append(car)
		active.append(false)
		var agent := ChaseAgent.new()
		agent.setup(car, slot == 0, nav, layer, rng)
		agents.append(agent)
		if slot == 0:
			car.damaged.connect(_on_runner_damaged)
			car.bumped.connect(_on_runner_bumped)
			car.boost_released.connect(func(_power: float) -> void: stats[17] += 1.0)
		else:
			car.damaged.connect(_on_cop_damaged.bind(slot))
			car.bumped.connect(_on_cop_bumped.bind(slot))
	runner = cars[0]
	restart()


## The arena swapped the city.
func set_nav(road_nav: RoadNav) -> void:
	nav = road_nav
	for agent: ChaseAgent in agents:
		agent.set_nav(road_nav)
	abort = true


## Starts a fresh chase: new difficulty, runner on a random road, the first cops around it.
func restart() -> void:
	abort = false
	elapsed = 0.0
	minute = rng.randf_range(0.0, 15.0)
	target_cops = _squad_size()
	_reinforce_clock = rng.randf_range(20.0, 40.0)
	for slot: int in range(1, SLOTS):
		_deactivate(slot)
	_respawn_wait.fill(0.0)
	var spot: Dictionary = nav.random_road_spot(rng)
	var point: Vector2 = spot.get("point", Vector2.ZERO)
	var dir: Vector2 = spot.get("dir", Vector2(0.0, -1.0))
	_place(runner, point, dir, 0.0 if rng.randf() < RUNNER_STANDING_START else rng.randf_range(15.0, 30.0))
	runner.health = RUNNER_HEALTH
	active[0] = true
	agents[0].reset()
	intel.reset(runner)
	for count: int in target_cops:
		_spawn_cop(_free_slot(), count == 0 or rng.randf() < 0.3)
	_accum.fill(0.0)
	_pending.fill(0.0)


## One decision: settles what happened since the last one (rewards, wrecks, the match ending), brings
## in reinforcements, updates what the cops know, and fills obs/priv/parts/flags.
func decide(dt: float) -> void:
	_dt = dt
	elapsed += dt
	parts = _accum.duplicate()
	_accum.fill(0.0)
	flags.fill(0.0)
	var here: Vector2 = _flat(runner.global_position)
	for slot: int in range(1, SLOTS):
		if not active[slot]:
			_respawn_wait[slot] -= dt
			continue
		var gap: float = _flat(cars[slot].global_position).distance_to(here)
		parts[slot * COMP_DIM + 2] = clampf(_last_gap[slot] - gap, -10.0, 10.0)
		_last_gap[slot] = gap
		var wrecked: bool = cars[slot].health <= 0.0 or cars[slot].global_position.y < -3.0
		if wrecked or gap > RECYCLE_DISTANCE:
			if wrecked:
				parts[slot * COMP_DIM + 5] += 1.0
				parts[4] += 1.0
				stats[7] += 1.0
				flags[slot * FLAG_DIM + 4] = 1.0
			flags[slot * FLAG_DIM] = 1.0
			_deactivate(slot)
			_respawn_wait[slot] = rng.randf_range(3.0, 8.0)
	var ended: bool = false
	var truncated: bool = false
	var speed: float = Vector2(runner.velocity.x, runner.velocity.z).length()
	parts[5] = speed
	stats[9] += speed
	stats[10] += 1.0
	if runner.health <= 0.0:
		parts[2] += 1.0
		for slot: int in range(1, SLOTS):
			if active[slot]:
				parts[slot * COMP_DIM + 1] += 1.0
		ended = true
		stats[1] += 1.0
	else:
		parts[0] += 1.0
		if abort or runner.global_position.y < -3.0:
			ended = true
			truncated = true
		elif elapsed >= MATCH_SECONDS:
			parts[7] += 1.0
			ended = true
			truncated = true
			stats[2] += 1.0
	if ended:
		stats[0] += 1.0
		stats[13] += elapsed
		for slot: int in SLOTS:
			if active[slot]:
				flags[slot * FLAG_DIM] = 1.0
				flags[slot * FLAG_DIM + 2] = 1.0 if truncated else 0.0
		restart()
	else:
		_reinforce(dt)
	var cops: Array = _active_cops()
	_sightings = intel.update(cops, runner, dt)
	if intel.known:
		stats[12] += 1.0
	_observe(dt, cops)


## Delivers delayed controls. Call every physics frame.
func physics_tick() -> void:
	for slot: int in SLOTS:
		if active[slot]:
			agents[slot].physics_tick()


## Applies the actions for this match's slots, which start at `base` in the action array.
func act(actions: PackedFloat32Array, base: int) -> void:
	var here: Vector2 = _flat(runner.global_position)
	var heading: Vector2 = _forward(runner)
	for slot: int in SLOTS:
		if not active[slot]:
			continue
		var offset: int = base + slot * ChaseSenses.ACT_DIM
		var handbrake: bool = actions[offset + 2] > 0.5
		agents[slot].apply(actions, offset)
		if slot == 0:
			stats[18] += 1.0 if runner.boost.phase == ChargeBoost.Phase.CHARGING else 0.0
			stats[20] += 1.0 if runner.drifting else 0.0
			stats[22] += 1.0 if handbrake else 0.0
			continue
		var cop: LabVehicle = cars[slot]
		stats[16] += agents[slot].burst.fire_count - _burst_counts[slot]
		_burst_counts[slot] = agents[slot].burst.fire_count
		stats[19] += 1.0 if cop.drifting else 0.0
		stats[21] += 1.0 if handbrake else 0.0
		stats[23] += 1.0 if cop.forward_speed < -1.0 else 0.0
		var at: Vector2 = _flat(cop.global_position)
		var distance: float = at.distance_to(here)
		var behind: bool = heading.dot(at - here) < 0.0
		var lag: float = clampf((distance - CATCH_UP_START) / (CATCH_UP_FULL - CATCH_UP_START), 0.0, 1.0) if behind else 0.0
		cop.tuning.maximum_speed_mps = cop_top_speed() * lerpf(1.0, CATCH_UP_BOOST, lag) * (CopBurst.SPEED_GAIN if agents[slot].burst.active() else 1.0)


## Simple scripted driving, for self-tests and as the fixed "scripted" opponent in training exams: the
## runner follows its route, cops drive at where they think the runner is and burst when close and
## lined up; navigation choices are random. With `only_marked`, only slots whose navigation action is
## -1 (Python's "drive this one with the script") are filled.
func autopilot(actions: PackedFloat32Array, base: int, only_marked: bool = false) -> void:
	var believed: Vector2 = intel.believed_position()
	for slot: int in SLOTS:
		var offset: int = base + slot * ChaseSenses.ACT_DIM
		if not active[slot] or (only_marked and actions[offset + 4] > -0.5):
			continue
		var car: LabVehicle = cars[slot]
		var here: Vector2 = _flat(car.global_position)
		var aim: Vector2 = agents[slot].route.point_at(agents[slot].progress + 18.0)
		var close: bool = slot > 0 and here.distance_to(believed) < 45.0
		if close:
			aim = believed + intel.last_velocity * 0.4
		var angle: float = _forward(car).angle_to(aim - here)
		actions[offset] = clampf(angle / 0.6, -1.0, 1.0)
		actions[offset + 1] = 1.0 if absf(angle) < 2.2 or car.forward_speed > 6.0 else -1.0
		actions[offset + 2] = 1.0 if absf(angle) > 0.7 and car.forward_speed > 16.0 else 0.0
		actions[offset + 3] = 1.0 if close and absf(angle) < 0.3 else 0.0
		if slot == 0:
			actions[offset + 3] = float(rng.randi_range(1, 4)) if rng.randf() < 0.03 else 0.0
		actions[offset + 4] = float(rng.randi_range(0, ChaseNav.OPTIONS - 1))


func cop_top_speed() -> float:
	return BASE_TOP_SPEED * minf(0.97 + 0.025 * minute, 1.3)


func active_cop_count() -> int:
	return _active_cops().size()


func _observe(dt: float, cops: Array) -> void:
	obs.fill(0.0)
	priv.fill(0.0)
	var here: Vector2 = _flat(runner.global_position)
	var match_cars: Array = [runner]
	match_cars.append_array(cops)
	var bursting: Array = []
	for cop: LabVehicle in cops:
		bursting.append(agents[cars.find(cop)].burst.active())
	var time_left: float = 1.0 - clampf(elapsed / MATCH_SECONDS, 0.0, 1.0)
	var pending: float = maxf(target_cops - cops.size(), 0.0) / 5.0
	var view: PackedFloat32Array = agents[0].observe_runner(dt, match_cars, cops, bursting, intel)
	_copy(obs, 0, view, ChaseSenses.OBS_DIM)
	flags[1] = 1.0
	flags[3] = 1.0 if agents[0].navigation.open else 0.0
	var gaps: Array = []
	var near: int = 0
	var cop_speed: float = 0.0
	for cop: LabVehicle in cops:
		var gap: float = _flat(cop.global_position).distance_to(here)
		gaps.append(gap)
		if gap < 50.0:
			near += 1
		cop_speed += Vector2(cop.velocity.x, cop.velocity.z).length()
	gaps.sort()
	var runner_priv: PackedFloat32Array = [time_left, cops.size() / 5.0, _gap_feature(gaps, 0), _gap_feature(gaps, 1),
		1.0 if intel.known else 0.0, clampf(intel.age / ChaseIntel.PING_SECONDS, 0.0, 1.0),
		runner.health / RUNNER_HEALTH, near / 5.0, cop_speed / maxf(cops.size(), 1) / 40.0, minute / 15.0, pending,
		1.0 if bursting.has(true) else 0.0]
	_copy(priv, 0, runner_priv, PRIV_DIM)
	stats[11] += cops.size()
	stats[14] += cop_speed
	var team_options: Dictionary = {}
	for cop: LabVehicle in cops:
		team_options[cop] = agents[cars.find(cop)].navigation.option
	var best_gap: float = gaps[0] if not gaps.is_empty() else 999.0
	for k: int in cops.size():
		var cop: LabVehicle = cops[k]
		var slot: int = cars.find(cop)
		flags[slot * FLAG_DIM + 1] = 1.0
		var team: Array = cops.duplicate()
		team.erase(cop)
		view = agents[slot].observe_cop(dt, match_cars, intel, _sightings[k], runner, team, cops.size(), team_options)
		flags[slot * FLAG_DIM + 3] = 1.0 if agents[slot].navigation.open else 0.0
		_copy(obs, slot * ChaseSenses.OBS_DIM, view, ChaseSenses.OBS_DIM)
		var forward: Vector2 = _forward(cop)
		var right := Vector2(-forward.y, forward.x)
		var offset: Vector2 = here - _flat(cop.global_position)
		var motion := Vector2(runner.velocity.x, runner.velocity.z)
		var cop_priv: PackedFloat32Array = [clampf(offset.dot(right) / 100.0, -3.0, 3.0),
			clampf(offset.dot(forward) / 100.0, -3.0, 3.0), motion.dot(right) / 40.0, motion.dot(forward) / 40.0,
			clampf(offset.length() / 150.0, 0.0, 3.0), runner.health / RUNNER_HEALTH, 1.0 if intel.known else 0.0,
			time_left, clampf(best_gap / 150.0, 0.0, 3.0), cops.size() / 5.0, ChaseSenses._boost_state(runner), pending]
		_copy(priv, slot * PRIV_DIM, cop_priv, PRIV_DIM)


func _gap_feature(gaps: Array, k: int) -> float:
	return clampf(gaps[k] / 150.0, 0.0, 3.0) if k < gaps.size() else 3.0


func _reinforce(dt: float) -> void:
	_reinforce_clock -= dt
	if _reinforce_clock <= 0.0:
		_reinforce_clock = rng.randf_range(20.0, 40.0)
		if rng.randf() < 0.5:
			target_cops = mini(target_cops + 1, MAX_COPS)
	if active_cop_count() >= target_cops:
		return
	var slot: int = _free_slot()
	if slot > 0 and _respawn_wait[slot] <= 0.0:
		_spawn_cop(slot, rng.randf() < 0.35)


## Cops arrive out of sight: behind on your road, or ahead and from side streets, like the lab chase.
func _spawn_cop(slot: int, behind: bool) -> bool:
	if slot <= 0:
		return false
	var here: Vector2 = _flat(runner.global_position)
	var heading: Vector2 = _forward(runner)
	var near: float = 40.0 if behind else 110.0
	var far: float = 110.0 if behind else 280.0
	var graph: RoadGraph = nav.graph
	var edges: PackedInt32Array = graph.edges_in(Rect2(here, Vector2.ZERO).grow(far))
	if edges.is_empty():
		return false
	for attempt: int in 60:
		var id: int = edges[rng.randi() % edges.size()]
		if graph.edge_alive[id] == 0:
			continue
		var a: Vector2 = graph.positions[graph.edge_a[id]]
		var b: Vector2 = graph.positions[graph.edge_b[id]]
		var point: Vector2 = a.lerp(b, rng.randf_range(0.2, 0.8))
		var distance: float = point.distance_to(here)
		if distance < near or distance > far:
			continue
		var side: float = heading.dot((point - here).normalized())
		if attempt < 40 and ((behind and side > -0.3) or (not behind and side < 0.1)):
			continue
		var crowded: bool = false
		for other: LabVehicle in _active_cops():
			if _flat(other.global_position).distance_to(point) < 25.0:
				crowded = true
				break
		if crowded:
			continue
		var dir: Vector2 = (b - a).normalized()
		var start_speed: float = 22.0
		if absf(dir.dot(heading)) > 0.5:
			if dir.dot(heading) < 0.0:
				dir = -dir
		else:
			if dir.dot(here + heading * distance - point) < 0.0:
				dir = -dir
			start_speed = 12.0
		var cop: LabVehicle = cars[slot]
		cop.process_mode = Node.PROCESS_MODE_INHERIT
		cop.collision_layer = layer
		cop.collision_mask = 1 | layer
		_place(cop, point, dir, 0.0 if rng.randf() < COP_PARKED_START else start_speed)
		cop.health = COP_HEALTH
		cop.tuning.maximum_speed_mps = cop_top_speed()
		active[slot] = true
		agents[slot].reset()
		agents[slot].burst.cooldown = CopBurst.cooldown_at(minute)
		agents[slot].delay_frames = rng.randi_range(COP_DELAY_FRAMES.x, COP_DELAY_FRAMES.y)
		_burst_counts[slot] = agents[slot].burst.fire_count
		_last_gap[slot] = distance
		_pending[slot] = 0.0
		for k: int in COMP_DIM:
			_accum[slot * COMP_DIM + k] = 0.0
		return true
	return false


func _deactivate(slot: int) -> void:
	var car: LabVehicle = cars[slot]
	active[slot] = false
	car.controls_enabled = false
	car.collision_layer = 0
	car.collision_mask = 0
	car.velocity = Vector3.ZERO
	car.forward_speed = 0.0
	car.global_position = Vector3(index * 12.0, -200.0, slot * 12.0)
	car.process_mode = Node.PROCESS_MODE_DISABLED


func _place(car: LabVehicle, point: Vector2, dir: Vector2, speed: float) -> void:
	car.reset_vehicle(Vector3(point.x, 0.25, point.y))
	car.rotation.y = atan2(-dir.x, -dir.y)
	car.forward_speed = speed
	car.velocity = Vector3(dir.x, 0.0, dir.y) * speed
	car.spin = 0.0
	car.stagger = 0.0
	car.reset_physics_interpolation()
	car.controls_enabled = true


func _free_slot() -> int:
	for slot: int in range(1, SLOTS):
		if not active[slot]:
			return slot
	return -1


func _active_cops() -> Array:
	var result: Array = []
	for slot: int in range(1, SLOTS):
		if active[slot]:
			result.append(cars[slot])
	return result


func _squad_size() -> int:
	var roll: float = rng.randf()
	for size: int in SQUAD_ODDS.size():
		roll -= SQUAD_ODDS[size]
		if roll <= 0.0:
			return size + 1
	return MAX_COPS


func _make_car(is_runner: bool) -> LabVehicle:
	var car := LabVehicle.new()
	car.collision_layer = layer
	car.collision_mask = 1 | layer
	car.floor_snap_length = 0.5
	var shape := BoxShape3D.new()
	shape.size = Vector3(2.3, 1.72, 4.95) if is_runner else Vector3(2.25, 1.6, 4.7)
	var holder := CollisionShape3D.new()
	holder.shape = shape
	holder.position.y = shape.size.y * 0.5
	car.add_child(holder)
	car.tuning = (load(RUNNER_TUNING if is_runner else POLICE_TUNING) as VehicleTuning).duplicate() as VehicleTuning
	var handling := CarHandling.new()
	if is_runner:
		car.mass = RUNNER_MASS
		car.max_health = RUNNER_HEALTH
	else:
		# Same handling as the lab's cops (scripts/review/lab_chase.gd).
		handling.steer_low_speed = 2.6
		handling.steer_top_speed = 2.1
		handling.grip = 11.0
		handling.steer_response = 9.0
		car.max_health = COP_HEALTH
		car.add_to_group("police")
	car.handling = handling
	car.takes_damage = true
	return car


func _on_runner_damaged(amount: float, source: String) -> void:
	stats[3] += amount
	for slot: int in range(1, SLOTS):
		if active[slot]:
			_accum[slot * COMP_DIM] += amount
	_accum[1] += amount
	if source == "crash":
		_accum[6] += amount
		stats[5] += amount
	else:
		_pending[0] = amount
		stats[4] += amount


func _on_runner_bumped(other: LabVehicle, _strength: float) -> void:
	var slot: int = cars.find(other)
	if slot > 0 and _pending[0] > 0.0:
		_accum[slot * COMP_DIM + 6] += _pending[0]
		stats[15] += 1.0
		stats[24] += 1.0 if agents[slot].burst.active() else 0.0
	_pending[0] = 0.0


func _on_cop_damaged(amount: float, source: String, slot: int) -> void:
	if source == "crash":
		_accum[slot * COMP_DIM + 3] += amount
		stats[6] += amount
	else:
		_accum[slot * COMP_DIM + 4] += amount
		_pending[slot] = amount


func _on_cop_bumped(other: LabVehicle, _strength: float, slot: int) -> void:
	var damage: float = _pending[slot]
	_pending[slot] = 0.0
	if damage <= 0.0:
		return
	if other == runner:
		_accum[3] += damage
		stats[25] += 1.0 if runner.boost.phase == ChargeBoost.Phase.BOOSTING else 0.0
		return
	var by: int = cars.find(other)
	if by > 0:
		_accum[by * COMP_DIM + 7] += damage
		stats[8] += damage


static func _copy(into: PackedFloat32Array, at: int, values: PackedFloat32Array, count: int) -> void:
	for k: int in mini(count, values.size()):
		into[at + k] = values[k]


static func _flat(v: Vector3) -> Vector2:
	return Vector2(v.x, v.z)


static func _forward(car: Node3D) -> Vector2:
	return Vector2(-car.global_basis.z.x, -car.global_basis.z.z).normalized()
