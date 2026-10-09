# Lowcar — building batch 05

Junction Convenience (011), Cycle Shop (012), Blue Gable House (040), Mint Office Block (070). Same approved pastels, cream trim, recessed blue glazing, and clean low-poly finish.

Placement scenes: `scenes/buildings/batch_05/`. One shared static visual mesh and simple main-body collider per building. Meters, ground-center origin, Godot +Z front. Canopies, pitched roofs, and roof ornaments extend beyond the main-body collider. Editable Blender sources are in `source/`.

All four appear in the driving city after relaunch. Review scene: `scenes/review/building_batch_05.tscn` (F6). 0 for all, 1–4 select, drag to orbit, wheel to zoom. Native overview: `previews/lineup.png`.

Rebuild with Blender and `tools/build_building_batch_05.py`.

The former tower asset path now contains a broad four-story office. Its visual mesh, bounds, and collider have been replaced.
