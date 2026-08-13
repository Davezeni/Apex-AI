"""GitHub Codespaces-backed sandbox.

Runs commands in a Codespace via the `gh` CLI (`gh codespace ssh` / `cp`).
Requires the GitHub CLI, a logged-in account, and an active Codespace for the
project repo. This backend is thin by design; a deeper Codespaces REST API
integration is a later increment. Not exercised in unit tests.
"""

from __future__ import annotations

import asyncio
import shutil

from .base import CommandResult, Sandbox, SandboxError


class CodespacesSandbox(Sandbox):
    name = "codespaces"

    def __init__(self, codespace_name: str) -> None:
        self._codespace = codespace_name
        self._gh = shutil.which("gh")

    async def available(self) -> bool:
        return self._gh is not None

    async def run_command(
        self, cmd: str, cwd: str = "", timeout: float = 120.0
    ) -> CommandResult:
        if not self._gh:
            raise SandboxError("gh CLI not found")

        # `gh codespace ssh -c NAME -- CMD` executes CMD in the Codespace.
        argv = [
            self._gh, "codespace", "ssh", "-c", self._codespace, "--",
            f"cd /workspaces/*/{cwd or ''} 2>/dev/null; {cmd}",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
        except asyncio.TimeoutError as exc:
            raise SandboxError(f"command timed out after {timeout}s") from exc
        except OSError as exc:
            raise SandboxError(f"failed to spawn gh: {exc}") from exc

        return CommandResult(
            exit_code=proc.returncode or 0,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
        )
