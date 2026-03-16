#!/usr/bin/env python3
"""Unit tests for search_semantic_scholar.py."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from search_semantic_scholar import fetch_semantic_scholar, parse_s2_response

SAMPLE_S2_RESPONSE = {
    "total": 2,
    "data": [
        {
            "paperId": "abc123def456",
            "title": "Transformers for Protein Structure Prediction",
            "abstract": "We show that transformer architectures can effectively predict protein structures.",
            "authors": [
                {"authorId": "1", "name": "Alice Chen"},
                {"authorId": "2", "name": "Bob Zhang"},
            ],
            "year": 2024,
            "citationCount": 42,
            "venue": "NeurIPS",
            "externalIds": {
                "ArXiv": "2401.99999",
                "DOI": "10.5555/example",
            },
            "url": "https://www.semanticscholar.org/paper/abc123def456",
            "tldr": {"text": "Transformers effectively predict protein structures."},
        },
        {
            "paperId": "xyz789",
            "title": "A Survey of Attention Mechanisms",
            "abstract": None,
            "authors": [{"authorId": "3", "name": "Carol Lee"}],
            "year": 2023,
            "citationCount": 150,
            "venue": "ACM Computing Surveys",
            "externalIds": {"DOI": "10.1145/survey"},
            "url": "https://www.semanticscholar.org/paper/xyz789",
            "tldr": {"text": "Comprehensive review of attention mechanisms."},
        },
    ],
}

EMPTY_S2_RESPONSE = {"total": 0, "data": []}


class TestParseS2Response(unittest.TestCase):
    def test_parse_valid_response(self):
        papers = parse_s2_response(SAMPLE_S2_RESPONSE)

        self.assertEqual(len(papers), 2)

        first = papers[0]
        self.assertEqual(first["title"], "Transformers for Protein Structure Prediction")
        self.assertEqual(first["authors"], ["Alice Chen", "Bob Zhang"])
        self.assertEqual(first["id"], "abc123def456")
        self.assertEqual(first["source"], "semantic_scholar")
        self.assertEqual(first["year"], 2024)
        self.assertEqual(first["citation_count"], 42)
        self.assertEqual(first["venue"], "NeurIPS")
        self.assertEqual(first["external_ids"]["arxiv"], "2401.99999")
        self.assertEqual(first["external_ids"]["doi"], "10.5555/example")
        self.assertEqual(first["external_ids"]["semantic_scholar"], "abc123def456")
        self.assertEqual(first["status"], "candidate")

    def test_abstract_fallback_to_tldr(self):
        """When abstract is None, should use TLDR text."""
        papers = parse_s2_response(SAMPLE_S2_RESPONSE)
        second = papers[1]
        self.assertEqual(second["abstract"], "Comprehensive review of attention mechanisms.")

    def test_parse_empty_response(self):
        papers = parse_s2_response(EMPTY_S2_RESPONSE)
        self.assertEqual(papers, [])

    def test_paper_fields_complete(self):
        papers = parse_s2_response(SAMPLE_S2_RESPONSE)
        required_fields = {
            "id", "source", "title", "authors", "abstract", "published",
            "updated", "year", "categories", "venue", "citation_count",
            "pdf_url", "web_url", "external_ids", "bibtex_key",
            "relevance_score", "relevance_rationale", "status",
        }
        for paper in papers:
            self.assertEqual(set(paper.keys()), required_fields)

    def test_missing_title_skipped(self):
        response = {"data": [{"paperId": "skip", "title": None}]}
        papers = parse_s2_response(response)
        self.assertEqual(papers, [])

    def test_missing_title_empty_skipped(self):
        response = {"data": [{"paperId": "skip", "title": ""}]}
        papers = parse_s2_response(response)
        self.assertEqual(papers, [])


class TestFetchSemanticScholar(unittest.TestCase):
    @patch("search_semantic_scholar.urllib.request.urlopen")
    def test_fetch_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(SAMPLE_S2_RESPONSE).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        papers = fetch_semantic_scholar("protein folding", max_results=10)
        self.assertEqual(len(papers), 2)

    @patch("search_semantic_scholar.urllib.request.urlopen")
    def test_fetch_with_year_filter(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(EMPTY_S2_RESPONSE).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        papers = fetch_semantic_scholar("test", max_results=5, year="2023-2026")
        self.assertEqual(papers, [])

        # Verify year was included in the URL
        call_args = mock_urlopen.call_args
        url = call_args[0][0].full_url if hasattr(call_args[0][0], "full_url") else str(call_args[0][0])
        self.assertIn("year", url)

    @patch.dict("os.environ", {"SEMANTIC_SCHOLAR_API_KEY": "test-key-123"})
    @patch("search_semantic_scholar.urllib.request.urlopen")
    def test_api_key_header(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(EMPTY_S2_RESPONSE).encode("utf-8")
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetch_semantic_scholar("test", max_results=5)

        # Verify API key header was set
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertEqual(request_obj.get_header("X-api-key"), "test-key-123")


if __name__ == "__main__":
    unittest.main()
