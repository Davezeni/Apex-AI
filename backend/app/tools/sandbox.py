"""Sandbox tool: run a command in the isolated execution environment."""

from __future__ import annotations

from typing import Any

from .base import Tool, ToolContext, ToolResult


class SandboxStatusTool(Tool):
    name = "sandbox_status"
    description = (
        "Report the sandbox (isolated execution environment) status: which "
        "backend is configured and whether it is available, and list any "
        "listening ports. Use to check where generated code can run."
    )
    parameters = {"type": "object", "properties": {}}

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        del args
        if ctx.sandbox is None:
            return ToolResult(
                ok=False,
                summary="no sandbox configured",
                content="No sandbox backend is configured.",
            )

        available = await ctx.sandbox.available()
        name = getattr(ctx.sandbox, "name", "unknown")

        ports = ""
        if available:
            ports_result = await ctx.sandbox.run_command(
                "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo '(port tools unavailable)'",
                timeout=20.0,
            )
            ports = ports_result.stdout

        content = (
            f"Sandbox backend: {name}\n"
            f"Available: {available}\n"
            f"Listening ports:\n{ports or '(none reported)'}"
        )
        return ToolResult(
            ok=available,
            summary=f"sandbox {name} available={available}",
            content=content,
            detail={"backend": name, "available": available, "ports": ports},
        )


class RunCommandTool(Tool):
    name = "run_command"
    description = (
        "Run a shell command in the isolated sandbox and return exit code, "
        "stdout, and stderr. Use to build, test, or run generated code."
    )
    parameters = {
        "type": "object",
        "properties": {
            "cmd": {"type": "string", "description": "The shell command to run"},
            "cwd": {"type": "string", "description": "Working dir inside the workspace (optional)"},
        },
        "required": ["cmd"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        if ctx.sandbox is None:
            return ToolResult(
                ok=False,
                summary="no sandbox configured",
                content="Sandbox is not configured. Configure Docker or Codespaces first.",
            )
        cmd = args.get("cmd")
        if not isinstance(cmd, str) or not cmd.strip():
            return ToolResult(ok=False, summary="cmd must be a non-empty string")

        cwd = args.get("cwd") or ""
        if not isinstance(cwd, str):
            cwd = ""

        try:
            result = await ctx.sandbox.run_command(cmd, cwd=cwd)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"sandbox error: {exc}")

        content = f"exit_code={result.exit_code}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        return ToolResult(
            ok=result.ok,
            summary=f"exit {result.exit_code}",
            content=content,
            detail={
                "exit_code": result.exit_code,
                "command": cmd,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
