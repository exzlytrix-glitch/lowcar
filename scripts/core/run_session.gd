extends Node
## Owns one run's state. Scene-local systems handle driving, streaming, and chase AI.

signal phase_changed(phase: Phase)
signal run_started(seed_value: int)
signal run_ended(reason: String)
signal stats_changed
signal pursuit_changed(tier: int)

enum Phase { MENU, DRIVING, PAUSED, ENDED }

var phase: Phase = Phase.MENU
var city_seed: int = 142857
var distance_m: float = 0.0
var elapsed_s: float = 0.0
var pursuit_tier: int = 1
var active_police_count: int = 0
var capture_progress: float = 0.0
var end_reason: String = ""
var _stats_clock: float = 0.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS


func begin_run(seed_value: int) -> void:
	city_seed = seed_value
	distance_m = 0.0
	elapsed_s = 0.0
	pursuit_tier = 1
	active_police_count = 0
	capture_progress = 0.0
	end_reason = ""
	_stats_clock = 0.0
	get_tree().paused = false
	_set_phase(Phase.DRIVING)
	run_started.emit(city_seed)
	stats_changed.emit()
	pursuit_changed.emit(pursuit_tier)


func advance(delta: float, travelled_m: float) -> void:
	if phase != Phase.DRIVING:
		return
	elapsed_s += delta
	distance_m += maxf(travelled_m, 0.0)
	_stats_clock += delta
	if _stats_clock >= 0.1:
		_stats_clock = 0.0
		stats_changed.emit()


func set_pursuit_tier(tier: int) -> void:
	pursuit_tier = maxi(tier, 1)
	pursuit_changed.emit(pursuit_tier)


func toggle_pause() -> void:
	if phase == Phase.DRIVING:
		_set_phase(Phase.PAUSED)
		get_tree().paused = true
	elif phase == Phase.PAUSED:
		get_tree().paused = false
		_set_phase(Phase.DRIVING)


func end_run(reason: String) -> void:
	if phase != Phase.DRIVING:
		return
	end_reason = reason
	_set_phase(Phase.ENDED)
	run_ended.emit(reason)


func return_to_menu() -> void:
	get_tree().paused = false
	_set_phase(Phase.MENU)


func _set_phase(next_phase: Phase) -> void:
	phase = next_phase
	phase_changed.emit(phase)
