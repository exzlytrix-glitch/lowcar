class_name RunScore
extends Node
## Chaos points for one chase, from the user's list: cops wrecked, time survived, near misses, and
## surviving (a bonus for every full minute, bigger each minute, so long runs pay off).

signal scored(label: String, points: int)

const POINTS_PER_SECOND: int = 10
const COP_WRECK: int = 250
const NEAR_MISS: int = 75
## Minute n survived pays n × MINUTE_BONUS.
const MINUTE_BONUS: int = 100
## A cop passing within this many metres (centre to centre) at this closing speed, without touching.
const NEAR_DISTANCE: float = 5.2
const NEAR_SPEED: float = 11.0
const CLEAR_DISTANCE: float = 9.0
const NEAR_COOLDOWN: float = 2.5

var running: bool = false
var seconds: float = 0.0
var cops_wrecked: int = 0
var near_misses: int = 0
var minutes: int = 0
var minute_points: int = 0
var top_speed: float = 0.0
var player: LabVehicle
## Cop → {"close", "fast", "touched", "cooldown"} while it is near you.
var _passes: Dictionary = {}


func start(car: LabVehicle) -> void:
	if is_instance_valid(player) and player.bumped.is_connected(_on_bumped):
		player.bumped.disconnect(_on_bumped)
	player = car
	player.bumped.connect(_on_bumped)
	running = true
	seconds = 0.0
	cops_wrecked = 0
	near_misses = 0
	minutes = 0
	minute_points = 0
	top_speed = 0.0
	_passes.clear()


func stop() -> void:
	running = false


func time_points() -> int:
	return int(seconds) * POINTS_PER_SECOND


func total() -> int:
	return time_points() + cops_wrecked * COP_WRECK + near_misses * NEAR_MISS + minute_points


func cop_wrecked() -> void:
	if not running:
		return
	cops_wrecked += 1
	scored.emit("COP WRECKED", COP_WRECK)


func tick(delta: float, cops: Array[LabVehicle]) -> void:
	if not running or not is_instance_valid(player):
		return
	seconds += delta
	top_speed = maxf(top_speed, Vector2(player.velocity.x, player.velocity.z).length())
	if int(seconds / 60.0) > minutes:
		minutes = int(seconds / 60.0)
		minute_points += minutes * MINUTE_BONUS
		scored.emit("%d MINUTE%s SURVIVED" % [minutes, "" if minutes == 1 else "S"], minutes * MINUTE_BONUS)
	_check_near_misses(delta, cops)


func _check_near_misses(delta: float, cops: Array[LabVehicle]) -> void:
	var here := Vector2(player.global_position.x, player.global_position.z)
	var going := Vector2(player.velocity.x, player.velocity.z)
	for cop: Variant in _passes.keys():
		if not is_instance_valid(cop) or not cops.has(cop):
			_passes.erase(cop)
	for cop: LabVehicle in cops:
		var at := Vector2(cop.global_position.x, cop.global_position.z)
		var distance: float = at.distance_to(here)
		var state: Dictionary = _passes.get(cop, {"close": false, "fast": false, "touched": false, "cooldown": 0.0})
		state["cooldown"] = maxf(float(state["cooldown"]) - delta, 0.0)
		if distance < NEAR_DISTANCE:
			state["close"] = true
			var closing: float = (going - Vector2(cop.velocity.x, cop.velocity.z)).length()
			if closing > NEAR_SPEED:
				state["fast"] = true
		elif distance > CLEAR_DISTANCE and state["close"]:
			if state["fast"] and not state["touched"] and float(state["cooldown"]) <= 0.0:
				near_misses += 1
				scored.emit("NEAR MISS", NEAR_MISS)
				state["cooldown"] = NEAR_COOLDOWN
			state["close"] = false
			state["fast"] = false
			state["touched"] = false
		_passes[cop] = state


func _on_bumped(other: LabVehicle, _strength: float) -> void:
	if _passes.has(other):
		_passes[other]["touched"] = true
	else:
		_passes[other] = {"close": true, "fast": false, "touched": true, "cooldown": 0.0}
