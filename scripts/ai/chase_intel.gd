class_name ChaseIntel
extends RefCounted
## What the cops know about the runner, shared over the radio: one cop seeing it tells the whole team.
## A cop sees the runner within SIGHT_RANGE when no building blocks the line, and always up close.
## Out of sight, the team only has the last place and speed it was seen at. If nobody has seen it for
## PING_SECONDS, dispatch calls in where it is, so breaking line of sight shakes the cops for a few
## seconds but never loses them for good.

const SIGHT_RANGE: float = 150.0
const ALWAYS_SEE: float = 25.0
const PING_SECONDS: float = 6.0
## Where the team aims when the runner is out of sight: the last sighting carried forward this long.
const LEAD_SECONDS: float = 1.0
const WALL_MASK: int = 1

## Somebody saw the runner (or dispatch called it in) at the latest update.
var known: bool = true
var last_position := Vector2.ZERO
var last_velocity := Vector2.ZERO
var last_forward := Vector2(0.0, -1.0)
## Seconds since the last sighting.
var age: float = 0.0


func reset(runner: LabVehicle) -> void:
	_refresh(runner)


## Updates from this decision's sightings and returns, per cop in `cops`, whether it sees the runner.
func update(cops: Array, runner: LabVehicle, dt: float) -> Array[bool]:
	var sightings: Array[bool] = []
	var anyone: bool = false
	var space: PhysicsDirectSpaceState3D = runner.get_world_3d().direct_space_state
	for cop: LabVehicle in cops:
		var sees: bool = sees_runner(space, cop, runner)
		sightings.append(sees)
		anyone = anyone or sees
	age += dt
	if anyone or age >= PING_SECONDS:
		_refresh(runner)
	else:
		known = false
	return sightings


func believed_position() -> Vector2:
	return last_position + last_velocity * minf(age, LEAD_SECONDS)


static func sees_runner(space: PhysicsDirectSpaceState3D, cop: LabVehicle, runner: LabVehicle) -> bool:
	var gap: float = cop.global_position.distance_to(runner.global_position)
	if gap < ALWAYS_SEE:
		return true
	if gap > SIGHT_RANGE:
		return false
	var query := PhysicsRayQueryParameters3D.create(cop.global_position + Vector3.UP * 1.2,
		runner.global_position + Vector3.UP * 1.0, WALL_MASK, [cop.get_rid(), runner.get_rid()])
	return space.intersect_ray(query).is_empty()


func _refresh(runner: LabVehicle) -> void:
	known = true
	age = 0.0
	last_position = Vector2(runner.global_position.x, runner.global_position.z)
	last_velocity = Vector2(runner.velocity.x, runner.velocity.z)
	last_forward = Vector2(-runner.global_basis.z.x, -runner.global_basis.z.z).normalized()
