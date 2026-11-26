#!/usr/bin/env python3
"""Away mode: talk to Claude Code sessions from Telegram (see SKILL.md).

  tg.py router          the only process talking to the bot; jsh (mymila) starts
                        it with the anchor job
  tg.py hook            PermissionRequest hook: while /ooo is on, also ask on Telegram
  tg.py stop            Stop hook: while /ooo is on, wait for Matteo's reply
  tg.py send TEXT       message Matteo from this session
  tg.py send --file PATH [TEXT]
                        send him a file: images as photos, anything else as a document
  tg.py ooo on|off      turn away mode on or off for this session
  tg.py name-check      SessionStart hook: ask once for the project's Telegram name
  tg.py chat-id         print the id of whoever messages the bot next (setup)

Everything except the router only reads and drops files in ~/.claude/tg, so it
works on any node that shares $HOME with the router, even without internet access.
"""
import html
import json
import os
import re
import secrets
import shutil
import signal
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BOX = Path.home() / ".claude" / "tg"
OUT, ANSWERS, AWAY, INBOX = BOX / "out", BOX / "answers", BOX / "away", BOX / "inbox"
WAITING = BOX / "waiting"  # per session: the token of its newest stop-hook waiter
FILES = BOX / "files"  # copies of files to send, where the router can read them
STATE, ALIVE = BOX / "state.json", BOX / "router.alive"
PHOTO_TYPES = {".png", ".jpg", ".jpeg", ".webp"}
MAX_PHOTO, MAX_FILE = 10 << 20, 50 << 20  # what Telegram accepts from bots
ENV = Path.home() / ".config" / "telegram.env"
TOKEN, CHAT = "", 0


# ---- used by the sessions (hooks, send, ooo) --------------------------------

def router_alive():
    try:
        return time.time() - ALIVE.stat().st_mtime < 60
    except FileNotFoundError:
        return False


def write_atomic(path, text):
    """Write then rename, so a reader on another node never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{secrets.token_hex(6)}"
    tmp.write_text(text)
    tmp.rename(path)


def drop(item):
    path = OUT / f"{time.time():.6f}-{secrets.token_hex(3)}.json"
    write_atomic(path, json.dumps(item))
    return path


def origin(sid, cwd=None):
    cwd = cwd or os.getcwd()
    # jsh (mymila) hands the tmux session's name to the shell on the job.
    short = os.environ.get("JSH_SESSION") or os.path.basename(cwd.rstrip("/")) or cwd
    # The project's own name, from env.TG_NAME in its .claude/settings.local.json.
    return {"sid": sid, "label": os.environ.get("TG_NAME") or short, "short": short}


def name_check():
    """SessionStart hook: in a git project with no TG_NAME yet, have Claude ask for one."""
    req = json.load(sys.stdin)
    cwd = Path(req.get("cwd") or os.getcwd())
    if "TG_NAME" in os.environ or not ENV.exists():  # answered already, or no Telegram here
        return
    if not any((d / ".git").exists() for d in (cwd, *cwd.parents)):
        return
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext":
        "This project has no name yet for Matteo's Telegram away mode (/ooo). In your first "
        "reply, ask him in one short line whether he wants to give it one: emojis are welcome "
        "(for example \"🟦 Multi-agent detection\"), or no name. Write his answer as env.TG_NAME "
        f"in {cwd}/.claude/settings.local.json, keeping whatever else that file holds. If he "
        "says no, write an empty string: it means don't ask again, and Telegram keeps showing "
        "the session's name."}}))


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


def stop():
    req = json.load(sys.stdin)
    sid = req.get("session_id", "none")
    away, inbox, mark = AWAY / sid, INBOX / sid, WAITING / sid
    if not away.exists():
        return
    # This runs in the background (asyncRewake in settings.json): the session goes
    # idle as usual, and exit code 2 wakes it with what this prints on stderr.
    # Every turn's end starts a waiter; the newest one wins and older ones leave.
    me = secrets.token_hex(4)
    write_atomic(mark, me)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while away.exists() and read(mark) == me:
        texts = []
        for f in sorted(inbox.glob("*.json")):
            claimed = f.with_suffix(f".{me}")
            try:
                f.rename(claimed)  # atomic: a reply goes to one waiter only
            except FileNotFoundError:
                continue
            item = json.loads(claimed.read_text())
            claimed.unlink()
            texts.append(item["text"])
            drop({"kind": "delivered", "msg": item["msg"]})
        if texts:
            print("Matteo replied on Telegram:\n\n" + "\n\n".join(texts)
                  + '\n\nAnswer him with ~/.claude/skills/ooo/tg.py send "..."', file=sys.stderr)
            sys.exit(2)
        time.sleep(2)


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
    for _ in range(30 if file else 10):  # the router deletes it once Telegram has it
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
    info = origin(sid)
    write_atomic(flag, json.dumps(info))
    drop({"kind": "msg", "text": "away mode on. Reply to this message to talk to this session.",
          **info})
    print("away mode on")
    warn_if_no_router()


# ---- router -----------------------------------------------------------------

lock = threading.Lock()
state = {"offset": 0, "msgs": {}, "reqs": {}}  # msgs: message id -> session; reqs: open prompts


def log(text):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), text, file=sys.stderr, flush=True)


def config():
    conf = {}
    for line in ENV.read_text().splitlines():
        key, sep, val = line.partition("=")
        if sep and not key.lstrip().startswith("#"):
            conf[key.strip()] = val.strip().strip("'\"")
    return conf


# Mila's python/3.10 module ships a CA bundle that cannot verify Telegram's
# certificate chain; the system bundle can.
SYSTEM_CA = "/etc/ssl/certs/ca-certificates.crt"
TLS = ssl.create_default_context(cafile=SYSTEM_CA if os.path.exists(SYSTEM_CA) else None)


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
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", body, headers)
    try:
        with urllib.request.urlopen(req, timeout=70, context=TLS) as r:
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


def head(label):  # the session's name, in bold, on its own line
    return f"<b>{html.escape(label, quote=False)}</b>"


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
        m = send_html("sendMessage", "text", f"{head(item['label'])}\n{fmt(item['text'][:3800])}",
                      chat_id=CHAT)
    elif kind == "file":
        path, m = Path(item["path"]), None
        caption = head(item["label"]) + (f"\n{fmt(item['text'][:900])}" if item["text"].strip() else "")
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
        text = (f"{head(item['label'])}\n<b>{esc(item['tool'])}</b>"
                + (f": {esc(item['title'][:300])}" if item["title"] else "")
                + f"\n<pre>{esc(item['preview'])}</pre>")
        keys = [[{"text": "Yes", "callback_data": f"allow:{item['id']}"},
                 {"text": "No", "callback_data": f"deny:{item['id']}"}]]
        m = send_html("sendMessage", "text", text, chat_id=CHAT,
                      reply_markup={"inline_keyboard": keys})
        state["reqs"][item["id"]] = {"msg": m["message_id"], "text": text}
    state["msgs"][str(m["message_id"])] = {"sid": item["sid"], "label": item["label"]}


def outbox():
    while True:
        ALIVE.touch()
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


def handle(u):
    q = u.get("callback_query")
    if q:  # a Yes/No tap
        if q["from"]["id"] != CHAT:
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
    if text.strip() == "/list":
        names = sorted(i["label"] + (f" ({i['short']})" if i["short"] != i["label"] else "")
                       for i in away.values())
        reply("Away mode:\n" + "\n".join(f"- {n}" for n in names) if away
              else "No session is in away mode.")
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
        if len(sids) > 1:
            reply("Several sessions match that name: reply to one of their messages instead.")
            return
        text = text[re.match(r"/to\s+" + r"\s+".join(map(re.escape, words[:n])) + r"\s*", text).end():]
        target = {"sid": sids[0], "label": away[sids[0]]["label"]}
    elif str(m.get("reply_to_message", {}).get("message_id")) in state["msgs"]:
        target = state["msgs"][str(m["reply_to_message"]["message_id"])]
    elif state["msgs"]:  # replies to nothing, or to a router notice: for the session that wrote last
        target = state["msgs"][next(reversed(state["msgs"]))]
    else:
        reply("No session has written yet. Use /to <session> <text>; "
              "/list shows the sessions in away mode.")
        return
    if not text.strip():
        return
    sid = target["sid"]
    if sid not in away:
        reply(f"Not sent: {target['label']} is not in away mode, so nothing would read it.")
        return
    write_atomic(INBOX / sid / f"{time.time():.6f}.json",
                 json.dumps({"text": text, "msg": m["message_id"]}))
    react(m["message_id"], "👀")  # queued; 👍 once the session picks it up


def router():
    global TOKEN, CHAT
    conf = config()
    TOKEN, CHAT = conf["TELEGRAM_BOT_TOKEN"], int(conf.get("TELEGRAM_CHAT_ID") or 0)
    if not CHAT:
        sys.exit(f"Set TELEGRAM_CHAT_ID in {ENV} first (tg.py chat-id finds it).")
    if router_alive():
        sys.exit("A router is already running (or stopped less than a minute ago).")
    for d in (OUT, ANSWERS, AWAY, INBOX):
        d.mkdir(parents=True, exist_ok=True)
    if STATE.exists():
        state.update(json.loads(STATE.read_text()))
    ALIVE.touch()
    threading.Thread(target=outbox, daemon=True).start()
    where = socket.gethostname().split(".")[0]
    job = os.environ.get("SLURM_JOB_ID")
    log(f"router up on {where}" + (f", job {job}" if job else ""))
    try:
        # Telegram suggests only the commands a bot registers.
        api("setMyCommands", commands=[
            {"command": "list", "description": "Sessions in away mode"},
            {"command": "to", "description": "Message a session by name: /to <name> <text>"}])
        api("sendMessage", chat_id=CHAT, text=f"Router up on {where}" + (f" (job {job})" if job else ""))
    except OSError as e:
        log(f"startup messages: {e}")
    while True:
        try:
            updates = api("getUpdates", offset=state["offset"], timeout=50,
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
    elif cmd == "hook":
        hook()
    elif cmd == "stop":
        stop()
    elif cmd == "send" and (args[1:] if args[:1] == ["--file"] else args):
        file = args[1] if args[:1] == ["--file"] else None
        send(" ".join(args[2:] if file else args), file)
    elif cmd == "ooo" and args and args[0] in ("on", "off") and len(args) <= 2:
        away_mode(args[0], args[1] if len(args) == 2 else os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    elif cmd == "name-check":
        name_check()
    elif cmd == "chat-id":
        chat_id()
    else:
        sys.exit(__doc__)
