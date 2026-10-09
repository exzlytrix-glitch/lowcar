extends SceneTree
func _initialize() -> void:
	var parts := (load("res://assets/models/vehicles/red_muscle_car/explosion_parts.glb") as PackedScene).instantiate()
	root.add_child(parts)
	parts.print_tree_pretty()
	parts.queue_free()
	quit()
