extends SceneTree
## Meaningful effects checks: readability inputs, world anchors, bounded reuse, lifecycle, real events.
var failures: Array[String] = []
var checks: int = 0

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var effects := CarMotionAccents.new()
	root.add_child(effects)
	var at := Transform3D.IDENTITY
	for index: int in range(30):
		effects.tick(1.0/30.0,at,0.0,0.0,true,true)
	check(effects.snapshot().wind_streaks == 0,"Parked car creates no airflow")
	for index: int in range(60):
		effects.tick(1.0/60.0,at,12.0,0.0,true,true)
	var slow: Dictionary = effects.snapshot()
	for index: int in range(60):
		effects.tick(1.0/60.0,at,32.0,0.0,true,true)
	var fast: Dictionary = effects.snapshot()
	check(fast.wind_streaks > slow.wind_streaks and fast.wind_strength > slow.wind_strength,"Airflow builds with actual driving speed")
	check(fast.wind_streaks <= effects.MAX_WIND_STREAKS,"Wind stays within the fixed streak budget")
	var geometry: Array = effects._wind_mesh.surface_get_arrays(0)
	var before_time: float = effects.snapshot().wind_time
	at.origin = Vector3(5,0,-8)
	effects.tick(0.01,at,32,0.0,true,true)
	check(effects.snapshot().wind_transform.origin == at.origin and effects.snapshot().wind_time == before_time and effects._wind_mesh.surface_get_arrays(0) == geometry,"Wind follows smooth travel while its drawn shape holds between ticks")
	for index: int in range(60):
		effects.tick(1.0/60.0,at,32.0,0.0,true,false)
	check(effects.snapshot().wind_streaks == 0,"Disabling driving fades airflow out")
	for fps: int in [30,60,120]:
		effects.clear(1)
		for index: int in range(fps):
			effects.tick(1.0/fps,at,25,0,true,true)
		check(effects.effect_sample_count == 12,"Effects keep 12 held samples at %d render FPS" % fps)
	effects.clear(2)
	at.origin = Vector3.ZERO
	effects.burst(at,true,0.35)
	var small: int = effects.snapshot().dust_puffs
	effects.clear(2)
	effects.burst(at,true,1.1)
	var large: int = effects.snapshot().dust_puffs
	check(large > small and large <= effects.MAX_DUST_PUFFS,"Harder impacts produce a larger bounded dust cloud")
	at.origin = Vector3(30,0,-25)
	effects.tick(1.0/12.0,at,32,0,true,true)
	check(effects.snapshot().burst_origins[0] == Vector3.ZERO,"Landing dust stays at the impact location as the car moves away")
	var count: int = effects.get_child_count()
	for index: int in range(100):
		at.origin.x = index
		effects.burst(at,true,1.2)
	check(effects.get_child_count() == count and effects.snapshot().active_bursts <= effects.BURST_POOL_SIZE,"One hundred impacts reuse the pool without growing the scene")
	for index: int in range(15):
		effects.tick(1.0/12.0,at,0,0,true,false)
	check(effects.snapshot().active_bursts == 0 and effects.snapshot().dust_puffs == 0,"Clouds and impact strokes expire completely")
	effects.burst(at,false,0.6)
	check(effects.snapshot().active_bursts == 1 and effects.snapshot().dust_puffs == 0,"Launch swishes stay distinct from landing clouds")
	effects.clear(3)
	check(effects.snapshot().active_bursts == 0 and effects.snapshot().wind_streaks == 0 and effects.snapshot().dust_puffs == 0,"Reset clears all effects immediately")
	effects.queue_free()
	await process_frame
	# Real floor contact from the reusable player, rather than a manually emitted event.
	var garage := (load("res://scenes/review/car_animation_garage.tscn") as PackedScene).instantiate()
	root.add_child(garage)
	garage.physics_drop()
	var seen: bool = false
	for index: int in range(95):
		await physics_frame
		await process_frame
		var state: Dictionary = garage.presentation.accents.snapshot()
		if garage.presentation.current_clip.begins_with("land_") and state.dust_puffs > 0:
			seen = true
			check(absf(state.burst_origins[0].y) < 0.05,"Actual landing dust anchors to floor contact rather than the trailing airborne visual")
			break
	check(seen,"Actual 12-meter drop triggers the cloud and outward impact strokes")
	garage.toggle_play()
	var paused_effects: Dictionary = garage.presentation.accents.snapshot()
	await create_timer(0.1,true).timeout
	check(garage.presentation.accents.snapshot() == paused_effects,"Pause freezes wind and impact ages together")
	garage.toggle_play()
	garage.start_effects_review()
	await process_frame
	for index: int in range(6):
		garage.step_effects_review(1.0/12.0)
	check(garage.effects_demo and garage.presentation.accents.snapshot().wind_streaks > 0,"Garage effects review exposes the actual airflow renderer")
	garage.toggle_play()
	garage.frame_slider.value = 60
	check(garage._effects_phase == "land_hard_b" and garage.presentation.chassis.scale.y < 0.6 and garage.presentation.accents.snapshot().dust_puffs > 0,"Paused effects timeline scrubs body and cloud together")
	garage.select_clip("idle")
	check(not garage.effects_demo and garage.presentation.accents.snapshot().active_bursts == 0 and garage.presentation.accents.snapshot().wind_streaks == 0,"Leaving effects review cleans up both layers")
	paused = false
	garage.queue_free()
	await process_frame
	if failures.is_empty():
		print("LOWCAR_MOTION_EFFECTS_PASS: %d checks" % checks)
		quit(0)
	else:
		for failure: String in failures:
			printerr("LOWCAR_MOTION_EFFECTS_FAIL: " + failure)
		quit(1)

func check(condition: bool, message: String) -> void:
	checks += 1
	if condition:
		print("PASS: " + message)
	else:
		failures.append(message)
