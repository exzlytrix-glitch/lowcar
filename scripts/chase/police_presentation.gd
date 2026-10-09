class_name PolicePresentation
extends Node3D
## Belle Rive fleet sedan; smooth travel with a twelve-pose-per-second body lean.
static var _siren_stream: AudioStreamWAV
var _vehicle: ArcadeVehicle
var _chassis: Node3D
var _wheels: Array[Node3D] = []
var _front_steers: Array[Node3D] = []
var _red: StandardMaterial3D
var _blue: StandardMaterial3D
var _clock: float = 0.0
var _pose_clock: float = 0.0
var _siren: AudioStreamPlayer3D

func _ready() -> void:
	_vehicle = get_parent() as ArcadeVehicle
	var model := $Model/Belle_Rive_Police_Cruiser
	_chassis = model.get_node("Chassis") as Node3D
	for wheel: Node in model.get_node("Wheels").get_children():
		var steer := wheel.get_node(String(wheel.name) + "Steer") as Node3D
		_wheels.append(steer.get_node(String(wheel.name) + "Spin") as Node3D)
		if String(wheel.name).begins_with("Front"):
			_front_steers.append(steer)
	var red_mesh := _chassis.get_node("RedLight/RedLightMesh") as MeshInstance3D
	var blue_mesh := _chassis.get_node("BlueLight/BlueLightMesh") as MeshInstance3D
	_red = red_mesh.get_active_material(0).duplicate() as StandardMaterial3D
	_blue = blue_mesh.get_active_material(0).duplicate() as StandardMaterial3D
	red_mesh.material_override = _red
	blue_mesh.material_override = _blue
	set_as_top_level(true)
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	global_transform = _vehicle.global_transform
	_siren = AudioStreamPlayer3D.new()
	_siren.stream = _make_siren()
	_siren.bus = &"SFX"
	_siren.volume_db = -25.0
	_siren.unit_size = 18.0
	_siren.max_distance = 100.0
	_siren.position.y = 1.5
	add_child(_siren)
	_siren.play()

func _process(delta: float) -> void:
	global_transform = _vehicle.get_global_transform_interpolated()
	_clock += delta
	for wheel: Node3D in _wheels:
		wheel.rotation.x = fmod(wheel.rotation.x - _vehicle.forward_speed * delta / 0.43, TAU)
	_pose_clock += delta
	if _pose_clock < 1.0 / 12.0:
		return
	_pose_clock = fmod(_pose_clock, 1.0 / 12.0)
	for steer: Node3D in _front_steers:
		steer.rotation.y = -_vehicle.steering * 0.32
	_chassis.rotation.z = -_vehicle.steering * 0.075 * minf(absf(_vehicle.forward_speed) / 12.0, 1.0)
	_chassis.rotation.x = -_vehicle.throttle * 0.025
	var red_on: bool = int(_clock / 0.18) % 2 == 0 and RunSession.phase == RunSession.Phase.DRIVING
	_flash(_red, Color("ff4b4c"), red_on)
	_flash(_blue, Color("419cff"), not red_on and RunSession.phase == RunSession.Phase.DRIVING)

func _flash(material: StandardMaterial3D, color: Color, enabled: bool) -> void:
	material.albedo_color = color if enabled else color.darkened(0.6)
	material.emission_enabled = enabled
	material.emission = color
	material.emission_energy_multiplier = 1.4 if enabled else 0.0

func silence() -> void:
	_siren.stop()

static func _make_siren() -> AudioStreamWAV:
	if _siren_stream != null:
		return _siren_stream
	var rate: int = 22050
	var frames: int = rate * 2
	var data := PackedByteArray()
	data.resize(frames * 2)
	var phase: float = 0.0
	for index: int in range(frames):
		var t: float = float(index) / rate
		var frequency: float = 660.0 + 250.0 * (0.5 - 0.5 * cos(TAU * t))
		phase += TAU * frequency / rate
		var sample: float = sin(phase) * 0.72 + sin(phase * 2.0) * 0.12
		data.encode_s16(index * 2, int(sample * 21000.0))
	_siren_stream = AudioStreamWAV.new()
	_siren_stream.format = AudioStreamWAV.FORMAT_16_BITS
	_siren_stream.mix_rate = rate
	_siren_stream.data = data
	_siren_stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	_siren_stream.loop_begin = 0
	_siren_stream.loop_end = frames
	return _siren_stream
