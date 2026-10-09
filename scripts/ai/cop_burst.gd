class_name CopBurst
extends RefCounted
## A cop's attack burst: for DURATION seconds its top speed is raised (the chase applies it), then it
## has to recharge. The learned cop decides when to fire it; in the game it is also the "!" moment.

const DURATION: float = 1.2
const SPEED_GAIN: float = 1.3

## Recharge time; shorter later in a run (same curve as the scripted cops' attack cooldown).
var cooldown: float = 4.5
var left: float = 0.0
var wait: float = 0.0
## True on the decision the burst fired.
var fired: bool = false


func reset() -> void:
	left = 0.0
	wait = 0.0
	fired = false


func tick(dt: float, want: bool) -> void:
	fired = false
	if left > 0.0:
		left = maxf(0.0, left - dt)
	elif wait > 0.0:
		wait = maxf(0.0, wait - dt)
	elif want:
		left = DURATION
		wait = cooldown
		fired = true


func active() -> bool:
	return left > 0.0


## 0 right after firing, 1 when it can fire again.
func readiness() -> float:
	if left > 0.0:
		return 0.0
	return 1.0 - clampf(wait / maxf(cooldown, 0.01), 0.0, 1.0)


static func cooldown_at(minute: float) -> float:
	return lerpf(4.5, 2.0, clampf(minute / 12.0, 0.0, 1.0))
