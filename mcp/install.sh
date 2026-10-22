#!/usr/bin/env bash
# Register the Zotero MCP server (github.com/54yyyu/zotero-mcp) with Claude Code
# (user scope) and, if installed, Codex. No credentials are stored in either
# config: the server command sources ~/.config/zotero-mcp.env itself at launch
# (see mcp/zotero.env.example).
set -euo pipefail

VERSION=0.15.1  # pinned: review a new release before bumping
CMD=". ~/.config/zotero-mcp.env && exec uvx zotero-mcp-server@$VERSION serve"

claude mcp remove --scope user zotero >/dev/null 2>&1 || true
claude mcp add --scope user zotero -- sh -c "$CMD"

if command -v codex >/dev/null; then
  codex mcp remove zotero >/dev/null 2>&1 || true
  codex mcp add zotero -- sh -c "$CMD"
fi
