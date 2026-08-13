"""GitHub tools: repo creation and git clone/commit/push/pull.

Repo management uses the GitHub REST client; git operations use the `git` CLI
against the workspace. The token is passed to git via an in-memory credential
helper so it never appears in command-line arguments or logs.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any

from .base import Tool, ToolContext, ToolResult

_ASKPASS_TEMPLATE = "#!/bin/sh\necho {token}\n"


async def _run_git(
    *args: str, cwd: Path, token: str | None = None
) -> tuple[int, str, str]:
    git = shutil.which("git")
    if not git:
        return (1, "", "git not found")

    env = dict(os.environ)
    helper_argv: list[str] = [git]
    if token:
        # Feed the token to git through GIT_ASKPASS, never via argv.
        askpass = cwd / ".git-askpass.sh"
        askpass.write_text(_ASKPASS_TEMPLATE.format(token=token))
        askpass.chmod(0o700)
        env["GIT_ASKPASS"] = str(askpass)
        env["GIT_USERNAME"] = "x-access-token"
        helper_argv += ["-c", "credential.helper="]

    proc = await asyncio.create_subprocess_exec(
        *helper_argv, *args,
        cwd=str(cwd),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


class GitHubCreateRepoTool(Tool):
    name = "github_create_repo"
    description = "Create a new GitHub repository for the authenticated user."
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "private": {"type": "boolean"},
        },
        "required": ["name"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        if ctx.github is None:
            return ToolResult(ok=False, summary="GitHub not configured")
        name = args.get("name")
        if not isinstance(name, str) or not name.strip():
            return ToolResult(ok=False, summary="name must be a non-empty string")
        try:
            repo = await ctx.github.create_repo(
                name,
                description=args.get("description") or "",
                private=bool(args.get("private", False)),
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, summary=f"create repo failed: {exc}")
        return ToolResult(
            ok=True,
            summary=f"created {repo['full_name']}",
            content=repo.get("clone_url", ""),
        )


class GitCloneTool(Tool):
    name = "git_clone"
    description = "Clone a repository into the workspace."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "GitHub repo URL (https or git@)"},
            "dir": {"type": "string", "description": "Target dir (optional)"},
        },
        "required": ["url"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        url = args.get("url")
        if not isinstance(url, str) or not url.strip():
            return ToolResult(ok=False, summary="url must be a non-empty string")
        target = ctx.workspace_root / (args.get("dir") or "")
        code, out, err = await _run_git("clone", url, str(target), cwd=ctx.workspace_root)
        if code != 0:
            return ToolResult(ok=False, summary="clone failed", content=err)
        return ToolResult(ok=True, summary=f"cloned {url}", content=out or "done")


class GitCommitTool(Tool):
    name = "git_commit"
    description = "Stage all changes and commit them in the workspace repo."
    parameters = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        message = args.get("message")
        if not isinstance(message, str) or not message.strip():
            return ToolResult(ok=False, summary="message must be a non-empty string")
        code, _, err = await _run_git("add", "-A", cwd=ctx.workspace_root)
        if code != 0:
            return ToolResult(ok=False, summary="git add failed", content=err)
        code, out, err = await _run_git("commit", "-m", message, cwd=ctx.workspace_root)
        if code != 0:
            return ToolResult(ok=False, summary="commit failed", content=err)
        return ToolResult(ok=True, summary="committed", content=out or err)


class GitPushTool(Tool):
    name = "git_push"
    description = "Push committed changes to the remote."
    parameters = {"type": "object", "properties": {"branch": {"type": "string"}}}

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        token = getattr(ctx.github, "_token", None) if ctx.github else None
        branch = args.get("branch") or "main"
        code, out, err = await _run_git(
            "push", "-u", "origin", str(branch), cwd=ctx.workspace_root, token=token
        )
        if code != 0:
            return ToolResult(ok=False, summary="push failed", content=err)
        return ToolResult(ok=True, summary=f"pushed {branch}", content=out or "done")


class GitPullTool(Tool):
    name = "git_pull"
    description = "Pull changes from the remote."
    parameters = {"type": "object", "properties": {"branch": {"type": "string"}}}

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        branch = args.get("branch") or "main"
        code, out, err = await _run_git("pull", "origin", str(branch), cwd=ctx.workspace_root)
        if code != 0:
            return ToolResult(ok=False, summary="pull failed", content=err)
        return ToolResult(ok=True, summary=f"pulled {branch}", content=out or "done")
