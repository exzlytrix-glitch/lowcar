# Lowcar — building batch 04

Flower Shop (007), Corner Hardware (008), Spin Laundry (009), Courtyard Duplex (042). The same approved pastel palette, white trim, recessed blue glazing, and clean low-poly finish.

Placement scenes: `scenes/buildings/batch_04/`. Shared static meshes, meter scale, ground-center origins, and Godot +Z front. The duplex uses six simple collision boxes to preserve its L-shaped body and open courtyard; the other three use a main-body box. Editable Blender files are in `source/`.

All four are included in the driving city automatically after relaunch. Review scene: `scenes/review/building_batch_04.tscn` (F6). 0 for all, 1–4 select, drag to orbit, wheel to zoom. Native overview: `previews/lineup.png`.

Rebuild with Blender and `tools/build_building_batch_04.py`.
