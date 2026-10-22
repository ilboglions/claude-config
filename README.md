# claude-config

Personal Claude Code configuration for AI safety / ML privacy research development.
It also works with OpenAI Codex (see [Codex](#codex)).

Includes a `CLAUDE.md` with project-level instructions and a set of custom skills tailored to an ML research workflow on a SLURM compute cluster.

## Skills

In Codex, invoke a skill as `$name` instead of `/name`.

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
| `/paper-review` | Backing my own review points on a paper with evidence; bullet-point review skeleton |
| `/lit-review` | Finding, triaging, and synthesizing related work |
| `/paperfinder` | Cold-start paper discovery from a topic, expanding through the citation graph |
| `/plot` | Paper-quality matplotlib/seaborn figures |
| `/matteo-writing` | Drafting or editing academic prose in Matteo's style |
| `/smart-rephrasing` | Better flow between sentences without changing wording or content; typo and grammar fixes |
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

`codex/default.rules` ports the same three lists to Codex as `allow`, `prompt`
and `forbidden` rules. One difference: in Codex, `allow` also runs the command
outside the sandbox.

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

## Codex

Codex reads the same skills and instructions from different places, and keeps
permissions in a separate rules file:

```bash
mkdir -p ~/.agents/skills ~/.codex/rules
for d in skills/*/; do
  ln -sfn "$(pwd)/$d" ~/.agents/skills/"$(basename "$d")"
done
ln -sfn "$(pwd)/CLAUDE.md" ~/.codex/AGENTS.md
ln -sfn "$(pwd)/codex/default.rules" ~/.codex/rules/default.rules
cp -n codex/config.toml ~/.codex/config.toml
```

When you pick "always allow" for a command, Codex appends a rule to
`~/.codex/rules/default.rules`, so it lands in this repo through the symlink.
`config.toml` is copied instead, because Codex writes per-project trust entries
with absolute paths into it. `cp -n` leaves an existing one alone, so merge by
hand if you already have one. Restart Codex after changing either file.

## Zotero MCP

`mcp/install.sh` registers [zotero-mcp](https://github.com/54yyyu/zotero-mcp)
with Claude Code at user scope, and with Codex if it is installed, through the
Zotero Web API with read and write access. MCP servers live in `~/.claude.json`
and `~/.codex/config.toml`, which are not versioned, so run it once per machine
(it needs [uv](https://docs.astral.sh/uv/)).

1. Create a key at <https://www.zotero.org/settings/keys/new> with **Allow library
   access** and **Allow write access** checked. The same page shows your numeric
   user ID ("Your userID for use in API calls").
2. Put the secrets outside the repo:
   ```bash
   cp mcp/zotero.env.example ~/.config/zotero-mcp.env
   chmod 600 ~/.config/zotero-mcp.env   # then fill in the values
   ```
3. Run `mcp/install.sh`, then check `claude mcp list` (and `codex mcp list`).

Both clients run every Zotero tool without asking, except adding papers or files,
deletes and bulk edits (`settings.json` for Claude Code, the Codex entry written
by `install.sh`). `CLAUDE.md` sets how references and Zotero are used.

The registered command sources `~/.config/zotero-mcp.env` right before starting
the server, so the credentials reach only that process and never a config file
or your shell. If `ZOTERO_API_KEY` is missing, the server silently falls back to
the local Zotero desktop API instead of failing.
