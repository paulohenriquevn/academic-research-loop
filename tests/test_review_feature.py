#!/usr/bin/env python3
"""Tests for the review feature in paper_database.py."""

import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from paper_database import (
    add_review,
    get_review_stats,
    get_stats,
    init_db,
    query_reviews,
    update_review,
)


class TestReviewFeature(unittest.TestCase):
    """Tests for review CRUD operations."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        init_db(self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def _add_sample_review(self, item_id="R0.1", severity="critical",
                           category="architecture", action_type=None):
        return add_review(
            self.db_path,
            review_file="REVIEW-0.md",
            item_id=item_id,
            severity=severity,
            category=category,
            description="Runtime not specified",
            required_action="Define streaming runtime architecture",
            acceptance_criteria="Runtime section exists with session model",
            target_section="Section 5.2",
            action_type=action_type,
        )

    # ------------------------------------------------------------------
    # add_review
    # ------------------------------------------------------------------
    def test_add_review_returns_added(self):
        result = self._add_sample_review()
        self.assertEqual(result["status"], "added")
        self.assertEqual(result["item_id"], "R0.1")

    def test_add_review_assigns_id(self):
        result = self._add_sample_review()
        self.assertIn("id", result)
        self.assertIsInstance(result["id"], int)

    def test_add_multiple_reviews(self):
        self._add_sample_review(item_id="R0.1")
        self._add_sample_review(item_id="R0.2", severity="major")
        self._add_sample_review(item_id="R0.3", severity="minor")
        reviews = query_reviews(self.db_path)
        self.assertEqual(len(reviews), 3)

    def test_add_review_with_action_type(self):
        self._add_sample_review(item_id="R0.1", action_type="REVISE")
        reviews = query_reviews(self.db_path)
        self.assertEqual(reviews[0]["action_type"], "REVISE")

    def test_add_review_default_status_pending(self):
        self._add_sample_review()
        reviews = query_reviews(self.db_path)
        self.assertEqual(reviews[0]["status"], "pending")

    # ------------------------------------------------------------------
    # update_review
    # ------------------------------------------------------------------
    def test_update_review_action_type(self):
        self._add_sample_review()
        result = update_review(self.db_path, "R0.1", {"action_type": "EXPERIMENT"})
        self.assertEqual(result["status"], "updated")
        reviews = query_reviews(self.db_path)
        self.assertEqual(reviews[0]["action_type"], "EXPERIMENT")

    def test_update_review_status_resolved(self):
        self._add_sample_review()
        update_review(self.db_path, "R0.1", {
            "status": "resolved",
            "resolution_notes": "Added runtime section",
        })
        reviews = query_reviews(self.db_path)
        self.assertEqual(reviews[0]["status"], "resolved")
        self.assertIsNotNone(reviews[0]["resolved_at"])

    def test_update_review_version_introduced(self):
        self._add_sample_review()
        update_review(self.db_path, "R0.1", {"version_introduced": 2})
        reviews = query_reviews(self.db_path)
        self.assertEqual(reviews[0]["version_introduced"], 2)

    def test_update_review_invalid_fields_ignored(self):
        self._add_sample_review()
        result = update_review(self.db_path, "R0.1", {"invalid_field": "value"})
        self.assertEqual(result["status"], "error")

    # ------------------------------------------------------------------
    # query_reviews
    # ------------------------------------------------------------------
    def test_query_reviews_all(self):
        self._add_sample_review(item_id="R0.1")
        self._add_sample_review(item_id="R0.2", severity="major")
        reviews = query_reviews(self.db_path)
        self.assertEqual(len(reviews), 2)

    def test_query_reviews_by_status(self):
        self._add_sample_review(item_id="R0.1")
        self._add_sample_review(item_id="R0.2")
        update_review(self.db_path, "R0.1", {"status": "resolved"})
        pending = query_reviews(self.db_path, status="pending")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["item_id"], "R0.2")

    def test_query_reviews_by_severity(self):
        self._add_sample_review(item_id="R0.1", severity="critical")
        self._add_sample_review(item_id="R0.2", severity="minor")
        critical = query_reviews(self.db_path, severity="critical")
        self.assertEqual(len(critical), 1)

    def test_query_reviews_by_action_type(self):
        self._add_sample_review(item_id="R0.1", action_type="REVISE")
        self._add_sample_review(item_id="R0.2", action_type="EXPERIMENT")
        revise = query_reviews(self.db_path, action_type="REVISE")
        self.assertEqual(len(revise), 1)
        self.assertEqual(revise[0]["item_id"], "R0.1")

    def test_query_reviews_by_review_file(self):
        self._add_sample_review(item_id="R0.1")
        add_review(
            self.db_path, review_file="REVIEW-1.md", item_id="R1.1",
            severity="major", category="coverage",
            description="Missing topic", required_action="Add section",
            acceptance_criteria="Section exists",
        )
        file0 = query_reviews(self.db_path, review_file="REVIEW-0.md")
        self.assertEqual(len(file0), 1)

    def test_query_reviews_ordered_by_severity(self):
        self._add_sample_review(item_id="R0.1", severity="minor")
        self._add_sample_review(item_id="R0.2", severity="critical")
        self._add_sample_review(item_id="R0.3", severity="major")
        reviews = query_reviews(self.db_path)
        severities = [r["severity"] for r in reviews]
        self.assertEqual(severities, ["critical", "major", "minor"])

    # ------------------------------------------------------------------
    # get_review_stats
    # ------------------------------------------------------------------
    def test_review_stats_empty(self):
        stats = get_review_stats(self.db_path)
        self.assertEqual(stats["total"], 0)

    def test_review_stats_with_data(self):
        self._add_sample_review(item_id="R0.1", severity="critical", action_type="REVISE")
        self._add_sample_review(item_id="R0.2", severity="major", action_type="EXPERIMENT")
        self._add_sample_review(item_id="R0.3", severity="minor", action_type="REVISE")
        update_review(self.db_path, "R0.1", {"status": "resolved"})
        stats = get_review_stats(self.db_path)
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["by_severity"]["critical"], 1)
        self.assertEqual(stats["by_severity"]["major"], 1)
        self.assertEqual(stats["by_status"]["resolved"], 1)
        self.assertEqual(stats["by_status"]["pending"], 2)
        self.assertEqual(stats["by_action"]["REVISE"], 2)
        self.assertEqual(stats["by_action"]["EXPERIMENT"], 1)

    # ------------------------------------------------------------------
    # get_stats includes reviews
    # ------------------------------------------------------------------
    def test_get_stats_includes_reviews(self):
        self._add_sample_review()
        stats = get_stats(self.db_path)
        self.assertIn("total_reviews", stats)
        self.assertEqual(stats["total_reviews"], 1)

    # ------------------------------------------------------------------
    # Schema version
    # ------------------------------------------------------------------
    def test_schema_version_is_3(self):
        conn = sqlite3.connect(self.db_path)
        version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
        conn.close()
        self.assertEqual(version, 3)

    def test_reviews_table_exists(self):
        conn = sqlite3.connect(self.db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        self.assertIn("reviews", tables)


class TestReviewCLI(unittest.TestCase):
    """Tests for review CLI subcommands."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        init_db(self.db_path)
        self.script = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "paper_database.py"
        )

    def tearDown(self):
        os.unlink(self.db_path)

    def _run_cli(self, args):
        import subprocess
        result = subprocess.run(
            [sys.executable, self.script] + args,
            capture_output=True, text=True,
        )
        return result

    def test_cli_add_review(self):
        result = self._run_cli([
            "add-review", "--db-path", self.db_path,
            "--review-file", "REVIEW-0.md",
            "--item-id", "R0.1",
            "--severity", "critical",
            "--category", "architecture",
            "--description", "Runtime not specified",
            "--required-action", "Define runtime",
            "--acceptance-criteria", "Runtime section exists",
            "--target-section", "Section 5",
        ])
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "added")

    def test_cli_query_reviews(self):
        add_review(
            self.db_path, "REVIEW-0.md", "R0.1", "critical", "architecture",
            "Problem", "Fix it", "Verify fix",
        )
        result = self._run_cli([
            "query-reviews", "--db-path", self.db_path,
            "--severity", "critical",
        ])
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(len(output), 1)

    def test_cli_update_review(self):
        add_review(
            self.db_path, "REVIEW-0.md", "R0.1", "critical", "architecture",
            "Problem", "Fix it", "Verify fix",
        )
        result = self._run_cli([
            "update-review", "--db-path", self.db_path,
            "--item-id", "R0.1",
            "--updates-json", '{"action_type": "REVISE", "status": "resolved"}',
        ])
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "updated")

    def test_cli_review_stats(self):
        add_review(
            self.db_path, "REVIEW-0.md", "R0.1", "critical", "architecture",
            "Problem", "Fix it", "Verify fix", action_type="REVISE",
        )
        result = self._run_cli([
            "review-stats", "--db-path", self.db_path,
        ])
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["total"], 1)


if __name__ == "__main__":
    unittest.main()
