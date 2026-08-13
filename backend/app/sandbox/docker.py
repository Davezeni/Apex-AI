"""Docker-backed sandbox.

Runs commands via `docker exec` in a workspace-mounted container, so
generated code executes in isolation from the host. Requires Docker and a
pulled runtime image (see docker-compose.yml). Also starts dev servers and
reports how the host can reach them (for the live preview proxy).
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

    async def _docker_run(self, *argv: str) -> CommandResult:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return CommandResult(
            exit_code=proc.returncode or 0,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
        )

    async def run_command(
        self, cmd: str, cwd: str = "", timeout: float = 120.0
    ) -> CommandResult:
        if not self._docker:
            raise SandboxError("docker executable not found")

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

    async def run_server(self, cmd: str, port: int, cwd: str = "") -> None:
        """Start a dev server detached inside the container (fire-and-forget)."""
        if not self._docker:
            raise SandboxError("docker executable not found")
        workdir = f"/workspace/{cwd}".rstrip("/") if cwd else "/workspace"
        # `-d` detaches so the server keeps running after this call returns.
        argv = [self._docker, "exec", "-d", "-w", workdir, self._container, "sh", "-c", cmd]
        result = await self._docker_run(*argv)
        if not result.ok:
            raise SandboxError(f"failed to start server: {result.stderr[:300]}")

    async def server_url(self, port: int) -> str:
        """Return the container's IP:port so the host can proxy to it."""
        if not self._docker:
            raise SandboxError("docker executable not found")
        r = await self._docker_run(
            self._docker, "inspect", "-f",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            self._container,
        )
        ip = r.stdout.strip() or "127.0.0.1"
        return f"http://{ip}:{port}"
