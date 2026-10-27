"""Client for the research site's API, shared by the command line (site.py) and the MCP
server (server.py). Standard library only.

Settings come from the environment, or from ~/.config/research-site.env (chmod 600):

    RESEARCH_SITE_URL=https://research.example.org
    RESEARCH_SITE_TOKEN=rs_...

A <project> is its slug; section ids come from projects(). Every function returns the
API's JSON, with the site's own links made absolute, and raises SiteError on failure.
"""
import json
import os
import ssl
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV_FILE = Path.home() / ".config" / "research-site.env"
ENTRY_KINDS = ("meetings", "results")


class SiteError(Exception):
    """Missing settings, an unreachable site, or the API's own error message."""


def settings():
    values = {}
    if ENV_FILE.exists():
        if ENV_FILE.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            print(f"warning: {ENV_FILE} is readable by others; chmod 600 it", file=sys.stderr)
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("'\"")
    url = os.environ.get("RESEARCH_SITE_URL") or values.get("RESEARCH_SITE_URL")
    token = os.environ.get("RESEARCH_SITE_TOKEN") or values.get("RESEARCH_SITE_TOKEN")
    if not url or not token:
        raise SiteError(f"Set RESEARCH_SITE_URL and RESEARCH_SITE_TOKEN (environment or {ENV_FILE}).")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" and parts.hostname not in ("localhost", "127.0.0.1"):
        raise SiteError("RESEARCH_SITE_URL must be https:// (the token would travel in the clear).")
    return url.rstrip("/"), token


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """A redirect would carry the token to wherever it points: stop instead."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, f"redirected to {newurl}; not followed",
                                     headers, fp)


def _tls():
    """Some Pythons (cluster modules, say) have an OpenSSL that looks for certificates in a
    place that does not exist, and so trust no site: use the system's bundle instead."""
    context = ssl.create_default_context()
    paths = ssl.get_default_verify_paths()
    if not (paths.cafile or paths.capath):
        for bundle in ("/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt", "/etc/ssl/cert.pem"):
            if os.path.exists(bundle):
                context.load_verify_locations(bundle)
                break
    return context


_opener = urllib.request.build_opener(_NoRedirects, urllib.request.HTTPSHandler(context=_tls()))


def api(method, path, payload=None):
    url, token = settings()
    request = urllib.request.Request(
        f"{url}/api/v1{path}", method=method,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "research-site client"})
    try:
        with _opener.open(request, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            message = json.loads(e.read()).get("error") or e.reason
        except ValueError:
            message = e.reason
        raise SiteError(f"{e.code}: {message}") from None
    except urllib.error.URLError as e:
        raise SiteError(f"Cannot reach the site: {e.reason}") from None


def site_url(path):
    return settings()[0] + path


def _project(slug):
    return "/projects/" + urllib.parse.quote(str(slug), safe="")


def _kind(kind):
    if kind not in ENTRY_KINDS:
        raise SiteError("kind is meetings or results.")
    return kind


def _linked(out):
    if "url" in out:
        out["url"] = site_url(out["url"])
    return out


def _given(**fields):
    return {k: v for k, v in fields.items() if v is not None}


# ---------------------------------------------------------------- reading

def projects():
    return api("GET", "/projects")["projects"]


def items(project, section):
    return api("GET", f"{_project(project)}/sections/{int(section)}/items")


def read_page(project, section):
    return api("GET", f"{_project(project)}/sections/{int(section)}/page")


def entries(project, kind, limit=20):
    return api("GET", f"{_project(project)}/{_kind(kind)}?limit={int(limit)}")["entries"]


# ---------------------------------------------------------------- writing

def add_meeting(project, title, body="", date=""):
    return _linked(api("POST", f"{_project(project)}/meetings", {"title": title, "date": date, "body": body}))


def add_result(project, title, body="", date="", url="", ref=""):
    return _linked(api("POST", f"{_project(project)}/results",
                       {"title": title, "date": date, "body": body, "url": url, "ref": ref}))


def change_entry(project, kind, entry_id, title=None, body=None, date=None, url=None):
    return _linked(api("PATCH", f"{_project(project)}/{_kind(kind)}/{int(entry_id)}",
                       _given(title=title, body=body, date=date, url=url)))


def add_item(project, section, title, date="", body="", status=""):
    return _linked(api("POST", f"{_project(project)}/sections/{int(section)}/items",
                       {"title": title, "date": date, "body": body, "status": status}))


def change_item(project, section, item_id, title=None, date=None, body=None, status=None):
    return _linked(api("PATCH", f"{_project(project)}/sections/{int(section)}/items/{int(item_id)}",
                       _given(title=title, date=date, body=body, status=status)))


def add_paper(project, section, link, title="", authors=(), year="", venue=""):
    return _linked(api("POST", f"{_project(project)}/sections/{int(section)}/papers",
                       {"link": link, "title": title, "authors": list(authors), "year": year, "venue": venue}))


def write_page(project, section, body):
    return _linked(api("PUT", f"{_project(project)}/sections/{int(section)}/page", {"body": body}))


def add_link(project, label, url, kind=""):
    return api("POST", f"{_project(project)}/links", {"label": label, "url": url, "kind": kind})
