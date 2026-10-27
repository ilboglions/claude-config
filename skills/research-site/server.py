# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp==2.3.0"]
# ///
"""MCP server (stdio) for the research site: the API of client.py as typed tools, for
Claude Code and Codex. mcp/install.sh registers it as `uv run --script <this file>`.
The token is read from the environment or ~/.config/research-site.env at each call, so
no agent config ever holds it."""
import functools
import inspect
import sys
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client  # noqa: E402

WRITING = ("Before calling, draft every piece of prose you send (bodies, notes, page text) with the "
           "matteo-writing skill, then pass it through the smart-rephrasing skill (Claude Code: "
           "/matteo-writing, /smart-rephrasing; Codex: $matteo-writing, $smart-rephrasing). "
           "Markdown; raw HTML and images are not rendered.")

server = MCPServer("research-site", instructions=f"""\
The owner's research site: one dashboard per project, with meeting notes, results, list
sections (roadmap, checklist, deadlines, ideas, questions, decisions), literature and
pages. Everyone the project is shared with reads what is written here, and nothing can be
deleted through these tools.

- Call list_projects first and take the project slug and section ids from it; never guess them.
- Write what the user tells you, where they say, without asking for confirmation. Ask
  only when the target is ambiguous.
- {WRITING}
- To change existing text, read it first (read_page, list_items, list_entries), then send
  the whole new version.
- Report the link each write returns.""")

Kind = Literal["meetings", "results"]


def tool(read_only=False, overwrites=False, prose=False):
    """Registers a tool whose API errors reach the agent as messages, not as a crash. A tool
    that takes prose carries the writing rule in its description too: some clients show
    tool descriptions but not the server's instructions."""
    def register(fn):
        description = inspect.cleandoc(fn.__doc__) + (" " + WRITING if prose else "")
        @functools.wraps(fn)
        def run(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except client.SiteError as e:
                raise ToolError(str(e)) from None
        annotations = ToolAnnotations(read_only_hint=read_only, destructive_hint=overwrites,
                                      open_world_hint=False)
        return server.tool(description=description, annotations=annotations)(run)
    return register


# ---------------------------------------------------------------- reading

@tool(read_only=True)
def list_projects() -> dict:
    """The projects this machine's token reaches: slug, name, description, and each section's
    id, kind and title."""
    return {"projects": client.projects()}


@tool(read_only=True)
def list_items(project: str, section: int) -> dict:
    """Items of a list, literature or log section (id, title, date, status, link, text), with
    the statuses the section allows; papers come with their tags, log entries with their
    author and the time they were written."""
    return client.items(project, section)


@tool(read_only=True)
def read_page(project: str, section: int) -> dict:
    """The markdown of a page section."""
    return client.read_page(project, section)


@tool(read_only=True)
def list_entries(project: str, kind: Kind, limit: int = 20) -> dict:
    """Meeting notes or results of a project, newest first, with their text."""
    return {"entries": client.entries(project, kind, limit)}


# ---------------------------------------------------------------- writing

@tool(prose=True)
def add_meeting_note(project: str, title: str, body: str, date: str = "") -> dict:
    """Adds a meeting note (date YYYY-MM-DD, today if empty)."""
    return client.add_meeting(project, title, body, date)


@tool(prose=True)
def add_result(project: str, title: str, body: str = "", date: str = "", url: str = "",
               ref: str = "") -> dict:
    """Adds a result, with an optional link (a W&B run, a figure). `ref` is your own id for
    it: sending the same ref again updates that result instead of adding one."""
    return client.add_result(project, title, body, date, url, ref)


@tool(overwrites=True, prose=True)
def update_entry(project: str, kind: Kind, entry_id: int, title: str | None = None,
                 body: str | None = None, date: str | None = None, url: str | None = None) -> dict:
    """Changes a meeting note or result; fields left out stay as they are. A new body
    replaces the old one: read it first with list_entries."""
    return client.change_entry(project, kind, entry_id, title, body, date, url)


@tool(prose=True)
def add_item(project: str, section: int, title: str, date: str = "", body: str = "",
             status: str = "") -> dict:
    """Adds an item to a roadmap, checklist, deadlines, ideas, questions or decisions
    section (not literature: add_paper; not a log, which people write in on the site).
    Status must be one the section allows (list_items shows them); empty means the first."""
    return client.add_item(project, section, title, date, body, status)


@tool(overwrites=True, prose=True)
def update_item(project: str, section: int, item_id: int, title: str | None = None,
                date: str | None = None, body: str | None = None, status: str | None = None,
                tags: list[str] | None = None) -> dict:
    """Changes an item, or moves it along (roadmap: planned/doing/done; checklist:
    todo/done; ideas: open/keep/drop; questions: open/answered; literature:
    unread/reading/read). Fields left out stay as they are; a new body replaces the old
    one, and new tags (papers only) replace the old ones."""
    return client.change_item(project, section, item_id, title, date, body, status, tags)


@tool()
def add_paper(project: str, section: int, link: str, title: str = "", authors: list[str] = [],
              year: str = "", venue: str = "", tags: list[str] = []) -> dict:
    """Adds a paper to a literature section, with optional tags. link is the paper's link
    (arXiv, DOI and ACL Anthology links are looked up; for any other link give title, and
    authors, year, venue), or BibTeX, one entry or more (from Zotero, a venue's page):
    BibTeX needs no lookup, links the venue's page and PDF, and a paper already there under
    the same link or title (its preprint) takes the venue's details and the tags."""
    return client.add_paper(project, section, link, title, authors, year, venue, tags)


@tool(overwrites=True, prose=True)
def write_page(project: str, section: int, body: str) -> dict:
    """Replaces the whole markdown of a page section: read it first with read_page and send
    the full new version."""
    return client.write_page(project, section, body)


@tool()
def add_link(project: str, label: str, url: str, kind: str = "") -> dict:
    """Adds a link (http or https) to the project's links bar; kind is an optional short tag
    such as overleaf, drive, wandb or github."""
    return client.add_link(project, label, url, kind)


if __name__ == "__main__":
    server.run("stdio")
