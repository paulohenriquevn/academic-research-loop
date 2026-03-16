#!/usr/bin/env python3
"""Unit tests for fetch_paper_content.py."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fetch_paper_content import (
    extract_sections_from_html,
    fetch_content,
    strip_html_tags,
)

SAMPLE_AR5IV_HTML = """
<html>
<head><title>Test Paper</title></head>
<body>
<script>var x = 1;</script>
<style>.hidden { display: none; }</style>
<h2>1. Introduction</h2>
<p>This paper presents a novel approach to natural language processing.
We demonstrate significant improvements over prior work in text classification.
The main contributions of this paper include a new architecture and training methodology.</p>
<h2>2. Related Work</h2>
<p>Previous approaches to NLP have focused on recurrent neural networks.
Transformer architectures have since become the dominant paradigm.
Our work builds on attention mechanisms first introduced by Vaswani et al.</p>
<h3>2.1 Attention Mechanisms</h3>
<p>Self-attention allows models to capture long-range dependencies.
Multi-head attention enables the model to attend to different representation subspaces.</p>
<h2>3. Methodology</h2>
<p>We propose a modified transformer architecture with sparse attention patterns.
The model uses a combination of local and global attention heads.
Training is performed on a large corpus of scientific text.</p>
</body>
</html>
"""


class TestStripHtmlTags(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(strip_html_tags("<b>bold</b>").strip(), "bold")

    def test_nested(self):
        result = strip_html_tags("<div><p>text</p></div>")
        self.assertIn("text", result)

    def test_entities(self):
        self.assertIn("&", strip_html_tags("&amp;"))
        self.assertIn("<", strip_html_tags("&lt;"))

    def test_empty(self):
        self.assertEqual(strip_html_tags(""), "")


class TestExtractSectionsFromHtml(unittest.TestCase):
    def test_extracts_sections(self):
        sections = extract_sections_from_html(SAMPLE_AR5IV_HTML)
        self.assertGreater(len(sections), 0)

    def test_section_headings(self):
        sections = extract_sections_from_html(SAMPLE_AR5IV_HTML)
        headings = [s["heading"] for s in sections]
        self.assertTrue(any("Introduction" in h for h in headings))
        self.assertTrue(any("Related Work" in h for h in headings))

    def test_section_text_not_empty(self):
        sections = extract_sections_from_html(SAMPLE_AR5IV_HTML)
        for section in sections:
            self.assertGreater(len(section["text"]), 50)

    def test_script_and_style_removed(self):
        sections = extract_sections_from_html(SAMPLE_AR5IV_HTML)
        all_text = " ".join(s["text"] for s in sections)
        self.assertNotIn("var x", all_text)
        self.assertNotIn("display: none", all_text)

    def test_empty_html(self):
        sections = extract_sections_from_html("")
        self.assertEqual(sections, [])


class TestFetchContent(unittest.TestCase):
    @patch("fetch_paper_content.fetch_ar5iv")
    def test_returns_ar5iv_when_available(self, mock_ar5iv):
        mock_ar5iv.return_value = {
            "source": "ar5iv",
            "url": "https://ar5iv.labs.arxiv.org/html/2401.12345",
            "full_text": "Full paper content",
        }

        result = fetch_content(arxiv_id="2401.12345")
        self.assertEqual(result["source"], "ar5iv")
        self.assertEqual(result["quality"], "full_text")

    @patch("fetch_paper_content.fetch_ar5iv")
    @patch("fetch_paper_content.fetch_arxiv_abstract")
    def test_falls_back_to_abstract(self, mock_abstract, mock_ar5iv):
        mock_ar5iv.return_value = None
        mock_abstract.return_value = {
            "source": "arxiv_abstract",
            "abstract": "Test abstract",
            "full_text": "## Title\n\nTest abstract",
        }

        result = fetch_content(arxiv_id="2401.12345")
        self.assertEqual(result["source"], "arxiv_abstract")
        self.assertEqual(result["quality"], "abstract_only")

    @patch("fetch_paper_content.fetch_ar5iv")
    @patch("fetch_paper_content.fetch_arxiv_abstract")
    def test_no_content_available(self, mock_abstract, mock_ar5iv):
        mock_ar5iv.return_value = None
        mock_abstract.return_value = None

        result = fetch_content(arxiv_id="9999.99999")
        self.assertIn("error", result)

    def test_extracts_arxiv_id_from_url(self):
        """Test that arxiv ID is extracted from URL."""
        with patch("fetch_paper_content.fetch_ar5iv") as mock:
            mock.return_value = {
                "source": "ar5iv",
                "full_text": "content",
            }
            result = fetch_content(url="https://arxiv.org/abs/2401.12345")
            mock.assert_called_once_with("2401.12345")

    def test_no_inputs_returns_error(self):
        result = fetch_content()
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
