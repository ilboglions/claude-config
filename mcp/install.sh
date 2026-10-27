#!/usr/bin/env bash
# Register the MCP servers with Claude Code (user scope) and, if installed, Codex:
# Zotero (github.com/54yyyu/zotero-mcp) and the research site (skills/research-site).
# No credentials are stored in either config: the Zotero command sources
# ~/.config/zotero-mcp.env itself at launch (see mcp/zotero.env.example), and the
# research-site server reads ~/.config/research-site.env at each call.
set -euo pipefail

VERSION=0.15.1  # pinned: review a new release before bumping
CMD=". ~/.config/zotero-mcp.env && exec uvx zotero-mcp-server@$VERSION serve"

claude mcp remove --scope user zotero >/dev/null 2>&1 || true
claude mcp add --scope user zotero -- sh -c "$CMD"

if command -v codex >/dev/null; then
  codex mcp remove zotero >/dev/null 2>&1 || true
  # Written by hand because `codex mcp add` cannot set tool approvals: every
  # tool runs without asking except adding papers or files, deletes and bulk edits.
  cat >> ~/.codex/config.toml <<EOF

[mcp_servers.zotero]
command = "sh"
args = ["-c", "$CMD"]
default_tools_approval_mode = "approve"
tools.zotero_delete_item.approval_mode = "prompt"
tools.zotero_delete_collection.approval_mode = "prompt"
tools.zotero_delete_annotation.approval_mode = "prompt"
tools.zotero_batch_update.approval_mode = "prompt"
tools.zotero_add_item.approval_mode = "prompt"
tools.zotero_attach_file.approval_mode = "prompt"
EOF
fi

# The research site: its server runs from this checkout, so re-run after moving it.
# --python overrides a stray .python-version (older uv obeys one even when the script
# needs a newer Python).
SITE="$(cd "$(dirname "$0")/.." && pwd)/skills/research-site/server.py"

claude mcp remove --scope user research-site >/dev/null 2>&1 || true
claude mcp add --scope user research-site -- uv run -q --python '>=3.10' --script "$SITE"

if command -v codex >/dev/null; then
  codex mcp remove research-site >/dev/null 2>&1 || true
  # Every tool runs without asking: the token cannot delete, and sharing stays on the site.
  cat >> ~/.codex/config.toml <<EOF

[mcp_servers.research-site]
command = "uv"
args = ["run", "-q", "--python", ">=3.10", "--script", "$SITE"]
default_tools_approval_mode = "approve"
EOF
fi
