"""Render a preview of an `eox build` scene in Blender (headless).

    uv run eox build
    B=/Applications/Blender.app/Contents/MacOS/Blender
    $B -b -P tools/render_preview.py -- out/cad/powerbox/stl docs/img/powerbox-exploded.png --lift PB-102
    $B -b -P tools/render_preview.py -- out/cad/pro/stl docs/img/pro-layout.png
    $B -b -P tools/render_preview.py -- out/cad/pro/stl docs/img/pro-side.png --view side
    $B -b -P tools/render_preview.py -- out/cad/pro-articulated/stl docs/img/pro-top-articulated.png --view top

STL names are <kind>__<label>.stl; colour comes from the label, then the kind.
--lift raises every object whose label contains one of the given names (an
exploded view). --view iso (default, perspective) | side | top (orthographic).
Blender is only the viewer; geometry comes from build123d.
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
stl_dir, out_png = Path(argv[0]), Path(argv[1])
lift = argv[argv.index("--lift") + 1].split(",") if "--lift" in argv else []
view = argv[argv.index("--view") + 1] if "--view" in argv else "iso"
out_png.parent.mkdir(parents=True, exist_ok=True)

COLORS = {  # RGBA, linear. Matched against the label first, then the kind.
    "PB-101": (0.78, 0.80, 0.82, 1),   # tray: brushed aluminium
    "PB-102": (0.92, 0.92, 0.90, 1),   # cover: white powder
    "PB-10": (0.55, 0.57, 0.60, 1),    # small box parts
    "battery": (0.05, 0.18, 0.45, 1),
    "distribution": (0.85, 0.35, 0.05, 1),
    "wheel": (0.06, 0.06, 0.06, 1),
    "axle": (0.30, 0.30, 0.32, 1),
    "motor": (0.15, 0.22, 0.30, 1),
    "controller": (0.02, 0.02, 0.02, 1),
    "frame": (0.62, 0.15, 0.12, 1),
    "pivot": (0.80, 0.65, 0.10, 1),
    "steering": (0.80, 0.65, 0.10, 1),
    "implement": (0.62, 0.15, 0.12, 1),
    "seat": (0.10, 0.10, 0.10, 1),
}
LIFT = 0.26  # m

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
objs = []
for f in sorted(stl_dir.glob("*.stl")):
    bpy.ops.wm.stl_import(filepath=str(f), global_scale=0.001)
    ob = bpy.context.selected_objects[0]
    kind, label = f.stem.split("__", 1)
    ob.name = label
    colour = next((v for k, v in COLORS.items() if k in label), COLORS.get(kind, (0.6, 0.6, 0.6, 1)))
    mat = bpy.data.materials.new(label)
    mat.diffuse_color = colour
    ob.data.materials.append(mat)
    if any(name in label for name in lift):
        ob.location.z += LIFT
    objs.append(ob)

scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.show_shadows = True
sh.show_object_outline = True
scene.display.shadow_focus = 0.8
scene.render.resolution_x, scene.render.resolution_y = 1400, 875
scene.render.image_settings.compression = 90
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.96, 0.96, 0.95)

# frame the camera on everything imported
bpy.context.view_layer.update()
pts = [ob.matrix_world @ Vector(c) for ob in objs for c in ob.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
target = (lo + hi) / 2
size = (hi - lo).length

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 50
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
ext = hi - lo
aspect = scene.render.resolution_x / scene.render.resolution_y
if view == "iso":
    cam.location = target + Vector((1.0, 1.15, 0.85)).normalized() * size * 1.9
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
else:
    cam_data.type = "ORTHO"
    if view == "side":                      # from the right-hand side: forward points right
        cam.location = target - Vector((0, size * 3, 0))
        cam.rotation_euler = (math.radians(90), 0, 0)
        cam_data.ortho_scale = max(ext.x, ext.z * aspect) * 1.12
    else:                                   # top: forward points right
        cam.location = target + Vector((0, 0, size * 3))
        cam.rotation_euler = (0, 0, 0)
        cam_data.ortho_scale = max(ext.x, ext.y * aspect) * 1.12
    cam_data.clip_end = size * 10
scene.render.filepath = str(out_png)
bpy.ops.render.render(write_still=True)
print("rendered", out_png)
