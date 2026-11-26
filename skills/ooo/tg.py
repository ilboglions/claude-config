#!/usr/bin/env python3
"""Away mode: talk to Claude Code sessions from Telegram (see SKILL.md).

  tg.py router          the only process talking to the bot; jsh (mymila) starts
                        it with the anchor job
  tg.py hook            PermissionRequest hook: while /ooo is on, also ask on Telegram
  tg.py stop            Stop hook: while /ooo is on, wait for Matteo's reply
  tg.py send TEXT       message Matteo from this session
  tg.py ooo on|off      turn away mode on or off for this session
  tg.py chat-id         print the id of whoever messages the bot next (setup)

Everything except the router only reads and drops files in ~/.claude/tg, so it
works on any node that shares $HOME with the router, even without internet access.
"""
import json
import os
import secrets
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
STATE, ALIVE = BOX / "state.json", BOX / "router.alive"
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
    write_atomic(OUT / f"{time.time():.6f}-{secrets.token_hex(3)}.json", json.dumps(item))


def origin(sid, cwd=None):
    cwd = cwd or os.getcwd()
    # jsh (mymila) hands the tmux session's name to the shell on the job.
    label = os.environ.get("JSH_SESSION") or os.path.basename(cwd.rstrip("/")) or cwd
    return {"sid": sid, "label": label}


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


def send(text):
    drop({"kind": "msg", "text": text, **origin(os.environ.get("CLAUDE_CODE_SESSION_ID", ""))})
    warn_if_no_router()


def away_mode(state, sid):
    if not sid:
        sys.exit("No session id: pass it, or run this from inside Claude Code.")
    flag = AWAY / sid
    if state == "off":
        flag.unlink(missing_ok=True)
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


def api(method, **params):
    body = urllib.parse.urlencode({k: v if isinstance(v, (str, int)) else json.dumps(v)
                                   for k, v in params.items()}).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/{method}", body,
                                timeout=70, context=TLS) as r:
        return json.load(r)["result"]


def save():
    msgs = state["msgs"]
    while len(msgs) > 500:
        del msgs[next(iter(msgs))]
    write_atomic(STATE, json.dumps(state))


def edit(msg_id, text):
    try:
        api("editMessageText", chat_id=CHAT, message_id=msg_id, text=text)
    except urllib.error.HTTPError:
        pass


def react(msg_id, emoji):
    try:
        api("setMessageReaction", chat_id=CHAT, message_id=msg_id,
            reaction=[{"type": "emoji", "emoji": emoji}])
    except urllib.error.HTTPError:
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
        m = api("sendMessage", chat_id=CHAT, text=f"[{item['label']}] {item['text']}"[:4000])
    else:
        text = (f"[{item['label']}] {item['tool']}" + (f": {item['title']}" if item["title"] else "")
                + f"\n\n{item['preview']}")[:3900]
        keys = [[{"text": "Yes", "callback_data": f"allow:{item['id']}"},
                 {"text": "No", "callback_data": f"deny:{item['id']}"}]]
        m = api("sendMessage", chat_id=CHAT, text=text, reply_markup={"inline_keyboard": keys})
        state["reqs"][item["id"]] = {"msg": m["message_id"], "text": text}
    state["msgs"][str(m["message_id"])] = {"sid": item["sid"], "label": item["label"]}


def outbox():
    while True:
        ALIVE.touch()
        for f in sorted(OUT.glob("*.json")):
            try:
                item = json.loads(f.read_text())
                with lock:
                    deliver(item)
                    save()
            except urllib.error.HTTPError as e:  # Telegram refused it: drop it
                log(f"Telegram refused {f.name}: {e}")
            except OSError as e:  # network trouble: keep it for the next round
                log(f"will retry {f.name}: {e}")
                break
            except (ValueError, KeyError) as e:
                log(f"bad item {f.name}: {e}")
            f.unlink(missing_ok=True)
        time.sleep(1)


def away_sessions():
    found = {}
    for f in AWAY.glob("*"):
        try:
            found[f.name] = json.loads(f.read_text())["label"]
        except (OSError, ValueError, KeyError):
            pass
    return found


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
        reply("Away mode: " + ", ".join(sorted(away.values())) if away
              else "No session is in away mode.")
        return
    if text.startswith("/to "):
        _, name, text = (text.split(None, 2) + [""])[:3]
        sids = [sid for sid, label in away.items() if label == name]
        if len(sids) != 1:
            reply(f"No session called {name} is in away mode (/list shows them)." if not sids else
                  f"Several sessions are called {name}: reply to one of their messages instead.")
            return
        sid = sids[0]
    elif m.get("reply_to_message"):
        sid = state["msgs"].get(str(m["reply_to_message"]["message_id"]), {}).get("sid")
    else:
        reply("Reply to a session's message to talk to it, or use /to <session> <text>. "
              "/list shows the sessions in away mode.")
        return
    if not text.strip():
        return
    if sid not in away:
        reply("Not sent: that session is not in away mode, so nothing would read it.")
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
        api("sendMessage", chat_id=CHAT, text=f"Router up on {where}" + (f" (job {job})" if job else ""))
    except OSError as e:
        log(f"hello message: {e}")
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
    elif cmd == "send" and args:
        send(" ".join(args))
    elif cmd == "ooo" and args and args[0] in ("on", "off") and len(args) <= 2:
        away_mode(args[0], args[1] if len(args) == 2 else os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    elif cmd == "chat-id":
        chat_id()
    else:
        sys.exit(__doc__)
