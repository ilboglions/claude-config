# claude-config

Personal Claude Code configuration for AI safety / ML privacy research development.

Includes a `CLAUDE.md` with project-level instructions and a set of custom skills tailored to an ML research workflow on a SLURM compute cluster.

## Skills

| Command | Description |
|---|---|
| `/review` | Code review — bugs, style, correctness |
| `/latex` | Writing, editing, or debugging LaTeX documents |
| `/bash` | Writing or debugging shell scripts |
| `/slurm` | Job scripts, resource allocation, debugging failed jobs |
| `/pytorch-debug` | Dtype, device, shape, gradient, and OOM errors |
| `/experiment` | Planning, scaffolding, and launching ML experiments |
| `/git` | Branching, rebasing, cherry-picking, conflict resolution |
| `/paper` | Summarizing and analyzing academic papers |
| `/lit-review` | Finding, triaging, and synthesizing related work |
| `/plot` | Paper-quality matplotlib/seaborn figures |
| `/matteo-writing` | Drafting or editing academic prose in Matteo's style |
| `/prereview` | Pre-submission peer review simulation; review parsing and rebuttal drafting |

## Settings

`settings.json` carries the harness config, not just preferences:

- **`permissions.allow`** — read-only cluster and inspection commands (`squeue`,
  `sacct`, `sinfo`, `disk-quota`, `nvidia-smi`, read-only `git`, file inspection)
  run without a prompt.
- **`permissions.ask`** — `sbatch`, `srun`, `salloc` and `scancel` always prompt,
  every single time. This enforces the "explicit sign-off before every job
  submission" rule mechanically, so an earlier approval can never carry over to a
  modified resubmission.
- **`permissions.deny`** — `rm -rf` is blocked outright.

## Usage

Symlink the skills into your personal Claude Code skills directory, so edits you
make while working flow straight back into this repo:

```bash
mkdir -p ~/.claude/skills
for d in skills/*/; do
  ln -sfn "$(pwd)/$d" ~/.claude/skills/"$(basename "$d")"
done
```

Link the global instructions and settings the same way:

```bash
ln -sfn "$(pwd)/CLAUDE.md" ~/.claude/CLAUDE.md
ln -sfn "$(pwd)/settings.json" ~/.claude/settings.json
```

(Copying with `cp -r` works too, but then live edits never make it back under
version control.)
