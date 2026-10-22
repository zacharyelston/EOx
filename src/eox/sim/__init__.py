"""Terrain-course simulation: the models driven over design/course.toml in MuJoCo.

    terrain  the course as a heightfield
    mjcf     a MuJoCo model of a tractor, from the same Tractor the calcs use
    run      drive the course, score each obstacle
"""

from types import SimpleNamespace


def detail(c) -> SimpleNamespace:
    """The course's simulation settings at its level of detail: [course.sim]
    plus [course.lod_levels.<course.lod>] (timestep, control rate, terrain
    resolution, which parts collide)."""
    return SimpleNamespace(**vars(c.sim), **vars(getattr(c.lod_levels, c.lod)), lod=c.lod)
