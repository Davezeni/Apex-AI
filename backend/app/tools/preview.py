"""Preview tool: expose the built app at a preview URL."""

from __future__ import annotations

from typing import Any

from .base import Tool, ToolContext, ToolResult


class PreviewTool(Tool):
    name = "start_preview"
    description = (
        "Expose the built app at a preview URL. For a static site (has an "
        "index.html), pass mode='static' (works everywhere). For a dev server, "
        "pass mode='server' with the command and port (needs a sandbox). The "
        "preview URL is available at /preview/."
    )
    parameters = {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "description": "static | server"},
            "command": {"type": "string", "description": "server start command (server mode)"},
            "port": {"type": "integer", "description": "server port (server mode)"},
        },
        "required": ["mode"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        mode = args.get("mode", "static")
        if mode == "server":
            if ctx.sandbox is None:
                return ToolResult(ok=False, summary="sandbox not available", content="Server preview needs a sandbox (Docker/Codespaces).")
            command = args.get("command")
            port = args.get("port")
            if not isinstance(command, str) or not isinstance(port, int):
                return ToolResult(ok=False, summary="server mode needs command and port")
            try:
                await ctx.sandbox.run_server(command, port)
                url = await ctx.sandbox.server_url(port)
            except Exception as exc:  # noqa: BLE001
                return ToolResult(ok=False, summary=f"server start failed: {exc}")
            return ToolResult(
                ok=True,
                summary=f"server started on port {port}",
                content=f"Preview URL: /preview/ (proxy to {url})",
            )

        # Static mode: confirm an index.html exists.
        entry = ctx.workspace_root / "index.html"
        if not entry.exists():
            return ToolResult(
                ok=False,
                summary="no index.html found",
                content="Create an index.html (or another static entry) first, then preview will serve it at /preview/.",
            )
        return ToolResult(
            ok=True,
            summary="static preview ready",
            content="Preview URL: /preview/ (serves the workspace index.html)",
        )
