class_name NewsReport
extends CanvasLayer
## After the wreck: the evening news wraps up the chase. Headline, how it went, the chaos points line by
## line, a record stamp, and the bank. Enter goes back to the hideout.

signal done

const HEADLINES: PackedStringArray = [
	"SUSPECT'S CAR DESTROYED AFTER %s CHASE",
	"RED MUSCLE CAR FINALLY STOPPED AFTER %s",
	"%s OF MAYHEM ENDS IN A FIREBALL",
	"POLICE END %s PURSUIT — CITY BREATHES AGAIN",
]

var _card: PanelContainer
var _rows: VBoxContainer
var _headline: Label
var _subline: Label
var _record: Label
var _bank: Label
var _hint: Label
var _ready_for_input: bool = false


func _ready() -> void:
	layer = 8
	var dim := ColorRect.new()
	dim.color = Color(0.04, 0.06, 0.09, 0.55)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	_card = NewsStyle.panel(Color(0.1, 0.14, 0.2, 0.95), 10, 0)
	_card.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_card.offset_left = -380
	_card.offset_right = 380
	_card.offset_top = -270
	_card.offset_bottom = 270
	add_child(_card)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 0)
	_card.add_child(column)
	var bar := NewsStyle.panel(NewsStyle.RED, 0, 16)
	bar.add_child(NewsStyle.label("BREAKING NEWS  ·  L24", 24))
	column.add_child(bar)
	var body := MarginContainer.new()
	for side: String in ["left", "right", "top", "bottom"]:
		body.add_theme_constant_override("margin_" + side, 26)
	column.add_child(body)
	var inner := VBoxContainer.new()
	inner.add_theme_constant_override("separation", 8)
	body.add_child(inner)
	_headline = NewsStyle.label("", 30)
	_headline.autowrap_mode = TextServer.AUTOWRAP_WORD
	inner.add_child(_headline)
	_subline = NewsStyle.label("", 18, NewsStyle.DIM, false)
	inner.add_child(_subline)
	inner.add_child(HSeparator.new())
	_rows = VBoxContainer.new()
	_rows.add_theme_constant_override("separation", 4)
	inner.add_child(_rows)
	_record = NewsStyle.label("", 26, NewsStyle.AMBER)
	_record.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	inner.add_child(_record)
	_bank = NewsStyle.label("", 18, NewsStyle.CREAM, false)
	inner.add_child(_bank)
	_hint = NewsStyle.label("Enter: back to the hideout", 16, NewsStyle.DIM, false)
	inner.add_child(_hint)
	visible = false


func show_report(score: RunScore, record: bool, bank: int, can_replay: bool = false) -> void:
	visible = true
	_ready_for_input = false
	_headline.text = HEADLINES[randi() % HEADLINES.size()] % NewsStyle.clock(score.seconds)
	_subline.text = "%d cruiser%s wrecked  ·  %d near miss%s  ·  top speed %d km/h" % [score.cops_wrecked,
		"" if score.cops_wrecked == 1 else "s", score.near_misses, "" if score.near_misses == 1 else "es",
		int(score.top_speed * 3.6)]
	for child: Node in _rows.get_children():
		child.queue_free()
	_row("Time survived  %s" % NewsStyle.clock(score.seconds), score.time_points())
	_row("Cops wrecked  %d × %d" % [score.cops_wrecked, RunScore.COP_WRECK], score.cops_wrecked * RunScore.COP_WRECK)
	_row("Near misses  %d × %d" % [score.near_misses, RunScore.NEAR_MISS], score.near_misses * RunScore.NEAR_MISS)
	_row("Survival bonus  %d minute%s" % [score.minutes, "" if score.minutes == 1 else "s"], score.minute_points)
	_rows.add_child(HSeparator.new())
	_row("TOTAL CHAOS", score.total(), true)
	_record.text = "★  NEW RECORD  ★" if record else ""
	_bank.text = "Chaos bank: %s  ·  spend it on upgrades in the garage" % NewsStyle.points(bank)
	_hint.text = "Enter: back to the hideout" + ("  ·  2: watch your recording of the chase" if can_replay else "")
	_card.scale = Vector2.ONE * 0.9
	_card.pivot_offset = _card.size * 0.5
	create_tween().tween_property(_card, "scale", Vector2.ONE, 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	await get_tree().create_timer(0.8).timeout
	_ready_for_input = true


func _unhandled_input(event: InputEvent) -> void:
	if not visible or not _ready_for_input:
		return
	var key := event as InputEventKey
	if key != null and key.pressed and not key.echo and key.physical_keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE]:
		get_viewport().set_input_as_handled()
		close()


func close() -> void:
	if not visible:
		return
	visible = false
	done.emit()


func _row(label: String, points: int, total: bool = false) -> void:
	var row := HBoxContainer.new()
	row.add_child(NewsStyle.label(label, 24 if total else 19, NewsStyle.CREAM, total))
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)
	row.add_child(NewsStyle.label(NewsStyle.points(points), 26 if total else 19, NewsStyle.AMBER if total else NewsStyle.CREAM, total))
	_rows.add_child(row)
