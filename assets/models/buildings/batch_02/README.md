# Lowcar — building batch 02

Everyday Bodega (004), Neighborhood Barber (010), Neighborhood Bakery (024), Wide Row House (038). Same palette, recessed painted glazing, white trim, and low-poly finish as the approved buildings.

Placement scenes: `scenes/buildings/batch_02/`. One merged visual mesh and simple solid body collider per building. Meters; ground-center origin; Godot +Z front. Canopies, balconies, and roof details extend beyond the main collider. Exterior models; no walkable interiors.

Editable sources: `source/*.blend`. Godot lineup: `previews/lineup.png`. Review with `scenes/review/building_batch_02.tscn` (F6); 0 for all, 1–4 select, drag to orbit, wheel to zoom.

Rebuild with Blender: `tools/build_building_batch_02.py`. All four are now used by the gameplay city generator.
