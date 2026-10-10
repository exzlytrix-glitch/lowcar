class_name HideoutMenu
extends CanvasLayer
## The hideout screen, dressed as a news channel covering the fugitive (theme A): station bug, a
## "most wanted" lower third, a ticker of headlines, and the garage panel (chaos bank, upgrades, records,
## and the button that starts the breakout).

signal start_requested

const TICKER: PackedStringArray = [
	"Police chief vows \"this time for sure\"",
	"Tire shop near the docks reports record sales",
	"Witness describes suspect vehicle as \"very red\"",
	"City council debates banning U-turns",
	"Donut shop opens a 24-hour lane for squad cars",
	"Insurance rates for police cruisers hit an all-time high",
	"Traffic cones declared an endangered species",
	"Local man swears the red car waved at him",
	"Mayor: \"Our roads are not a racetrack.\" Roads: unavailable for comment",
	"Garage owner insists he has never seen a red car in his life",
]
const TICKER_SPEED: float = 90.0

var profile: GameProfile
var _bank: Label
var _records: Label
var _message: Label
var _start: Button
var _upgrade_buttons: Dictionary = {}
var _ticker: Label
var _ticker_clip: Control
var _ticker_x: float = 0.0
var _message_clock: float = 0.0


func _ready() -> void:
	layer = 4
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	_build_bug(root)
	_build_panel(root)
	_build_lower_third(root)
	refresh()


func show_menu() -> void:
	visible = true
	refresh()
	_start.grab_focus()


## Hidden during the run, with no button keeping keyboard focus (Enter or Space would press it).
func hide_menu() -> void:
	visible = false
	var focused: Control = get_viewport().gui_get_focus_owner()
	if focused != null:
		focused.release_focus()


func refresh() -> void:
	if profile == null or _bank == null:
		return
	_bank.text = NewsStyle.points(profile.bank)
	for upgrade: Dictionary in GameProfile.UPGRADES:
		var id: String = upgrade["id"]
		var button: Button = _upgrade_buttons[id]
		var costs: Array = upgrade["costs"]
		var cost: int = profile.next_cost(id)
		var level_text: String = "%s  %d/%d" % [_pips(profile.level(id), costs.size()), profile.level(id), costs.size()]
		button.text = "%s\n%s   ·   %s" % [upgrade["name"], level_text,
			"MAXED" if cost < 0 else ("%s chaos" % NewsStyle.points(cost))]
		button.tooltip_text = upgrade["info"]
	if profile.runs == 0:
		_records.text = "No runs yet. The city is waiting."
	else:
		_records.text = "Best run  %s  ·  %s chaos  ·  %d cops wrecked\nRuns survived so far: %d" % [
			NewsStyle.clock(profile.best_seconds), NewsStyle.points(profile.best_points), profile.best_wrecks, profile.runs]


func _process(delta: float) -> void:
	if not visible:
		return
	_ticker_x -= TICKER_SPEED * delta
	if _ticker_x < -_ticker.size.x:
		_ticker_x = _ticker_clip.size.x
	_ticker.position.x = _ticker_x
	if _message_clock > 0.0:
		_message_clock -= delta
		if _message_clock <= 0.0:
			_message.text = ""


func _pips(level: int, count: int) -> String:
	return "■".repeat(level) + "□".repeat(count - level)


func _buy(id: String) -> void:
	var cost: int = profile.next_cost(id)
	if cost < 0:
		_say("Already maxed out.")
	elif profile.buy(id):
		_say("Installed. The mechanic says: \"don't scratch it.\"")
	else:
		_say("Not enough chaos. Go cause some.")
	refresh()


func _say(text: String) -> void:
	_message.text = text
	_message_clock = 3.0


# --- layout -------------------------------------------------------------------------

func _build_bug(root: Control) -> void:
	var bug := HBoxContainer.new()
	bug.position = Vector2(24, 20)
	bug.add_theme_constant_override("separation", 0)
	root.add_child(bug)
	var channel := NewsStyle.panel(NewsStyle.RED, 0, 14)
	channel.add_child(NewsStyle.label("L24", 30))
	bug.add_child(channel)
	var name_box := NewsStyle.panel(NewsStyle.NAVY, 0, 14)
	name_box.add_child(NewsStyle.label("LOWCAR NEWS  ·  THE HIDEOUT", 22))
	bug.add_child(name_box)


func _build_panel(root: Control) -> void:
	var panel := NewsStyle.panel(Color(0.1, 0.14, 0.2, 0.9), 10, 18)
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.offset_left = -430
	panel.offset_right = -24
	panel.offset_top = 20
	root.add_child(panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 10)
	panel.add_child(column)
	column.add_child(NewsStyle.label("THE GARAGE", 18, NewsStyle.AMBER))
	var bank_row := HBoxContainer.new()
	bank_row.add_child(NewsStyle.label("Chaos bank", 22))
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bank_row.add_child(spacer)
	_bank = NewsStyle.label("0", 30, NewsStyle.AMBER)
	bank_row.add_child(_bank)
	column.add_child(bank_row)
	_start = NewsStyle.button("▶  HIT THE STREETS", 28)
	_start.add_theme_stylebox_override("normal", NewsStyle.box(NewsStyle.RED, 6, 16))
	_start.pressed.connect(func() -> void: start_requested.emit())
	column.add_child(_start)
	column.add_child(NewsStyle.label("UPGRADES", 16, NewsStyle.DIM, false))
	for upgrade: Dictionary in GameProfile.UPGRADES:
		var id: String = upgrade["id"]
		var button := NewsStyle.button(upgrade["name"], 19)
		button.pressed.connect(_buy.bind(id))
		column.add_child(button)
		_upgrade_buttons[id] = button
	_message = NewsStyle.label("", 17, NewsStyle.AMBER, false)
	_message.autowrap_mode = TextServer.AUTOWRAP_WORD
	column.add_child(_message)
	_records = NewsStyle.label("", 16, NewsStyle.DIM, false)
	_records.autowrap_mode = TextServer.AUTOWRAP_WORD
	column.add_child(_records)
	column.add_child(NewsStyle.label("↑ ↓ choose  ·  Enter select", 15, NewsStyle.DIM, false))


func _build_lower_third(root: Control) -> void:
	var lower := VBoxContainer.new()
	lower.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	lower.offset_top = -132
	lower.offset_bottom = -20
	lower.offset_left = 24
	lower.offset_right = -24
	lower.add_theme_constant_override("separation", 0)
	root.add_child(lower)
	var headline_row := HBoxContainer.new()
	headline_row.add_theme_constant_override("separation", 0)
	lower.add_child(headline_row)
	var tag := NewsStyle.panel(NewsStyle.RED, 0, 14)
	tag.add_child(NewsStyle.label("MOST WANTED", 24))
	headline_row.add_child(tag)
	var headline := NewsStyle.panel(NewsStyle.CREAM, 0, 14)
	headline.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	headline.add_child(NewsStyle.label("Red muscle car still at large  ·  whereabouts unknown", 24, NewsStyle.NAVY, false))
	headline_row.add_child(headline)
	var strip := NewsStyle.panel(NewsStyle.NAVY, 0, 8)
	strip.custom_minimum_size.y = 40
	lower.add_child(strip)
	_ticker_clip = Control.new()
	_ticker_clip.clip_contents = true
	_ticker_clip.custom_minimum_size.y = 30
	strip.add_child(_ticker_clip)
	var shuffled: Array = Array(TICKER)
	shuffled.shuffle()
	_ticker = NewsStyle.label("    ●    ".join(PackedStringArray(shuffled)), 20, NewsStyle.CREAM, false)
	_ticker_clip.add_child(_ticker)
	_ticker_x = 1280.0
