"""Tests for workspace protection (exclusion of dependency/build artifacts)."""

from __future__ import annotations

from pathlib import Path

from app.workspace.protect import WorkspaceProtection


def test_known_artifact_names_excluded(tmp_path: Path):
    p = WorkspaceProtection(tmp_path)
    assert p.excluded(Path("node_modules/foo/bar.js"))
    assert p.excluded(Path("src/__pycache__/x.pyc"))
    assert p.excluded(Path("dist/bundle.js"))
    assert p.excluded(Path("vendor/github.com/x"))


def test_glob_patterns_excluded(tmp_path: Path):
    p = WorkspaceProtection(tmp_path)
    assert p.excluded(Path("src/main.pyc"))
    assert p.excluded(Path("pkg.egg-info/PKG-INFO"))
    assert p.excluded(Path(".env"))


def test_legitimate_code_not_excluded(tmp_path: Path):
    p = WorkspaceProtection(tmp_path)
    assert not p.excluded(Path("src/main.py"))
    assert not p.excluded(Path("README.md"))
    assert not p.excluded(Path("go.mod"))
    assert not p.excluded(Path("dist-data/notes.txt"))  # 'dist-data' != 'dist'


def test_ignore_file_never_excluded(tmp_path: Path):
    p = WorkspaceProtection(tmp_path)
    assert not p.excluded(Path(".apexignore"))


def test_ensure_defaults_and_scan(tmp_path: Path):
    p = WorkspaceProtection(tmp_path)
    assert p.ensure_defaults() is True
    assert p.ignore_file.exists()
    assert p.ensure_defaults() is False  # already exists

    # Create an artifact dir and a real file.
    (tmp_path / "node_modules" / "x").mkdir(parents=True)
    (tmp_path / "node_modules" / "x" / "y.js").write_text("x" * 100)
    (tmp_path / "main.py").write_text("print(1)")

    report = p.scan()
    # main.py + .apexignore are included; node_modules is excluded.
    assert report["included_files"] == 2
    assert any("node_modules" in e["path"] for e in report["excluded_items"])
    assert report["excluded_bytes"] == 100


def test_human_size():
    assert WorkspaceProtection.human(0) == "0 B"
    assert WorkspaceProtection.human(1024) == "1.0 KB"
    assert WorkspaceProtection.human(1024 * 1024) == "1.0 MB"
