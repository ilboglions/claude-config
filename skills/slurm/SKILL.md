---
name: slurm
description: Help write, debug, and manage SLURM jobs on the Mila cluster and on Compute Canada / Alliance clusters (TamIA, Killarney, Vulcan). Use when the user asks about sbatch, salloc, squeue, job scripts, cluster resource allocation, or submitting to an Alliance cluster from Mila.
---

# SLURM Assistant

Help the user write job scripts, debug failed jobs, and manage cluster resources.

## Choosing the Cluster

**Settle the target before writing anything.** If the user names a cluster, use it. If they do
not, and the job is large — multi-GPU, multi-hour, or a batch of many jobs — **run the survey
below and come back with a concrete recommendation** rather than asking blind.

### Roster

| Cluster | SSH alias | Account | GPUs | Max time | Allocation | Compute internet |
|---|---|---|---|---|---|---|
| Mila | `mila` | none | A100-80/40, L40S, RTX8000, H100, V100, A6000 | 7d (`long`) | per-GPU | direct |
| TamIA | `tamia` | `aip-sreddy` | 4x H100-80 / 8x H200-141 | 24h | **whole node** | squid proxy |
| Fir | `fir` | `def-`/`rrg-bengioy` | mixed | — | per-GPU | direct |
| Nibi | `nibi` | `def-`/`rrg-bengioy` | mixed | — | per-GPU | direct |
| Narval | `narval` | `def-`/`rrg-bengioy` | mixed | — | per-GPU | none |
| Rorqual | `rorqual` | `def-`/`rrg-bengioy` | mixed | — | per-GPU | none |
| Killarney | — | `aip-` | 4x L40S / 8x H100-80 | — | per-GPU | direct |
| Vulcan | — | `aip-` | 4x L40S | 7d | per-GPU | squid (on by default) |

Access to Mila, TamIA, Fir, Nibi, Narval and Rorqual is **verified** (key accepted => account
exists). Killarney and Vulcan need a separate `aip-` request in CCDB and are unconfirmed.
Alliance aliases are defined in `~/.ssh/config` on both the Mac and Mila via `%h.alliancecan.ca`.

**When TamIA is unavailable** (it is under a maintenance reservation until 2026-10-02), Fir and
Nibi are the best substitutes: per-GPU allocation instead of whole-node, direct compute-node
internet, and no 24h cap.

### Match the job to the cluster

| Job shape | Where |
|---|---|
| Dev, debug, interactive, fewer than 4 GPUs | Mila |
| Many small independent jobs / grid search | Mila (`long`, no per-user GPU cap) |
| Saturates 4x H100 or 8x H200, fits in 24h | TamIA |
| Needs more than 24h wall time | Mila `long` (7d) or Vulcan (7d) — **not** TamIA |
| Needs more than 80GB per GPU | TamIA H200 (141GB) only |
| Needs unrestricted internet from compute nodes | Fir, Nibi, Killarney |
| L40S is enough and a big pool matters | Mila (typically ~37 idle L40S nodes), Vulcan, Killarney |

### Survey before a big job

**Never judge availability from `sinfo -t idle` alone.** Nodes inside a maintenance reservation
report as `idle` while nothing can start on them. Check all three signals:

```bash
# 1. node state summary — 'maint' or 'drain' means the pool is not actually usable
ssh <alias> 'sinfo -h -o "%T %D" | sort | uniq -c'

# 2. active reservations — a cluster-wide MAINT reservation blocks everything
ssh <alias> 'scontrol show reservation | head -20'

# 3. ground truth: ask the scheduler when THIS job would start (does NOT submit)
ssh tamia 'sbatch --test-only --account=aip-sreddy --time=12:00:00 \
    --gpus-per-node=h100:4 --cpus-per-task=48 --mem=0 --wrap=true'
ssh mila  'sbatch --test-only --partition=long --gres=gpu:a100l:1 \
    --cpus-per-task=8 --mem=96G --time=12:00:00 --wrap=true'
```

`sbatch --test-only` validates the request and prints an estimated start time **without queueing
anything** — it accounts for reservations, fair-share and the current queue, so it is the single
most reliable signal. It is read-only and safe to run without asking.

Useful follow-up when an estimate looks bad:

```bash
ssh <alias> 'squeue -t PENDING -h -o "%r" | sort | uniq -c | sort -rn | head'
```

`ReqNodeNotAvail, Reserved for maintenance` on most of the queue means the cluster is parked,
not busy.

**A `MAINT` reservation's `EndTime` is an upper bound, not the planned return.** Admins set it
generously so nothing sneaks in mid-update, and `sbatch --test-only` will faithfully report that
boundary because it is the only end date Slurm knows. A 30-day reservation has meant an 8-hour
outage. **Always check the announcement before telling the user a cluster is unavailable:**

```bash
curl -s https://status.alliancecan.ca/ -o /tmp/st.html
grep -o 'view_incident?incident=[0-9]*' /tmp/st.html | sort -u
# then fetch each and read the incident text for the real window
curl -s "https://status.alliancecan.ca/view_incident?incident=<id>"
```

Per-system pages (`/system/<Name>`) currently return 500 — use the incident IDs from the front
page instead. Note that outages often exclude login nodes and shared filesystems, so being able
to `ssh` in and run `squeue` says nothing about whether jobs can start.

Present the comparison and a recommendation, then let the user choose before submitting.

## Job Script Guidelines

- Always include: `--job-name`, `--output`, `--error`, `--time`, `--mem`, `--gres` (for GPUs), `--cpus-per-task`
- Place scripts in a dedicated folder (e.g. `scripts/`)
- Use `set -euo pipefail` in the bash portion
- Log key info at the start: hostname, GPU info (`nvidia-smi`), date, git commit hash
- Activate the correct virtual environment before running Python

## Resource Allocation Rules

- **Small experiments (<1M params)**: 1 GPU, 4-8 CPUs, 16-32GB RAM
- **Medium experiments (1M-1B params)**: 1-2 GPUs, 8-16 CPUs, 32-64GB RAM
- **Large models (7B+)**: multiple GPUs, 64-128GB+ RAM
- **32B+ inference**: 4+ GPUs, match tensor parallelism to GPU count
- Rule of thumb: ~4-8 CPUs per GPU, ~2x model size in FP16 for VRAM

## Mila GPU Types & Selection

### GPU types (use with `--gres=gpu:<type>:N`)
- **a100**: A100 40GB HBM2e
- **a100l**: A100 80GB HBM2e
- **a6000**: RTX A6000 48GB GDDR6
- **h100**: H100 80GB HBM3
- **l40s**: L40S ~45GB GDDR6
- **rtx8000**: Quadro RTX 8000 48GB GDDR6
- **v100**: V100 32GB HBM2

### GPU selection by attribute
You can also request GPUs by memory, architecture, or feature:
- By memory: `--gres=gpu:48gb:1` (any 48GB GPU: RTX8000, A6000, L40S)
- By arch: `--gres=gpu:ampere:1` (A100, A6000, L40S)
- By interconnect: `--gres=gpu:nvlink:1`
- By system: `--gres=gpu:dgx:1`
- Memory tags: `12gb`, `32gb`, `40gb`, `48gb`, `80gb`
- Arch tags: `volta`, `turing`, `ampere`

## Mila Node Inventory

| Nodes | Count | GPUs | CPUs | RAM | Local Disk |
|---|---|---|---|---|---|
| cn-l[001-091] | 91 | 4x L40S (48GB) | 48 | 1024GB | 7TB |
| cn-c[001-040] | 40 | 8x RTX8000 (48GB) | 64 | 384GB | 3TB |
| cn-g[001-029] | 29 | 4x A100 (80GB) | 64 | 1024GB | 7TB |
| cn-a[001-011] | 11 | 8x RTX8000 (48GB) | 40 | 384GB | 3.6TB |
| cn-b[001-005] | 5 | 8x V100 (32GB) | 40 | 384GB | 3.6TB |
| cn-k[001-004] | 4 | 4x A100 (40GB) | 48 | 512GB | 3.6TB |
| cn-n[001-002] | 2 | 8x H100 (80GB) | 192 | 2048GB | 35TB |
| cn-d[001-002] (DGX) | 2 | 8x A100 (40GB) | 128 | 1024GB | 14TB |
| cn-d[003-004] (DGX) | 2 | 8x A100 (80GB) | 128 | 2048GB | 28TB |
| cn-e[002-003] (DGX) | 2 | 8x V100 (32GB) | 40 | 512GB | 7TB |
| cn-i001 | 1 | 4x A100 (80GB) | 64 | 1024GB | 3.6TB |
| cn-j001 | 1 | 8x A6000 (48GB) | 64 | 1024GB | 3.6TB |

CPU-only nodes:

| Nodes | Count | CPUs | RAM | Local Disk |
|---|---|---|---|---|
| cn-f[001-004] | 4 | 32 | 256GB | 10TB |
| cn-h[001-004] | 4 | 64 | 768GB | 7TB |
| cn-m[001-004] | 4 | 96 | 1024GB | 7TB |

**Key takeaway:** L40S nodes (91 nodes, 4 GPUs each) are by far the most plentiful. RTX8000 and A100-80GB are also abundant. H100 nodes are rare (only 2). GPUs per node is either 4 or 8 — don't request more than the node type has.

## Mila Partitions & Preemption

| Partition | Time Limit | QOS | Per-User Limits | Best For |
|---|---|---|---|---|
| `long` (default) | 7 days | normal | No apparent per-user GPU/CPU/mem cap | Multi-day training, many parallel jobs |
| `main` | 5 days | main-partition | 2 GPUs, 8 CPUs, 48GB mem | Single larger jobs |
| `unkillable` | 2 days | unkillable-partition | 1 GPU, 6 CPUs, 32GB mem | Jobs that must not be preempted |
| `short-unkillable` | 3 hours | — | small | Quick non-preemptible tests |

- `long` is the go-to for running many small jobs in parallel (no per-user GPU cap under QOS=normal)
- `main` caps at 2 GPUs total per user — only 1-2 GPU jobs concurrently
- `-grace` variants (`long-grace`, `main-grace`) share the same node pool but give a SIGTERM grace period before preemption
- **There is no `short` partition** — submitting to it fails with `invalid partition specified`.
  The full verified list is: `long`(default), `long-cpu`, `long-cpu-eek`, `long-cpu-grace`,
  `long-cpu-grace-eek`, `long-grace`, `main`, `main-cpu`, `main-cpu-grace`, `main-grace`,
  `short-unkillable`, `unkillable`, `unkillable-cpu`. Use `long-cpu` for quick CPU-only tests.
- CPU-only partitions (`*-cpu` variants) enforce `gres/gpu=0` via QOS — don't submit GPU jobs there
- With `torchrun`, always set `--master_port=$((29500 + SLURM_JOB_ID % 10000))` to avoid port collisions on shared nodes

**Preemption hierarchy:** unkillable > main > long. A higher-priority partition's job can kill a lower-priority one; `main` jobs do NOT preempt other `main` jobs regardless of fair-use. Once preempted, a job is killed and automatically re-queued on the same partition. **Checkpoint frequently on `long`** so preemption does not lose progress.

## Mila Storage

| Path | Quota | Key Policy |
|---|---|---|
| `$HOME` | 100GB / 1M files | Daily backup, low I/O — don't write logs here |
| `$SCRATCH` | 5TB / unlimited | **Files unused >90 days deleted** |
| `$SLURM_TMPDIR` | No quota | **Fastest I/O, cleared after job** |
| `/network/projects/<group>/` | 1TB / 1M files | Shared project storage |
| `$ARCHIVE` | 5TB | No backup, not on GPU nodes |

**Copy data to `$SLURM_TMPDIR` at job start for performance:**

```bash
# At job start: copy data to fast local disk
cp -r $SCRATCH/my_dataset $SLURM_TMPDIR/
# Train using local path
python train.py --data_dir $SLURM_TMPDIR/my_dataset
# At job end: copy results back
cp -r $SLURM_TMPDIR/checkpoints $SCRATCH/my_experiment/
```

Write logs/outputs to `$SCRATCH`, not `$HOME` — excessive I/O on `/home` degrades the shared filesystem. Check usage with `disk-quota`.

## Mila Module System

- `module load python/3.10` — required before creating venvs on cluster
- `module load miniconda/3` — for conda environments
- `module avail` / `module spider <term>` — search available modules
- Pre-built PyTorch/TF modules exist for Mila GPUs
- On login/CPU nodes without GPUs: `CONDA_OVERRIDE_CUDA=11.8` before conda commands

## Debugging Failed Jobs

- Check `.err` files first — experiment logs go to stderr
- `sacct -j <jobid> --format=JobID,State,ExitCode,MaxRSS,Elapsed,NodeList` for completed jobs
- Common issues: OOM (check MaxRSS), time limit, bad path, missing module/env
- For OOM: check batch size, model size, gradient accumulation, and whether `--mem` was sufficient
- **`torch.autograd.set_detect_anomaly(True)`** causes extreme filesystem IOPS — never leave on in batch jobs, admins will flag it

## Mila Monitoring

- `disk-quota` — check storage usage
- `squeue -u $USER` — your active jobs
- `echo $SLURM_JOB_GPUS` — which GPU(s) your job got
- Netdata per-node: `<node>.server.mila.quebec:19999` (requires Mila wifi or SSH tunnel)
- Grafana dashboard: `dashboard.server.mila.quebec`

## Mila Limits

- Max **1000 jobs** per user in the system at any time

## When Claude Itself Runs Inside an Allocation

If the Claude Code session was started with `salloc`/`sbatch` (e.g. a `mila-code` job), the shell already sits inside a job. Three things change:

- **The session scratchpad is node-local.** `/tmp` on a compute node is per-job local NVMe (`findmnt` shows `/<jobid>/.<jobid>/_tmp`), the same storage as `$SLURM_TMPDIR`. It does not exist on any other node, so **never `sbatch` from it and never point `--output`/`--error`/`--chdir` at it** — the job lands on a different node, cannot create its working dir, and dies in seconds with exit 1 and no log files. Submit from `$SCRATCH` instead.
- **`SLURM_JOB_ID` is already set**, so a nested `srun` becomes a job *step* of the current allocation rather than a new one — it inherits that allocation's CPUs and GPUs (often zero). Use `sbatch` for new work; only use bare `srun` when a step inside the current allocation is genuinely what is wanted.
- **`squeue -u $USER` lists the session's own job.** Filter it out before reporting on experiments — compare against `$SLURM_JOB_ID` — or an idle queue looks like a running job.

Also note the session's own node may be CPU-only, so `hostname` confirming "a compute node" does not imply a GPU is present. Check `nvidia-smi` separately.

## Compute Canada / Alliance Clusters (TamIA)

TamIA is the Alliance AI cluster at Université Laval, co-managed with Mila. It is a **separate
system**: separate filesystem, separate username, separate account string. Nothing is shared —
code moves by git, data by Globus or rsync.

Details below were verified against the live clusters on 2026-09-02.

| | Mila | TamIA |
|---|---|---|
| SSH alias | `mila` | `tamia` (ProxyJump through `mila`) |
| Username | `boglionm` | `boglioni` |
| `$HOME` | `/home/mila/b/boglionm` | `/home/b/boglioni` (25GB) |
| `$SCRATCH` | `/network/scratch/b/boglionm` | `/scratch/b/boglioni` |
| Project dir | — | `/project/aip-sreddy` -> `/project/6100856` |
| Account flag | none | `--account=aip-sreddy` (mandatory) |
| GPU request | `--gres=gpu:a100l:N` | `--gpus-per-node=h100:4` (whole node) |
| Max walltime | 7 days (`long`) | **24h**, hard |
| Compute node internet | yes | proxied via squid (see below); login node direct |
| uv | `~/.local/bin/uv` | `~/.local/bin/uv` |

Portal for live job/GPU utilization: https://portail.tamia.ecpia.ca/

### Connecting

Alliance clusters are defined in `~/.ssh/config` **on both the Mac and Mila** (the Mila-side
file covers `tamia fir killarney vulcan narval nibi rorqual` via `%h.alliancecan.ca`). Both use
`ControlMaster auto` so Duo 2FA fires only when no master socket exists.

**The agreed workflow: the user opens the session, Claude reuses it.**

1. Check for a live master before anything else:
   ```bash
   ssh -O check tamia     # "Master running (pid=...)" => commands run unattended
   ```
2. If there is none, **ask the user to run `ssh tamia` themselves** and approve the Duo push.
   Do not try to drive the prompt: tool calls have no tty, so ssh cannot prompt at all and
   fails at `Permission denied (publickey,keyboard-interactive)` without ever sending a push.
3. Once the master is up, everything (`sbatch`, `squeue`, `rsync`) runs unattended for
   `ControlPersist` (8h). `ssh -O exit tamia` clears a stale socket.

**The socket is node-local — this is the one way the setup fails confusingly.** A unix domain
socket only works on the machine whose process is listening. Mila's `$HOME` is shared NFS, so a
socket created on login-1 is *visible* from every compute node but dead there. Therefore:

| Claude runs on | User must open `ssh tamia` on |
|---|---|
| the Mac | the Mac |
| a Mila compute node | **that same compute node** |

This is why `ControlPath` carries `%l` (local hostname) on the Mila side — without it, sockets
from different nodes collide on one path.

The same node-local rule breaks SSH agent forwarding: on a compute node reached via `srun`,
`SSH_AUTH_SOCK` is inherited but points at the login node's `/tmp`, so `ssh-add -l` fails and no
key is available. A milatools/`mila-code` session is proxied from the Mac with `ForwardAgent
yes` and does get a working local agent socket.

**Verified network path** (probed from `cn-f001`): Mila compute nodes reach
`tamia.alliancecan.ca:22` **directly** — no `ProxyJump` needed. `pypi.org:443` and
`login-1.server.mila.quebec:2222` are also reachable from compute nodes.

### TamIA scheduling

- **Whole-node allocation.** Every GPU job takes all GPUs on its nodes: `--gpus-per-node=h100:4`
  or `--gpus-per-node=h200:8`. Single-GPU requests are not accepted. Pair with
  `--cpus-per-task=48 --mem=0` (H100 nodes: 48 cores, 512GB; H200 nodes: 64 cores, 1024GB).
- **`--time` picks the partition** — you never name one explicitly:

  | Partition | Limit | Pool |
  |---|---|---|
  | `gpubase_bynode_b1` | 3h | largest (~48 H100 + 12 H200 nodes) |
  | `gpubase_bynode_b2` | 12h | large |
  | `gpubase_bynode_b3` | 24h | smallest |
  | `gpubase_interac` | 6h | 8 H100 + 2 H200 held back for `salloc` |

  Asking for 24h when the job needs 10 queues it behind a much smaller pool. Request the time
  actually needed.
- Minimum job ~1h (5 min for tests); at most 1000 jobs queued+running.
- Node counts: 53x (4x H100 80GB, 48 cores, 512GB), 12x (8x H200 141GB, 64 cores, 1024GB),
  8x CPU-only (64 cores, 512GB). All NVLink, NDR200 InfiniBand per GPU, non-blocking fat-tree.
- No `crontab`. VSCode is banned on login nodes — never point a remote IDE session at
  `tamia.alliancecan.ca` (it is allowed on compute nodes).

### Cross-cluster submission

Submit remotely over the existing master connection. Nothing needs to be installed on the
target beyond the repo itself.

```bash
# sync code
ssh tamia 'cd ~/PROJECT && git pull'

# pre-flight: build/refresh the venv on the LOGIN node (only it has a direct route to PyPI)
ssh tamia 'cd ~/PROJECT && module load python/3.10.13 cuda/12.6 && uv sync'

# submit
ssh tamia 'cd ~/PROJECT && sbatch --account=aip-sreddy --job-name=X --time=12:00:00 \
    --gpus-per-node=h100:4 --cpus-per-task=48 --mem=0 --output=~/logs/X-%j.out job.sh'

# poll
ssh tamia 'squeue -u $USER'
```

**Quote remote commands with single quotes.** `"squeue -u $USER"` expands `$USER` to the *Mila*
username locally and returns an empty queue that reads as "no jobs running". `sq` is the
Alliance shorthand for the same thing.

### Environment: uv on both clusters

uv is the environment manager on both (`~/.local/bin/uv`, on `PATH` via `~/.local/bin/env`
sourced from `.bashrc`). Each project keeps its own `.venv` in the project directory.

TamIA's **login node has direct internet** (pypi reachable); compute nodes only reach the
network through the squid proxy, which is not dependable for package indexes. So do all
dependency resolution on the login node:

```bash
# login node, once per lock change
module load python/3.10.13 cuda/12.6
uv sync

# inside the job — use the venv as-is, never touch the index
export UV_OFFLINE=1
uv run --no-sync python src/train.py ...
```

Plain `uv run` in a job re-checks the lock against the package index; the squid proxy is not a
reliable route to PyPI, so this can stall until it times out. Always `--no-sync` on TamIA
compute nodes — it also makes runs deterministic against the lock.

Module names differ slightly: Mila uses `python/3.10` + `cuda/12.6.0`, TamIA uses
`python/3.10.13` + `cuda/12.6`. Batch scripts must load them explicitly — a Slurm script is a
non-interactive shell and does not source `.bashrc`.

The Alliance wheelhouse (`pip install --no-index`, `avail_wheels`) exists but is not needed
given uv + login-node internet. Reach for it only if a `uv sync` cannot resolve.

### Storage and the folder convention

| Path | TamIA quota | Policy |
|---|---|---|
| `$HOME` | 25GB | small — code lives in `/project`, not here |
| `$SCRATCH` | 1-2TB by tier | **purged after 2 months** |
| `/project/aip-sreddy` | 2-5TB by tier | daily backup, group-shared, holds code + venvs |
| `$SLURM_TMPDIR` | node-local 7.68TB NVMe | fastest, cleared at job end |

`$PROJECT` is **not set** on TamIA — use the explicit path.

**`~/NAME` is the portable anchor on both clusters.** Code, data and outputs are all reachable
at a `$HOME`-relative path, even though the real storage differs:

| Path | Mila | TamIA |
|---|---|---|
| `~/<Project>` | real directory in `$HOME` | symlink -> `/project/aip-sreddy/boglioni/<Project>` |
| `~/data` | -> `$SCRATCH/data` | -> `$SCRATCH/datasets` |
| `~/logs` | -> `$SCRATCH/logs` | -> `$SCRATCH/logs` |
| `~/<Project>Outputs` | -> `$SCRATCH/<Project>Outputs` | -> `$SCRATCH/<Project>Outputs` |

So job scripts can use `~/...` paths unchanged across clusters. When setting up a project on a
cluster for the first time, provision this layout — it is idempotent, so it is safe to re-run
before any submission:

```bash
for d in logs data "${PROJECT}Outputs"; do
    mkdir -p "$SCRATCH/$d"
    [[ -e "$HOME/$d" ]] || ln -s "$SCRATCH/$d" "$HOME/$d"
done
```

On TamIA also link the code and redirect caches off the 25GB `$HOME`:

```bash
ln -s /project/aip-sreddy/$USER/<Project> ~/<Project>
# .bashrc already sets: HF_HOME=$SCRATCH/hf_cache, ~/.cache -> $SCRATCH/.cache
```

Do not put venvs in `$SCRATCH` — partial purges break them in confusing ways.

### Internet access from compute nodes

This varies per cluster and the wiki's blanket "no internet" statements are misleading — most
AI clusters run a proxy that makes ordinary API traffic work.

| Cluster | Compute-node internet |
|---|---|
| Fir, Nibi | **Full direct access**, no proxy needed |
| Killarney | Full access |
| TamIA | No direct route; squid proxy at `squid.tamia.ecpia.ca:3128` |
| Vulcan | No direct route; squid proxy **on by default**, whitelisted domains |
| Narval, Rorqual | None (exception by support request) |
| Trillium | None (only OnDemand interactive apps) |

On TamIA, `module load httpproxy` sets `http_proxy`/`https_proxy`/`rsync_proxy` to the squid
host (`no_proxy=tamia.ecpia.ca`). **W&B generally works from TamIA compute nodes in practice**,
so online logging is a reasonable default there. If a job cannot reach an external host, load
`httpproxy` before the training command.

Two caveats when relying on the proxy:

- **Artifact upload is not supported** through it, and the W&B logger can hang after training
  finishes — burning the allocation until the job hits its time limit. If the run uploads
  artifacts, use `WANDB_MODE=offline` and sync afterwards:
  ```bash
  export WANDB_MODE=offline
  # later, from a login node: ssh tamia 'cd ~/logs/wandb && wandb sync latest-run'
  ```
- The proxy is not a general route to the internet — assume package indexes and arbitrary hosts
  may be blocked, and do dependency work on the login node.

### Submission style

Match the existing convention in these repos: **pass SBATCH options as `sbatch` CLI arguments**
rather than `#SBATCH` headers. Launchers generate an inner job script, then call `sbatch` with
the resource flags. This is what makes a job portable — the inner script stays cluster-neutral
and only the flags change:

```bash
# Mila
sbatch --job-name=$NAME --gres=gpu:a100l:1 --mem=96G --cpus-per-task=8 \
       --time=24:00:00 --partition=long --output=~/logs/$NAME-%j.out "$SCRIPT"

# TamIA
sbatch --job-name=$NAME --account=aip-sreddy --gpus-per-node=h100:4 --cpus-per-task=48 \
       --mem=0 --time=12:00:00 --output=~/logs/$NAME-%j.out "$SCRIPT"
```

Support `--dry-run` in launchers, and show the user the resolved `sbatch` command before running it.

### Troubleshooting

- **Key works on other Alliance clusters but is rejected on tamIA** — CCDB key sync to tamIA
  lags the other clusters and appears to freeze during its maintenance windows. Diagnose by
  offering the same key elsewhere:
  `ssh -v -o BatchMode=yes fir true 2>&1 | grep "Server accepts key"`.
  If other clusters accept it, nothing is wrong with the key — fall back to CCDB
  **password** + Duo at the prompt, which is unaffected.
- **`Permission denied` on `/project/aip-sreddy`** — the POSIX group membership is missing even
  though the Slurm association works (`sbatch --test-only` still succeeds). Check with `id`; if
  no `aip-sreddy` group is listed, the PI must re-add the user's CCRI to the RAP in CCDB.
  Alliance RAP memberships renew annually and this is what a lapse looks like.
- **Job dies instantly with no output** — check `--output` points at a path that exists on the
  *target* cluster.
- `sacct -j <jobid> --format=JobID,State,ExitCode,MaxRSS,Elapsed,NodeList` for post-mortems.

### Other Alliance clusters

Same access pattern and `aip-` account, different hardware:

| Cluster | Login | Hardware | Note |
|---|---|---|---|
| Killarney | `killarney.alliancecan.ca` | 168x 4x L40S, 10x 8x H100 | Vector/SciNet, geo-blocked outside Canada |
| Vulcan | `vulcan.alliancecan.ca` | 252x 4x L40S | Amii, **7-day** jobs, squid proxy on compute nodes |
| Fir / Narval / Nibi / Rorqual | `<name>.alliancecan.ca` | general-purpose | `def-`/`rrg-` accounts, per-GPU requests allowed |

The user also holds `def-bengioy` / `rrg-bengioy` / `rpp-bengioy` associations for the
general-purpose clusters.

## Safety

- **Never submit jobs (`sbatch`) without explicit user confirmation** — including remote submissions over SSH to an Alliance cluster
- Verify paths and configs before submission
- Test on small instances first when possible
