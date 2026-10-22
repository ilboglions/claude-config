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
