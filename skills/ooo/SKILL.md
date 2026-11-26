---
name: ooo
description: Away mode. While it is on, permission prompts also reach Matteo on Telegram with Yes/No buttons, and Claude messages him there only when blocked or when something is urgent. `/ooo` turns it on, `/ooo off` turns it off.
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
  One short plain-text message that stands on its own: he reads it on a phone without the terminal in front of him. Never put secrets in it.
- Don't use AskUserQuestion or other dialogs: they can't be answered from Telegram. Send the question with `tg.py send` and end your turn.
- His replies arrive as prompts that start with `[from Telegram; ...]`. Answer them with `tg.py send` as well.
- If the script says the router is not running, tell him in the terminal and carry on: nothing reaches Telegram until it starts.
