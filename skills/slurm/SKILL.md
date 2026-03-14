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

| Nodes | Count | GPUs | CPUs | RAM |
|---|---|---|---|---|
| cn-l[001-091] | 91 | 4x L40S (48GB) | 48 | 1024GB |
| cn-c[001-040] | 40 | 8x RTX8000 (48GB) | 64 | 384GB |
| cn-g[001-029] | 29 | 4x A100 (80GB) | 64 | 1024GB |
| cn-a[001-011] | 11 | 8x RTX8000 (48GB) | 40 | 384GB |
| cn-b[001-005] | 5 | 8x V100 (32GB) | 40 | 384GB |
| cn-k[001-004] | 4 | 4x A100 (40GB) | 48 | 512GB |
| cn-n[001-002] | 2 | 8x H100 (80GB) | 192 | 2048GB |
| cn-d[001-004] (DGX) | 4 | 8x A100 (40/80GB) | 128 | 1024-2048GB |
| cn-j001 | 1 | 8x A6000 (48GB) | 64 | 1024GB |

GPUs per node is either 4 or 8 — don't request more than the node type has.

## Partitions & Preemption

| Partition | Time Limit | Per-User Limits |
|---|---|---|
| `long` (default) | 7 days | No per-user GPU cap |
| `main` | 5 days | 2 GPUs, 8 CPUs, 48GB |
| `short` | 3 hours | 4 GPUs, 1TB mem |
| `unkillable` | 2 days | 1 GPU, 6 CPUs, 32GB |

**Preemption hierarchy:** unkillable > main > long. Once preempted, jobs are killed and auto-requeued. `main` jobs do NOT preempt other `main` jobs. `-grace` variants give a SIGTERM grace period before kill. **Checkpoint frequently on `long` partition.**

## Storage

| Path | Quota | Key Policy |
|---|---|---|
| `$HOME` | 100GB / 1M files | Daily backup, low I/O — don't write logs here |
| `$SCRATCH` | 5TB / unlimited | **Files unused >90 days deleted** |
| `$SLURM_TMPDIR` | No quota | **Fastest I/O, cleared after job** |
| `/network/projects/<group>/` | 1TB / 1M files | Shared project storage |
| `$ARCHIVE` | 5TB | No backup, not on GPU nodes |

**Always copy data to `$SLURM_TMPDIR` at job start for performance.** Write logs/outputs to `$SCRATCH`, not `$HOME`. Check usage with `disk-quota`.

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

## Safety

- **Never submit jobs (`sbatch`) without explicit user confirmation**
- Verify paths and configs before submission
- Test on small instances first when possible

## Scope

$ARGUMENTS
