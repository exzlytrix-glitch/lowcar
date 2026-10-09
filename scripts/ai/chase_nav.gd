class_name ChaseNav
extends RefCounted
## Where a learned car is driving to: its brain picks one of OPTIONS road targets about once a second
## (every DECISIONS decisions), and the car's road route leads there. Nothing rewards any option; they
## only make plans like cutting someone off possible, which a single "shortest route to the runner"
## never allowed.
##
## Cop options, all relative to where the team thinks the runner is (recomputed as it moves):
##   0 chase it directly  1 the junction ahead of it  2 the junction after that (straight on)
##   3 its next junction's left exit  4 its next junction's right exit
## Runner options (the target is fixed when chosen):
##   0 its GPS destination  1 straight on at the next junction  2 left there  3 right there  4 back the way it came
##
## Each option is described to the brain (OPTION_FEATURES each): where its target is, how far this car
## has to drive there, how far the other side is from it, and whether the option exists here.

const OPTIONS: int = 5
const DECISIONS: int = 10
const OPTION_FEATURES: int = 5
const FEATURES: int = OPTIONS * OPTION_FEATURES + OPTIONS + 1
## A cop covering a side exit waits this far down it.
const EXIT_COVER: float = 30.0
const STRAIGHT_TURN: float = 0.6
const SIDE_TURN: float = 0.5

var nav: RoadNav
var is_runner: bool = false
var option: int = 0
## The brain's choice is used this decision.
var open: bool = true
var targets: Array[Vector2] = []
var valid: Array[bool] = []
var _countdown: int = 0
var _drive_lengths := PackedFloat32Array()
var _frozen := Vector2.ZERO


func setup(road_nav: RoadNav, runner: bool) -> void:
	nav = road_nav
	is_runner = runner
	targets.resize(OPTIONS)
	valid.resize(OPTIONS)
	_drive_lengths.resize(OPTIONS)


## Starts over (new chase or new spawn): option 0, and the first decision is a choice.
func reset() -> void:
	option = 0
	_countdown = 0
	open = true
	_drive_lengths.fill(0.0)


## Call once per decision before observing: whether this decision's choice will be used.
func tick() -> void:
	open = _countdown <= 0
	if open:
		_countdown = DECISIONS
	_countdown -= 1


func choose(index: int) -> void:
	option = clampi(index, 0, OPTIONS - 1)
	if is_runner:
		_frozen = targets[option]


## Where the car should route to now.
func target() -> Vector2:
	return _frozen if is_runner and option != 0 else targets[option]


## Cop: options around the runner as the team knows it (`seen` position, `heading` direction).
func update_cop_targets(seen: Vector2, heading: Vector2) -> void:
	targets.fill(seen)
	valid.fill(false)
	valid[0] = true
	var next: Dictionary = nav.next_junction(seen, heading)
	if next.is_empty():
		return
	var junction: int = next["node"]
	var at: Vector2 = nav.graph.positions[junction]
	for k: int in range(1, OPTIONS):
		targets[k] = at
	valid[1] = true
	var ways: Array = nav.exits(junction, next["edge"])
	var straight: Dictionary = _straightest(ways)
	if not straight.is_empty():
		targets[2] = nav.graph.positions[straight["end"]]
		valid[2] = true
	if not ways.is_empty() and ways[0]["turn"] < -SIDE_TURN:
		targets[3] = nav.along_exit(junction, ways[0], EXIT_COVER)
		valid[3] = true
	if not ways.is_empty() and ways[ways.size() - 1]["turn"] > SIDE_TURN:
		targets[4] = nav.along_exit(junction, ways[ways.size() - 1], EXIT_COVER)
		valid[4] = true


## Runner: escape options from its own position and heading; `goal` is its GPS destination.
func update_runner_targets(here: Vector2, heading: Vector2, goal: Vector2) -> void:
	targets.fill(goal)
	valid.fill(false)
	valid[0] = true
	var behind: Dictionary = nav.next_junction(here, -heading)
	if not behind.is_empty():
		targets[4] = nav.graph.positions[behind["node"]]
		valid[4] = true
	var next: Dictionary = nav.next_junction(here, heading)
	if next.is_empty():
		return
	var junction: int = next["node"]
	var ways: Array = nav.exits(junction, next["edge"])
	for k: int in range(1, 4):
		targets[k] = nav.graph.positions[junction]
	var straight: Dictionary = _straightest(ways)
	if not straight.is_empty():
		targets[1] = nav.graph.positions[straight["end"]]
		valid[1] = true
	if not ways.is_empty() and ways[0]["turn"] < -SIDE_TURN:
		targets[2] = nav.graph.positions[ways[0]["end"]]
		valid[2] = true
	if not ways.is_empty() and ways[ways.size() - 1]["turn"] > SIDE_TURN:
		targets[3] = nav.graph.positions[ways[ways.size() - 1]["end"]]
		valid[3] = true


## Road distance from the car to every option (A* each, so only on decisions where the brain chooses).
func measure(here: Vector2, heading: Vector2) -> void:
	if not open:
		return
	for k: int in OPTIONS:
		var same: int = targets.find(targets[k])
		if same < k and not (is_runner and (k == 4 or same == 4)):
			_drive_lengths[k] = _drive_lengths[same]
			continue
		var facing: Vector2 = -heading if is_runner and k == 4 else heading
		_drive_lengths[k] = nav.route_length(nav.route(here, facing, targets[k]))


## Brain inputs: per option [target x, target ahead (this car's frame, /100), road distance /300,
## the other side's distance to it /300, exists], then the current option one-hot, then "choosing now".
## `others` are the positions that matter to the other side: the runner for cops, nearby cops for the runner.
func features(here: Vector2, forward: Vector2, others: Array) -> PackedFloat32Array:
	var out := PackedFloat32Array()
	out.resize(FEATURES)
	var right := Vector2(-forward.y, forward.x)
	for k: int in OPTIONS:
		var offset: Vector2 = targets[k] - here
		var closest: float = 900.0
		for point: Vector2 in others:
			closest = minf(closest, point.distance_to(targets[k]))
		var i: int = k * OPTION_FEATURES
		out[i] = clampf(offset.dot(right) / 100.0, -3.0, 3.0)
		out[i + 1] = clampf(offset.dot(forward) / 100.0, -3.0, 3.0)
		out[i + 2] = clampf(_drive_lengths[k] / 300.0, 0.0, 3.0)
		out[i + 3] = clampf(closest / 300.0, 0.0, 3.0)
		out[i + 4] = 1.0 if valid[k] else 0.0
	out[OPTIONS * OPTION_FEATURES + option] = 1.0
	out[FEATURES - 1] = 1.0 if open else 0.0
	return out


static func _straightest(ways: Array) -> Dictionary:
	var best: Dictionary = {}
	for way: Dictionary in ways:
		if absf(way["turn"]) < STRAIGHT_TURN and (best.is_empty() or absf(way["turn"]) < absf(best["turn"])):
			best = way
	return best
