"""Docker-backed sandbox.

Runs commands via `docker exec` in a workspace-mounted container, so
generated code executes in isolation from the host. Requires Docker and a
pulled runtime image (see docker-compose.yml). Not exercised in unit tests;
verified on a host with Docker installed.
"""

from __future__ import annotations

import asyncio
import shutil

from .base import CommandResult, Sandbox, SandboxError


class DockerSandbox(Sandbox):
    name = "docker"

    def __init__(self, container: str, workspace_mount: str = "/workspace") -> None:
        self._container = container
        self._workspace = workspace_mount
        self._docker = shutil.which("docker")

    async def available(self) -> bool:
        return self._docker is not None

    async def run_command(
        self, cmd: str, cwd: str = "", timeout: float = 120.0
    ) -> CommandResult:
        if not self._docker:
            raise SandboxError("docker executable not found")

        # The workspace on the host maps to /workspace inside the container.
        workdir = f"/workspace/{cwd}".rstrip("/") if cwd else "/workspace"
        argv = [self._docker, "exec", "-w", workdir, self._container, "sh", "-c", cmd]

        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout)
        except asyncio.TimeoutError as exc:
            raise SandboxError(f"command timed out after {timeout}s: {cmd[:80]}") from exc
        except OSError as exc:
            raise SandboxError(f"failed to spawn docker: {exc}") from exc

        return CommandResult(
            exit_code=proc.returncode or 0,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
        )
