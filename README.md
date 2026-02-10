# claude-config

Personal Claude Code configuration for deep learning / AI research development.

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
| `/plot` | Paper-quality matplotlib/seaborn figures |

## Usage

Copy skills to your personal Claude Code skills directory:

```bash
cp -r skills/* ~/.claude/skills/
```
