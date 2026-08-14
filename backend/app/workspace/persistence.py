"""Workspace persistence to Supabase.

Render's free tier has an ephemeral filesystem, so files the agent builds are
wiped on every redeploy. This module syncs the workspace file tree to a
`workspace_files` table in Supabase and restores it on startup, so built apps
survive redeploys.

Design:
- save(): upsert every workspace file (path, content) into Supabase.
- restore(): write Supabase's files back to the local workspace.
- Both are best-effort — if Supabase isn't configured, they no-op.

Files are stored as text; binary files are skipped (the agent mainly produces
text/code). Excluded artifacts (.apexignore rules) are skipped too.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx

TEXT_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".md",
    ".yml", ".yaml", ".go", ".rs", ".java", ".sh", ".txt", ".csv", ".xml",
    ".gitignore", ".env.example", ".toml",
}


class WorkspacePersistence:
    def __init__(self, url: str, service_role_key: str, workspace_root: Path) -> None:
        self._client = httpx.Client(
            base_url=url.rstrip("/"),
            headers={
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
            },
            timeout=30.0,
        )
        self._root = workspace_root

    # ---- helpers --------------------------------------------------------

    def _get_all(self) -> dict[str, str]:
        resp = self._client.get("/workspace_files", params={"select": "path,content"})
        resp.raise_for_status()
        return {r["path"]: r["content"] for r in resp.json()}

    def _upsert(self, path: str, content: str) -> None:
        self._client.post(
            "/workspace_files",
            json={"path": path, "content": content, "updated_at": time.time()},
            headers={"Prefer": "resolution=merge-duplicates"},
        ).raise_for_status()

    def _clear(self) -> None:
        self._client.delete("/workspace_files", params={"path": "neq.__none__"}).raise_for_status()

    # ---- public ---------------------------------------------------------

    def save(self, exclude: set[str] | None = None) -> int:
        """Upload workspace text files to Supabase. Returns count saved."""
        exclude = exclude or set()
        count = 0
        for p in self._root.rglob("*"):
            if not p.is_file():
                continue
            rel = str(p.relative_to(self._root))
            if rel in exclude:
                continue
            if p.suffix.lower() not in TEXT_EXTS and p.name != ".gitignore":
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue
            if len(content) > 1_000_000:
                continue
            try:
                self._upsert(rel, content)
                count += 1
            except Exception:  # noqa: BLE001
                continue
        return count

    def restore(self) -> int:
        """Write Supabase files back to the local workspace. Returns count."""
        try:
            files = self._get_all()
        except Exception:  # noqa: BLE001
            return 0
        count = 0
        for rel, content in files.items():
            # Path traversal guard.
            target = (self._root / rel).resolve()
            if not target.is_relative_to(self._root.resolve()):
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                count += 1
            except Exception:  # noqa: BLE001
                continue
        return count

    def close(self) -> None:
        self._client.close()


def build_workspace_persistence(
    store_backend: str, supabase_url: str | None, service_role_key: str | None,
    workspace_root: Path,
) -> "WorkspacePersistence | None":
    if store_backend != "supabase" or not supabase_url or not service_role_key:
        return None
    return WorkspacePersistence(supabase_url, service_role_key, workspace_root)
