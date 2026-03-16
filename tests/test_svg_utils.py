"""Tests for svg_utils.py — SVG utility primitives."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from svg_utils import (
    SvgCanvas,
    PALETTE,
    THEME_COLORS,
    escape_xml,
    draw_axes,
    draw_legend,
    nice_ticks,
    wrap_text,
)


# ---------------------------------------------------------------------------
# escape_xml
# ---------------------------------------------------------------------------

class TestEscapeXml:
    def test_ampersand(self):
        assert escape_xml("R&D") == "R&amp;D"

    def test_angle_brackets(self):
        assert escape_xml("<b>text</b>") == "&lt;b&gt;text&lt;/b&gt;"

    def test_quotes(self):
        assert escape_xml('say "hello"') == "say &quot;hello&quot;"

    def test_no_special_chars(self):
        assert escape_xml("plain text") == "plain text"

    def test_apostrophe(self):
        assert escape_xml("it's") == "it&apos;s"


# ---------------------------------------------------------------------------
# SvgCanvas
# ---------------------------------------------------------------------------

class TestSvgCanvas:
    def test_empty_canvas_renders_valid_svg(self):
        canvas = SvgCanvas(800, 400)
        svg = canvas.render()
        assert '<?xml version="1.0"' in svg
        assert '<svg xmlns="http://www.w3.org/2000/svg"' in svg
        assert 'viewBox="0 0 800 400"' in svg
        assert '</svg>' in svg

    def test_canvas_dimensions(self):
        canvas = SvgCanvas(1200, 600)
        svg = canvas.render()
        assert 'width="1200"' in svg
        assert 'height="600"' in svg

    def test_background_rect(self):
        canvas = SvgCanvas(100, 100, bg="white")
        svg = canvas.render()
        assert 'fill="white"' in svg

    def test_no_background(self):
        canvas = SvgCanvas(100, 100, bg="")
        svg = canvas.render()
        # Should not have a background rect
        assert svg.count("<rect") == 0


class TestSvgRect:
    def test_basic_rect(self):
        canvas = SvgCanvas(100, 100)
        canvas.rect(10, 20, 50, 30, fill="#2563EB")
        svg = canvas.render()
        assert 'x="10.0"' in svg
        assert 'y="20.0"' in svg
        assert 'width="50.0"' in svg
        assert 'height="30.0"' in svg
        assert 'fill="#2563EB"' in svg

    def test_rect_with_rounded_corners(self):
        canvas = SvgCanvas(100, 100)
        canvas.rect(0, 0, 50, 50, rx=5)
        svg = canvas.render()
        assert 'rx="5.0"' in svg

    def test_rect_with_stroke(self):
        canvas = SvgCanvas(100, 100)
        canvas.rect(0, 0, 50, 50, stroke="#000", stroke_width=2)
        svg = canvas.render()
        assert 'stroke="#000"' in svg
        assert 'stroke-width="2.0"' in svg

    def test_rect_with_opacity(self):
        canvas = SvgCanvas(100, 100)
        canvas.rect(0, 0, 50, 50, opacity=0.5)
        svg = canvas.render()
        assert 'opacity="0.50"' in svg


class TestSvgText:
    def test_basic_text(self):
        canvas = SvgCanvas(200, 100)
        canvas.text(100, 50, "Hello World", font_size=14)
        svg = canvas.render()
        assert "Hello World" in svg
        assert 'font-size="14"' in svg

    def test_text_escapes_special_chars(self):
        canvas = SvgCanvas(200, 100)
        canvas.text(50, 50, "R&D <test>")
        svg = canvas.render()
        assert "R&amp;D &lt;test&gt;" in svg

    def test_text_anchor(self):
        canvas = SvgCanvas(200, 100)
        canvas.text(50, 50, "Left", anchor="start")
        svg = canvas.render()
        assert 'text-anchor="start"' in svg

    def test_text_rotation(self):
        canvas = SvgCanvas(200, 100)
        canvas.text(50, 50, "Rotated", rotate=-90)
        svg = canvas.render()
        assert "rotate(-90," in svg

    def test_text_weight(self):
        canvas = SvgCanvas(200, 100)
        canvas.text(50, 50, "Bold", weight="bold")
        svg = canvas.render()
        assert 'font-weight="bold"' in svg


class TestSvgLine:
    def test_basic_line(self):
        canvas = SvgCanvas(200, 100)
        canvas.line(0, 0, 200, 100, stroke="#333", width=2)
        svg = canvas.render()
        assert 'x1="0.0"' in svg
        assert 'y2="100.0"' in svg
        assert 'stroke="#333"' in svg

    def test_dashed_line(self):
        canvas = SvgCanvas(200, 100)
        canvas.line(0, 0, 200, 0, dash="4 2")
        svg = canvas.render()
        assert 'stroke-dasharray="4 2"' in svg


class TestSvgCircle:
    def test_basic_circle(self):
        canvas = SvgCanvas(200, 200)
        canvas.circle(100, 100, 50, fill="#DC2626")
        svg = canvas.render()
        assert 'cx="100.0"' in svg
        assert 'cy="100.0"' in svg
        assert 'r="50.0"' in svg
        assert 'fill="#DC2626"' in svg


class TestSvgPath:
    def test_basic_path(self):
        canvas = SvgCanvas(200, 200)
        canvas.path("M 10 10 L 100 100", stroke="#000", width=2)
        svg = canvas.render()
        assert 'd="M 10 10 L 100 100"' in svg


class TestSvgGroup:
    def test_group_wrapping(self):
        canvas = SvgCanvas(200, 200)
        canvas.group_start(transform="translate(10,20)")
        canvas.rect(0, 0, 50, 50)
        canvas.group_end()
        svg = canvas.render()
        assert '<g transform="translate(10,20)">' in svg
        assert "</g>" in svg


class TestSvgDefs:
    def test_add_def(self):
        canvas = SvgCanvas(200, 200)
        canvas.add_def('<linearGradient id="grad1"/>')
        svg = canvas.render()
        assert "<defs>" in svg
        assert "grad1" in svg


# ---------------------------------------------------------------------------
# High-level helpers
# ---------------------------------------------------------------------------

class TestNiceTicks:
    def test_basic_range(self):
        y_min, y_max, ticks = nice_ticks(0, 100)
        assert y_min == 0
        assert y_max == 100
        assert ticks > 0

    def test_non_round_range(self):
        y_min, y_max, ticks = nice_ticks(3.2, 97.8)
        assert y_min <= 3.2
        assert y_max >= 97.8

    def test_small_range(self):
        y_min, y_max, ticks = nice_ticks(40, 55)
        assert y_min <= 40
        assert y_max >= 55
        assert ticks > 0

    def test_equal_values(self):
        y_min, y_max, ticks = nice_ticks(50, 50)
        assert y_max > y_min
        assert ticks > 0


class TestWrapText:
    def test_short_text(self):
        assert wrap_text("Hello") == ["Hello"]

    def test_long_text(self):
        lines = wrap_text("This is a long label that needs wrapping", max_chars=15)
        assert len(lines) > 1
        for line in lines:
            assert len(line) <= 20  # some tolerance for word boundaries

    def test_single_long_word(self):
        lines = wrap_text("Supercalifragilistic", max_chars=10)
        assert len(lines) == 1  # can't break a single word


class TestDrawAxes:
    def test_axes_draw_without_error(self):
        canvas = SvgCanvas(800, 400)
        draw_axes(canvas, 60, 20, 700, 340, x_label="Systems", y_label="EM (%)")
        svg = canvas.render()
        assert "Systems" in svg
        assert "EM (%)" in svg
        assert "<line" in svg


class TestDrawLegend:
    def test_legend_horizontal(self):
        canvas = SvgCanvas(800, 400)
        draw_legend(canvas, 100, 50, [("NQ", "#2563EB"), ("TriviaQA", "#DC2626")])
        svg = canvas.render()
        assert "NQ" in svg
        assert "TriviaQA" in svg
        assert "#2563EB" in svg

    def test_legend_vertical(self):
        canvas = SvgCanvas(800, 400)
        draw_legend(canvas, 100, 50, [("A", "#000"), ("B", "#fff")], direction="vertical")
        svg = canvas.render()
        assert "A" in svg
        assert "B" in svg


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_palette_has_enough_colors(self):
        assert len(PALETTE) >= 8

    def test_palette_colors_are_hex(self):
        import re
        for color in PALETTE:
            assert re.match(r"^#[0-9A-Fa-f]{6}$", color), f"Invalid hex: {color}"

    def test_theme_colors_have_default(self):
        assert "default" in THEME_COLORS
