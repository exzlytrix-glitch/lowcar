@tool
extends EditorScenePostImport
## Painted glazing stays graphic; the modeled recesses and trims carry depth.

func _post_import(scene: Node) -> Object:
	for object: MeshInstance3D in scene.find_children("*", "MeshInstance3D", true, false):
		for surface in range(object.mesh.get_surface_count()):
			var material := object.mesh.surface_get_material(surface) as StandardMaterial3D
			if material != null and (material.resource_name.begins_with("Glass") or material.resource_name.begins_with("Reflection")):
				material.disable_receive_shadows = true
	return scene
