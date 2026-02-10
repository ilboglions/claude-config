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

## Known GPU Types

- **a100**: A100 40GB HBM2e
- **a100l**: A100 80GB HBM2e
- **a6000**: RTX A6000 48GB GDDR6
- **h100**: H100 80GB HBM3
- **l40s**: L40S ~45GB GDDR6
- **rtx8000**: Quadro RTX 8000 48GB GDDR6
- **v100**: V100 32GB HBM2

## Debugging Failed Jobs

- Check `.err` files first — experiment logs go to stderr
- `sacct -j <jobid> --format=JobID,State,ExitCode,MaxRSS,Elapsed,NodeList` for completed jobs
- Common issues: OOM (check MaxRSS), time limit, bad path, missing module/env
- For OOM: check batch size, model size, gradient accumulation, and whether `--mem` was sufficient

## Safety

- **Never submit jobs (`sbatch`) without explicit user confirmation**
- Verify paths and configs before submission
- Test on small instances first when possible

## Scope

$ARGUMENTS
