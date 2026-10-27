#!/usr/bin/env python3
"""Command-line client for the research site's API (client.py does the talking).
Standard library only, except `wandb-sync`, which needs the wandb package (and a W&B
login) where it runs. Settings: see client.py.

Commands (a <project> is its slug; section ids come from `projects`; <kind> is
meetings or results):

    site.py projects
    site.py items      <project> <section>
    site.py read-page  <project> <section>
    site.py entries    <project> <kind> [--limit N]
    site.py meeting    <project> --title T [--date YYYY-MM-DD] [--body TEXT | --body-file F]
    site.py result     <project> --title T [--date D] [--url U] [--ref R] [--body ... | --body-file F]
    site.py edit-entry <project> <kind> <id> [--title T] [--date D] [--url U] [--body ... | --body-file F]
    site.py item       <project> <section> --title T [--date D] [--status S] [--body ... | --body-file F]
    site.py edit-item  <project> <section> <item> [--title T] [--date D] [--status S] [--tags "a, b"]
                       [--body ... | --body-file F]
    site.py status     <project> <section> <item> <status>
    site.py paper      <project> <section> <link | - for BibTeX on stdin> [--tags "a, b"]
                       [--title T --authors "A; B" --year Y --venue V]
    site.py page       <project> <section> (--body TEXT | --body-file F)
    site.py link       <project> --label L --url U [--kind K]
    site.py wandb-sync <project> <entity/wandb-project> [--metrics a,b] [--config k,l]
                       [--tag T] [--limit N] [--dry-run]

--body-file - reads the text from standard input.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client  # noqa: E402


def body_of(args, default=""):
    if getattr(args, "body_file", None):
        return sys.stdin.read() if args.body_file == "-" else Path(args.body_file).read_text()
    body = getattr(args, "body", None)
    return default if body is None else body


def tags_of(text):
    return None if text is None else [t.strip() for t in text.split(",") if t.strip()]


# ---------------------------------------------------------------- W&B

def fmt(value):
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def run_body(run, metrics, config_keys):
    summary = {k: v for k, v in dict(run.summary).items() if not k.startswith("_")}
    if metrics:
        keys = [k for k in metrics if k in summary]
    else:
        keys = sorted(k for k, v in summary.items()
                      if isinstance(v, (int, float)) and not isinstance(v, bool))[:12]
    lines = []
    if keys:
        lines += ["| metric | value |", "|---|---|"] + [f"| {k} | {fmt(summary[k])} |" for k in keys]
    config = {k: run.config[k] for k in config_keys if k in run.config}
    if config:
        lines += ["", "Config: " + ", ".join(f"{k} = {fmt(v)}" for k, v in config.items())]
    if run.tags:
        lines += ["", "Tags: " + ", ".join(run.tags)]
    return "\n".join(lines)


def wandb_sync(args):
    import wandb  # only this command needs it

    filters = {"state": "finished"}
    if args.tag:
        filters["tags"] = {"$in": [args.tag]}
    runs = wandb.Api().runs(args.wandb, filters=filters, order="-created_at")
    metrics = [m for m in (args.metrics or "").split(",") if m]
    config_keys = [k for k in (args.config or "").split(",") if k]
    created = updated = 0
    for i, run in enumerate(runs):
        if i >= args.limit:
            break
        payload = {"title": run.name, "date": str(run.created_at)[:10], "url": run.url,
                   "ref": "wandb:" + "/".join(run.path), "body": run_body(run, metrics, config_keys)}
        if args.dry_run:
            print(json.dumps(payload, indent=2))
            continue
        result = client.add_result(args.project, **payload)
        created += result["created"]
        updated += not result["created"]
    if not args.dry_run:
        print(f"{created} new results, {updated} updated, on "
              f"{client.site_url('/p/' + args.project + '/results')}")


# ---------------------------------------------------------------- commands

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def with_body(p, default=""):
        group = p.add_mutually_exclusive_group()
        group.add_argument("--body", default=default)
        group.add_argument("--body-file")
        return p

    sub.add_parser("projects")
    p = sub.add_parser("items"); p.add_argument("project"); p.add_argument("section", type=int)
    p = sub.add_parser("read-page"); p.add_argument("project"); p.add_argument("section", type=int)
    p = sub.add_parser("entries"); p.add_argument("project"); p.add_argument("kind", choices=client.ENTRY_KINDS)
    p.add_argument("--limit", type=int, default=20)
    p = with_body(sub.add_parser("meeting")); p.add_argument("project"); p.add_argument("--title", required=True); p.add_argument("--date", default="")
    p = with_body(sub.add_parser("result")); p.add_argument("project"); p.add_argument("--title", required=True)
    p.add_argument("--date", default=""); p.add_argument("--url", default=""); p.add_argument("--ref", default="")
    p = with_body(sub.add_parser("edit-entry"), None); p.add_argument("project"); p.add_argument("kind", choices=client.ENTRY_KINDS)
    p.add_argument("id", type=int); p.add_argument("--title"); p.add_argument("--date"); p.add_argument("--url")
    p = with_body(sub.add_parser("item")); p.add_argument("project"); p.add_argument("section", type=int)
    p.add_argument("--title", required=True); p.add_argument("--date", default=""); p.add_argument("--status", default="")
    p = with_body(sub.add_parser("edit-item"), None); p.add_argument("project"); p.add_argument("section", type=int)
    p.add_argument("item", type=int); p.add_argument("--title"); p.add_argument("--date"); p.add_argument("--status")
    p.add_argument("--tags")
    p = sub.add_parser("status"); p.add_argument("project"); p.add_argument("section", type=int)
    p.add_argument("item", type=int); p.add_argument("value")
    p = sub.add_parser("paper"); p.add_argument("project"); p.add_argument("section", type=int); p.add_argument("link")
    p.add_argument("--title", default=""); p.add_argument("--authors", default=""); p.add_argument("--year", default="")
    p.add_argument("--venue", default=""); p.add_argument("--tags", default="")
    p = with_body(sub.add_parser("page")); p.add_argument("project"); p.add_argument("section", type=int)
    p = sub.add_parser("link"); p.add_argument("project"); p.add_argument("--label", required=True)
    p.add_argument("--url", required=True); p.add_argument("--kind", default="")
    p = sub.add_parser("wandb-sync"); p.add_argument("project"); p.add_argument("wandb", help="entity/project")
    p.add_argument("--metrics"); p.add_argument("--config"); p.add_argument("--tag")
    p.add_argument("--limit", type=int, default=50); p.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    c = args.command
    if c == "projects":
        for project in client.projects():
            print(f"{project['slug']}\t{project['name']}")
            for s in project["sections"]:
                print(f"    {s['id']}\t{s['kind']}\t{s['title']}")
    elif c == "items":
        data = client.items(args.project, args.section)
        print(f"statuses: {', '.join(data['statuses']) or '-'}")
        for item in data["items"]:
            print(f"{item['id']}\t{item['status'] or '-'}\t{item['date'] or '-'}\t{item['title']}")
    elif c == "read-page":
        print(client.read_page(args.project, args.section)["body"])
    elif c == "entries":
        for e in client.entries(args.project, args.kind, args.limit):
            print(f"{e['id']}\t{e['date']}\t{e['title']}")
    elif c == "wandb-sync":
        wandb_sync(args)
    else:
        if c == "meeting":
            out = client.add_meeting(args.project, args.title, body_of(args), args.date)
        elif c == "result":
            out = client.add_result(args.project, args.title, body_of(args), args.date, args.url, args.ref)
        elif c == "edit-entry":
            out = client.change_entry(args.project, args.kind, args.id, args.title, body_of(args, None),
                                      args.date, args.url)
        elif c == "item":
            out = client.add_item(args.project, args.section, args.title, args.date, body_of(args), args.status)
        elif c == "edit-item":
            out = client.change_item(args.project, args.section, args.item, args.title, args.date,
                                     body_of(args, None), args.status, tags_of(args.tags))
        elif c == "status":
            out = client.change_item(args.project, args.section, args.item, status=args.value)
        elif c == "paper":
            out = client.add_paper(args.project, args.section, sys.stdin.read() if args.link == "-" else args.link,
                                   args.title, [a.strip() for a in args.authors.split(";") if a.strip()],
                                   args.year, args.venue, tags_of(args.tags) or ())
        elif c == "page":
            out = client.write_page(args.project, args.section, body_of(args))
        else:
            out = client.add_link(args.project, args.label, args.url, args.kind)
        if "added" in out:
            print(f"{out['added']} added, {out['updated']} updated, {out['unchanged']} already there")
        print(out.get("url", "done"))


if __name__ == "__main__":
    try:
        main()
    except client.SiteError as e:
        sys.exit(str(e))
