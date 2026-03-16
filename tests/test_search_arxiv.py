#!/usr/bin/env python3
"""Unit tests for search_arxiv.py."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from search_arxiv import (
    build_query,
    fetch_arxiv,
    parse_arxiv_response,
)

SAMPLE_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <totalResults xmlns="http://a9.com/-/spec/opensearch/1.1/">2</totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.12345v2</id>
    <title>Large Language Models for Scientific Discovery</title>
    <summary>We present a comprehensive study of LLMs applied to scientific research tasks.</summary>
    <published>2024-01-15T00:00:00Z</published>
    <updated>2024-02-01T00:00:00Z</updated>
    <author><name>John Smith</name></author>
    <author><name>Jane Doe</name></author>
    <category term="cs.CL" />
    <category term="cs.AI" />
    <link title="pdf" href="https://arxiv.org/pdf/2401.12345v2" />
    <arxiv:doi>10.1234/example.2024</arxiv:doi>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2312.98765v1</id>
    <title>Attention Mechanisms in Protein Folding</title>
    <summary>A novel attention-based approach for predicting protein structures.</summary>
    <published>2023-12-20T00:00:00Z</published>
    <updated>2023-12-20T00:00:00Z</updated>
    <author><name>Alice Researcher</name></author>
    <category term="cs.AI" />
    <category term="q-bio.BM" />
    <link title="pdf" href="https://arxiv.org/pdf/2312.98765v1" />
  </entry>
</feed>
"""

EMPTY_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <totalResults xmlns="http://a9.com/-/spec/opensearch/1.1/">0</totalResults>
</feed>
"""


class TestBuildQuery(unittest.TestCase):
    def test_simple_query(self):
        result = build_query("large language models")
        self.assertEqual(result, "all:large language models")

    def test_query_with_category(self):
        result = build_query("attention", category="cs.CL")
        self.assertEqual(result, "cat:cs.CL AND all:attention")

    def test_query_without_category(self):
        result = build_query("transformers", category=None)
        self.assertEqual(result, "all:transformers")


class TestParseArxivResponse(unittest.TestCase):
    def test_parse_valid_response(self):
        papers = parse_arxiv_response(SAMPLE_ARXIV_XML)

        self.assertEqual(len(papers), 2)

        first = papers[0]
        self.assertEqual(first["title"], "Large Language Models for Scientific Discovery")
        self.assertEqual(first["authors"], ["John Smith", "Jane Doe"])
        self.assertEqual(first["id"], "2401.12345")
        self.assertEqual(first["source"], "arxiv")
        self.assertEqual(first["year"], 2024)
        self.assertEqual(first["published"], "2024-01-15")
        self.assertEqual(first["categories"], ["cs.CL", "cs.AI"])
        self.assertIn("pdf", first["pdf_url"])
        self.assertEqual(first["external_ids"]["doi"], "10.1234/example.2024")
        self.assertEqual(first["external_ids"]["arxiv"], "2401.12345")
        self.assertEqual(first["status"], "candidate")
        self.assertIsNone(first["bibtex_key"])
        self.assertIsNone(first["relevance_score"])

    def test_parse_second_paper(self):
        papers = parse_arxiv_response(SAMPLE_ARXIV_XML)
        second = papers[1]
        self.assertEqual(second["title"], "Attention Mechanisms in Protein Folding")
        self.assertEqual(second["authors"], ["Alice Researcher"])
        self.assertEqual(second["id"], "2312.98765")
        self.assertEqual(second["year"], 2023)
        self.assertIsNone(second["external_ids"]["doi"])

    def test_parse_empty_response(self):
        papers = parse_arxiv_response(EMPTY_ARXIV_XML)
        self.assertEqual(papers, [])

    def test_paper_fields_complete(self):
        """Every paper must have all required fields."""
        papers = parse_arxiv_response(SAMPLE_ARXIV_XML)
        required_fields = {
            "id", "source", "title", "authors", "abstract", "published",
            "updated", "year", "categories", "venue", "citation_count",
            "pdf_url", "web_url", "external_ids", "bibtex_key",
            "relevance_score", "relevance_rationale", "status",
        }
        for paper in papers:
            self.assertEqual(set(paper.keys()), required_fields,
                             f"Paper '{paper['title']}' has wrong fields")

    def test_version_stripped_from_id(self):
        papers = parse_arxiv_response(SAMPLE_ARXIV_XML)
        # "2401.12345v2" should become "2401.12345"
        self.assertEqual(papers[0]["id"], "2401.12345")
        self.assertNotIn("v", papers[0]["id"])


class TestFetchArxiv(unittest.TestCase):
    @patch("search_arxiv.urllib.request.urlopen")
    def test_fetch_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = SAMPLE_ARXIV_XML.encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        papers = fetch_arxiv("LLM", max_results=10, sort_by="relevance")
        self.assertEqual(len(papers), 2)
        mock_urlopen.assert_called_once()

    @patch("search_arxiv.urllib.request.urlopen")
    def test_fetch_empty(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = EMPTY_ARXIV_XML.encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        papers = fetch_arxiv("nonexistent", max_results=10, sort_by="relevance")
        self.assertEqual(papers, [])


if __name__ == "__main__":
    unittest.main()
