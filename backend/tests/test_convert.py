"""Tests for document conversion via the Markdown interchange hub."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.media import convert


def test_csv_roundtrip_through_markdown(tmp_path: Path):
    src = tmp_path / "data.csv"
    src.write_text("name,score\nalice,10\nbob,20\n")

    md = convert.to_markdown(src)
    assert "| name | score |" in md
    assert "| alice | 10 |" in md

    dst = tmp_path / "out.csv"
    convert.from_markdown(md, ".csv", dst)
    assert "alice,10" in dst.read_text()


def test_csv_to_xlsx(tmp_path: Path):
    src = tmp_path / "data.csv"
    src.write_text("name,score\nalice,10\nbob,20\n")
    dst = tmp_path / "out.xlsx"
    convert.convert_file(src, dst)
    assert dst.exists()
    # Read it back and confirm structure is preserved.
    md = convert.to_markdown(dst)
    assert "| alice | 10 |" in md


def test_markdown_to_html(tmp_path: Path):
    md = "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    html = convert.markdown_to_html(md)
    assert "<table>" in html and "<td>1</td>" in html


def test_unsupported_source_raises(tmp_path: Path):
    src = tmp_path / "x.bin"
    src.write_bytes(b"\x00\x01")
    with pytest.raises(convert.ConversionError):
        convert.to_markdown(src)
