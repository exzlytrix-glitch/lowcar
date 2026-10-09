class_name LauncherAttachment
extends Node

signal activated
signal readiness_changed(ready: bool)

@export var definition: AttachmentDefinition
var cooldown_remaining: float = 0.0
var _last_ready: bool = false
@onready var vehicle: ArcadeVehicle = get_parent().get_parent() as ArcadeVehicle


func _physics_process(delta: float) -> void:
	cooldown_remaining = maxf(cooldown_remaining - delta, 0.0)
	var ready_now: bool = is_ready()
	if ready_now != _last_ready:
		_last_ready = ready_now
		readiness_changed.emit(ready_now)


func is_ready() -> bool:
	return definition != null and vehicle.controls_enabled and not get_tree().paused and cooldown_remaining <= 0.0 and (not definition.requires_ground or vehicle.is_on_floor())


func try_activate() -> bool:
	if not is_ready():
		return false
	vehicle.velocity.y = definition.upward_speed_mps
	cooldown_remaining = definition.cooldown_seconds
	activated.emit()
	return true


func reset_attachment() -> void:
	cooldown_remaining = 0.0
	_last_ready = false

