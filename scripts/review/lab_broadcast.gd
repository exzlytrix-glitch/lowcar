class_name LabBroadcast
extends CanvasLayer
## TV-news look for the lab's --show mode: no lab text, just a blinking "LIVE" banner and a caption bar
## that comments on the chase (speed, district, units in pursuit, boosts, rams, hits, wrecks).

const CAPTION_SECONDS: float = 4.0
const EVENT_GAP: float = 1.5
const RAM_RANGE: float = 45.0

var chase: LabChase
var player: LabVehicle
var generator: RoadGenerator
var _banner: Label
var _dot: Label
var _caption: Label
var _clock: float = 1.0
var _since_change: float = 0.0
var _blink: float = 0.0
var _rng := RandomNumberGenerator.new()
var _last_cops: int = 0
var _was_boosting: bool = false
var _smoking_said: bool = false
var _fire_said: bool = false
var _last_line: String = ""


func _ready() -> void:
	_rng.randomize()
	layer = 5
	var top := PanelContainer.new()
	top.position = Vector2(24, 20)
	top.add_theme_stylebox_override("panel", _box(Color("#D7263D"), 10))
	add_child(top)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	top.add_child(row)
	_dot = Label.new()
	_dot.text = "●"
	_dot.add_theme_font_size_override("font_size", 28)
	row.add_child(_dot)
	_banner = Label.new()
	_banner.text = "LIVE  ·  HIGH-SPEED CHASE"
	_banner.add_theme_font_size_override("font_size", 28)
	row.add_child(_banner)
	var bottom := PanelContainer.new()
	bottom.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	bottom.offset_left = 24
	bottom.offset_right = -24
	bottom.offset_top = -86
	bottom.offset_bottom = -24
	bottom.add_theme_stylebox_override("panel", _box(Color(0.1, 0.14, 0.2, 0.82), 10))
	add_child(bottom)
	_caption = Label.new()
	_caption.add_theme_font_size_override("font_size", 26)
	_caption.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	bottom.add_child(_caption)
	player.damaged.connect(_on_damaged)
	_say("Breaking: police in pursuit of a red muscle car")


func wrecked(seconds: int) -> void:
	_say("SUSPECT VEHICLE DOWN after %d:%02d — a new pursuit is already underway" % [seconds / 60, seconds % 60])
	_clock = CAPTION_SECONDS + 2.0


func _process(delta: float) -> void:
	_blink += delta
	_dot.modulate.a = 1.0 if fmod(_blink, 1.0) < 0.6 else 0.25
	_since_change += delta
	_clock -= delta
	if not is_instance_valid(player) or chase == null:
		return
	var event: String = _event()
	if not event.is_empty() and _since_change > EVENT_GAP:
		_say(event)
		_clock = CAPTION_SECONDS
	elif _clock <= 0.0:
		_say(_story())
		_clock = CAPTION_SECONDS


func _event() -> String:
	var boosting: bool = player.boost.phase == ChargeBoost.Phase.BOOSTING
	var fired: bool = boosting and not _was_boosting
	_was_boosting = boosting
	if fired:
		return _pick(["SUSPECT HITS THE BOOST!", "Suspect lights up the boost — units falling behind!", "Whoa — the suspect just rocketed off!"])
	var cops: int = chase.cops.size()
	if cops > _last_cops and _last_cops > 0:
		_last_cops = cops
		return "Backup has arrived — %d units now in pursuit" % cops
	_last_cops = cops
	for cop: LabVehicle in chase.cops:
		if is_instance_valid(cop) and chase.bursting(cop) and cop.global_position.distance_to(player.global_position) < RAM_RANGE:
			return _pick(["Unit closing in — ramming attempt!", "A cruiser is going for the hit!", "Here comes a ram!"])
	if player.health < 25.0 and not _fire_said:
		_fire_said = true
		return "The suspect vehicle is ON FIRE!"
	if player.health < 50.0 and not _smoking_said:
		_smoking_said = true
		return "Suspect vehicle smoking badly — it can't take much more"
	return ""


func _story() -> String:
	var speed: int = int(Vector2(player.velocity.x, player.velocity.z).length() * 3.6)
	var at := Vector2(player.global_position.x, player.global_position.z)
	var district: String = "downtown"
	if generator != null:
		district = String(RoadGenerator.STYLE_NAMES[generator.style_at(at)]).to_lower()
	var heading: String = _compass(Vector2(-player.global_basis.z.x, -player.global_basis.z.z))
	var seconds: int = int(chase.elapsed)
	var cops: int = chase.cops.size()
	if speed > 160:
		return "Suspect topping %d km/h!" % speed
	var lines: Array[String] = [
		"Suspect doing %d km/h through the %s district" % [speed, district],
		"%d unit%s in pursuit" % [cops, "" if cops == 1 else "s"],
		"Suspect heading %s — and NOT slowing down" % heading,
		"Pursuit now %d:%02d and counting" % [seconds / 60, seconds % 60],
		"Dispatch: all units, suspect last seen heading %s" % heading,
		"Chopper 7 has eyes on the suspect",
		"Witnesses report a red muscle car going extremely fast",
		"Units are trying to cut the suspect off",
		"Viewers are advised to stay off the roads in the %s district" % district,
	]
	if player.health < 60.0:
		lines.append("The suspect's car is badly dented")
	return _pick(lines)


func _on_damaged(amount: float, source: String) -> void:
	if _since_change < EVENT_GAP:
		return
	if source == "standoff":
		_say(_pick(["Suspect stalls — and the cops are all over him!", "Standoff! The suspect is getting hammered!"]))
		_clock = CAPTION_SECONDS
		return
	if source == "crash" and amount >= 15.0:
		_say(_pick(["Suspect slams into a wall!", "OOF — straight into the side of a building!"]))
		_clock = CAPTION_SECONDS
	elif source != "crash" and amount >= 5.0:
		_say(_pick(["BIG HIT — a cruiser smashes into the suspect!", "Contact! The suspect takes a massive hit!"]))
		_clock = CAPTION_SECONDS


func _say(text: String) -> void:
	_caption.text = text
	_last_line = text
	_since_change = 0.0


func _pick(options: Array) -> String:
	var choice: String = options[_rng.randi() % options.size()]
	if choice == _last_line and options.size() > 1:
		choice = options[(options.find(choice) + 1) % options.size()]
	return choice


static func _compass(direction: Vector2) -> String:
	var names: PackedStringArray = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
	# Screen north is -z; angle measured clockwise from north.
	var angle: float = fposmod(atan2(direction.x, -direction.y), TAU)
	return names[int(round(angle / (TAU / 8.0))) % 8]


static func _box(color: Color, pad: float) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = color
	box.set_corner_radius_all(6)
	box.content_margin_left = pad * 1.6
	box.content_margin_right = pad * 1.6
	box.content_margin_top = pad * 0.6
	box.content_margin_bottom = pad * 0.6
	return box
