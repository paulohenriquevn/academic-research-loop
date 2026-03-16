#!/usr/bin/env python3
"""
Minimal SVG utility library for the Academic Research Loop plugin.

Provides reusable primitives for generating publication-quality SVG figures.
Used by the figure-generator agent as a building block — the agent writes
the chart logic; this module provides the canvas and drawing primitives.

No external dependencies — uses only Python stdlib.
"""

import math
import re

# Academic color palette (colorblind-friendly, WCAG AA contrast on white)
PALETTE = [
    "#2563EB",  # blue
    "#DC2626",  # red
    "#059669",  # green
    "#7C3AED",  # purple
    "#EA580C",  # orange
    "#0D9488",  # teal
    "#D97706",  # amber
    "#6366F1",  # indigo
    "#BE185D",  # pink
    "#4B5563",  # gray
]

FONT_BODY = "Georgia, 'Times New Roman', serif"
FONT_AXIS = "'Helvetica Neue', Arial, sans-serif"

# Theme colors for paper categories
THEME_COLORS = {
    "retrieval": "#2563EB",
    "reader": "#059669",
    "joint_training": "#7C3AED",
    "robustness": "#EA580C",
    "agentic": "#DC2626",
    "default": "#4B5563",
}


def escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


class SvgCanvas:
    """Builds SVG documents with academic styling.

    Usage:
        canvas = SvgCanvas(800, 400)
        canvas.rect(10, 10, 100, 50, fill="#2563EB")
        canvas.text(60, 40, "Hello", font_size=14)
        svg_string = canvas.render()
    """

    def __init__(self, width: int, height: int, bg: str = "white"):
        self.width = width
        self.height = height
        self.bg = bg
        self._elements: list[str] = []
        self._defs: list[str] = []

    def add_def(self, definition: str) -> None:
        """Add a <defs> element (gradients, patterns, etc.)."""
        self._defs.append(definition)

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str = "#000",
        opacity: float = 1.0,
        rx: float = 0,
        stroke: str = "",
        stroke_width: float = 0,
    ) -> None:
        """Draw a rectangle."""
        attrs = (
            f'x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}"'
        )
        if opacity < 1.0:
            attrs += f' opacity="{opacity:.2f}"'
        if rx > 0:
            attrs += f' rx="{rx:.1f}"'
        if stroke:
            attrs += f' stroke="{stroke}" stroke-width="{stroke_width:.1f}"'
        self._elements.append(f"  <rect {attrs}/>")

    def text(
        self,
        x: float,
        y: float,
        content: str,
        font_size: int = 12,
        font_family: str = FONT_AXIS,
        anchor: str = "middle",
        fill: str = "#333",
        weight: str = "normal",
        rotate: float = 0,
        baseline: str = "auto",
    ) -> None:
        """Draw text."""
        escaped = escape_xml(str(content))
        transform = ""
        if rotate:
            transform = f' transform="rotate({rotate},{x:.1f},{y:.1f})"'
        baseline_attr = ""
        if baseline != "auto":
            baseline_attr = f' dominant-baseline="{baseline}"'
        self._elements.append(
            f'  <text x="{x:.1f}" y="{y:.1f}" font-size="{font_size}" '
            f'font-family="{font_family}" text-anchor="{anchor}" '
            f'fill="{fill}" font-weight="{weight}"{baseline_attr}'
            f"{transform}>{escaped}</text>"
        )

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        stroke: str = "#ccc",
        width: float = 1,
        dash: str = "",
    ) -> None:
        """Draw a line."""
        attrs = (
            f'x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{width:.1f}"'
        )
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        self._elements.append(f"  <line {attrs}/>")

    def circle(
        self,
        cx: float,
        cy: float,
        r: float,
        fill: str = "#000",
        stroke: str = "",
        stroke_width: float = 0,
        opacity: float = 1.0,
    ) -> None:
        """Draw a circle."""
        attrs = f'cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"'
        if opacity < 1.0:
            attrs += f' opacity="{opacity:.2f}"'
        if stroke:
            attrs += f' stroke="{stroke}" stroke-width="{stroke_width:.1f}"'
        self._elements.append(f"  <circle {attrs}/>")

    def path(
        self,
        d: str,
        fill: str = "none",
        stroke: str = "#000",
        width: float = 1,
        opacity: float = 1.0,
    ) -> None:
        """Draw a path."""
        attrs = (
            f'd="{d}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{width:.1f}"'
        )
        if opacity < 1.0:
            attrs += f' opacity="{opacity:.2f}"'
        self._elements.append(f"  <path {attrs}/>")

    def group_start(self, transform: str = "", opacity: float = 1.0) -> None:
        """Open a <g> group."""
        attrs = ""
        if transform:
            attrs += f' transform="{transform}"'
        if opacity < 1.0:
            attrs += f' opacity="{opacity:.2f}"'
        self._elements.append(f"  <g{attrs}>")

    def group_end(self) -> None:
        """Close a </g> group."""
        self._elements.append("  </g>")

    def comment(self, text: str) -> None:
        """Add an XML comment."""
        self._elements.append(f"  <!-- {text} -->")

    def render(self) -> str:
        """Render the complete SVG document."""
        defs_str = ""
        if self._defs:
            defs_str = "  <defs>\n    " + "\n    ".join(self._defs) + "\n  </defs>\n"

        elements_str = "\n".join(self._elements)
        bg = ""
        if self.bg:
            bg = f'  <rect width="100%" height="100%" fill="{self.bg}"/>\n'

        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {self.width} {self.height}" '
            f'width="{self.width}" height="{self.height}">\n'
            f"{defs_str}"
            f"{bg}"
            f"{elements_str}\n"
            f"</svg>"
        )


# ---------------------------------------------------------------------------
# High-level drawing helpers
# ---------------------------------------------------------------------------


def draw_axes(
    canvas: SvgCanvas,
    x: float,
    y: float,
    w: float,
    h: float,
    x_label: str = "",
    y_label: str = "",
    y_min: float = 0,
    y_max: float = 100,
    y_ticks: int = 5,
    grid: bool = True,
) -> None:
    """Draw X and Y axes with labels and optional grid lines."""
    # Y axis
    canvas.line(x, y, x, y + h, stroke="#333", width=1.5)
    # X axis
    canvas.line(x, y + h, x + w, y + h, stroke="#333", width=1.5)

    # Y ticks and grid
    for i in range(y_ticks + 1):
        tick_y = y + h - (h * i / y_ticks)
        tick_val = y_min + (y_max - y_min) * i / y_ticks
        canvas.line(x - 4, tick_y, x, tick_y, stroke="#333", width=1)
        canvas.text(
            x - 8, tick_y, f"{tick_val:.0f}",
            font_size=10, anchor="end", baseline="middle",
        )
        if grid and i > 0:
            canvas.line(x, tick_y, x + w, tick_y, stroke="#e5e7eb", width=0.5)

    # Axis labels
    if x_label:
        canvas.text(
            x + w / 2, y + h + 40, x_label,
            font_size=12, font_family=FONT_BODY, weight="bold",
        )
    if y_label:
        canvas.text(
            x - 45, y + h / 2, y_label,
            font_size=12, font_family=FONT_BODY, weight="bold", rotate=-90,
        )


def draw_legend(
    canvas: SvgCanvas,
    x: float,
    y: float,
    items: list[tuple[str, str]],
    direction: str = "horizontal",
    font_size: int = 10,
) -> None:
    """Draw a legend. Items are (label, color) tuples."""
    offset_x = 0
    offset_y = 0
    for label, color in items:
        canvas.rect(x + offset_x, y + offset_y - 8, 12, 12, fill=color, rx=2)
        canvas.text(
            x + offset_x + 16, y + offset_y, label,
            font_size=font_size, anchor="start", baseline="middle",
        )
        if direction == "horizontal":
            offset_x += len(label) * 6.5 + 28
        else:
            offset_y += 18


def nice_ticks(data_min: float, data_max: float, n_ticks: int = 5) -> tuple[float, float, int]:
    """Compute nice axis bounds and tick count for a data range."""
    if data_max <= data_min:
        return 0, max(data_max * 1.1, 1), n_ticks
    raw_step = (data_max - data_min) / n_ticks
    magnitude = 10 ** math.floor(math.log10(raw_step))
    residual = raw_step / magnitude
    if residual <= 1.5:
        nice_step = 1 * magnitude
    elif residual <= 3:
        nice_step = 2 * magnitude
    elif residual <= 7:
        nice_step = 5 * magnitude
    else:
        nice_step = 10 * magnitude
    nice_min = math.floor(data_min / nice_step) * nice_step
    nice_max = math.ceil(data_max / nice_step) * nice_step
    actual_ticks = round((nice_max - nice_min) / nice_step)
    return nice_min, nice_max, max(actual_ticks, 1)


def wrap_text(text: str, max_chars: int = 15) -> list[str]:
    """Split long text into lines for SVG rendering."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines
