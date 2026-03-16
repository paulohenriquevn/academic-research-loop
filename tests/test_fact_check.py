#!/usr/bin/env python3
"""Unit tests for fact_check.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fact_check import (
    check_claim_support,
    extract_cited_passages,
    run_fact_check,
)
from paper_database import add_analysis, add_paper, init_db, update_paper

SAMPLE_DRAFT = """# Survey of LLMs for Science

## Introduction

Large language models have shown remarkable capabilities in scientific discovery [@smith2024large].
Recent work has demonstrated that transformers can predict protein structures [@chen2023protein].

## Methods

Several approaches have been proposed for applying LLMs to chemistry [@unknown2024].
The attention mechanism is key to understanding molecular interactions [@smith2024large; @chen2023protein].

## Discussion

Some researchers argue that LLMs are insufficient for rigorous scientific reasoning [@critic2024limits].
"""


class TestExtractCitedPassages(unittest.TestCase):
    def test_extract_single_citation(self):
        passages = extract_cited_passages(SAMPLE_DRAFT)
        self.assertTrue(len(passages) >= 4)

    def test_extract_citation_keys(self):
        passages = extract_cited_passages(SAMPLE_DRAFT)
        first = passages[0]
        self.assertIn("smith2024large", first["cited_keys"])

    def test_extract_multiple_citations(self):
        passages = extract_cited_passages(SAMPLE_DRAFT)
        multi = [p for p in passages if len(p["cited_keys"]) > 1]
        self.assertTrue(len(multi) >= 1)
        # Find the passage with both keys
        attention_passage = [p for p in multi if "smith2024large" in p["cited_keys"]]
        self.assertTrue(len(attention_passage) >= 1)

    def test_no_citations(self):
        passages = extract_cited_passages("No citations here.")
        self.assertEqual(passages, [])

    def test_line_numbers(self):
        passages = extract_cited_passages(SAMPLE_DRAFT)
        for p in passages:
            self.assertGreater(p["line_number"], 0)


class TestCheckClaimSupport(unittest.TestCase):
    def test_verified_claim(self):
        passage = {
            "text": "Large language models have capabilities in scientific discovery [@smith2024large]",
            "cited_keys": ["smith2024large"],
            "line_number": 5,
        }
        papers = {
            "smith2024large": {
                "title": "Large Language Models for Scientific Discovery",
                "abstract": "We study how large language models can accelerate scientific discovery.",
                "full_text": "",
            }
        }
        result = check_claim_support(passage, papers, {})
        self.assertEqual(result["confidence"], "high")
        self.assertEqual(result["verified_keys"], ["smith2024large"])
        self.assertEqual(result["issues"], [])

    def test_missing_reference(self):
        passage = {
            "text": "Some claim [@nonexistent2024]",
            "cited_keys": ["nonexistent2024"],
            "line_number": 10,
        }
        result = check_claim_support(passage, {}, {})
        self.assertEqual(result["confidence"], "low")
        self.assertEqual(result["missing_keys"], ["nonexistent2024"])
        self.assertEqual(len(result["issues"]), 1)
        self.assertEqual(result["issues"][0]["type"], "missing_reference")

    def test_weak_support(self):
        passage = {
            "text": "Hydraulic fracturing techniques improve underground reservoir permeability [@smith2024large]",
            "cited_keys": ["smith2024large"],
            "line_number": 15,
        }
        papers = {
            "smith2024large": {
                "title": "Large Language Models for Scientific Discovery",
                "abstract": "We study how LLMs can help with literature review tasks.",
                "full_text": "",
            }
        }
        result = check_claim_support(passage, papers, {})
        # Hydraulic fracturing / reservoir has zero overlap with LLM / literature review
        self.assertIn(result["confidence"], ["medium", "low"])


class TestRunFactCheck(unittest.TestCase):
    def setUp(self):
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp_db.name
        init_db(self.db_path)

        # Add papers with bibtex_keys
        paper1 = {
            "id": "2401.12345",
            "source": "arxiv",
            "title": "Large Language Models for Scientific Discovery",
            "authors": ["John Smith"],
            "abstract": "We study large language models applied to scientific discovery and research acceleration.",
            "external_ids": {"arxiv": "2401.12345"},
            "status": "shortlisted",
        }
        add_paper(self.db_path, paper1)
        update_paper(self.db_path, "2401.12345", {"bibtex_key": "smith2024large"})

    def test_full_fact_check(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(SAMPLE_DRAFT)
            draft_path = f.name

        result = run_fact_check(draft_path, self.db_path)
        self.assertEqual(result["status"], "complete")
        self.assertGreater(result["total_cited_passages"], 0)
        self.assertIn("confidence_breakdown", result)
        self.assertIn("overall_score", result)

    def test_no_citations_draft(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Paper\n\nNo citations here.")
            draft_path = f.name

        result = run_fact_check(draft_path, self.db_path)
        self.assertEqual(result["status"], "no_citations")


if __name__ == "__main__":
    unittest.main()
