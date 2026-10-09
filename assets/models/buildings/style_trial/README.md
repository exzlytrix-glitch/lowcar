# Lowcar building studies

Three original, editable buildings for the bright Lowcar city. Broad pastel plaster, cream trim, blue recessed glazing, simple physical reflections, chunky silhouette details, and faceted plants share the red car's clean shape language.

| Model | Identity | Main footprint | Full height | Triangles |
| --- | --- | --- | --- | --- |
| corner_market.glb | Coral corner market, diagonal entrance, striped awnings, balcony, roof garden | 10.8 × 9.5 m, chamfered corner | 10.85 m | 8,916 |
| terrace_apartments.glb | Mint apartments, staggered balconies, coral stair tower, setback roof room and pergola | 9.2 × 9.0 m | 14.95 m | 9,118 |
| redline_garage.glb | Yellow auto shop, three sawtooth roof teeth, blue clerestories, two open bays and one shutter | 13.8 × 9.0 m | 6.68 m | 4,962 |

Each export is one static mesh with material surfaces. The Blender sources retain named editable parts. Window recesses, awnings, balcony slabs, railings, signage, roof objects, and small street props are geometry. Materials are opaque, texture-free, and shared within each building.

The Godot import preset preserves the small authored details without generated LODs or compressed positions. Its post-import script gives painted glazing clean direct/ambient lighting; recesses, frames, sills, and awnings carry the window shadows.

## Review in Godot

Run `tools/building_gallery.sh` from the project, or open `scenes/review/building_gallery.tscn` in Godot and press F6. The red muscle car is shown at its real game scale.

- **0:** all three buildings.
- **1 / 2 / 3:** market / apartments / garage.
- **Drag:** orbit. **Mouse wheel:** zoom. **Left / Right:** rotate in steps.
- **G:** street view from behind the car. **I** or **F:** reset overview. **B:** rear view.
- **Tab:** hide or show controls.

The reusable visual scenes are in `scenes/buildings`. They use a ground-center origin, meters, Godot **+Z** as the front/street direction, and **+Y** up. Balconies and street props extend beyond the main footprints; use `manifest.json` for complete bounds.

These study scenes remain reusable visual meshes. The gameplay building kit now places them alongside all completed batches and adds world collision, including mesh collision for the garage’s open bays. F5 runs the integrated city.

## Source and previews

`source/*.blend` contains each editable building and a separate studio camera/light collection. The studio is excluded from GLB exports. Blender uses **-Y** as the building front; glTF converts this to Godot **+Z**.

`previews/` contains real Godot captures: lineup, individual overview, rear, and street views. Source and preview folders have `.gdignore` files so Godot does not import the Blender projects or preview images.

Rebuild from the project directory:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python tools/build_building_trial.py
/Applications/Godot.app/Contents/MacOS/Godot --headless --path . --editor --import
/Applications/Godot.app/Contents/MacOS/Godot --headless --path . --script tools/verify_buildings.gd
tools/building_gallery.sh -- --capture-buildings
```

Verification checks all three real imports, hashes, units, bounds, triangle counts, materials, editable sources, and triangle-level entrance clearance for the garage's open and closed bays.
