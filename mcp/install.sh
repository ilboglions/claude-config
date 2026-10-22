#!/usr/bin/env bash
# Register the Zotero MCP server (github.com/54yyyu/zotero-mcp) at user scope.
# No credentials are stored in ~/.claude.json: the server command sources
# ~/.config/zotero-mcp.env itself at launch (see mcp/zotero.env.example).
set -euo pipefail

VERSION=0.15.1  # pinned: review a new release before bumping

claude mcp remove --scope user zotero >/dev/null 2>&1 || true
claude mcp add --scope user zotero -- \
  sh -c ". ~/.config/zotero-mcp.env && exec uvx zotero-mcp-server@$VERSION serve"
