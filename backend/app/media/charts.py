"""Chart generation with matplotlib (static PNG) — no server needed."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt  # noqa: E402

KINDS = ("bar", "line", "pie", "scatter", "hist")


def render_chart(
    labels: list[str],
    values: list[float],
    kind: str,
    out_path: Path,
    title: str = "",
) -> Path:
    if kind not in KINDS:
        raise ValueError(f"unsupported chart kind {kind!r} (choose {KINDS})")
    if len(labels) != len(values):
        raise ValueError("labels and values must have the same length")
    if not labels:
        raise ValueError("no data provided")

    fig, ax = plt.subplots(figsize=(8, 5))

    if kind == "bar":
        ax.bar(labels, values)
    elif kind == "line":
        ax.plot(labels, values, marker="o")
    elif kind == "pie":
        ax.pie(values, labels=labels, autopct="%1.1f%%")
    elif kind == "scatter":
        ax.scatter(range(len(values)), values)
        ax.set_xticks(range(len(values)), labels)
    elif kind == "hist":
        ax.hist(values, bins=min(20, len(values)))

    if kind != "pie":
        ax.set_ylabel("value")
    if title:
        ax.set_title(title)
    ax.tick_params(axis="x", rotation=45)

    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path
