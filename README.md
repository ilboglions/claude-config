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
| `/research-site` | Reading and writing the research site through its API (MCP server or CLI): meeting notes, results, W&B runs, papers, milestones, pages |
| `/ooo` | Away mode: permission prompts also go to Telegram with Yes/No buttons, and Claude messages me there only when blocked or urgent (`/ooo off` ends it) |

## Settings

`settings.json` carries the harness config, not just preferences:

- **`permissions.allow`** — read-only cluster and inspection commands (`squeue`,
  `sacct`, `sinfo`, `disk-quota`, `nvidia-smi`, read-only `git`, file inspection)
  run without a prompt.
- **`permissions.ask`** — `sbatch`, `srun`, `salloc` and `scancel` always prompt,
  every single time. This enforces the "explicit sign-off before every job
  submission" rule mechanically, so an earlier approval can never carry over to a
  modified resubmission.
  `git push` always prompts too, so a push in away mode becomes a Yes/No on the
  phone that the harness checks, not an agent acting on a chat reply.
- **`permissions.deny`** — `rm -rf` is blocked outright.
- **`attribution`** — empty strings drop the `Co-Authored-By: Claude` trailer from
  commits and the "Generated with Claude Code" line from PR descriptions, so
  commits carry only my name.

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
cp -n codex/cairn.config.toml ~/.codex/cairn.config.toml
cp -n codex/config.toml ~/.codex/config.toml
```

`codex --profile cairn` runs Codex on Qwen served by Cairn at Mila. It needs the
`mila` SSH connection open (its `LocalForward 8080` reaches the server) and the
Cairn key in `CAIRN_API_KEY`. Plain `codex` keeps using OpenAI.

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
   It registers the research-site server too (below).

Both clients run every Zotero tool without asking, except adding papers or files,
deletes and bulk edits (`settings.json` for Claude Code, the Codex entry written
by `install.sh`). `CLAUDE.md` sets how references and Zotero are used.

The registered command sources `~/.config/zotero-mcp.env` right before starting
the server, so the credentials reach only that process and never a config file
or your shell. If `ZOTERO_API_KEY` is missing, the server silently falls back to
the local Zotero desktop API instead of failing.

## Research-site MCP

`mcp/install.sh` also registers `skills/research-site/server.py`, a local stdio
server that gives Claude Code and Codex typed tools for the research site's API
(the same calls as `site.py`, which stays for cron and `wandb-sync`). It runs from
this checkout through `uv run --script`, so re-run `install.sh` if you move the repo.

The token lives in `~/.config/research-site.env` (chmod 600; see
`skills/research-site/SKILL.md`), which the server reads at each call: neither
client config holds it. Every tool runs without asking in both clients. The token
cannot delete anything or share projects, so those stay on the site.

## Away mode (Telegram)

`/ooo` in a session turns on away mode for that session: every permission prompt
also arrives on Telegram with Yes/No buttons, and Claude messages me there only when
it is blocked or something is urgent. The terminal prompt stays open, and whichever
answer comes first wins. `/ooo off` turns it off.

To talk to a session, reply to one of its messages on Telegram (👀 when queued, 👍
when the session picks it up). A message that replies to nothing goes to the session
whose message came last. When the session finishes a turn, a Stop hook waits in the
background (`asyncRewake`) and wakes it with my reply, so the terminal stays usable
meanwhile and `/ooo off` works at any time. A reply that arrives while Claude is working ends its turn at
its next step and is handed over right away, like Esc followed by typing it (a reply
sitting next to a tool result would rightly be distrusted). A session that ends in away mode (exit, closed pane,
cancelled job) leaves it by itself and says so on Telegram. To reach a session that has not written
yet, tap `/to` (or `/list`) in the bot's `/` menu: it shows one button per session in
away mode, and tapping one opens a reply addressed to it, so only the message is
typed. `/to <name> <text>` also works, by project or session name, case and emojis
ignored.

Each message starts with the session's name in bold. While two sessions in away mode
share a project name, the tmux session's name follows it (`🟧 LACUNA · lacuna2`), so
they stay apart. The name is the project's own when its `.claude/settings.local.json` sets one:

```json
{ "env": { "TG_NAME": "🟦 Multi-agent detection" } }
```

Otherwise it is the tmux session's name (`JSH_SESSION`, from jsh) or the folder's.
In a git repository without `TG_NAME`, a SessionStart hook has Claude ask me once for
a name; declining writes an empty `TG_NAME`, so it never asks again. Sessions format
their messages with Telegram's HTML tags (`<b>`, `<i>`, `<u>`, ...): the router keeps
those, escapes everything else, and resends a message plain if Telegram still cannot
parse it. They can also send files (`tg.py send --file plot.png "caption"`): images
arrive as photos, anything else as a document, up to 50 MB. If Telegram answers 429
(too many requests), the router holds every message, in order, until the wait
Telegram asked for is over, and logs it; nothing is dropped.

One router, `skills/ooo/tg.py router`, is the only process talking to the bot. jsh
(from my mymila repo) starts it in the anchor job's own
script, so it starts with the job, comes back after a preemption, and does not depend
on a login node. Its log is `~/.claude/tg/router.log`, and it says "Router up" on
Telegram whenever it starts. The hooks and `tg.py send` only read and drop files in
`~/.claude/tg`, so sessions need no internet access, only the shared `$HOME`.
`settings.json` carries both hooks and an allow rule for `tg.py`.

Optionally, a hub on a server of your own can run the bots instead, including a second
bot, for sessions on several machines. Each machine then runs `tg.py mirror` (on the
cluster, `tg.py router` does it), which keeps its mailboxes in sync with the hub over
HTTPS with a client certificate; sessions don't change. Every session registers at
start, so the hub can list it and turn its away mode on or off. Where the bot token is
present, the router takes the bot back while the hub is unreachable, and hands it over
again when it returns. The hub's address and certificate go in each machine's private
`~/.config/telegram.env` (see `telegram.env.example`); the hub itself is not part of
this repo. On a machine reached only through Telegram, `TG_ALWAYS_AWAY=1` there starts every
session in away mode.

Setup, once, on the cluster:

1. Create a bot with @BotFather (`/newbot`) and keep the token.
2. Put the secrets outside the repo:
   ```bash
   cp skills/ooo/telegram.env.example ~/.config/telegram.env
   chmod 600 ~/.config/telegram.env   # then fill in the token
   ~/.claude/skills/ooo/tg.py chat-id # message the bot, copy the id into the file
   ```
3. Install mymila's cluster side (`./install.sh --cluster`), so the next anchor job
   starts the router.

The router acts only on messages and taps from `TELEGRAM_CHAT_ID`. Anything it accepts
reaches a session as an instruction, so keep the bot out of groups and never share its
token.
