extends SceneTree
const CITY_SMOKE_SUPPORT := preload("res://tests/city_smoke_support.gd")
## Actual main-scene input, physics, charge tradeoff, release tiers, pause, crash, and flames.

var failures: Array[String] = []
var checks: int = 0
var game: Node
var car: ArcadeVehicle
var presentation: CarPresentation
var session: Node

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	game = (load("res://scenes/main/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await process_frame
	session = root.get_node("RunSession")
	car = game.get_node("Vehicles/PlayerCar") as ArcadeVehicle
	presentation = car.get_node("Presentation") as CarPresentation
	var shift := InputEventKey.new()
	shift.physical_keycode = KEY_SHIFT
	shift.keycode = KEY_SHIFT
	shift.pressed = true
	shift.shift_pressed = true
	Input.parse_input_event(shift)
	await frames(10)
	check(car.boost.phase == ChargeBoost.Phase.READY, "Title screen cannot charge or fire a boost")
	shift.pressed = false
	shift.shift_pressed = false
	Input.parse_input_event(shift)
	await prepare()
	var cruise_speed: float = car.forward_speed
	shift.pressed = true
	shift.shift_pressed = true
	Input.parse_input_event(shift)
	await frames(60)
	check(car.boost.phase == ChargeBoost.Phase.CHARGING and not car.handbrake_active, "Physical Shift charges boost without applying the handbrake")
	check(car.forward_speed < cruise_speed-5.0, "Holding charge slows actual driving even with acceleration held")
	check(presentation.boost_exhaust.snapshot().visible and presentation.boost_exhaust.flame_length > 0.3, "Charge visibly burns from both exhausts")
	var short_flame: float = presentation.boost_exhaust.flame_length
	shift.pressed = false
	shift.shift_pressed = false
	Input.parse_input_event(shift)
	await frames(4)
	check(car.boost.phase == ChargeBoost.Phase.BOOSTING and car.forward_speed > cruise_speed, "Physical Shift release launches a real forward boost")
	check(presentation.boost_exhaust.flame_length > short_flame, "Release turns the charging fire into longer thrust flames")
	var control := InputEventKey.new()
	control.physical_keycode = KEY_CTRL
	control.keycode = KEY_CTRL
	control.ctrl_pressed = true
	control.pressed = true
	Input.parse_input_event(control)
	await frames(3)
	check(car.handbrake_active and car.boost.phase == ChargeBoost.Phase.READY, "Ctrl keeps the handbrake and cancels active thrust")
	control.ctrl_pressed = false
	control.pressed = false
	Input.parse_input_event(control)
	var mapped_pad := InputEventJoypadButton.new()
	mapped_pad.button_index = JOY_BUTTON_RIGHT_SHOULDER
	mapped_pad.pressed = true
	check(InputMap.event_is_action(mapped_pad,"charge_boost"), "Gamepad right shoulder maps to the same charge/release action")
	# Three durations exercise the tradeoff and payoff using actual player input and road travel.
	var speeds: Array[float] = []
	var durations: Array[float] = []
	var charging_speeds: Array[float] = []
	for hold_frames: int in [60,240,600]:
		await prepare()
		Input.action_press("charge_boost")
		await frames(hold_frames)
		charging_speeds.append(car.forward_speed)
		check(car.boost.phase == ChargeBoost.Phase.CHARGING and car.forward_speed < cruise_speed, "%d-second hold trades speed for charge" % (hold_frames/60))
		Input.action_release("charge_boost")
		await frames(4)
		speeds.append(car.forward_speed)
		durations.append(car.boost.duration)
	check(speeds[0] < speeds[1] and speeds[1] < speeds[2], "Longer holds produce strictly faster actual bursts")
	check(durations[0] < durations[1] and durations[1] < durations[2], "Longer holds also produce longer boost duration")
	check(charging_speeds[0] > charging_speeds[1] and charging_speeds[1] > charging_speeds[2], "Charging progressively sacrifices more driving speed")
	check(speeds[2] <= 64.001 and durations[2] <= 4.001, "Full charge respects the tuned speed and duration limits")
	print("BOOST_TIERS: speeds_mps=%s duration_seconds=%s charge_speeds_mps=%s" % [speeds,durations,charging_speeds])
	await frames(260)
	check(car.boost.phase == ChargeBoost.Phase.READY and car.forward_speed > cruise_speed and car.forward_speed < 64.0, "Ending thrust sheds speed without snapping the car back to cruise")
	await frames(150)
	check(car.boost.phase == ChargeBoost.Phase.READY and car.forward_speed < 34.0, "Boost expires and driving returns smoothly to cruise speed")
	check(not presentation.boost_exhaust.snapshot().visible, "Exhaust fire fades out after thrust expires")
	await prepare()
	Input.action_press("charge_boost")
	await frames(780)
	check(is_equal_approx(car.boost.charge_seconds,10.0) and car.boost.phase == ChargeBoost.Phase.CHARGING, "Holding beyond ten seconds caps charge and waits for release")
	check(game.get_node("GameUI")._boost_title.text.contains("FULL CHARGE"), "The HUD clearly marks the fully charged state")
	Input.action_release("charge_boost")
	await frames(3)
	check(car.boost.power > 0.999 and car.forward_speed > 63.9, "Releasing a capped hold delivers full power")
	var clear_exhaust: bool = true
	for frame: int in range(12):
		await frames(1)
		for side: int in [-1,1]:
			var mouth := Vector3(side*0.76,0.363,2.55)
			var tip: Vector3 = presentation.boost_exhaust._point(mouth,presentation.boost_exhaust.flame_length,presentation.boost_exhaust.flame_width,0.0,1.0,0.0)
			clear_exhaust = clear_exhaust and presentation.chassis.to_global(mouth).y > 0.16 and presentation.chassis.to_global(tip).y > 0.12
	check(clear_exhaust, "Full-boost nose lift keeps both pipe mouths and jet tips clear of the road")
	var full_speed: float = car.forward_speed
	Input.action_press("charge_boost")
	await frames(30)
	check(car.boost.phase == ChargeBoost.Phase.CHARGING and car.forward_speed < full_speed and car.boost.charge_seconds < 0.51, "A new Shift hold cuts thrust, slows the car, and starts a fresh charge")
	Input.action_release("charge_boost")
	await frames(3)
	check(car.boost.phase == ChargeBoost.Phase.BOOSTING and car.boost.power < 0.01 and car.boost.duration < 1.0, "Recharging replaces the old burst rather than stacking duration or power")
	Input.action_press("charge_boost")
	await frames(30)
	check(car.boost.phase == ChargeBoost.Phase.CHARGING, "Boost can be charged again without a hidden cooldown")
	# Freeze both physics-time charge and held flame drawings while paused.
	var pause_boost: Dictionary = car.boost.snapshot()
	var pause_fire: Dictionary = presentation.boost_exhaust.snapshot()
	session.toggle_pause()
	Input.action_release("charge_boost")
	await create_timer(0.1,true).timeout
	check(car.boost.snapshot()==pause_boost and presentation.boost_exhaust.snapshot()==pause_fire, "Pause freezes charge and flames, including a release while paused")
	session.toggle_pause()
	await frames(4)
	check(car.boost.phase == ChargeBoost.Phase.BOOSTING, "A paused release fires only when play resumes")
	Input.action_release("accelerate")
	game.restart_run()
	await frames(8)
	check(car.boost.phase == ChargeBoost.Phase.READY and car.boost.power == 0.0 and not presentation.boost_exhaust.snapshot().visible, "Restart clears charge, thrust, and fire together")
	# A stationary release still works, and airborne boost preserves real jump physics.
	Input.action_press("charge_boost")
	await frames(120)
	Input.action_release("charge_boost")
	await frames(4)
	check(car.forward_speed > 38.0 and car.velocity.length() > 35.0, "A release from rest creates thrust without needing W held")
	await prepare()
	Input.action_press("charge_boost")
	await frames(120)
	Input.action_press("attachment_primary")
	await frames(2)
	Input.action_release("attachment_primary")
	await frames(25)
	Input.action_release("charge_boost")
	await frames(4)
	check(not car.is_on_floor() and car.boost.phase == ChargeBoost.Phase.BOOSTING and car.forward_speed > 38.0, "Charge boost combines with an actual Ground Punch jump")
	# Higher speeds still use swept world collision and the normal terminal lifecycle.
	CITY_SMOKE_SUPPORT.approach_building(game.get_node("World") as CityStreamer, car)
	await frames(35)
	check(session.phase==session.Phase.ENDED and car.boost.phase==ChargeBoost.Phase.READY, "A boosted building impact ends the run and clears thrust")
	game.return_to_title()
	await frames(8)
	check(not presentation.boost_exhaust.snapshot().visible, "Return to title removes all boost flames")
	# Shape changes are stepped; parenting carries the held mesh with the chassis every frame.
	presentation.set_process(false)
	var fake := ChargeBoost.new()
	fake.phase = ChargeBoost.Phase.CHARGING
	fake.charge_seconds = 8.0
	for fps: int in [30,60,120]:
		presentation.boost_exhaust.clear()
		for frame: int in range(fps):
			presentation.boost_exhaust.tick(1.0/fps,fake,car.tuning,true)
		check(presentation.boost_exhaust.sample_count==12, "Flame drawings hold at 12 FPS under %d render FPS" % fps)
	var held_fire: Dictionary = presentation.boost_exhaust.snapshot()
	presentation.boost_exhaust.tick(0.02,fake,car.tuning,true)
	check(presentation.boost_exhaust.snapshot()==held_fire, "Flame geometry stays unchanged between held samples")
	check(presentation.boost_exhaust.get_parent()==presentation.chassis, "Twin flames stay attached to the animated exhaust pipes")
	for burst: int in range(100):
		fake.phase = ChargeBoost.Phase.BOOSTING
		fake.power = 1.0
		presentation.boost_exhaust.tick(1.0/12.0,fake,car.tuning,true)
		presentation.boost_exhaust.tick(1.0/12.0,fake,car.tuning,false)
	check(presentation.boost_exhaust.snapshot().nodes==1 and presentation.boost_exhaust.snapshot().surfaces<=1, "Repeated bursts reuse one bounded twin-flame mesh")
	Input.action_release("accelerate")
	Input.action_release("charge_boost")
	Input.action_release("attachment_primary")
	paused = false
	game.queue_free()
	await process_frame
	if failures.is_empty():
		print("LOWCAR_BOOST_PASS: %d checks" % checks)
		quit(0)
	else:
		for failure: String in failures:
			printerr("LOWCAR_BOOST_FAIL: "+failure)
		quit(1)

func prepare() -> void:
	Input.action_release("charge_boost")
	Input.action_release("accelerate")
	game.start_run(142857)
	Input.action_press("accelerate")
	await frames(150)

func frames(count: int) -> void:
	for frame: int in range(count):
		await physics_frame
	await process_frame

func check(condition: bool, message: String) -> void:
	checks += 1
	if condition:
		print("PASS: "+message)
	else:
		failures.append(message)
