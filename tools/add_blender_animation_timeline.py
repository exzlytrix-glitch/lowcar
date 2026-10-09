"""Add the native pack's held poses to the editable Blender source.

Run after build_red_muscle_car.py. All 30 clips occupy named timeline sections;
Godot still uses its individual AnimationLibrary clips at runtime.
"""
from pathlib import Path
from math import radians
import json
import bpy
from mathutils import Euler, Matrix, Vector

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / 'assets/models/vehicles/red_muscle_car/source/red_muscle_car.blend'
clips = json.loads((PROJECT / 'resources/animation/car_clips.json').read_text())['clips']
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
scene.render.fps = 12
scene.render.fps_base = 1
scene.timeline_markers.clear()
root = bpy.data.objects['Lowcar_Red_Muscle']
chassis = bpy.data.objects['Chassis']
trunk = bpy.data.objects['TrunkHinge']
wheels = list(bpy.data.objects['Wheels'].children)
rest = {obj.name: obj.location.copy() for obj in wheels}
for wheel in wheels:
    steer = wheel.children[0]
    spin = steer.children[0]
    steer.name = wheel.name + 'Steer'
    spin.name = wheel.name + 'Spin'
for obj in [root,chassis,trunk,*wheels]:
    obj.animation_data_clear()
chassis.rotation_mode = 'QUATERNION'
convert = Matrix(((1,0,0),(0,0,-1),(0,1,0)))
frame_offset = 1
sections = []

def sample(clip, frame):
    keys = clip['keys']
    left, right = keys[0], keys[-1]
    for a,b in zip(keys,keys[1:]):
        if a['frame'] <= frame <= b['frame']:
            left,right = a,b
            break
    span = right['frame'] - left['frame']
    t = (frame - left['frame']) / span if span else 0
    t = t*t*(3-2*t)
    return {k: Vector(left[k]).lerp(Vector(right[k]),t) for k in left if k != 'frame'}

for name,clip in clips.items():
    start = frame_offset
    scene.timeline_markers.new(name,frame=start)
    for frame in range(clip['frames']+1):
        p = sample(clip,frame)
        scale = p['body_scale']
        rot = Euler(tuple(radians(v) for v in p['body_rotation']),'YXZ').to_matrix()
        pivot = Vector((0,.78*scale.y,0))
        offset = pivot - rot @ pivot + p['body_offset']
        chassis.scale = Vector((scale.x,scale.z,scale.y))
        chassis.rotation_quaternion = (convert @ rot @ convert.transposed()).to_quaternion()
        chassis.location = convert @ offset
        trunk.rotation_euler.x = radians(p['trunk_rotation'].x)
        root.location.z = (1.15 if name == 'air_rise' else 1.65 if name == 'air_hang' else 1.65 - 1.3 * frame / clip['frames'] if name == 'air_drop' else max(0,(frame-1)*.15) if name == 'launch' else 0)
        for obj in [root,chassis,trunk,*wheels]:
            if obj in wheels:
                r = rest[obj.name]
                t = p['tire_scale']
                obj.scale = Vector((t.x,t.z,t.y))
                obj.location = Vector((r.x*scale.x,r.y*scale.z,r.z*t.y + p['tire_offset'].y))
            obj.keyframe_insert(data_path='location',frame=frame_offset)
            obj.keyframe_insert(data_path='scale',frame=frame_offset)
            obj.keyframe_insert(data_path='rotation_quaternion' if obj == chassis else 'rotation_euler',frame=frame_offset)
        frame_offset += 1
    sections.append({'clip':name,'start_frame':start,'end_frame':frame_offset-1})
    # A short neutral separator makes scrubbing clip boundaries unambiguous.
    frame_offset += 2

for action in bpy.data.actions:
    if action.layers:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'CONSTANT'
scene.frame_start = 1
scene.frame_end = frame_offset - 3
scene.frame_set(1)
root['animation_sections'] = json.dumps(sections)
root['pose_fps'] = 12
root['animation_source'] = 'resources/animation/car_clips.json'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
(PROJECT/'assets/models/vehicles/red_muscle_car/source/animation_timeline.json').write_text(json.dumps(sections,indent=2)+'\n')
print(f'LOWCAR_BLENDER_ANIMATION_TIMELINE: {len(sections)} sections, {scene.frame_end} frames, 12 FPS held poses')
