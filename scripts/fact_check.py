#!/usr/bin/env python3
"""
Fact-checking utility for the Academic Research Loop plugin.

Cross-references claims in the draft against the paper database and analyses
to verify that citations actually support the claims being made.

Usage:
    python3 fact_check.py check --draft-file draft.md --db-path research.db --bib-file references.bib
    python3 fact_check.py extract-claims --draft-file draft.md
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path


def extract_cited_passages(draft_text: str) -> list[dict]:
    """Extract passages that contain citations from the draft.

    Returns a list of dicts with:
      - text: the sentence or passage containing the citation
      - cited_keys: list of BibTeX keys cited in this passage
      - line_number: approximate line number in the draft
    """
    passages = []
    lines = draft_text.split("\n")

    for i, line in enumerate(lines, 1):
        # Find all [@key] or [@key1; @key2] citations in this line
        citation_matches = re.findall(r"\[@([^\]]+)\]", line)

        if not citation_matches:
            continue

        keys = []
        for match in citation_matches:
            # Handle multiple keys: [@key1; @key2]
            for part in match.split(";"):
                key = part.strip().lstrip("@")
                if key:
                    keys.append(key)

        if keys:
            passages.append({
                "text": line.strip(),
                "cited_keys": keys,
                "line_number": i,
            })

    return passages


def load_paper_abstracts(db_path: str) -> dict[str, dict]:
    """Load paper abstracts and titles from database, keyed by bibtex_key."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT bibtex_key, title, abstract, full_text FROM papers WHERE bibtex_key IS NOT NULL"
    ).fetchall()
    conn.close()

    papers = {}
    for row in rows:
        key = row["bibtex_key"]
        papers[key] = {
            "title": row["title"],
            "abstract": row["abstract"] or "",
            "full_text": row["full_text"] or "",
        }
    return papers


def load_analyses(db_path: str) -> dict[str, dict]:
    """Load paper analyses from database, keyed by paper_id."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Join to get bibtex_key
    rows = conn.execute(
        """SELECT a.*, p.bibtex_key FROM analyses a
           JOIN papers p ON a.paper_id = p.id
           WHERE p.bibtex_key IS NOT NULL"""
    ).fetchall()
    conn.close()

    analyses = {}
    for row in rows:
        key = row["bibtex_key"]
        analyses[key] = {
            "key_findings": json.loads(row["key_findings"]) if row["key_findings"] else [],
            "methodology": row["methodology"] or "",
            "limitations": row["limitations"] or "",
            "relevance_notes": row["relevance_notes"] or "",
        }
    return analyses


def check_claim_support(passage: dict, papers: dict[str, dict],
                        analyses: dict[str, dict]) -> dict:
    """Check if cited papers plausibly support the passage's claims.

    Returns a verification result with confidence level.
    """
    issues = []
    verified_keys = []
    missing_keys = []

    for key in passage["cited_keys"]:
        if key not in papers:
            missing_keys.append(key)
            issues.append({
                "type": "missing_reference",
                "key": key,
                "message": f"Citation [@{key}] not found in paper database",
            })
            continue

        paper = papers[key]
        analysis = analyses.get(key, {})

        # Check if there's any topical overlap between the passage and the paper
        passage_lower = passage["text"].lower()
        paper_text = f"{paper['title']} {paper['abstract']}".lower()
        analysis_text = " ".join(analysis.get("key_findings", [])).lower()

        # Simple keyword overlap check
        passage_words = set(re.findall(r"\b\w{4,}\b", passage_lower))
        paper_words = set(re.findall(r"\b\w{4,}\b", paper_text + " " + analysis_text))

        overlap = passage_words & paper_words
        overlap_ratio = len(overlap) / max(len(passage_words), 1)

        if overlap_ratio < 0.1:
            issues.append({
                "type": "weak_support",
                "key": key,
                "message": f"Citation [@{key}] ('{paper['title'][:60]}...') has low topical overlap with the claim",
                "overlap_ratio": round(overlap_ratio, 3),
            })
        else:
            verified_keys.append(key)

    return {
        "passage": passage["text"][:200],
        "line_number": passage["line_number"],
        "cited_keys": passage["cited_keys"],
        "verified_keys": verified_keys,
        "missing_keys": missing_keys,
        "issues": issues,
        "confidence": "high" if not issues else ("low" if missing_keys else "medium"),
    }


def run_fact_check(draft_path: str, db_path: str) -> dict:
    """Run full fact-check on a draft against the paper database."""
    draft_text = Path(draft_path).read_text(encoding="utf-8")

    passages = extract_cited_passages(draft_text)

    if not passages:
        return {
            "status": "no_citations",
            "message": "No citations found in draft",
            "total_passages": 0,
        }

    papers = load_paper_abstracts(db_path)
    analyses = load_analyses(db_path)

    results = []
    for passage in passages:
        result = check_claim_support(passage, papers, analyses)
        results.append(result)

    # Aggregate
    total = len(results)
    high_confidence = sum(1 for r in results if r["confidence"] == "high")
    medium_confidence = sum(1 for r in results if r["confidence"] == "medium")
    low_confidence = sum(1 for r in results if r["confidence"] == "low")

    all_issues = [issue for r in results for issue in r["issues"]]
    missing_refs = [i for i in all_issues if i["type"] == "missing_reference"]
    weak_supports = [i for i in all_issues if i["type"] == "weak_support"]

    return {
        "status": "complete",
        "total_cited_passages": total,
        "confidence_breakdown": {
            "high": high_confidence,
            "medium": medium_confidence,
            "low": low_confidence,
        },
        "overall_score": round(high_confidence / max(total, 1), 3),
        "issues_summary": {
            "missing_references": len(missing_refs),
            "weak_support": len(weak_supports),
            "total_issues": len(all_issues),
        },
        "issues": all_issues,
        "detailed_results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fact-check draft citations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    check_p = subparsers.add_parser("check", help="Run fact-check on draft")
    check_p.add_argument("--draft-file", required=True)
    check_p.add_argument("--db-path", required=True)

    # extract-claims
    extract_p = subparsers.add_parser("extract-claims",
                                      help="Extract cited passages from draft")
    extract_p.add_argument("--draft-file", required=True)

    args = parser.parse_args()

    if args.command == "check":
        result = run_fact_check(args.draft_file, args.db_path)
        json.dump(result, sys.stdout, indent=2)

    elif args.command == "extract-claims":
        draft_text = Path(args.draft_file).read_text(encoding="utf-8")
        passages = extract_cited_passages(draft_text)
        json.dump(passages, sys.stdout, indent=2)

    print()


if __name__ == "__main__":
    main()
