extends Node
## Input stays outside vehicle physics so AI can supply the same driver commands later.

@onready var vehicle: ArcadeVehicle = get_parent() as ArcadeVehicle
@onready var launcher: LauncherAttachment = vehicle.get_node("Attachments/GroundPunch") as LauncherAttachment


func _physics_process(_delta: float) -> void:
	if not vehicle.controls_enabled:
		vehicle.set_driver_command(0.0, 0.0, false)
		return
	vehicle.set_driver_command(
		Input.get_axis("brake_reverse", "accelerate"),
		Input.get_axis("steer_left", "steer_right"),
		Input.is_action_pressed("handbrake"),
		Input.is_action_pressed("charge_boost")
	)
	if Input.is_action_just_pressed("attachment_primary"):
		launcher.try_activate()


func _unhandled_input(event: InputEvent) -> void:
	if not vehicle.controls_enabled or get_tree().paused:
		return
	if event is InputEventMouseButton:
		var click := event as InputEventMouseButton
		if click.button_index == MOUSE_BUTTON_LEFT and click.pressed and click.double_click:
			launcher.try_activate()
			get_viewport().set_input_as_handled()
