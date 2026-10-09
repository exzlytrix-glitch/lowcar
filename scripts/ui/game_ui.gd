class_name LowcarUI
extends CanvasLayer
## Functional starter UI. Scenes can replace these controls as presentation develops.

signal start_requested
signal restart_requested
signal resume_requested
signal menu_requested

@export var vehicle_path: NodePath
@export var world_path: NodePath

var _vehicle: ArcadeVehicle
var _world: CityStreamer
var _root: Control
var _hud: Control
var _menu: Control
var _pause: Control
var _result: Control
var _distance: Label
var _speed: Label
var _attachment: Label
var _result_title: Label
var _result_stats: Label
var _debug: Label
var _boost_title: Label
var _boost_hint: Label
var _boost_bar: ProgressBar
var _chase: ChaseDirector
var _pursuit: Label
var _pursuit_hint: Label
var _capture_bar: ProgressBar
var _capture_panel: PanelContainer
var _capture_title: Label
var _notice: Label
var debug_visible: bool = false
var _waiting_for_crash_drawing: bool = false
const CREAM := Color("#F7F1E6")
const INK := Color("#203548")
const AMBER := Color("#E8AD43")


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_vehicle = get_node(vehicle_path) as ArcadeVehicle
	_world = get_node(world_path) as CityStreamer
	_chase = get_node("../ChaseDirector") as ChaseDirector
	_build()
	RunSession.phase_changed.connect(_on_phase_changed)
	_on_phase_changed(RunSession.phase)


func _process(_delta: float) -> void:
	if _waiting_for_crash_drawing and RunSession.phase == RunSession.Phase.ENDED and not _death_drawing_active():
		_waiting_for_crash_drawing = false
		_result.visible = true
		var result_buttons: Array[Node] = _result.find_children("*", "Button", true, false)
		if not result_buttons.is_empty():
			(result_buttons[0] as Button).grab_focus()
	_distance.text = "%04d M   /   %02d:%02d" % [int(RunSession.distance_m), int(RunSession.elapsed_s) / 60, int(RunSession.elapsed_s) % 60]
	_speed.text = "%03d KM/H" % int(absf(_vehicle.forward_speed) * 3.6)
	_update_boost()
	_update_pursuit()
	var launcher: LauncherAttachment = _vehicle.get_node("Attachments/GroundPunch") as LauncherAttachment
	if launcher.is_ready():
		_attachment.text = "GROUND PUNCH   •   READY"
		_attachment.modulate = AMBER
	elif not _vehicle.is_on_floor():
		_attachment.text = "GROUND PUNCH   •   AIRBORNE"
		_attachment.modulate = CREAM
	else:
		_attachment.text = "GROUND PUNCH   •   %.1f S" % launcher.cooldown_remaining
		_attachment.modulate = CREAM
	_debug.visible = debug_visible and RunSession.phase != RunSession.Phase.MENU
	_debug.text = "FPS %d  |  SEED %d\nBLOCKS %d  |  PURSUIT TIER %d\nACTIVE PATROLS %d" % [
		Engine.get_frames_per_second(), RunSession.city_seed,
		_world.active_chunks.size(), RunSession.pursuit_tier, RunSession.active_police_count
	]


func _build() -> void:
	_root = Control.new()
	_root.name = "UIRoot"
	_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	_hud = Control.new()
	_hud.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_hud)
	var upper := _hud_panel(Vector2(24, 24), Vector2(355, 102))
	var heading := _label("LOWCAR", 28)
	heading.modulate = Color("#F07260")
	upper.add_child(heading)
	_distance = _label("", 22)
	upper.add_child(_distance)
	_build_pursuit()
	var lower_panel := PanelContainer.new()
	lower_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	lower_panel.add_theme_stylebox_override("panel", _panel_style())
	lower_panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	lower_panel.offset_left = 24
	lower_panel.offset_top = -118
	lower_panel.offset_right = 395
	lower_panel.offset_bottom = -24
	_hud.add_child(lower_panel)
	var lower := VBoxContainer.new()
	lower.add_theme_constant_override("separation", 7)
	lower_panel.add_child(lower)
	_speed = _label("", 22)
	lower.add_child(_speed)
	_attachment = _label("", 18)
	lower.add_child(_attachment)
	lower.add_child(_label("SPACE / DOUBLE-CLICK / GAMEPAD X", 13))
	var boost_panel := PanelContainer.new()
	boost_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	boost_panel.add_theme_stylebox_override("panel", _panel_style())
	boost_panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	boost_panel.offset_left = -394
	boost_panel.offset_top = -136
	boost_panel.offset_right = -24
	boost_panel.offset_bottom = -24
	_hud.add_child(boost_panel)
	var boost_column := VBoxContainer.new()
	boost_column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	boost_column.add_theme_constant_override("separation", 8)
	boost_panel.add_child(boost_column)
	_boost_title = _label("BOOST / HOLD SHIFT", 20)
	boost_column.add_child(_boost_title)
	_boost_bar = ProgressBar.new()
	_boost_bar.custom_minimum_size = Vector2(0,12)
	_boost_bar.max_value = 1.0
	_boost_bar.show_percentage = false
	_boost_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var fill := StyleBoxFlat.new()
	fill.bg_color = AMBER
	var track := StyleBoxFlat.new()
	track.bg_color = Color("40566b")
	_boost_bar.add_theme_stylebox_override("fill",fill)
	_boost_bar.add_theme_stylebox_override("background",track)
	boost_column.add_child(_boost_bar)
	_boost_hint = _label("HOLD TO CHARGE / RELEASE TO BOOST", 13)
	boost_column.add_child(_boost_hint)
	_debug = _label("", 14)
	_debug.position = Vector2(30, 150)
	_debug.add_theme_color_override("font_color", INK)
	_hud.add_child(_debug)
	_menu = _overlay()
	var menu_box := _dialog(_menu)
	menu_box.add_child(_label("LOWCAR", 58))
	menu_box.add_child(_label("BELLE RIVE", 20))
	menu_box.add_child(_label("RED CAR. BAD IDEAS. ACTUAL COPS.", 19))
	menu_box.add_child(_label("SURVIVE THE CHASE. KEEP MOVING.\nPINNED? BOOST OR LAUNCH TO BREAK FREE.", 15))
	menu_box.add_child(_label("WASD / ARROWS — DRIVE\nSHIFT — HOLD TO CHARGE, RELEASE TO BOOST\nCTRL — HANDBRAKE\nSPACE / DOUBLE-CLICK — LAUNCH", 16))
	menu_box.add_child(_button("START THE CHASE", func() -> void: start_requested.emit()))
	menu_box.add_child(_button("QUIT", func() -> void: get_tree().quit()))
	_pause = _overlay()
	var pause_box := _dialog(_pause)
	pause_box.add_child(_label("PAUSED", 42))
	pause_box.add_child(_button("RESUME", func() -> void: resume_requested.emit()))
	pause_box.add_child(_button("RESTART", func() -> void: restart_requested.emit()))
	pause_box.add_child(_button("BACK TO TITLE", func() -> void: menu_requested.emit()))
	_result = _overlay()
	var result_box := _dialog(_result)
	_result_title = _label("CRASHED", 42)
	result_box.add_child(_result_title)
	_result_stats = _label("", 19)
	result_box.add_child(_result_stats)
	result_box.add_child(_label("R — INSTANT RESTART / SAME CITY", 14))
	result_box.add_child(_button("DRIVE AGAIN", func() -> void: restart_requested.emit()))
	result_box.add_child(_button("BACK TO TITLE", func() -> void: menu_requested.emit()))


func _build_pursuit() -> void:
	var panel := PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	panel.offset_left = -324
	panel.offset_right = -24
	panel.offset_top = 24
	panel.offset_bottom = 266
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_theme_stylebox_override("panel", _panel_style())
	_hud.add_child(panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 8)
	panel.add_child(column)
	_pursuit = _label("PURSUIT 1", 21)
	_pursuit.modulate = Color("ff856e")
	column.add_child(_pursuit)
	var radar := PursuitRadar.new()
	radar.vehicle = _vehicle
	radar.custom_minimum_size = Vector2(0, 142)
	radar.clip_contents = true
	radar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(radar)
	_pursuit_hint = _label("", 13)
	column.add_child(_pursuit_hint)
	_capture_panel = PanelContainer.new()
	_capture_panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_capture_panel.offset_left = -204
	_capture_panel.offset_right = 204
	_capture_panel.offset_top = 85
	_capture_panel.offset_bottom = 175
	_capture_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_capture_panel.add_theme_stylebox_override("panel", _panel_style())
	_hud.add_child(_capture_panel)
	var capture_column := VBoxContainer.new()
	_capture_panel.add_child(capture_column)
	_capture_title = _label("PINNED / BREAK FREE!", 22)
	_capture_title.modulate = Color("ff856e")
	capture_column.add_child(_capture_title)
	_capture_bar = ProgressBar.new()
	_capture_bar.max_value = 1.0
	_capture_bar.show_percentage = false
	_capture_bar.custom_minimum_size.y = 12
	var fill := StyleBoxFlat.new()
	fill.bg_color = Color("ed6858")
	_capture_bar.add_theme_stylebox_override("fill", fill)
	capture_column.add_child(_capture_bar)
	capture_column.add_child(_label("SHIFT — BOOST / SPACE — LAUNCH", 13))
	_notice = _label("", 21)
	_notice.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_notice.offset_left = -235
	_notice.offset_right = 235
	_notice.offset_top = 27
	_notice.offset_bottom = 62
	_notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_notice.add_theme_color_override("font_color", INK)
	_hud.add_child(_notice)


func _update_pursuit() -> void:
	_pursuit.text = "PURSUIT %d / %d UNITS" % [RunSession.pursuit_tier, RunSession.active_police_count]
	var nearest: String = "NEAREST %d M" % int(_chase.nearest_distance) if is_finite(_chase.nearest_distance) else "PATROLS INBOUND"
	var backup: String = "MAX HEAT" if RunSession.pursuit_tier >= _chase.tuning.maximum_tier else "BACKUP %d S" % ceili(_chase.tuning.seconds_per_tier - fmod(RunSession.elapsed_s, _chase.tuning.seconds_per_tier))
	_pursuit_hint.text = "%s / %s" % [nearest, backup]
	_capture_panel.visible = RunSession.capture_progress > 0.01 and RunSession.phase == RunSession.Phase.DRIVING
	_capture_bar.value = RunSession.capture_progress
	_capture_title.text = "PINNED / BREAK FREE!" if _vehicle.is_on_floor() and Vector2(_vehicle.velocity.x, _vehicle.velocity.z).length() < _chase.tuning.capture_max_speed_mps and _chase.nearest_distance < _chase.tuning.capture_radius_m else "ESCAPING / KEEP GOING!"
	_notice.visible = _chase.notice_remaining > 0.0 and RunSession.phase == RunSession.Phase.DRIVING
	_notice.text = _chase.notice


func _update_boost() -> void:
	var boost: ChargeBoost = _vehicle.boost
	match boost.phase:
		ChargeBoost.Phase.CHARGING:
			var ratio: float = boost.charge_ratio(_vehicle.tuning)
			_boost_title.text = "BOOST / FULL CHARGE" if ratio >= 0.999 else "BOOST / %.1f OF %.0f S" % [boost.charge_seconds,_vehicle.tuning.boost_max_charge_seconds]
			_boost_title.modulate = AMBER
			_boost_bar.value = ratio
			_boost_hint.text = "RELEASE SHIFT / RB — LET IT RIP"
		ChargeBoost.Phase.BOOSTING:
			_boost_title.text = "BOOST / %.1f S" % boost.remaining
			_boost_title.modulate = Color("ff9363")
			_boost_bar.value = boost.remaining/maxf(boost.duration,0.01)
			_boost_hint.text = "SHIFT — RECHARGE / BRAKE — CANCEL"
		_:
			_boost_title.text = "BOOST / HOLD SHIFT"
			_boost_title.modulate = CREAM
			_boost_bar.value = 0.0
			_boost_hint.text = "HOLD SHIFT / RB — CHARGE UP TO 10 S"


func _on_phase_changed(phase: RunSession.Phase) -> void:
	_menu.visible = phase == RunSession.Phase.MENU
	_pause.visible = phase == RunSession.Phase.PAUSED
	_waiting_for_crash_drawing = phase == RunSession.Phase.ENDED and _death_drawing_active()
	_result.visible = phase == RunSession.Phase.ENDED and not _waiting_for_crash_drawing
	_hud.visible = phase != RunSession.Phase.MENU
	if phase == RunSession.Phase.ENDED:
		_result_title.text = RunSession.end_reason
		_result_stats.text = "%d METERS / %.1f SECONDS / PURSUIT %d" % [int(RunSession.distance_m), RunSession.elapsed_s, RunSession.pursuit_tier]
	var active_overlay: Control = null
	if _menu.visible:
		active_overlay = _menu
	elif _pause.visible:
		active_overlay = _pause
	elif _result.visible:
		active_overlay = _result
	if active_overlay != null:
		var buttons: Array[Node] = active_overlay.find_children("*", "Button", true, false)
		if not buttons.is_empty():
			(buttons[0] as Button).grab_focus()


func _death_drawing_active() -> bool:
	var presentation := _vehicle.get_node("Presentation") as CarPresentation
	if presentation.current_clip not in CarCrashEffects.DEATH_CLIPS:
		return false
	var clip: Animation = presentation.animation.get_animation("car/" + presentation.current_clip)
	return presentation.animation.current_animation_position < clip.length - 0.01


func _hud_panel(at: Vector2, minimum: Vector2) -> VBoxContainer:
	var panel := PanelContainer.new()
	panel.position = at
	panel.custom_minimum_size = minimum
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_theme_stylebox_override("panel", _panel_style())
	_hud.add_child(panel)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 6)
	content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(content)
	return content


func _overlay() -> CenterContainer:
	var overlay := CenterContainer.new()
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_root.add_child(overlay)
	return overlay


func _dialog(overlay: Control) -> VBoxContainer:
	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(460, 0)
	panel.add_theme_stylebox_override("panel", _panel_style(32))
	overlay.add_child(panel)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 18)
	panel.add_child(content)
	return content


func _label(text: String, size: int) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", CREAM)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label


func _button(text: String, action: Callable) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size.y = 52
	button.add_theme_font_size_override("font_size", 20)
	button.add_theme_color_override("font_color", CREAM)
	var normal := StyleBoxFlat.new()
	normal.bg_color = Color("#385267")
	normal.set_corner_radius_all(8)
	button.add_theme_stylebox_override("normal", normal)
	var hover: StyleBoxFlat = normal.duplicate()
	hover.bg_color = Color("#506E82")
	button.add_theme_stylebox_override("hover", hover)
	var focus: StyleBoxFlat = normal.duplicate()
	focus.bg_color = Color("#506E82")
	focus.set_border_width_all(2)
	focus.border_color = AMBER
	button.add_theme_stylebox_override("focus", focus)
	button.pressed.connect(action)
	return button


func _panel_style(padding: int = 16) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(INK, 0.94)
	style.set_corner_radius_all(14)
	style.content_margin_left = padding
	style.content_margin_right = padding
	style.content_margin_top = padding
	style.content_margin_bottom = padding
	return style
