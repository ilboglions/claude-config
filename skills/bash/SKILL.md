---
name: bash
description: Help write, debug, or improve bash/shell scripts. Use when the user asks for help with shell scripting, bash, or sh.
---

# Bash Scripting Assistant

Help the user write, debug, or improve shell scripts.

## Guidelines

- **Use `set -euo pipefail`** at the top of scripts unless there's a reason not to
- **Quote all variables** — `"$var"` not `$var`
- **Use `[[` over `[`** for conditionals in bash
- **Prefer `$(command)` over backticks** for command substitution
- **Use functions** to organize scripts longer than ~30 lines
- **Validate inputs early** — check that required args, files, and env vars exist before doing work
- **Use meaningful variable names** — `MODEL_NAME` not `m`
- **Add usage messages** — if the script takes arguments, print usage on `-h` or wrong arg count
- **Handle cleanup** — use `trap` for temp files or background processes
- **Be portable when possible** — note if something is bash-specific vs POSIX sh

## When Debugging

- Suggest `set -x` for tracing
- Check exit codes of piped commands (`${PIPESTATUS[@]}`)
- Look for unquoted variables, missing error handling, and word splitting issues

## Scope

$ARGUMENTS
