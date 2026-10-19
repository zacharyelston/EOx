"""Pictures of a course run, from MuJoCo's offscreen renderer.

    panels   one frame per chosen obstacle, side by side, captioned (PNG)
    overview the whole course from above, the machine at the start (PNG)
    video    the run, chase camera (MP4 with ffmpeg, else GIF)
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from eox.sim import mjcf, terrain


def _model(p, tr, fitted):
    course = terrain.build(p.course)
    spec = mjcf.build(p, tr, course, fitted)
    return mjcf.load(spec), course


def _frame(r, m, d, qpos, camera):
    import mujoco
    d.qpos[:] = qpos
    mujoco.mj_forward(m, d)
    r.update_scene(d, camera=camera)
    return r.render()


def panels(p, tr, fitted, result, names: list[str], path: Path, size=(640, 400), camera="chase"):
    """A strip of frames, one per obstacle in `names`, captioned with the outcome."""
    import mujoco
    from PIL import Image, ImageDraw

    m, _ = _model(p, tr, fitted)
    d = mujoco.MjData(m)
    w, h = size
    cap = 34
    obs = [o for o in result.obstacles if o.name in names and o.snapshot is not None]
    strip = Image.new("RGB", (w * len(obs), h + cap), (252, 252, 251))
    draw = ImageDraw.Draw(strip)
    with mujoco.Renderer(m, h, w) as r:
        for k, o in enumerate(obs):
            strip.paste(Image.fromarray(_frame(r, m, d, o.snapshot, camera)), (k * w, 0))
            label = f"{o.name}: {o.status}" + (f" ({o.outcome})" if o.outcome != "cleared" else "")
            draw.text((k * w + 12, h + 10), label, fill=(11, 11, 11))
    path.parent.mkdir(parents=True, exist_ok=True)
    strip.save(path, optimize=True)
    return path


def overview(p, tr, fitted, path: Path, size=(1600, 640)):
    """The course from a high oblique viewpoint, the machine at the start line."""
    import mujoco
    from PIL import Image

    m, course = _model(p, tr, fitted)
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = (course.length * 0.47, 0.0, 0.0)
    cam.distance = course.length * 0.62
    cam.azimuth, cam.elevation = -62.0, -24.0
    with mujoco.Renderer(m, size[1], size[0]) as r:
        r.update_scene(d, camera=cam)
        img = r.render()
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(path, optimize=True)
    return path


def video(p, tr, fitted, result, path: Path, fps=15, speedup=3.0, size=(960, 540), camera="chase") -> Path:
    """The whole run from the chase camera. MP4 if ffmpeg is on the PATH, else GIF."""
    import mujoco
    from PIL import Image

    m, _ = _model(p, tr, fitted)
    d = mujoco.MjData(m)
    times, traj = result.times, result.qpos
    stamps = np.arange(0.0, times[-1], speedup / fps)
    idx = np.searchsorted(times, stamps).clip(0, len(times) - 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    with mujoco.Renderer(m, size[1], size[0]) as r:
        if ffmpeg:
            path = path.with_suffix(".mp4")
            with tempfile.TemporaryDirectory() as tmp:
                for n, i in enumerate(idx):
                    Image.fromarray(_frame(r, m, d, traj[i], camera)).save(f"{tmp}/{n:05d}.png")
                subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps), "-i", f"{tmp}/%05d.png",
                                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", str(path)], check=True)
        else:
            path = path.with_suffix(".gif")
            frames = [Image.fromarray(_frame(r, m, d, traj[i], camera)).resize((size[0] // 2, size[1] // 2))
                      for i in idx]
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0,
                           optimize=True)
    return path
