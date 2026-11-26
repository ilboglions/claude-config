#!/usr/bin/env python3
"""Away mode: reach Claude Code sessions running in tmux from Telegram (see SKILL.md).

  tg.py router          the only process talking to the bot; run it on the login
                        node that holds your tmux server
  tg.py hook            PermissionRequest hook: while /ooo is on, also ask on Telegram
  tg.py send TEXT       message Matteo from this session
  tg.py ooo on|off SID  turn away mode on or off for one session
  tg.py chat-id         print the id of whoever messages the bot next (setup)

Everything except the router only drops files in ~/.claude/tg, so it works from
any node that shares $HOME with the router, even without internet access.
"""
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BOX = Path.home() / ".claude" / "tg"
OUT, ANSWERS, AWAY = BOX / "out", BOX / "answers", BOX / "away"
STATE, ALIVE = BOX / "state.json", BOX / "router.alive"
ENV = Path.home() / ".config" / "telegram.env"
# Typed in front of every reply, so the session knows where to answer.
PREFIX = '[from Telegram; answer with ~/.claude/skills/ooo/tg.py send "..."] '
TOKEN, CHAT = "", 0


# ---- used by the sessions (hook, send, ooo) ---------------------------------

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


def origin(cwd=None):
    # srun hands the pane's environment to the shell on the job, so TMUX and
    # TMUX_PANE still name the pane on the login node.
    return {"tmux": os.environ.get("TMUX", "").rsplit(",", 1)[0],
            "pane": os.environ.get("TMUX_PANE", ""),
            "cwd": cwd or os.getcwd()}


def hook():
    req = json.load(sys.stdin)
    away = AWAY / req.get("session_id", "none")
    if not away.exists() or not router_alive():
        return  # no output: the terminal prompt alone decides
    rid = secrets.token_hex(4)
    answer = ANSWERS / rid
    inp = req.get("tool_input") or {}
    if "command" in inp:
        title, preview = inp.get("description", ""), inp["command"]
    else:
        title, preview = "", json.dumps(inp, indent=1, ensure_ascii=False)
    drop({"kind": "perm", "id": rid, "tool": req.get("tool_name", "?"), "title": title,
          "preview": preview[:1500], **origin(req.get("cwd"))})
    # The terminal prompt stays open next to this one, and an answer there wins:
    # Claude Code then lets this hook run on and ignores what it prints.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        while away.exists() and router_alive():
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


def send(text):
    drop({"kind": "msg", "text": text, **origin()})
    if not router_alive():
        print("queued, but the router is not running: nothing reaches Telegram until it starts")


def away_mode(state, sid):
    flag = AWAY / sid
    if state == "off":
        flag.unlink(missing_ok=True)
        print("away mode off")
        return
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.touch()
    drop({"kind": "msg", "text": "away mode on. Reply to this message to talk to this session.",
          **origin()})
    print("away mode on" + ("" if router_alive() else
          ", but the router is not running: nothing reaches Telegram until it starts"))


# ---- router -----------------------------------------------------------------

lock = threading.Lock()
state = {"offset": 0, "msgs": {}, "reqs": {}}  # msgs: message id -> session; reqs: open prompts


def log(text):
    print(time.strftime("%H:%M:%S"), text, file=sys.stderr, flush=True)


def config():
    conf = {}
    for line in ENV.read_text().splitlines():
        key, sep, val = line.partition("=")
        if sep and not key.lstrip().startswith("#"):
            conf[key.strip()] = val.strip().strip("'\"")
    return conf


def api(method, **params):
    body = urllib.parse.urlencode({k: v if isinstance(v, (str, int)) else json.dumps(v)
                                   for k, v in params.items()}).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/{method}", body,
                                timeout=70) as r:
        return json.load(r)["result"]


def tmux(*args):
    r = subprocess.run(["tmux", *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def my_tmux():
    return ((tmux("list-sessions", "-F", "#{socket_path},#{pid}") or "").splitlines() or [""])[0]


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


def deliver(item):
    if item["kind"] == "done":  # the hook stopped waiting without a Telegram answer
        req = state["reqs"].pop(item["id"], None)
        if req:
            edit(req["msg"], req["text"] +
                 "\n\n→ expired (answered in the terminal, timed out, or away mode off)")
        return
    item["label"] = item["cwd"].rstrip("/").rsplit("/", 1)[-1]
    if item["pane"] and item["tmux"] == my_tmux():
        item["label"] = tmux("display-message", "-p", "-t", item["pane"], "#S") or item["label"]
    if item["kind"] == "msg":
        m = api("sendMessage", chat_id=CHAT, text=f"[{item['label']}] {item['text']}"[:4000])
    else:
        text = (f"[{item['label']}] {item['tool']}" + (f": {item['title']}" if item["title"] else "")
                + f"\n\n{item['preview']}")[:3900]
        keys = [[{"text": "Yes", "callback_data": f"allow:{item['id']}"},
                 {"text": "No", "callback_data": f"deny:{item['id']}"}]]
        m = api("sendMessage", chat_id=CHAT, text=text, reply_markup={"inline_keyboard": keys})
        state["reqs"][item["id"]] = {"msg": m["message_id"], "text": text}
    state["msgs"][str(m["message_id"])] = {k: item[k] for k in ("tmux", "pane", "label")}


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


def type_into(target, text):
    """Type a reply into a session's pane. Returns why it was not sent, or None."""
    if not target or not target.get("pane"):
        return "Not sent: that session is not in tmux."
    if target["tmux"] != my_tmux():
        return "Not sent: that session's tmux runs on another login node than the router."
    screen = tmux("capture-pane", "-p", "-t", target["pane"])
    if screen is None:
        return "Not sent: that pane is gone."
    # With a dialog open, the Enter at the end would pick one of its options.
    if "Esc to cancel" in screen or re.search(r"❯ \d\.", screen):
        return "Not sent: a dialog is open in that session. Answer it first."
    tmux("send-keys", "-t", target["pane"], "-l", PREFIX + " ".join(text.splitlines()))
    time.sleep(0.3)
    tmux("send-keys", "-t", target["pane"], "Enter")
    return None


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
    if text.strip() == "/list":
        reply("Sessions: " + ", ".join((tmux("list-sessions", "-F", "#S") or "none").split()))
        return
    if text.startswith("/to "):
        _, name, text = (text.split(None, 2) + [""])[:3]
        panes = tmux("list-panes", "-s", "-t", f"={name}", "-F", "#{pane_id}")
        target = {"tmux": my_tmux(), "pane": panes.split()[0], "label": name} if panes else None
    elif m.get("reply_to_message"):
        target = state["msgs"].get(str(m["reply_to_message"]["message_id"]))
    else:
        reply("Reply to a session's message to talk to it, or use /to <session> <text>. "
              "/list shows the sessions.")
        return
    if not text.strip():
        return
    problem = type_into(target, text)
    if problem:
        reply(problem)
    else:
        try:
            api("setMessageReaction", chat_id=CHAT, message_id=m["message_id"],
                reaction=[{"type": "emoji", "emoji": "👍"}])
        except urllib.error.HTTPError:
            reply(f"Sent to {target['label']}.")


def router():
    global TOKEN, CHAT
    conf = config()
    TOKEN, CHAT = conf["TELEGRAM_BOT_TOKEN"], int(conf.get("TELEGRAM_CHAT_ID") or 0)
    if not CHAT:
        sys.exit(f"Set TELEGRAM_CHAT_ID in {ENV} first (tg.py chat-id finds it).")
    if router_alive():
        sys.exit("A router is already running (or stopped less than a minute ago).")
    for d in (OUT, ANSWERS, AWAY):
        d.mkdir(parents=True, exist_ok=True)
    if STATE.exists():
        state.update(json.loads(STATE.read_text()))
    threading.Thread(target=outbox, daemon=True).start()
    log("router up")
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
    elif cmd == "send" and args:
        send(" ".join(args))
    elif cmd == "ooo" and len(args) == 2 and args[0] in ("on", "off"):
        away_mode(*args)
    elif cmd == "chat-id":
        chat_id()
    else:
        sys.exit(__doc__)
