# Cube police officer

The approved pastel lavender pedestrian, with the same body geometry and 11-bone rig. Simplified soft navy cap, vest, belt, two pouches and a little radio; butter gold cap badge, chest shield and buckle. No textures or lettering.

`police_officer.glb` is one skinned mesh with three materials. `source/police_officer.blend` keeps the body and gear individually editable. Gear follows the head, torso or hips through rigid bone weights.

Ground-centered origin, facing Godot +Z. Use `res://scenes/characters/police_officer.tscn`, or double-click **Review Police Officer.command** at the project root. This is a model pass with no officer behavior or animations.

Rebuild: `/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/build_police_officer.py`.
