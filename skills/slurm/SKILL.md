---
name: slurm
description: Help write, debug, and manage SLURM jobs. Use when the user asks about sbatch, salloc, squeue, job scripts, or cluster resource allocation.
---

# SLURM Assistant

Help the user write job scripts, debug failed jobs, and manage cluster resources.

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

## Known GPU Types & Selection

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

## Node Inventory

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

## Partitions & Preemption

| Partition | Time Limit | QOS | Per-User Limits | Best For |
|---|---|---|---|---|
| `long` (default) | 7 days | normal | No apparent per-user GPU/CPU/mem cap | Multi-day training, many parallel jobs |
| `main` | 5 days | main-partition | 2 GPUs, 8 CPUs, 48GB mem | Single larger jobs |
| `short` | 3 hours | short-partition | 4 GPUs, 1TB mem | Quick tests, interactive debugging |
| `unkillable` | 2 days | unkillable-partition | 1 GPU, 6 CPUs, 32GB mem | Jobs that must not be preempted |

- `long` is the go-to for running many small jobs in parallel (no per-user GPU cap under QOS=normal)
- `main` caps at 2 GPUs total per user — only 1-2 GPU jobs concurrently
- `-grace` variants (`long-grace`, `main-grace`) share the same node pool but give a SIGTERM grace period before preemption
- CPU-only partitions exist (`*-cpu` variants) — QOS enforces `gres/gpu=0`, so don't submit GPU jobs there
- With `torchrun`, always set `--master_port=$((29500 + SLURM_JOB_ID % 10000))` to avoid port collisions on shared nodes

**Preemption hierarchy:** unkillable > main > long. A higher-priority partition's job can kill a lower-priority one; `main` jobs do NOT preempt other `main` jobs regardless of fair-use. Once preempted, a job is killed and automatically re-queued on the same partition. **Checkpoint frequently on `long`** so preemption does not lose progress.

## Storage

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

## Module System

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

## Monitoring

- `disk-quota` — check storage usage
- `squeue -u $USER` — your active jobs
- `echo $SLURM_JOB_GPUS` — which GPU(s) your job got
- Netdata per-node: `<node>.server.mila.quebec:19999` (requires Mila wifi or SSH tunnel)
- Grafana dashboard: `dashboard.server.mila.quebec`

## Limits

- Max **1000 jobs** per user in the system at any time

## When Claude Itself Runs Inside an Allocation

If the Claude Code session was started with `salloc`/`sbatch` (e.g. a `mila-code` job), the shell already sits inside a job. Three things change:

- **The session scratchpad is node-local.** `/tmp` on a compute node is per-job local NVMe (`findmnt` shows `/<jobid>/.<jobid>/_tmp`), the same storage as `$SLURM_TMPDIR`. It does not exist on any other node, so **never `sbatch` from it and never point `--output`/`--error`/`--chdir` at it** — the job lands on a different node, cannot create its working dir, and dies in seconds with exit 1 and no log files. Submit from `$SCRATCH` instead.
- **`SLURM_JOB_ID` is already set**, so a nested `srun` becomes a job *step* of the current allocation rather than a new one — it inherits that allocation's CPUs and GPUs (often zero). Use `sbatch` for new work; only use bare `srun` when a step inside the current allocation is genuinely what is wanted.
- **`squeue -u $USER` lists the session's own job.** Filter it out before reporting on experiments — compare against `$SLURM_JOB_ID` — or an idle queue looks like a running job.

Also note the session's own node may be CPU-only, so `hostname` confirming "a compute node" does not imply a GPU is present. Check `nvidia-smi` separately.

## Safety

- **Never submit jobs (`sbatch`) without explicit user confirmation**
- Verify paths and configs before submission
- Test on small instances first when possible
