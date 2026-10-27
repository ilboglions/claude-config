---
name: research-site
description: Read and write the user's research site (one dashboard per project) through its API - meeting notes, results (including syncing W&B runs), papers, roadmap/checklist/deadline/ideas items and their status, pages and links. Use when the user asks to put something on the research site or a project dashboard, log a meeting or a result there, sync W&B runs to it, add a paper to a project's literature, tick off a milestone, or revise what is already there.
---

# Research site

Two ways in, same API and same token:

- **The `research-site` MCP server** (`server.py` here), registered by `mcp/install.sh` for
  Claude Code and Codex. Use its tools when they are available.
- **The command line**, `python3 <this skill's folder>/site.py <command>`: for machines
  without the server, for cron, and for `wandb-sync`.

The token adds and changes content. It cannot delete, manage people or share projects:
those stay with the user, on the site.

## Rules

1. **Find the place first.** `list_projects` (CLI: `projects`) gives each project's slug and
   its sections' ids, kinds and titles. Take them from there; never guess.
2. **Write what the user tells you, where they say, without asking for confirmation.** Ask
   only when the target is ambiguous: no project named and several fit, or two sections
   could hold it.
3. **Every piece of prose goes through both writing skills before it is sent.** Load
   `/matteo-writing` and draft with it, then pass the draft through `/smart-rephrasing`
   (in Codex, `$matteo-writing` and `$smart-rephrasing`). This holds for meeting notes,
   result write-ups, item text and pages, and for text the user dictates too. Data that
   is generated rather than written is exempt: `wandb-sync` tables, paper details looked
   up from a link.
4. **To change existing text, read it first** (`read_page`, `list_items`, `list_entries`),
   then send the whole new version: a new body replaces the old one.
5. Everyone the project is shared with reads what goes there. Nothing can be removed with
   the token: if the user wants something gone, they delete it on the site.
6. Report the link each write returns.

Text is markdown (task lists work); raw HTML is shown as text and images are not shown.

## Setup (once per machine)

The user makes a token on the site (People → Access tokens), limited to the projects this
machine should reach, and puts it in `~/.config/research-site.env`:

```bash
RESEARCH_SITE_URL=https://<the site>
RESEARCH_SITE_TOKEN=rs_...
```

`chmod 600 ~/.config/research-site.env`, then run `mcp/install.sh` from this repo (it needs
[uv](https://docs.astral.sh/uv/)) and restart the agent. The server and the CLI read the
file at each call, so the token is in no agent config. If the file or the token is
missing, say so and stop: never ask for the token in the chat, never print it or the
file, never put it in a command line or a repository.

## Tools and commands

| MCP tool | CLI | Does |
|---|---|---|
| `list_projects` | `projects` | Projects and their sections (id, kind, title) |
| `list_items` | `items <project> <section>` | Items of a list or literature section, with ids, statuses and text |
| `read_page` | `read-page <project> <section>` | A page section's markdown |
| `list_entries` | `entries <project> meetings\|results` | Meeting notes or results, newest first |
| `add_meeting_note` | `meeting <project> --title T [--date D] --body-file F` | Adds a meeting note (date defaults to today) |
| `add_result` | `result <project> --title T [--url U] [--ref R] --body-file F` | Adds a result; the same `ref` again updates it |
| `update_entry` | `edit-entry <project> meetings\|results <id> [...]` | Changes a meeting note or result |
| `add_item` | `item <project> <section> --title T [--date D] [--status S]` | Adds to a roadmap, checklist, deadlines, ideas, questions or decisions section |
| `update_item` | `edit-item <project> <section> <item> [...]`, `status ... <status>` | Changes an item or moves it along (roadmap: planned/doing/done; checklist: todo/done; ideas: open/keep/drop; questions: open/answered; literature: unread/reading/read) |
| `add_paper` | `paper <project> <section> <link>` | Adds a paper from an arXiv/DOI/ACL link (details looked up); other links need a title (`--authors "A; B"`, `--year`, `--venue`) |
| `write_page` | `page <project> <section> --body-file F` | Replaces a page section's markdown |
| `add_link` | `link <project> --label L --url U [--kind K]` | Adds a link to the links bar |

On the command line, long text goes through a file or stdin (`--body-file -`).

## W&B runs → Results

On a machine logged in to W&B (`wandb login`):

```bash
python3 <this skill's folder>/site.py wandb-sync <project> <entity>/<wandb-project> \
    [--metrics acc,loss] [--config lr,batch_size] [--tag paper] [--limit 50] [--dry-run]
```

Each finished run becomes a result (title = run name, date, link to the run, a table of
the chosen summary metrics, or of up to 12 numeric ones, plus chosen config values). Runs
are keyed by their W&B path, so running it again updates them instead of duplicating.
Use `--dry-run` first to show the user what would be posted. It can run from cron.

## Errors

Both report the API's message (the CLI exits non-zero): 401 bad or revoked token; 404
project or section not reachable with this token; 400 what was wrong with the input; 429
too many failed attempts from this network.
