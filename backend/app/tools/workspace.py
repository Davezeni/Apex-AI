"""Workspace protection tool: keep the workspace lean."""

from __future__ import annotations

from typing import Any

from ..workspace.protect import WorkspaceProtection
from .base import Tool, ToolContext, ToolResult


class WorkspaceProtectTool(Tool):
    name = "workspace_protect"
    description = (
        "Protect the workspace by excluding dependency and build artifacts "
        "(node_modules, __pycache__, dist, vendor, target, etc.) from the file "
        "tree and exports. Call to scan and report what can be excluded, or "
        "with action='apply' to write the default .apexignore exclusions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "'scan' (default) to report excluded items; 'apply' to write defaults",
            }
        },
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        protection = WorkspaceProtection(ctx.workspace_root)
        action = args.get("action", "scan")

        if action == "apply":
            written = protection.ensure_defaults()
            summary = "created .apexignore" if written else ".apexignore already exists"
            report = protection.scan()
            content = self._format(report)
            return ToolResult(ok=True, summary=summary, content=content)

        report = protection.scan()
        return ToolResult(
            ok=True,
            summary=(
                f"{report['excluded_bytes'] and protection.human(report['excluded_bytes']) or '0 B'} "
                f"in {len(report['excluded_items'])} excluded item(s)"
            ),
            content=self._format(report),
        )

    @staticmethod
    def _format(report: dict) -> str:
        h = WorkspaceProtection.human
        lines = [
            "Workspace protection report:",
            f"  included: {report['included_files']} file(s), {h(report['included_bytes'])}",
            f"  excluded: {len(report['excluded_items'])} item(s), {h(report['excluded_bytes'])}",
            f"  .apexignore present: {report['has_ignore_file']}",
        ]
        if report["excluded_items"]:
            lines.append("  Excluded items (largest first):")
            for e in report["excluded_items"][:20]:
                lines.append(f"    - {e['path']} ({h(e['size'])})")
        return "\n".join(lines)
