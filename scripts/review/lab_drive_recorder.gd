class_name LabDriveRecorder
extends Node
## Saves the player's real driving as training data for the cops. J in the lab starts a chase and
## records the car 30 times a second; J again (or getting wrecked) saves it to training/drives/
## together with the exact city settings, so training can rebuild that city and replay the drive
## as the runner the cops practise chasing.

const RATE: int = 30
const FOLDER: String = "res://training/drives"

var player: LabVehicle
var chase: LabChase
var settings_source: Callable
var recording: bool = false
var last_saved: String = ""
var _frames: Array = []
var _tick: int = 0
var _started_seed: int = 0
var _settings: Dictionary = {}
var _wrecked: bool = false


func start() -> void:
	if recording:
		return
	var settings: CityGenSettings = settings_source.call()
	_settings = _settings_dict(settings)
	_started_seed = settings.city_seed
	_frames.clear()
	_tick = 0
	_wrecked = false
	recording = true
	if not chase.active or not chase.auto_spawn:
		chase.start()


func stop(wrecked: bool = false) -> String:
	if not recording:
		return ""
	recording = false
	_wrecked = wrecked
	if _frames.size() < RATE * 5:
		last_saved = ""
		return ""
	last_saved = _save()
	return last_saved


func seconds() -> float:
	return float(_frames.size()) / RATE


func _physics_process(_delta: float) -> void:
	if not recording:
		return
	_tick += 1
	if _tick % (Engine.physics_ticks_per_second / RATE) != 0:
		return
	var rotation: Quaternion = player.global_basis.get_rotation_quaternion()
	var p: Vector3 = player.global_position
	var v: Vector3 = player.velocity
	_frames.append([snappedf(p.x, 0.01), snappedf(p.y, 0.01), snappedf(p.z, 0.01),
		snappedf(rotation.x, 0.0001), snappedf(rotation.y, 0.0001), snappedf(rotation.z, 0.0001), snappedf(rotation.w, 0.0001),
		snappedf(v.x, 0.01), snappedf(v.y, 0.01), snappedf(v.z, 0.01)])


func _save() -> String:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(FOLDER))
	var stamp: String = Time.get_datetime_string_from_system().replace(":", "-").replace("T", "_")
	var path: String = "%s/drive_%s_seed%d.json" % [FOLDER, stamp, _started_seed]
	var data: Dictionary = {
		"version": 1,
		"rate": RATE,
		"frame_layout": ["x", "y", "z", "qx", "qy", "qz", "qw", "vx", "vy", "vz"],
		"seconds": seconds(),
		"wrecked": _wrecked,
		"chase_minute_at_end": snappedf(chase.minute(), 0.01),
		"city": _settings,
		"frames": _frames,
	}
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return ""
	file.store_string(JSON.stringify(data))
	return path


func _settings_dict(settings: CityGenSettings) -> Dictionary:
	var result: Dictionary = {}
	for property: Dictionary in settings.get_property_list():
		if property["usage"] & PROPERTY_USAGE_SCRIPT_VARIABLE:
			result[property["name"]] = settings.get(property["name"])
	return result
