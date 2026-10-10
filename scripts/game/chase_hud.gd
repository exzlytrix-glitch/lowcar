class_name ChaseHud
extends CanvasLayer
## The chase HUD on top of the news broadcast (LabBroadcast: LIVE banner and captions): chase clock and
## chaos score, cops in pursuit and wrecked, health with its damage stage, boost charge, and big
## callouts when points come in.

const CALLOUT_SECONDS: float = 1.6

var player: LabVehicle
var chase: LabChase
var score: RunScore
var _time: Label
var _chaos: Label
var _status: Label
var _health_bar: ProgressBar
var _health_fill := StyleBoxFlat.new()
var _health_label: Label
var _boost_bar: ProgressBar
var _boost_fill := StyleBoxFlat.new()
var _boost_label: Label
var _callouts: VBoxContainer


func _ready() -> void:
	layer = 6
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	var panel := NewsStyle.panel(NewsStyle.INK, 10, 16)
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.offset_left = -300
	panel.offset_right = -24
	panel.offset_top = 20
	root.add_child(panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 2)
	panel.add_child(column)
	_time = NewsStyle.label("0:00", 40)
	_time.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	column.add_child(_time)
	_chaos = NewsStyle.label("0", 32, NewsStyle.AMBER)
	_chaos.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	column.add_child(_chaos)
	column.add_child(_right(NewsStyle.label("CHAOS", 14, NewsStyle.DIM, false)))
	_status = NewsStyle.label("", 17, NewsStyle.CREAM, false)
	_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	column.add_child(_status)
	var gauges := VBoxContainer.new()
	gauges.anchor_top = 1.0
	gauges.anchor_bottom = 1.0
	gauges.offset_left = 24
	gauges.offset_right = 324
	gauges.offset_top = -196
	gauges.offset_bottom = -100
	gauges.add_theme_constant_override("separation", 4)
	root.add_child(gauges)
	_health_label = NewsStyle.label("CLEAN", 18)
	gauges.add_child(_health_label)
	_health_bar = _bar(_health_fill, 18.0)
	gauges.add_child(_health_bar)
	_boost_label = NewsStyle.label("BOOST", 15, NewsStyle.DIM)
	gauges.add_child(_boost_label)
	_boost_bar = _bar(_boost_fill, 10.0)
	_boost_fill.bg_color = Color("#56B4E9")
	gauges.add_child(_boost_bar)
	_callouts = VBoxContainer.new()
	_callouts.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_callouts.offset_top = 110
	_callouts.offset_left = -300
	_callouts.offset_right = 300
	_callouts.alignment = BoxContainer.ALIGNMENT_BEGIN
	_callouts.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_callouts)


func callout(label: String, points: int) -> void:
	var text := NewsStyle.label("+%s  %s" % [NewsStyle.points(points), label], 34, NewsStyle.AMBER)
	text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	text.pivot_offset = Vector2(300, 20)
	text.scale = Vector2.ONE * 1.35
	_callouts.add_child(text)
	var tween := text.create_tween()
	tween.tween_property(text, "scale", Vector2.ONE, 0.18).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.tween_interval(CALLOUT_SECONDS)
	tween.tween_property(text, "modulate:a", 0.0, 0.4)
	tween.tween_callback(text.queue_free)


func _process(_delta: float) -> void:
	if not visible or not is_instance_valid(player) or score == null:
		return
	_time.text = NewsStyle.clock(score.seconds)
	_chaos.text = NewsStyle.points(score.total())
	_status.text = "%d in pursuit  ·  %d wrecked\n%d near miss%s" % [chase.cops.size(), score.cops_wrecked,
		score.near_misses, "" if score.near_misses == 1 else "es"]
	var share: float = player.health / maxf(player.max_health, 1.0)
	_health_bar.value = share * 100.0
	var stage: String = "CLEAN"
	var color := NewsStyle.GREEN
	if share < 0.25:
		stage = "ON FIRE"
		color = NewsStyle.RED
	elif share < 0.5:
		stage = "SMOKING"
		color = Color("#E8873A")
	elif share < 0.75:
		stage = "DENTED"
		color = NewsStyle.AMBER
	_health_label.text = "%s  ·  %d" % [stage, int(ceil(player.health))]
	_health_fill.bg_color = color
	var boost: ChargeBoost = player.boost
	if boost.phase == ChargeBoost.Phase.BOOSTING:
		_boost_label.text = "BOOSTING!"
		_boost_bar.value = 100.0 * boost.remaining / maxf(boost.duration, 0.01)
	else:
		_boost_label.text = "BOOST  ·  hold Shift to charge" if boost.phase == ChargeBoost.Phase.READY else "BOOST  ·  charging"
		_boost_bar.value = 100.0 * boost.charge_ratio(player.tuning)


func _bar(fill: StyleBoxFlat, height: float) -> ProgressBar:
	var bar := ProgressBar.new()
	bar.custom_minimum_size = Vector2(300, height)
	bar.show_percentage = false
	bar.max_value = 100.0
	var back := StyleBoxFlat.new()
	back.bg_color = Color(0.1, 0.14, 0.2, 0.7)
	back.set_corner_radius_all(4)
	fill.set_corner_radius_all(4)
	bar.add_theme_stylebox_override("background", back)
	bar.add_theme_stylebox_override("fill", fill)
	return bar


func _right(label: Label) -> Label:
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	return label
