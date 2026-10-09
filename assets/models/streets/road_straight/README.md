# Lowcar straight street

One clean charcoal street tile, 20 m long: 8 m of road plus cream curb stones and broad sidewalk slabs for 12 m total width. Road surface is at Y=0; sidewalks reach Y=0.18. Repeat along Godot Z at 20 m spacing. Center dashes keep a 5 m rhythm across adjoining tiles.

`road_straight.glb` contains one visual mesh with six flat materials. `source/road_straight.blend` retains editable curb, sidewalk and paint parts. `scenes/streets/road_straight.tscn` adds road, sidewalk and sloped curb collision. Rebuild with Blender using `tools/build_road_straight.py`.

Double-click **Review Road.command** at the project root for the red car and three approved buildings beside three adjoining tiles. Previews: `previews/street.png` and `previews/driving_view.png`. This is a model review scene; the driving city's road layout is unchanged.
