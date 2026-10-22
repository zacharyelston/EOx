# Remote simulations on ML2

EOX runs on `ml2@ml2.anceralabs.com` over SSH. The current MuJoCo physics
loop runs on the CPU; design trials distribute independent evaluations across
processes. NVIDIA GPUs support headless rendering through EGL. GPU physics
would require a separate backend and validation.

## Host checked on 2026-10-22

- Threadripper PRO 3955WX: 16 physical cores, 32 hardware threads.
- Approximately 128 GB RAM.
- Quadro RTX 6000: 24 GB; Quadro RTX 8000: 48 GB.
- NVIDIA driver 535.216.03; EGL and ffmpeg available.
- `uv` at `/home/ml2/.local/bin/uv`; Python 3.12 available.

Start with 8 workers. Try 16 for larger populations after checking other
workloads. Useful concurrency is bounded by the number of uncached designs
in a generation; generations run sequentially. Limit numerical-library
threads to one per process to avoid multiplying thread pools.

## Copy a committed source snapshot

From the local repository:

```bash
git rev-parse HEAD
ssh ml2@ml2.anceralabs.com 'mkdir -p "$HOME/eox-sim"; mktemp -d "$HOME/eox-sim/run-XXXXXX"'
git archive --format=tar HEAD -o /tmp/eox-source.tar
```

Record the commit SHA and replace `run-XXXXXX` below with the directory
returned by `mktemp`. Uncommitted edits are not included. Local credentials,
virtual environments, and generated outputs are not copied.

```bash
scp /tmp/eox-source.tar ml2@ml2.anceralabs.com:/home/ml2/eox-sim/run-XXXXXX/source.tar
ssh ml2@ml2.anceralabs.com
cd /home/ml2/eox-sim/run-XXXXXX
tar -xf source.tar
rm source.tar
"$HOME/.local/bin/uv" sync --locked --python 3.12
```

The extracted snapshot has no Git metadata. Subsequent commands run from its
root directory, without changing other projects on the host.

## Run Home and render on the RTX 8000

In the remote shell:

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONUNBUFFERED=1
mkdir -p out/ml2
.venv/bin/eox course --model home --config both --render --video \
  --out "$PWD/out/ml2" > out/ml2/home-course.log 2>&1
```

Use an absolute `--out`: the current CLI rejects a relative custom output
path while reporting results. Omit `--render --video` for physics-only runs.
Use headless rendering rather than the interactive `--view` option.

EGL numbering differs from `nvidia-smi` numbering on this host: EGL device 0
was verified as the RTX 8000, device 1 as the RTX 6000. After driver or
hardware changes, verify again with these environment variables set:

```bash
.venv/bin/python - <<'PY'
import mujoco
from OpenGL import GL

model = mujoco.MjModel.from_xml_string("<mujoco/>")
with mujoco.Renderer(model, 64, 64):
    print(GL.glGetString(GL.GL_RENDERER).decode())
PY
```

Outputs: `out/home-course.md`, figures and PNG in `out/ml2/`, and the
deck-fitted MP4 and exported models in `out/sim/`.

## Run parallel design trials

```bash
.venv/bin/eox evolve --trial home-front-battery \
  --population 8 --generations 2 --workers 8 --fresh \
  > out/ml2/evolve-smoke.log 2>&1
```

This short run checks execution and process parallelism; it does not recommend
moving the battery forward. Exit status 1 can mean the best candidate violates
a design constraint; inspect the report and log to distinguish that from an
execution failure. Two generations need not find a feasible design.

For the full configured experiment, omit `--population` and `--generations`.
The configured population is 14, so more than 14 workers cannot help its
generation evaluations. Results go to `trials/home-front-battery/` inside
the isolated snapshot.

`--fresh` removes that snapshot's evaluation cache. Use it for the first run
because source archives include published trial history; omit it to resume
an unchanged experiment. After changing code, parameters, or simulation
settings, use a new snapshot and fresh cache: cache keys do not encode all
those inputs. Preserve the source SHA, configuration, seed, worker count,
lockfile, and logs with the results.

For long jobs, use `tmux` or another session supervisor to survive SSH
disconnects.

## Check compatibility and retrieve results

On the remote host:

```bash
.venv/bin/pytest -q
```

Run tests before generating new trial results, or use a separate snapshot
for trials. The regression suite reads the published
`trials/home-front-battery/best.toml`; an exploratory run overwrites it and
can legitimately produce an infeasible candidate that fails that regression.

From the local machine:

```bash
mkdir -p out/ml2
scp ml2@ml2.anceralabs.com:/home/ml2/eox-sim/run-XXXXXX/out/home-course.md out/ml2/
scp -r ml2@ml2.anceralabs.com:/home/ml2/eox-sim/run-XXXXXX/out/ml2/. out/ml2/
scp ml2@ml2.anceralabs.com:/home/ml2/eox-sim/run-XXXXXX/out/sim/home-deck.mp4 out/ml2/
scp -r ml2@ml2.anceralabs.com:/home/ml2/eox-sim/run-XXXXXX/trials/home-front-battery out/ml2/
```

Review results before adopting parameters or replacing published media.
