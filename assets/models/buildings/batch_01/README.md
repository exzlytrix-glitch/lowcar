# Lowcar — building batch 01

Four French Quarter-inspired exteriors: Corner Café (023), Coral Row House (037), Blue Townhouse (039), and Skinny Apartments (058).

Use the scenes in `scenes/buildings/batch_01/` for placement. Each has one merged visual mesh and a simple solid building-body collider on the World layer. Units are meters, origin is ground-center, and front faces Godot +Z. Balconies and roof ornaments extend beyond the body collider. These exterior models have no walkable interiors.

Editable Blender sources are in `source/`; the manifest records bounds and export hashes. `previews/lineup.png` is rendered in Godot beside the actual red muscle car.

Review scene: `scenes/review/building_batch_01.tscn` (F6). 0 shows all four; 1–4 select a building. Drag to orbit, wheel to zoom, G for street view, B for rear, I for overview, Tab to hide controls.

Rebuild with Blender using `tools/build_building_batch_01.py`. All four are now used by the gameplay city generator, alongside the original studies and the other completed batches.
