# Lowcar street stuff

Seven clean, texture-free models matching the approved road and pastel buildings: straight sidewalk, faceted corner, curb ramp, cream-and-sage lantern pole, open teal trash can, peach slat bench, and coral fire hydrant.

Sidewalks reach 0.18 m, matching the road model. The straight piece is 4 × 2 m, the corner is 4 × 4 m, and the ramp is 3 × 2 m. The curb faces Godot +Z. Place street furniture on the sidewalk top; each prop has a ground-center origin. The lantern pole is 4.5 m high.

Each GLB uses one visual mesh. Editable Blender sources live in `source/`; collision-ready placement scenes live in `scenes/streets/street_stuff/`. Sidewalk collision follows the geometry, including the ramp. Furniture uses simple box or cylinder collision. Rebuild with Blender using `tools/build_street_stuff.py`.

Double-click **Review Street Stuff.command** at the project root. Press **1** for the sidewalk pieces and **2** for the furniture on the approved road. Native Godot previews are `previews/sidewalks.png` and `previews/furniture.png`.
