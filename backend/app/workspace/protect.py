"""Workspace protection: keep the workspace lean by excluding dependency and
build artifacts (node_modules, __pycache__, dist, vendor, target, …).

The pattern mirrors how hosted agent platforms keep a workspace snapshot small:
a curated catalog of known artifact directories/globs, plus a user-editable
`.apexignore` file (gitignore syntax) in the workspace root. Excluded paths are
skipped by the file tree and the zip export, so the workspace never balloons
with generated files.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

# Known dependency/artifact names per ecosystem. A path is excluded if ANY
# component matches one of these names. `None` entries are not possible here;
# the set is deliberately conservative to avoid hiding legitimate code.
ARTIFACT_NAMES: frozenset[str] = frozenset(
    {
        # Node / JS / TS
        "node_modules", ".npm", ".next", ".nuxt", ".output", ".parcel-cache",
        ".vite", ".svelte-kit", ".turbo", "dist", "build", "out",
        # Python
        "__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache",
        ".ruff_cache", ".tox", ".nox", ".coverage", "htmlcov", "coverage",
        # Go / Rust
        "vendor", "target",
        # Java / Gradle / Maven
        ".gradle", ".idea", "target",
        # .NET
        "bin", "obj",
        # Caches / OS / editors
        ".cache", ".DS_Store", "Thumbs.db", ".vscode", ".idea",
    }
)

# Glob patterns (matched against the relative path and the basename).
ARTIFACT_GLOBS: tuple[str, ...] = (
    "*.pyc", "*.pyo", "*.egg-info", "*.class", "*.o", "*.so",
    "*.log", ".env", ".env.*",
)

IGNORE_FILE = ".apexignore"

# Header written when defaults are auto-applied.
_DEFAULT_IGNORE = """\
# Apex AI workspace protection (auto-generated, gitignore syntax).
# Files/directories matching these are excluded from the file tree and exports.
# Add or remove lines freely; this file is yours to edit.

# Node / JS / TS
node_modules/
.npm/
.next/
.nuxt/
.output/
.parcel-cache/
.vite/
.svelte-kit/
.turbo/
dist/
build/
out/

# Python
__pycache__/
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.tox/
.nox/
.coverage
htmlcov/
coverage/
*.pyc
*.egg-info/

# Go / Rust
vendor/
target/

# Java / .NET
.gradle/
.idea/
bin/
obj/

# Caches / OS / editors
.cache/
.DS_Store
Thumbs.db
.vscode/
"""


class WorkspaceProtection:
    """Determines which workspace paths are excluded, and reports size savings."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.ignore_file = root / IGNORE_FILE

    # ---- ignore-file handling ------------------------------------------

    def _load_patterns(self) -> list[str]:
        if not self.ignore_file.exists():
            return []
        patterns: list[str] = []
        for line in self.ignore_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line.rstrip("/"))
        return patterns

    def ensure_defaults(self) -> bool:
        """Write the default .apexignore if none exists. Returns True if written."""
        if self.ignore_file.exists():
            return False
        self.ignore_file.write_text(_DEFAULT_IGNORE, encoding="utf-8")
        return True

    # ---- matching -------------------------------------------------------

    def excluded(self, rel: Path) -> bool:
        """True if the relative path should be excluded."""
        # The ignore file itself is never "excluded" from the tree.
        if rel.name == IGNORE_FILE:
            return False

        # Any path component matches a known artifact name or glob
        # (so e.g. 'pkg.egg-info' and 'x.pyc' are caught mid-path).
        for part in rel.parts:
            if part in ARTIFACT_NAMES:
                return True
            if any(fnmatch.fnmatch(part, g) for g in ARTIFACT_GLOBS):
                return True

        # User .apexignore patterns: matched against full path and basename.
        s = str(rel).replace("\\", "/")
        for pat in self._load_patterns():
            if fnmatch.fnmatch(s, pat) or fnmatch.fnmatch(rel.name, pat):
                return True
        return False

    # ---- scan & report --------------------------------------------------

    @staticmethod
    def _dir_size(p: Path) -> int:
        total = 0
        try:
            for child in p.rglob("*"):
                try:
                    if child.is_file():
                        total += child.stat().st_size
                except OSError:
                    continue
        except OSError:
            pass
        return total

    def scan(self) -> dict:
        """Walk the workspace, reporting included size and excluded items."""
        included_bytes = 0
        excluded: list[dict] = []
        file_count = 0

        def rec(d: Path) -> None:
            nonlocal included_bytes, file_count
            try:
                entries = sorted(d.iterdir(), key=lambda p: p.name)
            except OSError:
                return
            for p in entries:
                rel = p.relative_to(self.root)
                if self.excluded(rel):
                    excluded.append(
                        {"path": str(rel), "size": self._dir_size(p)}
                    )
                    continue
                if p.is_dir():
                    rec(p)
                else:
                    try:
                        included_bytes += p.stat().st_size
                        file_count += 1
                    except OSError:
                        continue

        rec(self.root)
        excluded_bytes = sum(e["size"] for e in excluded)
        excluded.sort(key=lambda e: e["size"], reverse=True)
        return {
            "included_files": file_count,
            "included_bytes": included_bytes,
            "excluded_items": excluded,
            "excluded_bytes": excluded_bytes,
            "has_ignore_file": self.ignore_file.exists(),
        }

    @staticmethod
    def human(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024 or unit == "GB":
                return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
            n /= 1024
        return f"{n} B"
