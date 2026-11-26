---
name: ooo
description: Away mode. While it is on, permission prompts also reach Matteo on Telegram with Yes/No buttons, Claude messages him there only when blocked or when something is urgent, and his Telegram replies come back into the session. `/ooo` turns it on, `/ooo off` turns it off.
disable-model-invocation: true
argument-hint: "[off]"
---

# Away mode

Arguments: `$ARGUMENTS`

If the arguments are `off`, run exactly this, tell Matteo in one line that away mode is off, and from now on ignore the rules below:

```bash
~/.claude/skills/ooo/tg.py ooo off ${CLAUDE_SESSION_ID}
```

Otherwise run exactly this, and confirm in one line:

```bash
~/.claude/skills/ooo/tg.py ooo on ${CLAUDE_SESSION_ID}
```

Keep the path written as `~/.claude/skills/ooo/tg.py`, here and below: the allow rule in `settings.json` matches that spelling, so these calls never wait for a permission answer.

## While away mode is on

Matteo is not at the terminal. He reads Telegram on his phone.

- Keep working on the task as far as you can without him. Permission prompts already reach his phone on their own, so don't announce them.
- Message him only when you are blocked on a decision that is his to make, when something is urgent (a job failed, data is at risk, a quota is about to run out), or when you finished the task:
  ```bash
  ~/.claude/skills/ooo/tg.py send "..."
  ```
- Send him a file whenever it says more than text: a plot, a table, a short log, a PDF. Images (PNG, JPG) show up inline, anything else arrives as a file to open, up to 50 MB. Prefer PNG for plots, and keep the caption to a line or two:
  ```bash
  ~/.claude/skills/ooo/tg.py send --file path/to/plot.png "📊 Loss over the first 18 iterations"
  ```
- To ask him something, send the question and end your turn. His answer wakes the session and reaches you as a hook message starting with "Matteo replied on Telegram". Answer it with `tg.py send` as well.
- Don't use AskUserQuestion or other dialogs: they can't be answered from Telegram.
- If the script says the router is not running, tell him in the terminal and carry on: nothing reaches Telegram until it starts.

## How to write the messages

He reads them on a phone, often between other things, without the terminal in front of him.

- Short: a few lines. Each message stands on its own.
- In small blocks separated by a blank line: what happened, then what you need from him, if anything. A line break inside the quotes, or `\n`, starts a new line.
- Plain text only. Telegram does not render Markdown: it shows the raw symbols. So no Markdown tables, asterisks, backticks or headings. Use `- ` for a short list.
- For a table, write a few short lines (`August: 0.71`), or render it as an image (a PNG, made with matplotlib for example) and send that with `--file`. Same for anything with more than a handful of numbers.
- At most one or two emojis, as markers at the start of a block: ✅ done, ❌ failed, ⚠️ needs attention, ❓ question, 📊 figure.
- Never put secrets in a message or a file.

For example:

```
✅ g01 finished: 60 of 60 iterations, no errors.

Validation F1: 0.71 in August, 0.68 in September.

❓ Start g02 with the same config?
```
