"""Tests for charts and document authoring (no network required)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.media import author, charts
from app.media.vision import mime_for


def test_chart_render_bar(tmp_path: Path):
    out = tmp_path / "chart.png"
    charts.render_chart(["a", "b", "c"], [1, 2, 3], "bar", out, title="T")
    assert out.exists() and out.stat().st_size > 0


def test_chart_render_pie(tmp_path: Path):
    out = tmp_path / "pie.png"
    charts.render_chart(["x", "y"], [3, 7], "pie", out)
    assert out.exists()


def test_chart_rejects_mismatched(tmp_path: Path):
    with pytest.raises(ValueError):
        charts.render_chart(["a"], [1, 2], "bar", tmp_path / "x.png")


def test_author_sad(tmp_path: Path):
    md = author.generate_document("sad", "Test System", {"overview": "hello", "goals": ["g1", "g2"]})
    assert "# Test System — System Architecture Document" in md
    assert "- g1" in md and "- g2" in md


def test_author_readme(tmp_path: Path):
    out = tmp_path / "README.md"
    author.write_document("readme", "Proj", {"overview": "ov", "stack": "git clone x"}, out)
    assert out.exists()
    assert "git clone x" in out.read_text()


def test_author_unknown_type():
    with pytest.raises(ValueError):
        author.generate_document("bogus", "T", {})


def test_mime_for():
    assert mime_for("a.png") == "image/png"
    assert mime_for("a.JPG") == "image/jpeg"
    assert mime_for("a.txt") == "image/png"
