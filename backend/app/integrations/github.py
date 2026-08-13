"""GitHub REST client (repo CRUD + file operations) via httpx.

Uses the fine-grained PAT with `Authorization: Bearer <token>`. Git
clone/commit/push/pull are handled by the git tool (tools/github.py) via
subprocess, keeping this client focused on API operations.
"""

from __future__ import annotations

from typing import Any

import httpx

API = "https://api.github.com"


class GitHubError(Exception):
    """A GitHub API error (non-2xx) with a readable message."""


class GitHubClient:
    def __init__(self, token: str, timeout: float = 30.0) -> None:
        self._token = token
        self._client = httpx.AsyncClient(
            base_url=API,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=timeout,
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = await self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            detail = resp.json().get("message", resp.text[:200]) if resp.content else resp.text
            raise GitHubError(f"GitHub {method} {path}: {resp.status_code} {detail}")
        if resp.status_code == 204:
            return None
        return resp.json()

    async def whoami(self) -> dict[str, Any]:
        return await self._request("GET", "/user")

    async def list_repos(self, per_page: int = 30) -> list[dict[str, Any]]:
        return await self._request("GET", f"/user/repos?per_page={per_page}&sort=updated")

    async def create_repo(
        self, name: str, description: str = "", private: bool = False
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/user/repos",
            json={"name": name, "description": description, "private": private, "auto_init": False},
        )

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        return await self._request("GET", f"/repos/{owner}/{repo}")

    async def get_file(self, owner: str, repo: str, path: str) -> dict[str, Any]:
        return await self._request("GET", f"/repos/{owner}/{repo}/contents/{path}")

    async def put_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"message": message, "content": content, "branch": branch}
        if sha:
            body["sha"] = sha
        return await self._request("PUT", f"/repos/{owner}/{repo}/contents/{path}", json=body)

    async def close(self) -> None:
        await self._client.aclose()
