#!/usr/bin/env python3
"""Unit tests for paper_database.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from paper_database import (
    add_agent_message,
    add_analysis,
    add_evidence,
    add_paper,
    add_quality_score,
    evidence_matrix,
    get_quality_history,
    get_stats,
    init_db,
    query_evidence,
    query_messages,
    query_papers,
    update_paper,
)

SAMPLE_PAPER = {
    "id": "2401.12345",
    "source": "arxiv",
    "title": "Large Language Models for Scientific Discovery",
    "authors": ["John Smith", "Jane Doe"],
    "abstract": "We present a study of LLMs.",
    "published": "2024-01-15",
    "updated": "2024-02-01",
    "year": 2024,
    "categories": ["cs.CL", "cs.AI"],
    "venue": None,
    "citation_count": None,
    "pdf_url": "https://arxiv.org/pdf/2401.12345",
    "web_url": "https://arxiv.org/abs/2401.12345",
    "external_ids": {"arxiv": "2401.12345", "doi": "10.1234/test"},
    "bibtex_key": None,
    "relevance_score": None,
    "relevance_rationale": None,
    "status": "candidate",
}

SAMPLE_PAPER_2 = {
    "id": "2312.99999",
    "source": "semantic_scholar",
    "title": "Attention Mechanisms in Biology",
    "authors": ["Alice Researcher"],
    "abstract": "We study attention in biological systems.",
    "year": 2023,
    "categories": [],
    "venue": "NeurIPS",
    "citation_count": 42,
    "external_ids": {"arxiv": "2312.99999", "doi": None},
    "status": "candidate",
}


class TestInitDB(unittest.TestCase):
    def test_init_creates_tables(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        init_db(db_path)

        import sqlite3
        conn = sqlite3.connect(db_path)
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()

        self.assertIn("papers", tables)
        self.assertIn("analyses", tables)
        self.assertIn("quality_scores", tables)
        self.assertIn("agent_messages", tables)
        self.assertIn("schema_version", tables)


class TestAddPaper(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        init_db(self.db_path)

    def test_add_new_paper(self):
        result = add_paper(self.db_path, SAMPLE_PAPER)
        self.assertEqual(result["status"], "added")
        self.assertEqual(result["id"], "2401.12345")

    def test_add_duplicate_by_arxiv_id(self):
        add_paper(self.db_path, SAMPLE_PAPER)
        dup = dict(SAMPLE_PAPER)
        dup["id"] = "different_id"
        result = add_paper(self.db_path, dup)
        self.assertEqual(result["status"], "duplicate")
        self.assertEqual(result["existing_id"], "2401.12345")

    def test_add_duplicate_by_doi(self):
        add_paper(self.db_path, SAMPLE_PAPER)
        dup = {
            "id": "new_id",
            "source": "other",
            "title": "Different Title",
            "authors": [],
            "external_ids": {"arxiv": None, "doi": "10.1234/test"},
            "status": "candidate",
        }
        result = add_paper(self.db_path, dup)
        self.assertEqual(result["status"], "duplicate")

    def test_add_two_different_papers(self):
        r1 = add_paper(self.db_path, SAMPLE_PAPER)
        r2 = add_paper(self.db_path, SAMPLE_PAPER_2)
        self.assertEqual(r1["status"], "added")
        self.assertEqual(r2["status"], "added")


class TestUpdatePaper(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        init_db(self.db_path)
        add_paper(self.db_path, SAMPLE_PAPER)

    def test_update_relevance(self):
        result = update_paper(self.db_path, "2401.12345", {
            "relevance_score": 5,
            "relevance_rationale": "Core topic paper",
            "status": "shortlisted",
        })
        self.assertEqual(result["status"], "updated")

        papers = query_papers(self.db_path, status="shortlisted")
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["relevance_score"], 5)

    def test_update_full_text(self):
        result = update_paper(self.db_path, "2401.12345", {
            "full_text": "Full paper content here...",
            "content_source": "ar5iv",
        })
        self.assertEqual(result["status"], "updated")

    def test_update_invalid_field(self):
        result = update_paper(self.db_path, "2401.12345", {
            "nonexistent_field": "value",
        })
        self.assertEqual(result["status"], "error")


class TestQueryPapers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        init_db(self.db_path)
        add_paper(self.db_path, SAMPLE_PAPER)
        add_paper(self.db_path, SAMPLE_PAPER_2)
        update_paper(self.db_path, "2401.12345", {
            "relevance_score": 5, "status": "shortlisted",
        })
        update_paper(self.db_path, "2312.99999", {
            "relevance_score": 2, "status": "excluded",
        })

    def test_query_all(self):
        papers = query_papers(self.db_path)
        self.assertEqual(len(papers), 2)

    def test_query_by_status(self):
        papers = query_papers(self.db_path, status="shortlisted")
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["id"], "2401.12345")

    def test_query_by_min_relevance(self):
        papers = query_papers(self.db_path, min_relevance=3)
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["relevance_score"], 5)

    def test_query_returns_parsed_json_fields(self):
        papers = query_papers(self.db_path, status="shortlisted")
        self.assertIsInstance(papers[0]["authors"], list)
        self.assertIsInstance(papers[0]["external_ids"], dict)


class TestAddAnalysis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        init_db(self.db_path)
        add_paper(self.db_path, SAMPLE_PAPER)

    def test_add_analysis(self):
        result = add_analysis(self.db_path, "2401.12345", {
            "key_findings": ["LLMs can accelerate discovery", "Need domain adaptation"],
            "methodology": "Systematic review of 50 papers",
            "limitations": "Only English papers considered",
            "relevance_notes": "Core paper for our survey",
            "notable_refs": ["2301.00001", "2302.00002"],
            "raw_markdown": "# Analysis\n...",
        })
        self.assertEqual(result["status"], "added")

    def test_update_analysis(self):
        """Adding analysis for same paper should update (UPSERT)."""
        add_analysis(self.db_path, "2401.12345", {"key_findings": ["v1"]})
        add_analysis(self.db_path, "2401.12345", {"key_findings": ["v2"]})
        # Should not raise — UPSERT behavior


class TestQualityScores(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        init_db(self.db_path)

    def test_add_passing_score(self):
        result = add_quality_score(
            self.db_path, phase=2, phase_name="screening",
            iteration=1, score=0.8, threshold=0.6,
            dimensions={"completeness": 0.9, "rationale": 0.7},
            feedback="Good screening quality",
        )
        self.assertEqual(result["status"], "recorded")
        self.assertTrue(result["passed"])

    def test_add_failing_score(self):
        result = add_quality_score(
            self.db_path, phase=5, phase_name="writing",
            iteration=1, score=0.4, threshold=0.7,
            feedback="Draft incomplete",
        )
        self.assertFalse(result["passed"])

    def test_quality_history(self):
        add_quality_score(self.db_path, 2, "screening", 1, 0.5, 0.6)
        add_quality_score(self.db_path, 2, "screening", 2, 0.7, 0.6)
        add_quality_score(self.db_path, 3, "analysis", 1, 0.8, 0.6)

        history = get_quality_history(self.db_path, phase=2)
        self.assertEqual(len(history), 2)

        all_history = get_quality_history(self.db_path)
        self.assertEqual(len(all_history), 3)


class TestAgentMessages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        init_db(self.db_path)

    def test_add_broadcast_message(self):
        result = add_agent_message(
            self.db_path, from_agent="discovery", phase=1, iteration=1,
            message_type="finding",
            content="Found 15 papers on transformer architectures",
        )
        self.assertEqual(result["status"], "sent")
        self.assertIn("message_id", result)

    def test_add_directed_message(self):
        result = add_agent_message(
            self.db_path, from_agent="outline-architect", phase=4, iteration=1,
            message_type="decision", content="Using thematic organization",
            to_agent="writing-instructor",
            metadata={"outline_version": 2},
        )
        self.assertEqual(result["status"], "sent")

    def test_query_messages_by_phase(self):
        add_agent_message(self.db_path, "a", 1, 1, "finding", "msg1")
        add_agent_message(self.db_path, "b", 2, 1, "finding", "msg2")
        add_agent_message(self.db_path, "c", 1, 2, "finding", "msg3")

        msgs = query_messages(self.db_path, phase=1)
        self.assertEqual(len(msgs), 2)

    def test_query_messages_by_type(self):
        add_agent_message(self.db_path, "a", 1, 1, "finding", "msg1")
        add_agent_message(self.db_path, "a", 1, 1, "instruction", "msg2")

        msgs = query_messages(self.db_path, message_type="instruction")
        self.assertEqual(len(msgs), 1)

    def test_query_messages_for_agent(self):
        add_agent_message(self.db_path, "a", 1, 1, "finding", "broadcast")
        add_agent_message(self.db_path, "a", 1, 1, "instruction", "for-b",
                          to_agent="b")
        add_agent_message(self.db_path, "a", 1, 1, "instruction", "for-c",
                          to_agent="c")

        msgs = query_messages(self.db_path, to_agent="b")
        self.assertEqual(len(msgs), 2)  # broadcast + directed to b


class TestStats(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        init_db(self.db_path)
        add_paper(self.db_path, SAMPLE_PAPER)
        add_paper(self.db_path, SAMPLE_PAPER_2)
        update_paper(self.db_path, "2401.12345", {"status": "shortlisted"})
        add_quality_score(self.db_path, 2, "screening", 1, 0.8, 0.6)
        add_agent_message(self.db_path, "a", 1, 1, "finding", "msg")

    def test_stats(self):
        stats = get_stats(self.db_path)
        self.assertEqual(stats["total_papers"], 2)
        self.assertEqual(stats["by_status"]["shortlisted"], 1)
        self.assertEqual(stats["by_status"]["candidate"], 1)
        self.assertEqual(stats["total_quality_scores"], 1)
        self.assertEqual(stats["total_agent_messages"], 1)
        self.assertIn(2, stats["quality_summary"])


class TestEvidence(unittest.TestCase):
    """Tests for evidence extraction and querying."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        init_db(self.db_path)
        add_paper(self.db_path, {
            "id": "paper1", "source": "arxiv", "title": "Paper One",
            "authors": ["A"], "external_ids": {"arxiv": "1111"},
            "bibtex_key": "author2024one",
        })
        add_paper(self.db_path, {
            "id": "paper2", "source": "arxiv", "title": "Paper Two",
            "authors": ["B"], "external_ids": {"arxiv": "2222"},
            "bibtex_key": "author2024two",
        })

    def tearDown(self):
        Path(self.db_path).unlink()

    def test_add_evidence(self):
        result = add_evidence(self.db_path, "paper1", {
            "metric": "F1", "value": 0.94, "unit": "score",
            "dataset": "ToxicChat", "evidence_type": "measured",
            "source_location": "Table 2",
        })
        self.assertEqual(result["status"], "added")
        self.assertIn("id", result)

    def test_query_evidence_by_paper(self):
        add_evidence(self.db_path, "paper1", {
            "metric": "F1", "value": 0.94, "evidence_type": "measured",
        })
        add_evidence(self.db_path, "paper2", {
            "metric": "F1", "value": 0.89, "evidence_type": "measured",
        })
        results = query_evidence(self.db_path, paper_id="paper1")
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0]["value"], 0.94)

    def test_query_evidence_by_metric(self):
        add_evidence(self.db_path, "paper1", {
            "metric": "F1", "value": 0.94, "evidence_type": "measured",
        })
        add_evidence(self.db_path, "paper1", {
            "metric": "latency_ms", "value": 12.0, "evidence_type": "measured",
        })
        results = query_evidence(self.db_path, metric="latency_ms")
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0]["value"], 12.0)

    def test_query_evidence_by_type(self):
        add_evidence(self.db_path, "paper1", {
            "metric": "F1", "value": 0.94, "evidence_type": "measured",
        })
        add_evidence(self.db_path, "paper1", {
            "metric": "latency_ms", "value": 5.0, "evidence_type": "hypothesized",
        })
        measured = query_evidence(self.db_path, evidence_type="measured")
        self.assertEqual(len(measured), 1)
        hypothesized = query_evidence(self.db_path, evidence_type="hypothesized")
        self.assertEqual(len(hypothesized), 1)

    def test_evidence_with_baseline(self):
        add_evidence(self.db_path, "paper1", {
            "metric": "F1", "value": 0.94, "dataset": "ToxicChat",
            "baseline_name": "Llama Guard 2", "baseline_value": 0.89,
            "evidence_type": "measured", "source_location": "Table 2",
        })
        results = query_evidence(self.db_path, paper_id="paper1")
        self.assertEqual(results[0]["baseline_name"], "Llama Guard 2")
        self.assertAlmostEqual(results[0]["baseline_value"], 0.89)

    def test_evidence_matrix_only_measured(self):
        add_evidence(self.db_path, "paper1", {
            "metric": "F1", "value": 0.94, "evidence_type": "measured",
        })
        add_evidence(self.db_path, "paper2", {
            "metric": "F1", "value": 0.89, "evidence_type": "measured",
        })
        add_evidence(self.db_path, "paper1", {
            "metric": "F1", "value": 0.97, "evidence_type": "hypothesized",
        })
        matrix = evidence_matrix(self.db_path)
        self.assertEqual(matrix["total_entries"], 2)  # only measured
        self.assertIn("F1", matrix["matrix"])
        self.assertEqual(len(matrix["matrix"]["F1"]), 2)

    def test_evidence_matrix_filter_metric(self):
        add_evidence(self.db_path, "paper1", {
            "metric": "F1", "value": 0.94, "evidence_type": "measured",
        })
        add_evidence(self.db_path, "paper1", {
            "metric": "latency_ms", "value": 12.0, "evidence_type": "measured",
        })
        matrix = evidence_matrix(self.db_path, metric="latency_ms")
        self.assertEqual(len(matrix["metrics"]), 1)
        self.assertEqual(matrix["metrics"][0], "latency_ms")

    def test_evidence_in_stats(self):
        add_evidence(self.db_path, "paper1", {
            "metric": "F1", "value": 0.94, "evidence_type": "measured",
        })
        add_evidence(self.db_path, "paper1", {
            "metric": "recall", "value": 0.80, "evidence_type": "inferred",
        })
        stats = get_stats(self.db_path)
        self.assertEqual(stats["total_evidence"], 2)
        self.assertEqual(stats["evidence_by_type"]["measured"], 1)
        self.assertEqual(stats["evidence_by_type"]["inferred"], 1)


if __name__ == "__main__":
    unittest.main()
