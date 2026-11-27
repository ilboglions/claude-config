#!/usr/bin/env python3
"""Away mode: talk to Claude Code sessions from Telegram (see SKILL.md).

  tg.py router          the only process talking to the bot (jsh starts it with the
                        anchor job); with a hub configured, it mirrors to the hub
                        instead and talks to Telegram only while the hub is away
  tg.py mirror          keep this machine's mailboxes in sync with a hub
  tg.py hook            PermissionRequest hook: while /ooo is on, also ask on Telegram
  tg.py stop            Stop hook: wait for Matteo's reply in the background
  tg.py start-wait      SessionStart hook: the same, from the session's start
  tg.py interrupt       PostToolUse hook: a reply is waiting, end the turn now
  tg.py wake            PostToolUse hook: then hand the reply over, once the turn has ended
  tg.py busy            UserPromptSubmit hook: a turn is starting
  tg.py send TEXT       message Matteo from this session
  tg.py send --file PATH [TEXT]
                        send him a file: images as photos, anything else as a document
  tg.py ooo on|off      turn away mode on or off for this session
  tg.py session-start   SessionStart hook: register the session; ask once for a name
  tg.py session-end     SessionEnd hook: a session that ends leaves away mode
  tg.py chat-id         print the id of whoever messages the bot next (setup)

Sessions only read and drop files in their mailbox (~/.claude/tg, or ~/.claude/tg-<bot>
for another bot), so they work on any node that shares $HOME with the router or the
mirror, even without internet access.
"""
import html
import json
import os
import re
import secrets
import shutil
import signal
import socket
try:
    import ssl
except ImportError:  # a Python without its OpenSSL (a cluster module not loaded): hooks don't need it
    ssl = None
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV = Path.home() / ".config" / "telegram.env"


def config():
    conf = {}
    for line in ENV.read_text().splitlines():
        key, sep, val = line.partition("=")
        if sep and not key.lstrip().startswith("#"):
            conf[key.strip()] = val.strip().strip("'\"")
    return conf


try:
    CONF = config()  # this machine's private settings
except OSError:
    CONF = {}


class Box:
    """One bot's mailbox on this machine."""

    def __init__(self, bot):
        self.bot = bot
        self.dir = Path.home() / ".claude" / ("tg" if bot == "work" else f"tg-{bot}")
        self.out, self.answers = self.dir / "out", self.dir / "answers"
        self.away, self.inbox = self.dir / "away", self.dir / "inbox"
        self.sessions = self.dir / "sessions"  # every live session, away or not
        self.waiting = self.dir / "waiting"    # per session: its newest stop-hook waiter
        self.turn = self.dir / "turn"          # per session: "busy" or "idle"
        self.files = self.dir / "files"        # copies of files to send
        self.state, self.alive = self.dir / "state.json", self.dir / "router.alive"


# The session's own mailbox: its project's TG_BOT, else this machine's default.
BOT = os.environ.get("TG_BOT") or CONF.get("TG_DEFAULT_BOT") or "work"
B = Box(BOT)
BOX, OUT, ANSWERS, AWAY, INBOX = B.dir, B.out, B.answers, B.away, B.inbox
SESSIONS, WAITING, TURN, FILES, STATE, ALIVE = B.sessions, B.waiting, B.turn, B.files, B.state, B.alive
PHOTO_TYPES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_PHOTO, MAX_FILE = 10 << 20, 50 << 20  # what Telegram accepts from bots
SAFE_ID = re.compile(r"^[0-9A-Za-z_-]{1,64}$")  # session and request ids, before they become paths
TOKEN, CHAT = "", 0


# ---- used by the sessions (hooks, send, ooo) --------------------------------

def router_alive(b=B):
    try:
        return time.time() - b.alive.stat().st_mtime < 60
    except FileNotFoundError:
        return False


def write_atomic(path, text):
    """Write then rename, so a reader on another node never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{secrets.token_hex(6)}"
    tmp.write_text(text)
    tmp.rename(path)


def drop(item, b=B):
    if item.get("sid"):  # the chat's name as it is now, for the header
        item = {**item, "chat": chat_title(item["sid"])}
    path = b.out / f"{time.time():.6f}-{secrets.token_hex(3)}.json"
    write_atomic(path, json.dumps(item))
    return path


def origin(sid, cwd=None):
    cwd = cwd or os.getcwd()
    # jsh (mymila) hands the tmux session's name to the shell on the job.
    short = os.environ.get("JSH_SESSION") or os.path.basename(cwd.rstrip("/")) or cwd
    # The project's own name, from env.TG_NAME in its .claude/settings.local.json.
    return {"sid": sid, "label": os.environ.get("TG_NAME") or short, "short": short}


_titles = {}  # sid -> (transcript, its size when read, title)


def chat_title(sid):
    """The chat's name as Claude Code shows it: the one given with /rename, else the one it
    made up. Claude Code writes both into the transcript again and again, so the tail
    holds the latest."""
    if not SAFE_ID.match(sid or ""):
        return ""
    path, size, title = _titles.get(sid, (None, -1, ""))
    try:
        # a chat moved to another folder leaves its old transcript behind: take the live one
        path = path or max((Path.home() / ".claude" / "projects").glob(f"*/{sid}.jsonl"),
                           key=lambda t: t.stat().st_mtime)
        now = path.stat().st_size
        if now != size:
            title = ""
            with open(path, "rb") as f:
                f.seek(max(0, now - 1_000_000))
                tail = f.read()
            for line in reversed(tail.splitlines()):
                if b'-title"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") == "custom-title" and d.get("customTitle"):
                    title = d["customTitle"]
                    break
                if d.get("type") == "ai-title" and not title:
                    title = d.get("aiTitle") or ""
            _titles[sid] = (path, now, title)
    except (ValueError, OSError):  # no transcript (yet)
        return ""
    return title


def claude_pid():
    if os.environ.get("CLAUDE_PID"):
        return int(os.environ["CLAUDE_PID"])
    try:  # a hook runs under a shell that Claude Code started
        out = subprocess.run(["ps", "-o", "ppid=", "-p", str(os.getppid())],
                             capture_output=True, text=True, timeout=5).stdout
        return int(out.strip() or 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def where():
    """Where the session runs, so the router or mirror can tell when it died without
    its SessionEnd hook (a closed pane on the cluster, a job that ended)."""
    return {"job": os.environ.get("SLURM_JOB_ID", ""), "host": socket.gethostname(),
            "pid": claude_pid()}


def session_start():
    """SessionStart hook: register the session; on a machine set to be always away, turn
    away mode on; and in a git project with no TG_NAME yet, have Claude ask for one."""
    req = json.load(sys.stdin)
    sid, cwd = req.get("session_id", ""), Path(req.get("cwd") or os.getcwd())
    context = []
    if SAFE_ID.match(sid):
        info = {**origin(sid, str(cwd)), **where()}
        write_atomic(SESSIONS / f"{sid}.json", json.dumps(info))
        # A machine Matteo only reaches through Telegram: every session is away from the start.
        if CONF.get("TG_ALWAYS_AWAY", "").lower() in ("1", "yes", "true"):
            if not (AWAY / sid).exists():
                write_atomic(AWAY / sid, json.dumps(info))
                drop({"kind": "msg", "text": "session started, away mode on. Reply to this "
                      "message to talk to it.", **origin(sid, str(cwd))})
            context.append("Matteo reaches this machine only through Telegram, so away mode is "
                           "on for this session from the start, as if he had typed /ooo. "
                           "Follow these rules.\n\n" + away_rules())
    if "TG_NAME" not in os.environ and ENV.exists() and \
            any((d / ".git").exists() for d in (cwd, *cwd.parents)):
        context.append(
            "This project has no name yet for Matteo's Telegram away mode (/ooo). In your first "
            "reply, ask him in one short line whether he wants to give it one: emojis are welcome "
            "(for example \"🟦 Multi-agent detection\"), or no name. Write his answer as env.TG_NAME "
            f"in {cwd}/.claude/settings.local.json, keeping whatever else that file holds. If he "
            "says no, write an empty string: it means don't ask again, and Telegram keeps showing "
            "the session's name.")
    if context:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                 "additionalContext": "\n\n".join(context)}}))


def other_boxes():
    """This machine's other bots' mailboxes: a project can switch bot mid-session."""
    home = Path.home() / ".claude"
    return [Box("work" if d.name == "tg" else d.name[3:])
            for d in (home / "tg", *home.glob("tg-*")) if d.is_dir() and d != B.dir]


def session_end():
    """SessionEnd hook: a session that exits is unregistered, and leaves away mode, on
    every bot (its project may have switched bot while it ran)."""
    req = json.load(sys.stdin)
    sid = req.get("session_id", "")
    if not SAFE_ID.match(sid):
        return
    for b in (B, *other_boxes()):
        (b.sessions / f"{sid}.json").unlink(missing_ok=True)
        flag = b.away / sid
        if not flag.exists():
            continue
        try:
            info = json.loads(flag.read_text())
        except ValueError:
            info = origin(sid, req.get("cwd"))
        end_session(sid, info, b)


def end_session(sid, info, b=B):
    """Take a session out of away mode for good, and tell Matteo (the hook and the router)."""
    (b.away / sid).unlink(missing_ok=True)
    (b.waiting / sid).unlink(missing_ok=True)
    (b.turn / sid).unlink(missing_ok=True)
    unread = list((b.inbox / sid).glob("*.json"))
    for f in unread:
        f.unlink(missing_ok=True)
    n = len(unread)
    note = f" {n} message{'s' if n > 1 else ''} from you {'were' if n > 1 else 'was'} not read." if n else ""
    drop({"kind": "msg", "text": "session ended, away mode off." + note,
          **{k: info.get(k) for k in ("sid", "label", "short")}}, b)


def hook():
    req = json.load(sys.stdin)
    sid = req.get("session_id", "none")
    away = AWAY / sid
    if not away.exists():
        return  # no output: the terminal prompt alone decides
    rid = secrets.token_hex(4)
    answer = ANSWERS / rid
    inp = req.get("tool_input") or {}
    if "command" in inp:
        title, preview = inp.get("description", ""), inp["command"]
    else:
        title, preview = "", json.dumps(inp, indent=1, ensure_ascii=False)
    drop({"kind": "perm", "id": rid, "tool": req.get("tool_name", "?"), "title": title,
          "preview": preview[:1500], **origin(sid, req.get("cwd"))})
    # The terminal prompt stays open next to this one, and an answer there wins:
    # Claude Code then lets this hook run on and ignores what it prints.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        while away.exists():
            if answer.exists():
                if answer.read_text().strip() == "allow":
                    decision = {"behavior": "allow"}
                else:
                    decision = {"behavior": "deny", "message": "Matteo denied this from Telegram."}
                print(json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PermissionRequest", "decision": decision}}))
                return
            time.sleep(1)
    finally:
        answer.unlink(missing_ok=True)
        drop({"kind": "done", "id": rid})


def read(path):
    try:
        return path.read_text()
    except FileNotFoundError:
        return None


def mark(sid, turn):
    """Whether the session is "busy" (in a turn) or "idle". Replies are handed over only to
    an idle session: one that arrives mid-turn sits next to a tool result, where Claude
    rightly distrusts instructions."""
    write_atomic(TURN / sid, turn)


def idle_for(sid):  # seconds since the session went idle; -1 while busy or unknown
    try:
        f = TURN / sid
        return time.time() - f.stat().st_mtime if f.read_text() == "idle" else -1
    except FileNotFoundError:
        return -1


def hand_over(sid, idle=2):
    """If the session has been idle for a moment and something is waiting for it, wake it
    (exit code 2 of an asyncRewake hook). Replies only reach a session in away mode;
    notices (away mode turned on or off from Telegram) reach any session."""
    if idle_for(sid) < idle:
        return False
    got = claim_replies(sid, notices_only=not (AWAY / sid).exists())
    if not got:
        return False
    mark(sid, "busy")
    notices = [t for kind, t in got if kind == "notice"]
    replies = [t for kind, t in got if kind != "notice"]
    text = "\n\n".join(notices)
    if replies:
        text += ("\n\n" if text else "") + "Matteo replied on Telegram:\n\n" + "\n\n".join(replies) \
                + '\n\nAnswer him with ~/.claude/skills/ooo/tg.py send "..."'
    print(text, file=sys.stderr)
    sys.exit(2)


def start_wait():
    """SessionStart hook, asyncRewake: a session that starts in away mode (on an
    always-away machine, or resumed while away) waits for Telegram from the start,
    not only once its first turn has ended."""
    req = json.load(sys.stdin)
    time.sleep(2)  # let session-start register the session and set its flag
    stop(req)


def stop(req=None):
    req = req if req is not None else json.load(sys.stdin)
    sid = req.get("session_id", "none")
    away, mark_file = AWAY / sid, WAITING / sid
    # A session in away mode always waits; with a hub, any other registered session
    # waits too while the mirror runs, so away mode can be turned on from Telegram.
    if not away.exists() and not (CONF.get("TG_HUB_URL") and (SESSIONS / f"{sid}.json").exists()
                                  and router_alive()):
        return
    # This runs in the background (asyncRewake in settings.json): the session goes
    # idle as usual, and exit code 2 wakes it with what this prints on stderr.
    # Every turn's end starts a waiter; the newest one wins and older ones leave.
    mark(sid, "idle")
    me = secrets.token_hex(4)
    write_atomic(mark_file, me)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while read(mark_file) == me and (away.exists() or (SESSIONS / f"{sid}.json").exists()):
        hand_over(sid)
        time.sleep(1 if away.exists() else 2)


def claim_replies(sid, notices_only=False):
    """Take what waits for this session, each item exactly once: [(kind, text)]."""
    got, me = [], secrets.token_hex(4)
    for f in sorted((INBOX / sid).glob("*.json")):
        try:
            if notices_only and json.loads(f.read_text()).get("kind") != "notice":
                continue
        except (OSError, ValueError):
            continue
        claimed = f.with_suffix(f".{me}")
        try:
            f.rename(claimed)  # atomic: an item goes to one reader only
        except FileNotFoundError:
            continue
        item = json.loads(claimed.read_text())
        claimed.unlink()
        got.append((item.get("kind", "reply"), item["text"]))
        if item.get("msg"):
            drop({"kind": "delivered", "msg": item["msg"]})
    return got


# A reply that comes while Claude works must not wait for the turn to end. After each
# tool call (settings.json runs these only when the inbox has something), "interrupt"
# ends the turn, like Esc, and "wake", running in the background, wakes the session
# with the reply once it is idle, like typing it in.

def interrupt():
    """PostToolUse hook: end the turn now, a Telegram reply is waiting."""
    sid = json.load(sys.stdin).get("session_id", "none")
    if (AWAY / sid).exists() and any((INBOX / sid).glob("*.json")):
        mark(sid, "idle")
        print(json.dumps({"continue": False, "stopReason": "📩 Telegram message from Matteo"}))


def wake():
    """PostToolUse hook, asyncRewake: hand the reply over once the turn has ended."""
    sid = json.load(sys.stdin).get("session_id", "none")
    for _ in range(60):
        if not (AWAY / sid).exists() and not (SESSIONS / f"{sid}.json").exists():
            return
        hand_over(sid)
        time.sleep(0.5)


def busy():
    """UserPromptSubmit hook: he typed in the terminal, so a turn is starting."""
    mark(json.load(sys.stdin).get("session_id", "none"), "busy")


def warn_if_no_router():
    if not router_alive():
        print("The router is not running: nothing reaches Telegram until it starts.")


def send(text, file=None):
    # Sessions often write "\n" for a line break inside a quoted shell argument.
    item = {"kind": "msg", "text": text.replace("\\n", "\n"),
            **origin(os.environ.get("CLAUDE_CODE_SESSION_ID", ""))}
    if file:
        src = Path(file).expanduser()
        if not src.is_file():
            sys.exit(f"No such file: {src}")
        if src.stat().st_size > MAX_FILE:
            sys.exit(f"{src.name} is over 50 MB, the most a bot can send.")
        # Copied next to the queue: the router may run on another node than this file.
        copy = FILES / f"{secrets.token_hex(4)}-{src.name}"
        FILES.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, copy)
        item.update(kind="file", path=str(copy), name=src.name)
    path = drop(item)
    for _ in range(30 if file else 10):  # the router or mirror deletes it once it's sent on
        if not path.exists():
            print("Sent to Telegram.")
            return
        time.sleep(0.5)
    print("Queued for Telegram, not sent yet.")
    warn_if_no_router()


def away_mode(state, sid):
    if not sid:
        sys.exit("No session id: pass it, or run this from inside Claude Code.")
    flag = AWAY / sid
    if state == "off":
        if flag.exists():
            flag.unlink()
            drop({"kind": "msg", "text": "away mode off.", **origin(sid)})
        print("away mode off")
        return
    for b in other_boxes():  # a project that switched bot leaves the old one's list
        (b.away / sid).unlink(missing_ok=True)
        (b.sessions / f"{sid}.json").unlink(missing_ok=True)
    info = origin(sid)
    write_atomic(flag, json.dumps({**info, **where()}))
    drop({"kind": "msg", "text": "away mode on. Reply to this message to talk to this session.",
          **info})
    print("away mode on")
    warn_if_no_router()


# ---- router -----------------------------------------------------------------

lock = threading.Lock()
state = {"offset": 0, "msgs": {}, "reqs": {}}  # msgs: message id -> session; reqs: open prompts


def log(text):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), text, file=sys.stderr, flush=True)


# Mila's python/3.10 module ships a CA bundle that cannot verify Telegram's
# certificate chain; the system bundle can.
SYSTEM_CA = "/etc/ssl/certs/ca-certificates.crt"
TLS = ssl.create_default_context(cafile=SYSTEM_CA if os.path.exists(SYSTEM_CA) else None) if ssl else None


class RateLimited(OSError):
    """Telegram answered 429: nothing is sent until the wait it asked for is over."""


pause_until = 0.0


def api(method, files=None, **params):
    global pause_until
    # Calling again before the wait is over only makes Telegram extend it.
    if method != "getUpdates" and time.time() < pause_until:
        raise RateLimited(f"waiting {pause_until - time.time():.0f} s more")
    fields = {k: v if isinstance(v, (str, int)) else json.dumps(v) for k, v in params.items()}
    headers = {}
    if files:  # multipart upload: {field: (filename, bytes)}
        b = secrets.token_hex(16)
        parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                 for k, v in fields.items()]
        for k, (name, data) in files.items():
            name = name.replace('"', "'").replace("\r", " ").replace("\n", " ")
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"'
                         f'\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + data + b"\r\n")
        body = b"".join(parts) + f"--{b}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={b}"
    else:
        body = urllib.parse.urlencode(fields).encode()
    base = CONF.get("TELEGRAM_API_URL", "https://api.telegram.org/bot")
    req = urllib.request.Request(f"{base}{TOKEN}/{method}", body, headers)
    try:
        with urllib.request.urlopen(req, timeout=70, context=TLS if base.startswith("https") else None) as r:
            return json.load(r)["result"]
    except urllib.error.HTTPError as e:
        if e.code != 429:
            try:  # Telegram says what it refused, e.g. "can't parse entities"
                e.description = json.load(e).get("description", "")
            except ValueError:
                e.description = ""
            raise
        try:
            wait = json.load(e)["parameters"]["retry_after"]
        except (ValueError, KeyError, TypeError):
            wait = 30
        pause_until = time.time() + wait + 1
        log(f"429 on {method}: Telegram asks to wait {wait} s, holding every message until then")
        raise RateLimited(f"429, retry after {wait} s") from None


def save():
    msgs = state["msgs"]
    while len(msgs) > 500:
        del msgs[next(iter(msgs))]
    write_atomic(STATE, json.dumps(state))


# Telegram's HTML formatting. Sessions may use these tags; everything else is escaped.
TAGS = re.compile(r"</?(?:b|strong|i|em|u|ins|s|strike|del|code|pre|blockquote|tg-spoiler)>"
                  r'|<a href="[^"<>]*">|</a>', re.I)


def fmt(text):
    """Keep Telegram's formatting tags and escape the rest, so a stray < or & breaks nothing."""
    out, pos = [], 0
    for m in TAGS.finditer(text):
        out += [html.escape(text[pos:m.start()], quote=False), m.group(0)]
        pos = m.end()
    return "".join(out) + html.escape(text[pos:], quote=False)


def suffix(i):
    """" · data cleanup": the chat's name in Claude Code, or the tmux session's until it has one."""
    return f" · {i.get('chat') or chat_title(i.get('sid', '')) or i.get('short') or i['label']}"


def shown(i):  # the name on buttons and prompts
    return i["label"] + suffix(i)


def head(i):  # the header line: the project's name in bold, the chat's name plain
    return f"<b>{html.escape(i['label'], quote=False)}</b>" + html.escape(suffix(i), quote=False)


def send_html(method, key, text, **params):
    """Send formatted; if Telegram can't parse the tags (say, one left open), send it plain."""
    try:
        return api(method, parse_mode="HTML", **{key: text}, **params)
    except urllib.error.HTTPError as e:
        if e.code != 400 or "entit" not in getattr(e, "description", ""):
            raise
        log(f"{method}: Telegram could not parse the formatting ({e.description}); sent it plain")
        return api(method, **{key: html.unescape(TAGS.sub("", text))}, **params)


def edit(msg_id, text):
    try:
        send_html("editMessageText", "text", text, chat_id=CHAT, message_id=msg_id)
    except OSError:  # cosmetic: skip it rather than hold anything up
        pass


def react(msg_id, emoji):
    try:
        api("setMessageReaction", chat_id=CHAT, message_id=msg_id,
            reaction=[{"type": "emoji", "emoji": emoji}])
    except OSError:  # cosmetic: skip it rather than hold anything up
        pass


def deliver(item):
    kind = item["kind"]
    if kind == "done":  # the hook stopped waiting without a Telegram answer
        req = state["reqs"].pop(item["id"], None)
        if req:
            edit(req["msg"], req["text"] +
                 "\n\n→ expired (answered in the terminal, timed out, or away mode off)")
        return
    if kind == "delivered":  # the session picked up a reply
        react(item["msg"], "👍")
        return
    if kind == "msg":
        m = send_html("sendMessage", "text", f"{head(item)}\n{fmt(item['text'][:3800])}",
                      chat_id=CHAT)
    elif kind == "file":
        path, m = Path(item["path"]), None
        caption = head(item) + (f"\n{fmt(item['text'][:900])}" if item["text"].strip() else "")
        if path.suffix.lower() in PHOTO_TYPES and path.stat().st_size <= MAX_PHOTO:
            try:
                m = send_html("sendPhoto", "caption", caption, chat_id=CHAT,
                              files={"photo": (item["name"], path.read_bytes())})
            except urllib.error.HTTPError as e:  # e.g. extreme proportions: send it as a file
                if e.code != 400:
                    raise
                log(f"sendPhoto refused {item['name']} ({e}); sending it as a document")
        if m is None:
            m = send_html("sendDocument", "caption", caption, chat_id=CHAT,
                          files={"document": (item["name"], path.read_bytes())})
    else:
        esc = lambda s: html.escape(s, quote=False)
        text = (f"{head(item)}\n<b>{esc(item['tool'])}</b>"
                + (f": {esc(item['title'][:300])}" if item["title"] else "")
                + f"\n<pre>{esc(item['preview'])}</pre>")
        keys = [[{"text": "Yes", "callback_data": f"allow:{item['id']}"},
                 {"text": "No", "callback_data": f"deny:{item['id']}"}]]
        m = send_html("sendMessage", "text", text, chat_id=CHAT,
                      reply_markup={"inline_keyboard": keys})
        state["reqs"][item["id"]] = {"msg": m["message_id"], "text": text}
    state["msgs"][str(m["message_id"])] = {"sid": item["sid"], "label": item["label"],
                                           "short": item.get("short", item["label"])}


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:  # another user's process holds that id now: can't tell
        return True


suspects = set()  # sessions that looked dead at the last sweep


def sweep(boxes=(B,)):
    """Sessions that died without their SessionEnd hook are unregistered and leave away
    mode: their job is gone, or their Claude process on this node is. Two sweeps in a
    row must agree."""
    try:
        jobs = set(subprocess.run(["squeue", "-u", os.environ.get("USER", ""), "-h", "-o", "%i"],
                                  capture_output=True, text=True, timeout=30, check=True).stdout.split())
    except (OSError, subprocess.SubprocessError):
        jobs = None  # no Slurm here, or can't ask it right now: judge by process only
    here, dead = socket.gethostname(), set()
    for b in boxes:
        for f in [*b.away.glob("*"), *b.sessions.glob("*.json")]:
            try:
                info = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            job, pid = info.get("job"), info.get("pid")
            if not ((jobs is not None and job and job not in jobs) or (
                    info.get("host") == here and pid and not alive(pid))):
                continue
            key = str(f)
            dead.add(key)
            if key not in suspects:
                continue
            if f.parent == b.sessions:
                f.unlink(missing_ok=True)
            else:
                log(f"{info.get('label')} died without its SessionEnd hook; leaving away mode")
                end_session(f.name, info, b)
    # Only this sweep's bots: each bot's mirror sweeps its own, and must not reset the others'.
    swept = tuple(str(b.dir) + os.sep for b in boxes)
    suspects.difference_update({k for k in suspects if k.startswith(swept)})
    suspects.update(dead)


def outbox(stop=None):
    last_sweep = 0
    while not (stop and stop.is_set()):
        ALIVE.touch()
        if time.time() - last_sweep > 60:
            last_sweep = time.time()
            sweep()
        if time.time() < pause_until:  # Telegram asked to wait (429): keep everything queued
            time.sleep(1)
            continue
        for f in sorted(OUT.glob("*.json")):
            item = {}
            try:
                item = json.loads(f.read_text())
                with lock:
                    deliver(item)
                    save()
            except urllib.error.HTTPError as e:  # Telegram refused it: drop it
                log(f"Telegram refused {f.name}: {e}")
            except FileNotFoundError as e:  # its file is gone: nothing to retry
                log(f"dropped {f.name}: {e}")
            except OSError as e:  # network trouble or a 429: keep it, in order, for later
                if not isinstance(e, RateLimited):
                    log(f"will retry {f.name}: {e}")
                break
            except (ValueError, KeyError) as e:
                log(f"bad item {f.name}: {e}")
            if item.get("path"):
                Path(item["path"]).unlink(missing_ok=True)
            f.unlink(missing_ok=True)
        time.sleep(1)


def away_sessions():
    found = {}
    for f in AWAY.glob("*"):
        try:
            info = json.loads(f.read_text())
            found[f.name] = {"label": info["label"], "short": info.get("short", info["label"])}
        except (OSError, ValueError, KeyError):
            pass
    return found


def norm(name):  # how /to compares names: no emojis or punctuation, any case
    return " ".join("".join(c for c in name.lower() if c.isalnum() or c.isspace()).split())


def pick_session(reply_to=None):
    """One button per session in away mode; tapping one opens a reply addressed to it."""
    away = away_sessions()
    if not away:
        api("sendMessage", chat_id=CHAT, text="No session is in away mode.")
        return
    names = {sid: shown({"sid": sid, **i}) for sid, i in away.items()}
    rows = [[{"text": names[sid], "callback_data": f"to:{sid}"}]
            for sid in sorted(names, key=lambda s: names[s].lower())]
    api("sendMessage", chat_id=CHAT, text="Which session? Tap one, then write your message.",
        reply_markup={"inline_keyboard": rows},
        **({"reply_to_message_id": reply_to} if reply_to else {}))


def prompt_for(sid):
    # A reply box addressed to the session. Recorded as one of its messages, so the
    # answer goes through the usual reply routing.
    away = away_sessions()
    if sid not in away:
        api("sendMessage", chat_id=CHAT, text="That session is no longer in away mode.")
        return
    i = {"sid": sid, **away[sid]}
    name = shown(i)
    m = api("sendMessage", chat_id=CHAT, text=f"✍️ Message for {name}:",
            reply_markup={"force_reply": True, "input_field_placeholder": f"to {name}"[:64]})
    state["msgs"][str(m["message_id"])] = i


def handle(u):
    q = u.get("callback_query")
    if q:  # a button tap
        if q["from"]["id"] != CHAT:
            return
        if q.get("data", "").startswith("to:"):  # a session picked from the list
            api("answerCallbackQuery", callback_query_id=q["id"])
            prompt_for(q["data"][3:].split("|")[-1])
            return
        verdict, _, rid = q.get("data", "").partition(":")
        req = state["reqs"].pop(rid, None) if verdict in ("allow", "deny") else None
        if not req:
            api("answerCallbackQuery", callback_query_id=q["id"], text="This request already ended.")
            return
        write_atomic(ANSWERS / rid, verdict)
        api("answerCallbackQuery", callback_query_id=q["id"])
        edit(req["msg"], req["text"] + ("\n\n→ approved" if verdict == "allow" else "\n\n→ denied"))
        return

    m = u.get("message") or {}
    if m.get("from", {}).get("id") != CHAT or m.get("chat", {}).get("type") != "private":
        return
    text = m.get("text", "")
    reply = lambda t: api("sendMessage", chat_id=CHAT, text=t, reply_to_message_id=m["message_id"])
    away = away_sessions()
    if text.strip().split("@")[0] in ("/list", "/to"):  # pick by tapping, nothing to type
        pick_session()
        return
    if text.startswith("/to "):
        # The name is the project's name or the session's, and may be several words:
        # take the longest run of leading words that matches one.
        words = text[4:].split()
        for n in range(len(words), 0, -1):
            key = norm(" ".join(words[:n]))
            sids = [s for s, i in away.items() if key and key in (norm(i["label"]), norm(i["short"]))]
            if sids:
                break
        else:
            reply("No session with that name is in away mode (/list shows them).")
            return
        if len(sids) > 1:  # several sessions in one project: let him tap the right one
            pick_session(reply_to=m["message_id"])
            return
        text = text[re.match(r"/to\s+" + r"\s+".join(map(re.escape, words[:n])) + r"\s*", text).end():]
        target = {"sid": sids[0], **away[sids[0]]}
    elif str(m.get("reply_to_message", {}).get("message_id")) in state["msgs"]:
        target = state["msgs"][str(m["reply_to_message"]["message_id"])]
    elif state["msgs"]:  # replies to nothing, or to a router notice: for the session that wrote last
        target = state["msgs"][next(reversed(state["msgs"]))]
    else:
        pick_session(reply_to=m["message_id"])  # nobody wrote yet: let him pick
        return
    if not text.strip():
        return
    sid = target["sid"]
    if sid not in away:
        reply(f"Not sent: {shown(target)} is not in away mode, so nothing would read it.")
        return
    write_atomic(INBOX / sid / f"{time.time():.6f}.json",
                 json.dumps({"text": text, "msg": m["message_id"]}))
    react(m["message_id"], "👀")  # queued; 👍 once the session picks it up


def run_router(stop=None, poll_timeout=50, hello="Router up"):
    """Talk to Telegram for the work bot's mailbox; with `stop`, until it is set."""
    global TOKEN, CHAT
    TOKEN, CHAT = CONF["TELEGRAM_BOT_TOKEN"], int(CONF.get("TELEGRAM_CHAT_ID") or 0)
    if not CHAT:
        sys.exit(f"Set TELEGRAM_CHAT_ID in {ENV} first (tg.py chat-id finds it).")
    for d in (OUT, ANSWERS, AWAY, INBOX):
        d.mkdir(parents=True, exist_ok=True)
    if STATE.exists():
        state.update(json.loads(STATE.read_text()))
    ALIVE.touch()
    feeder = threading.Thread(target=outbox, args=(stop,), daemon=True)
    feeder.start()
    where_ = socket.gethostname().split(".")[0]
    job = os.environ.get("SLURM_JOB_ID")
    log(f"{hello.lower()} on {where_}" + (f", job {job}" if job else ""))
    try:
        # Telegram suggests only the commands a bot registers.
        api("setMyCommands", commands=[
            {"command": "to", "description": "Pick a session and message it"},
            {"command": "list", "description": "Sessions in away mode"}])
        api("sendMessage", chat_id=CHAT, text=f"{hello} on {where_}" + (f" (job {job})" if job else ""))
    except OSError as e:
        log(f"startup messages: {e}")
    while not (stop and stop.is_set()):
        try:
            updates = api("getUpdates", offset=state["offset"], timeout=poll_timeout,
                          allowed_updates=["message", "callback_query"])
        except OSError as e:
            log(f"getUpdates: {e}")
            time.sleep(5)
            continue
        for u in updates:
            with lock:
                state["offset"] = u["update_id"] + 1
                try:
                    handle(u)
                except OSError as e:
                    log(f"update {u['update_id']}: {e}")
                save()
    feeder.join(timeout=5)


def router():
    if CONF.get("TG_HUB_URL"):
        try:
            hub_tls()
        except (OSError, ValueError, AttributeError) as e:
            # Better the plain router than nobody: the hub only polls the work bot while
            # this machine's mirror syncs, so the two can't collide.
            log(f"the hub's client certificate is unusable ({e}); running the plain router")
        else:
            mirror()
            return
    if router_alive():
        sys.exit("A router is already running (or stopped less than a minute ago).")
    run_router()


# ---- mirror: this machine's mailboxes, kept in sync with a hub ----------------

HUB_TLS = None
HUB_GRACE = float(CONF.get("TG_HUB_GRACE") or 150)  # seconds without the hub before falling back


def hub(path, payload=None, raw=None, timeout=45):
    url = CONF["TG_HUB_URL"].rstrip("/") + path
    data = raw if raw is not None else json.dumps(payload or {}).encode()
    kind = "application/octet-stream" if raw is not None else "application/json"
    req = urllib.request.Request(url, data, {"Content-Type": kind})
    with urllib.request.urlopen(req, timeout=timeout,
                                context=HUB_TLS if url.startswith("https:") else None) as r:
        return json.load(r)


def snapshot(b):
    """The sessions this machine has for one bot, and which are in away mode."""
    found = {}
    for f in b.sessions.glob("*.json"):
        try:
            s = json.loads(f.read_text())
            found[s["sid"]] = {"sid": s["sid"], "label": s["label"], "short": s.get("short", s["label"])}
        except (OSError, ValueError, KeyError):
            pass
    for f in b.away.glob("*"):
        try:
            s = json.loads(f.read_text())
            found.setdefault(f.name, {"sid": f.name, "label": s["label"],
                                      "short": s.get("short", s["label"])})
        except (OSError, ValueError, KeyError):
            continue
    for sid, s in found.items():
        s["away"] = (b.away / sid).exists()
        s["chat"] = chat_title(sid)
    return list(found.values())


def away_rules():
    try:
        skill = (Path(__file__).resolve().parent / "SKILL.md").read_text()
    except OSError:
        return ""
    i = skill.find("## While away mode is on")
    return skill[i:] if i >= 0 else ""


def apply(b, c):
    """A command from the hub, written into the mailbox the sessions read."""
    t = c.get("type")
    if t == "state":
        write_atomic(b.state, json.dumps(c["state"]))
        return
    sid = str(c.get("sid", c.get("rid", "")))
    if not SAFE_ID.match(sid):
        return
    if t == "reply":
        write_atomic(b.inbox / sid / f"{time.time():.6f}.json",
                     json.dumps({"text": c["text"], "msg": c["msg"]}))
    elif t == "answer" and c.get("verdict") in ("allow", "deny"):
        write_atomic(b.answers / sid, c["verdict"])
    elif t == "away":
        try:
            info = json.loads((b.sessions / f"{sid}.json").read_text())
        except (OSError, ValueError):
            return
        notice = lambda text: write_atomic(b.inbox / sid / f"{time.time():.6f}.json",
                                           json.dumps({"kind": "notice", "text": text}))
        who = {k: info.get(k) for k in ("sid", "label", "short")}
        if c.get("on") and not (b.away / sid).exists():
            write_atomic(b.away / sid, json.dumps(info))
            notice("Matteo turned away mode on from Telegram, as if he had typed /ooo. Until he "
                   "turns it off, follow these rules.\n\n" + away_rules())
            drop({"kind": "msg", "text": "away mode on (from Telegram). Reply to this message "
                  "to talk to this session.", **who}, b)
        elif not c.get("on") and (b.away / sid).exists():
            (b.away / sid).unlink(missing_ok=True)
            notice("Matteo turned away mode off from Telegram: from now on, ignore the away-mode "
                   "rules and work as usual.")
            drop({"kind": "msg", "text": "away mode off (from Telegram).", **who}, b)


class Link:
    """One mailbox's link to the hub, and for the work bot, the fallback router."""

    def __init__(self, b, fallback):
        self.b, self.fallback = b, fallback
        self.routing = threading.Event()  # set while this machine talks to Telegram itself
        self.stop_router = None
        self.router_thread = None
        self.down = False  # logged that the hub is unreachable, until it answers again

    def unreachable(self, e):
        if not self.down:
            log(f"{self.b.bot}: hub unreachable: {e}")
        self.down = True

    def start_router(self):
        log(f"{self.b.bot}: no hub for {HUB_GRACE:.0f} s, talking to Telegram directly")
        self.stop_router = threading.Event()
        self.routing.set()
        self.router_thread = threading.Thread(
            target=run_router, kwargs={"stop": self.stop_router, "poll_timeout": 10,
                                       "hello": "Router up (the hub is unreachable)"}, daemon=True)
        self.router_thread.start()

    def end_router(self):
        log(f"{self.b.bot}: the hub is back, handing the bot back to it")
        self.stop_router.set()
        self.router_thread.join(timeout=30)  # its last getUpdates ends within 10 s
        self.routing.clear()

    def push(self):
        """Hand the sessions' new items to the hub as soon as they appear."""
        b = self.b
        while True:
            b.alive.touch()
            if self.routing.is_set():  # the fallback router delivers them itself
                time.sleep(1)
                continue
            batch = []
            for f in sorted(b.out.glob("*.json"))[:50]:
                try:
                    item = json.loads(f.read_text())
                    if item.get("kind") == "file":
                        fid = secrets.token_hex(8)
                        hub(f"/v1/file?bot={b.bot}&id={fid}&name={urllib.parse.quote(item['name'])}",
                            raw=Path(item["path"]).read_bytes(), timeout=600)
                        item["file_id"] = fid
                except (FileNotFoundError, ValueError, KeyError):
                    f.unlink(missing_ok=True)  # broken or its file is gone: nothing to retry
                    continue
                except OSError as e:
                    self.unreachable(e)
                    break
                batch.append((f, item))
            if batch:
                try:
                    hub(f"/v1/push?bot={b.bot}",
                        {"items": [{k: v for k, v in i.items() if k != "path"} for _, i in batch]})
                except (OSError, ValueError) as e:
                    self.unreachable(e)
                    time.sleep(5)
                    continue
                for f, item in batch:
                    if item.get("path"):
                        Path(item["path"]).unlink(missing_ok=True)
                    f.unlink(missing_ok=True)
            time.sleep(0.5)

    def sync(self):
        """Long-poll the hub: report the sessions, apply its commands; and for the work bot,
        take over Telegram after 150 s without it, then give it back."""
        b, acks, last_ok, last_sweep, hand_back = self.b, [], time.time(), 0, False
        while True:
            if time.time() - last_sweep > 60:
                last_sweep = time.time()
                sweep((b,))
            payload = {"mode": "router" if self.routing.is_set() else "mirror",
                       "sessions": snapshot(b), "acks": acks,
                       "wait": 0 if self.routing.is_set() else 25}
            if hand_back and b.state.exists():
                payload["state"] = json.loads(b.state.read_text())
            try:
                r = hub(f"/v1/sync?bot={b.bot}", payload)
            except (OSError, ValueError) as e:
                if self.fallback and not self.routing.is_set() and time.time() - last_ok > HUB_GRACE:
                    self.start_router()
                elif not self.routing.is_set():
                    self.unreachable(e)
                time.sleep(10 if self.routing.is_set() else 5)
                continue
            if self.down:
                log(f"{b.bot}: hub reachable again")
            last_ok, self.down = time.time(), False
            if self.routing.is_set():  # stop talking to Telegram before the hub starts
                self.end_router()
                hand_back = True
                continue
            hand_back, acks = False, []
            for c in r.get("cmds", []):
                if c.get("type") == "state" and not self.fallback:
                    continue
                try:
                    apply(b, c)
                except (OSError, ValueError, KeyError) as e:
                    log(f"{b.bot}: could not apply a command: {e}")
                acks.append(c.get("id"))


def hub_tls():
    """The TLS context with this machine's client certificate (https hubs only)."""
    global HUB_TLS
    if CONF["TG_HUB_URL"].startswith("https:") and HUB_TLS is None:
        ctx = ssl.create_default_context(cafile=SYSTEM_CA if os.path.exists(SYSTEM_CA) else None)
        ctx.load_cert_chain(os.path.expanduser(CONF.get("TG_HUB_CERT", "")),
                            os.path.expanduser(CONF.get("TG_HUB_KEY", "")))
        HUB_TLS = ctx


def mirror():
    if not CONF.get("TG_HUB_URL"):
        sys.exit(f"Set TG_HUB_URL (and TG_HUB_CERT, TG_HUB_KEY) in {ENV} first.")
    if router_alive(Box("work")):
        sys.exit("A router or mirror is already running (or stopped less than a minute ago).")
    hub_tls()
    threads = []
    for bot in ("work", "personal"):
        b = Box(bot)
        for d in (b.out, b.answers, b.away, b.inbox, b.sessions):
            d.mkdir(parents=True, exist_ok=True)
        # Only the work bot can fall back, where this machine has its token, and only
        # when it is the mailbox the router code works on.
        link = Link(b, fallback=bot == "work" and bool(CONF.get("TELEGRAM_BOT_TOKEN"))
                    and b.dir == BOX)
        threads += [threading.Thread(target=link.push, daemon=True),
                    threading.Thread(target=link.sync, daemon=True)]
    for t in threads:
        t.start()
    log("mirror up")
    while all(t.is_alive() for t in threads):
        time.sleep(5)
    sys.exit("a mirror thread died")


def chat_id():
    global TOKEN
    TOKEN = config()["TELEGRAM_BOT_TOKEN"]
    print("Now send any message to your bot from your phone...")
    while True:
        for u in api("getUpdates", timeout=50):
            if "message" in u:
                api("getUpdates", offset=u["update_id"] + 1, timeout=0)  # mark it read
                sender = u["message"]["from"]
                print(f"TELEGRAM_CHAT_ID={sender['id']}   (from @{sender.get('username', '?')})")
                return


if __name__ == "__main__":
    cmd, args = (sys.argv[1:2] or [""])[0], sys.argv[2:]
    if cmd == "router":
        router()
    elif cmd == "mirror":
        mirror()
    elif cmd == "hook":
        hook()
    elif cmd == "stop":
        stop()
    elif cmd == "start-wait":
        start_wait()
    elif cmd == "send" and (args[1:] if args[:1] == ["--file"] else args):
        file = args[1] if args[:1] == ["--file"] else None
        send(" ".join(args[2:] if file else args), file)
    elif cmd == "ooo" and args and args[0] in ("on", "off") and len(args) <= 2:
        away_mode(args[0], args[1] if len(args) == 2 else os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    elif cmd in ("session-start", "name-check"):
        session_start()
    elif cmd == "session-end":
        session_end()
    elif cmd == "interrupt":
        interrupt()
    elif cmd == "wake":
        wake()
    elif cmd == "busy":
        busy()
    elif cmd == "chat-id":
        chat_id()
    else:
        sys.exit(__doc__)
