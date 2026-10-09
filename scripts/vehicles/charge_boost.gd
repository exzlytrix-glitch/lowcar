class_name ChargeBoost
extends RefCounted
## Physics-time charge/release state. Holds cap at ten seconds; a new hold cuts thrust to recharge.

enum Phase { READY, CHARGING, BOOSTING }
var phase: Phase = Phase.READY
var charge_seconds: float = 0.0
var power: float = 0.0
var duration: float = 0.0
var remaining: float = 0.0
var elapsed: float = 0.0
var fired_this_tick: bool = false


func tick(delta: float, held: bool, enabled: bool, braking: bool, tuning: VehicleTuning) -> void:
	fired_this_tick = false
	if not enabled or braking:
		clear()
		return
	if phase == Phase.BOOSTING:
		if held:
			phase = Phase.CHARGING
			charge_seconds = 0.0
			power = 0.0
			duration = 0.0
			remaining = 0.0
			elapsed = 0.0
		else:
			elapsed += delta
			remaining = maxf(0.0, duration - elapsed)
			if remaining <= 0.0:
				phase = Phase.READY
				power = 0.0
			return
	if phase == Phase.READY and held:
		phase = Phase.CHARGING
	if phase == Phase.CHARGING:
		if held:
			charge_seconds = minf(charge_seconds + delta, tuning.boost_max_charge_seconds)
		elif charge_seconds >= 0.12:
			var ratio: float = charge_ratio(tuning)
			power = ratio * ratio * (3.0 - 2.0 * ratio)
			duration = lerpf(tuning.boost_min_duration_seconds, tuning.boost_max_duration_seconds, power)
			remaining = duration
			elapsed = 0.0
			phase = Phase.BOOSTING
			charge_seconds = 0.0
			fired_this_tick = true
		else:
			phase = Phase.READY
			charge_seconds = 0.0


func charge_ratio(tuning: VehicleTuning) -> float:
	return clampf(charge_seconds / maxf(tuning.boost_max_charge_seconds, 0.01), 0.0, 1.0)


func speed_limit(tuning: VehicleTuning) -> float:
	return lerpf(tuning.boost_min_speed_mps, tuning.boost_max_speed_mps, power)


func charge_speed_multiplier(tuning: VehicleTuning) -> float:
	return lerpf(0.72, 0.36, charge_ratio(tuning))


func clear() -> void:
	phase = Phase.READY
	charge_seconds = 0.0
	power = 0.0
	duration = 0.0
	remaining = 0.0
	elapsed = 0.0
	fired_this_tick = false


func snapshot() -> Dictionary:
	return {"phase":phase,"charge_seconds":charge_seconds,"power":power,"duration":duration,
		"remaining":remaining,"elapsed":elapsed}
