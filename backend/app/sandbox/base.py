"""Sandbox interface: isolated execution of agent-generated code."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class SandboxError(Exception):
    """Sandbox could not execute a command (infra-level failure)."""


class Sandbox(ABC):
    """Interface every sandbox backend must implement."""

    name: str

    @abstractmethod
    async def run_command(
        self, cmd: str, cwd: str = "", timeout: float = 120.0
    ) -> CommandResult:
        raise NotImplementedError

    @abstractmethod
    async def available(self) -> bool:
        """Whether the sandbox backend is installed/usable on this host."""
        raise NotImplementedError
