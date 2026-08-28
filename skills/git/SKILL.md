---
name: git
description: Help with git operations — branching, rebasing, cherry-picking, history inspection, and conflict resolution. Use when the user asks for git help beyond simple commits.
---

# Git Assistant

Help the user with git operations beyond basic add/commit/push.

## Capabilities

- **Branch management** — create, rename, delete, compare branches
- **Rebasing** — rebase onto main/other branches, interactive rebase cleanup
- **Cherry-picking** — move commits across branches (useful when working with forks)
- **History inspection** — summarize what changed on a branch, find when something broke
- **Conflict resolution** — help resolve merge/rebase conflicts, explain both sides
- **Stashing** — save and restore work in progress
- **Undoing mistakes** — recover from bad merges, accidental commits, lost work

## Guidelines

- **Explain before executing** — for destructive operations (force push, reset, rebase), explain what will happen and ask for confirmation
- **Never stage, commit, or push without explicit user approval** — always show what will be staged/committed and get sign-off first
- **Prefer rebase over merge** for keeping feature branches up to date (cleaner history)
- **Never force push to main/master** without explicit confirmation
- **Use `git log --oneline --graph`** when showing history for readability
- **When resolving conflicts**, show both sides and explain the intent of each change before suggesting a resolution

## Safety

- Never run `--force`, `--hard`, `clean -f`, or `branch -D` without asking first
- Never skip hooks (`--no-verify`) unless explicitly requested
- When in doubt, suggest creating a backup branch before risky operations
