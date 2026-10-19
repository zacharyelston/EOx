"""Render the power box preview in Blender (headless).

    uv run eox build
    /Applications/Blender.app/Contents/MacOS/Blender -b -P tools/render_preview.py -- out/cad/stl docs/img

Writes powerbox-exploded.png (cover lifted) and powerbox-closed.png.
Blender is only the viewer here; geometry comes from build123d.
"""

import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["out/cad/stl", "docs/img"]
stl_dir, out_dir = Path(argv[0]), Path(argv[1])
out_dir.mkdir(parents=True, exist_ok=True)

COLORS = {  # RGBA, linear
    "PB-101": (0.78, 0.80, 0.82, 1),   # tray: brushed aluminium
    "PB-102": (0.92, 0.92, 0.90, 1),   # cover: white powder
    "PB-103": (0.55, 0.57, 0.60, 1),
    "PB-104": (0.55, 0.57, 0.60, 1),
    "PB-105": (0.55, 0.57, 0.60, 1),
    "PB-106": (0.60, 0.75, 0.62, 1),   # bulkhead: tinted so it reads in the preview
    "fan": (0.15, 0.15, 0.15, 1),
    "battery": (0.05, 0.18, 0.45, 1),
    "motor": (0.12, 0.12, 0.13, 1),
    "controller": (0.02, 0.02, 0.02, 1),
    "electrics": (0.85, 0.35, 0.05, 1),
    "shaft": (0.70, 0.70, 0.72, 1),
}
LIFT = 0.26  # m, cover lift in the exploded view

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

objs = {}
for f in sorted(stl_dir.glob("*.stl")):
    bpy.ops.wm.stl_import(filepath=str(f), global_scale=0.001)
    ob = bpy.context.selected_objects[0]
    key = f.stem.split("__")[1]
    ob.name = key
    colour = next(v for k, v in COLORS.items() if key.startswith(k))
    mat = bpy.data.materials.new(key)
    mat.diffuse_color = colour
    ob.data.materials.append(mat)
    objs[key] = ob

scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.show_shadows = True
sh.show_object_outline = True
scene.display.shadow_focus = 0.8
scene.render.resolution_x, scene.render.resolution_y = 1600, 1000
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.96, 0.96, 0.95)

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 50
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def shoot(name, target, dist):
    direction = Vector((1.0, 1.15, 0.85)).normalized()
    cam.location = Vector(target) + direction * dist
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(out_dir / name)
    bpy.ops.render.render(write_still=True)


# the fan is screwed to the cover, so it lifts with it
lifted = [o for k, o in objs.items() if k.startswith("PB-102") or k == "fan"]
for o in lifted:
    o.location.z += LIFT
shoot("powerbox-exploded.png", (0.0, 0.0, 0.22), 2.3)
for o in lifted:
    o.location.z -= LIFT
shoot("powerbox-closed.png", (0.0, 0.0, 0.13), 2.0)
print("rendered to", out_dir)
