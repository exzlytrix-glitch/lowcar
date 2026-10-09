extends RefCounted
## Aim crash replays at a real solid facade, rather than a former box coordinate.

static func approach_building(world: CityStreamer, car: ArcadeVehicle) -> void:
	var chunk: CityChunk = world.active_chunks[Vector2i.ZERO]
	for building: Node3D in chunk.get_children():
		if not building.is_in_group("city_buildings"):
			continue
		for collision: CollisionShape3D in building.find_children("*", "CollisionShape3D", true, false):
			if not collision.shape is BoxShape3D:
				continue
			var size: Vector3 = (collision.shape as BoxShape3D).size
			var front := building.global_basis.z.normalized()
			var at := collision.global_position + front * (size.z * .5 + 7.0)
			at.y = .1
			car.global_position = at
			car.rotation.y = building.global_rotation.y
			car.velocity = -front * absf(car.forward_speed)
			car.reset_physics_interpolation()
			return
	assert(false, "No solid city building available for collision replay")
