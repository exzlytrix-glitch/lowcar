# Lowcar — building batch 03

Paperback Bookshop (006), Neighborhood Pharmacy (005), Six-Unit Apartments (057), Cream City Office (069). Same approved palette, recessed blue glazing, cream trim, and low-poly finish.

Placement scenes: `scenes/buildings/batch_03/`. One merged mesh and solid main-body collider per building. Meters, ground-center origin, Godot +Z front. Balconies, canopies, and roof ornaments extend beyond the body collider. No walkable interiors.

Editable sources: `source/*.blend`. Godot preview: `previews/lineup.png`. Open `scenes/review/building_batch_03.tscn` (F6) to inspect; 0 shows all, 1–4 select, drag to orbit, wheel to zoom.

Rebuild using Blender and `tools/build_building_batch_03.py`. All four are now used by the gameplay city generator.

The former tower asset path now contains a broad three-story office. Its visual mesh, bounds, and collider have been replaced.
