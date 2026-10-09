extends Node3D
## Smooth camera follows the physics state independently of held chassis poses.

@export var follow_response: float = 10.0
@export var turn_response: float = 8.0
@onready var vehicle: ArcadeVehicle = get_parent() as ArcadeVehicle
@onready var spring_arm: SpringArm3D = $SpringArm3D
@onready var camera: Camera3D = $SpringArm3D/Camera3D


func _ready() -> void:
	set_as_top_level(true)
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	spring_arm.add_excluded_object(vehicle.get_rid())
	reset_view()


func _process(delta: float) -> void:
	var car_transform: Transform3D = vehicle.get_global_transform_interpolated()
	var desired: Vector3 = car_transform.origin + Vector3.UP * 1.2
	global_position = global_position.lerp(desired, 1.0 - exp(-follow_response * delta))
	rotation.y = lerp_angle(rotation.y, car_transform.basis.get_euler().y, 1.0 - exp(-turn_response * delta))
	var airborne: bool = not vehicle.is_on_floor()
	var pinned: bool = RunSession.capture_progress > 0.04
	var follow_length: float = 12.0 if pinned else (10.8 if airborne else 9.2)
	var follow_angle: float = -27.0 if airborne else (-25.0 if pinned else -18.0)
	spring_arm.spring_length = lerpf(spring_arm.spring_length, follow_length, 1.0 - exp(-4.0 * delta))
	spring_arm.rotation.x = lerpf(spring_arm.rotation.x, deg_to_rad(follow_angle), 1.0 - exp(-4.0 * delta))
	var speed_ratio: float = clampf(absf(vehicle.forward_speed) / vehicle.tuning.maximum_speed_mps, 0.0, 1.0)
	var boost_fov: float = lerpf(2.0,5.0,vehicle.boost.power) if vehicle.boost.phase == ChargeBoost.Phase.BOOSTING else 0.0
	camera.fov = lerpf(camera.fov, 58.0 + speed_ratio * 5.0 + boost_fov, 1.0 - exp(-3.0 * delta))


func reset_view() -> void:
	global_position = vehicle.global_position + Vector3.UP * 1.2
	rotation = Vector3(0.0, vehicle.rotation.y, 0.0)
	spring_arm.spring_length = 9.2
	spring_arm.rotation.x = deg_to_rad(-18.0)
	camera.fov = 58.0
