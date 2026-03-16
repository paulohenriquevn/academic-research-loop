#!/usr/bin/env python3
"""
SQLite paper database for the Academic Research Loop plugin.

Replaces flat JSON files with a proper relational database for papers,
analyses, quality scores, and agent messages.

Usage:
    python3 paper_database.py init --db-path research.db
    python3 paper_database.py add-paper --db-path research.db --paper-json '{...}'
    python3 paper_database.py add-analysis --db-path research.db --paper-id ID --analysis-json '{...}'
    python3 paper_database.py add-quality-score --db-path research.db --phase N --score 0.85 --details '{...}'
    python3 paper_database.py query --db-path research.db --status shortlisted [--min-relevance 3]
    python3 paper_database.py export --db-path research.db --format json --status candidate
    python3 paper_database.py stats --db-path research.db
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SCHEMA_VERSION = 2

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    authors TEXT NOT NULL,          -- JSON array
    abstract TEXT,
    published TEXT,
    updated TEXT,
    year INTEGER,
    categories TEXT,                -- JSON array
    venue TEXT,
    citation_count INTEGER,
    pdf_url TEXT,
    web_url TEXT,
    external_ids TEXT NOT NULL,     -- JSON object
    bibtex_key TEXT,
    relevance_score INTEGER,
    relevance_rationale TEXT,
    status TEXT NOT NULL DEFAULT 'candidate',
    full_text TEXT,                 -- extracted full text (if available)
    content_source TEXT,            -- how full text was obtained
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL REFERENCES papers(id),
    key_findings TEXT,             -- JSON array
    methodology TEXT,
    limitations TEXT,
    relevance_notes TEXT,
    notable_refs TEXT,             -- JSON array of paper IDs to follow
    raw_markdown TEXT,             -- full analysis markdown
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(paper_id)
);

CREATE TABLE IF NOT EXISTS quality_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase INTEGER NOT NULL,
    phase_name TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    score REAL NOT NULL,           -- 0.0 to 1.0
    passed INTEGER NOT NULL,       -- 1 if score >= threshold, 0 otherwise
    threshold REAL NOT NULL,
    dimensions TEXT,               -- JSON object {dimension: score}
    feedback TEXT,                 -- evaluator feedback
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_agent TEXT NOT NULL,
    to_agent TEXT,                  -- NULL = broadcast to all
    phase INTEGER NOT NULL,
    iteration INTEGER NOT NULL,
    message_type TEXT NOT NULL,     -- 'finding', 'instruction', 'feedback', 'question', 'decision'
    content TEXT NOT NULL,
    metadata TEXT,                  -- JSON object for structured data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL REFERENCES papers(id),
    metric TEXT NOT NULL,              -- e.g. "F1", "recall", "latency_ms", "EM"
    value REAL NOT NULL,               -- numeric value
    unit TEXT,                         -- e.g. "ms", "%", "score"
    dataset TEXT,                      -- e.g. "ToxicChat", "HotpotQA"
    baseline_name TEXT,                -- what was compared against
    baseline_value REAL,               -- baseline numeric value
    conditions TEXT,                   -- e.g. "T5-large, 100 passages, English"
    evidence_type TEXT NOT NULL DEFAULT 'measured',  -- measured/inferred/hypothesized
    source_location TEXT,              -- e.g. "Table 2", "Figure 3", "Section 4.2"
    notes TEXT,                        -- any caveats or context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);
CREATE INDEX IF NOT EXISTS idx_papers_relevance ON papers(relevance_score);
CREATE INDEX IF NOT EXISTS idx_analyses_paper_id ON analyses(paper_id);
CREATE INDEX IF NOT EXISTS idx_quality_phase ON quality_scores(phase);
CREATE INDEX IF NOT EXISTS idx_messages_phase ON agent_messages(phase);
CREATE INDEX IF NOT EXISTS idx_messages_type ON agent_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_evidence_paper ON evidence(paper_id);
CREATE INDEX IF NOT EXISTS idx_evidence_metric ON evidence(metric);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Create a database connection with WAL mode for concurrent reads."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    """Initialize the database schema."""
    conn = get_connection(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
        (SCHEMA_VERSION,),
    )
    conn.commit()
    conn.close()


def add_paper(db_path: str, paper: dict) -> dict:
    """Add a paper to the database. Returns status and paper ID."""
    conn = get_connection(db_path)

    # Check for duplicates by external IDs
    ext_ids = paper.get("external_ids", {})
    arxiv_id = ext_ids.get("arxiv")
    doi = ext_ids.get("doi")

    existing = None
    if arxiv_id:
        row = conn.execute(
            "SELECT id FROM papers WHERE external_ids LIKE ?",
            (f'%"arxiv": "{arxiv_id}"%',),
        ).fetchone()
        if row:
            existing = row["id"]

    if not existing and doi:
        row = conn.execute(
            "SELECT id FROM papers WHERE external_ids LIKE ?",
            (f'%"doi": "{doi}"%',),
        ).fetchone()
        if row:
            existing = row["id"]

    if existing:
        conn.close()
        return {"status": "duplicate", "existing_id": existing}

    paper_id = paper.get("id", "")
    conn.execute(
        """INSERT INTO papers (id, source, title, authors, abstract, published,
           updated, year, categories, venue, citation_count, pdf_url, web_url,
           external_ids, bibtex_key, relevance_score, relevance_rationale, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            paper_id,
            paper.get("source", ""),
            paper.get("title", ""),
            json.dumps(paper.get("authors", [])),
            paper.get("abstract"),
            paper.get("published"),
            paper.get("updated"),
            paper.get("year"),
            json.dumps(paper.get("categories", [])),
            paper.get("venue"),
            paper.get("citation_count"),
            paper.get("pdf_url"),
            paper.get("web_url"),
            json.dumps(ext_ids),
            paper.get("bibtex_key"),
            paper.get("relevance_score"),
            paper.get("relevance_rationale"),
            paper.get("status", "candidate"),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "added", "id": paper_id}


def update_paper(db_path: str, paper_id: str, updates: dict) -> dict:
    """Update specific fields of a paper."""
    conn = get_connection(db_path)

    allowed_fields = {
        "relevance_score", "relevance_rationale", "status", "bibtex_key",
        "full_text", "content_source",
    }
    set_clauses = []
    values = []
    for field, value in updates.items():
        if field in allowed_fields:
            set_clauses.append(f"{field} = ?")
            values.append(value)

    if not set_clauses:
        conn.close()
        return {"status": "error", "message": "no valid fields to update"}

    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    values.append(paper_id)

    conn.execute(
        f"UPDATE papers SET {', '.join(set_clauses)} WHERE id = ?", values
    )
    conn.commit()
    conn.close()
    return {"status": "updated", "id": paper_id}


def add_analysis(db_path: str, paper_id: str, analysis: dict) -> dict:
    """Add or update an analysis for a paper."""
    conn = get_connection(db_path)

    conn.execute(
        """INSERT OR REPLACE INTO analyses
           (paper_id, key_findings, methodology, limitations,
            relevance_notes, notable_refs, raw_markdown)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            paper_id,
            json.dumps(analysis.get("key_findings", [])),
            analysis.get("methodology", ""),
            analysis.get("limitations", ""),
            analysis.get("relevance_notes", ""),
            json.dumps(analysis.get("notable_refs", [])),
            analysis.get("raw_markdown", ""),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "added", "paper_id": paper_id}


def add_quality_score(db_path: str, phase: int, phase_name: str,
                      iteration: int, score: float, threshold: float,
                      dimensions: dict | None = None,
                      feedback: str = "") -> dict:
    """Record a quality evaluation score for a phase output."""
    passed = 1 if score >= threshold else 0
    conn = get_connection(db_path)
    conn.execute(
        """INSERT INTO quality_scores
           (phase, phase_name, iteration, score, passed, threshold, dimensions, feedback)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            phase, phase_name, iteration, score, passed, threshold,
            json.dumps(dimensions or {}), feedback,
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "recorded", "passed": bool(passed), "score": score}


def add_agent_message(db_path: str, from_agent: str, phase: int,
                      iteration: int, message_type: str, content: str,
                      to_agent: str | None = None,
                      metadata: dict | None = None) -> dict:
    """Record an inter-agent message."""
    conn = get_connection(db_path)
    conn.execute(
        """INSERT INTO agent_messages
           (from_agent, to_agent, phase, iteration, message_type, content, metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (from_agent, to_agent, phase, iteration, message_type, content,
         json.dumps(metadata or {})),
    )
    conn.commit()
    msg_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"status": "sent", "message_id": msg_id}


def query_papers(db_path: str, status: str | None = None,
                 min_relevance: int | None = None) -> list[dict]:
    """Query papers with optional filters."""
    conn = get_connection(db_path)

    query = "SELECT * FROM papers WHERE 1=1"
    params: list = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if min_relevance is not None:
        query += " AND relevance_score >= ?"
        params.append(min_relevance)

    query += " ORDER BY relevance_score DESC NULLS LAST, citation_count DESC NULLS LAST"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [_row_to_paper(row) for row in rows]


def query_messages(db_path: str, phase: int | None = None,
                   to_agent: str | None = None,
                   message_type: str | None = None) -> list[dict]:
    """Query agent messages with optional filters."""
    conn = get_connection(db_path)

    query = "SELECT * FROM agent_messages WHERE 1=1"
    params: list = []

    if phase is not None:
        query += " AND phase = ?"
        params.append(phase)
    if to_agent:
        query += " AND (to_agent = ? OR to_agent IS NULL)"
        params.append(to_agent)
    if message_type:
        query += " AND message_type = ?"
        params.append(message_type)

    query += " ORDER BY created_at ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]


def add_evidence(db_path: str, paper_id: str, evidence: dict) -> dict:
    """Add a quantitative evidence entry for a paper."""
    conn = get_connection(db_path)
    conn.execute(
        """INSERT INTO evidence
           (paper_id, metric, value, unit, dataset, baseline_name, baseline_value,
            conditions, evidence_type, source_location, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            paper_id,
            evidence.get("metric", ""),
            evidence.get("value", 0),
            evidence.get("unit"),
            evidence.get("dataset"),
            evidence.get("baseline_name"),
            evidence.get("baseline_value"),
            evidence.get("conditions"),
            evidence.get("evidence_type", "measured"),
            evidence.get("source_location"),
            evidence.get("notes"),
        ),
    )
    conn.commit()
    eid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return {"status": "added", "id": eid, "paper_id": paper_id}


def query_evidence(db_path: str, paper_id: str | None = None,
                   metric: str | None = None,
                   evidence_type: str | None = None) -> list[dict]:
    """Query evidence entries with optional filters."""
    conn = get_connection(db_path)
    query = """SELECT e.*, p.bibtex_key, p.title as paper_title
               FROM evidence e JOIN papers p ON e.paper_id = p.id WHERE 1=1"""
    params: list = []
    if paper_id:
        query += " AND e.paper_id = ?"
        params.append(paper_id)
    if metric:
        query += " AND e.metric = ?"
        params.append(metric)
    if evidence_type:
        query += " AND e.evidence_type = ?"
        params.append(evidence_type)
    query += " ORDER BY e.metric, e.paper_id"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def evidence_matrix(db_path: str, metric: str | None = None) -> dict:
    """Build a cross-paper evidence matrix.

    Returns a matrix structure: {metric: [{paper, value, dataset, baseline, ...}]}
    Only includes MEASURED evidence by default.
    """
    conn = get_connection(db_path)
    query = """SELECT e.*, p.bibtex_key, p.title as paper_title
               FROM evidence e JOIN papers p ON e.paper_id = p.id
               WHERE e.evidence_type = 'measured'"""
    params: list = []
    if metric:
        query += " AND e.metric = ?"
        params.append(metric)
    query += " ORDER BY e.metric, e.value DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    matrix: dict[str, list[dict]] = {}
    for row in rows:
        d = dict(row)
        m = d["metric"]
        if m not in matrix:
            matrix[m] = []
        matrix[m].append(d)

    return {
        "status": "ok",
        "metrics": list(matrix.keys()),
        "total_entries": sum(len(v) for v in matrix.values()),
        "matrix": matrix,
    }


def get_quality_history(db_path: str, phase: int | None = None) -> list[dict]:
    """Get quality score history, optionally filtered by phase."""
    conn = get_connection(db_path)

    query = "SELECT * FROM quality_scores"
    params: list = []
    if phase is not None:
        query += " WHERE phase = ?"
        params.append(phase)
    query += " ORDER BY created_at ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stats(db_path: str) -> dict:
    """Get database statistics."""
    conn = get_connection(db_path)

    stats = {}
    stats["total_papers"] = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    stats["by_status"] = {}
    for row in conn.execute("SELECT status, COUNT(*) as cnt FROM papers GROUP BY status"):
        stats["by_status"][row["status"]] = row["cnt"]

    stats["total_analyses"] = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    stats["total_quality_scores"] = conn.execute("SELECT COUNT(*) FROM quality_scores").fetchone()[0]
    stats["total_agent_messages"] = conn.execute("SELECT COUNT(*) FROM agent_messages").fetchone()[0]
    stats["total_evidence"] = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
    stats["evidence_by_type"] = {}
    for row in conn.execute("SELECT evidence_type, COUNT(*) as cnt FROM evidence GROUP BY evidence_type"):
        stats["evidence_by_type"][row["evidence_type"]] = row["cnt"]

    # Quality scores summary
    stats["quality_summary"] = {}
    for row in conn.execute(
        "SELECT phase, phase_name, AVG(score) as avg_score, COUNT(*) as attempts, "
        "SUM(passed) as passes FROM quality_scores GROUP BY phase"
    ):
        stats["quality_summary"][row["phase"]] = {
            "phase_name": row["phase_name"],
            "avg_score": round(row["avg_score"], 3),
            "attempts": row["attempts"],
            "passes": row["passes"],
        }

    conn.close()
    return stats


def _row_to_paper(row: sqlite3.Row) -> dict:
    """Convert a database row to a paper dict."""
    d = dict(row)
    for json_field in ("authors", "categories", "external_ids"):
        if d.get(json_field):
            d[json_field] = json.loads(d[json_field])
    return d


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Academic paper database")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    init_p = subparsers.add_parser("init", help="Initialize database")
    init_p.add_argument("--db-path", required=True)

    # add-paper
    ap = subparsers.add_parser("add-paper", help="Add a paper")
    ap.add_argument("--db-path", required=True)
    ap.add_argument("--paper-json", required=True)

    # update-paper
    up = subparsers.add_parser("update-paper", help="Update paper fields")
    up.add_argument("--db-path", required=True)
    up.add_argument("--paper-id", required=True)
    up.add_argument("--updates-json", required=True)

    # add-analysis
    aa = subparsers.add_parser("add-analysis", help="Add paper analysis")
    aa.add_argument("--db-path", required=True)
    aa.add_argument("--paper-id", required=True)
    aa.add_argument("--analysis-json", required=True)

    # add-quality-score
    aq = subparsers.add_parser("add-quality-score", help="Record quality score")
    aq.add_argument("--db-path", required=True)
    aq.add_argument("--phase", type=int, required=True)
    aq.add_argument("--phase-name", required=True)
    aq.add_argument("--iteration", type=int, required=True)
    aq.add_argument("--score", type=float, required=True)
    aq.add_argument("--threshold", type=float, default=0.6)
    aq.add_argument("--dimensions-json", default="{}")
    aq.add_argument("--feedback", default="")

    # add-message
    am = subparsers.add_parser("add-message", help="Record agent message")
    am.add_argument("--db-path", required=True)
    am.add_argument("--from-agent", required=True)
    am.add_argument("--phase", type=int, required=True)
    am.add_argument("--iteration", type=int, required=True)
    am.add_argument("--message-type", required=True,
                    choices=["finding", "instruction", "feedback", "question", "decision", "meeting_minutes"])
    am.add_argument("--content", required=True)
    am.add_argument("--to-agent", default=None)
    am.add_argument("--metadata-json", default="{}")

    # query
    qp = subparsers.add_parser("query", help="Query papers")
    qp.add_argument("--db-path", required=True)
    qp.add_argument("--status", default=None)
    qp.add_argument("--min-relevance", type=int, default=None)

    # query-messages
    qm = subparsers.add_parser("query-messages", help="Query agent messages")
    qm.add_argument("--db-path", required=True)
    qm.add_argument("--phase", type=int, default=None)
    qm.add_argument("--to-agent", default=None)
    qm.add_argument("--message-type", default=None)

    # add-evidence
    ae = subparsers.add_parser("add-evidence", help="Add quantitative evidence entry")
    ae.add_argument("--db-path", required=True)
    ae.add_argument("--paper-id", required=True)
    ae.add_argument("--evidence-json", required=True,
                    help='JSON: {"metric":"F1","value":0.94,"dataset":"ToxicChat","evidence_type":"measured",...}')

    # query-evidence
    qe = subparsers.add_parser("query-evidence", help="Query evidence entries")
    qe.add_argument("--db-path", required=True)
    qe.add_argument("--paper-id", default=None)
    qe.add_argument("--metric", default=None)
    qe.add_argument("--evidence-type", default=None,
                    choices=["measured", "inferred", "hypothesized"])

    # evidence-matrix
    em = subparsers.add_parser("evidence-matrix",
                                help="Build cross-paper evidence matrix (measured only)")
    em.add_argument("--db-path", required=True)
    em.add_argument("--metric", default=None, help="Filter by specific metric")

    # quality-history
    qh = subparsers.add_parser("quality-history", help="Get quality scores")
    qh.add_argument("--db-path", required=True)
    qh.add_argument("--phase", type=int, default=None)

    # stats
    sp = subparsers.add_parser("stats", help="Database statistics")
    sp.add_argument("--db-path", required=True)

    # export
    ep = subparsers.add_parser("export", help="Export papers as JSON")
    ep.add_argument("--db-path", required=True)
    ep.add_argument("--status", default=None)
    ep.add_argument("--format", choices=["json"], default="json")

    args = parser.parse_args()

    if args.command == "init":
        init_db(args.db_path)
        json.dump({"status": "initialized", "path": args.db_path}, sys.stdout, indent=2)

    elif args.command == "add-paper":
        result = add_paper(args.db_path, json.loads(args.paper_json))
        json.dump(result, sys.stdout, indent=2)

    elif args.command == "update-paper":
        result = update_paper(args.db_path, args.paper_id, json.loads(args.updates_json))
        json.dump(result, sys.stdout, indent=2)

    elif args.command == "add-analysis":
        result = add_analysis(args.db_path, args.paper_id, json.loads(args.analysis_json))
        json.dump(result, sys.stdout, indent=2)

    elif args.command == "add-quality-score":
        result = add_quality_score(
            args.db_path, args.phase, args.phase_name, args.iteration,
            args.score, args.threshold,
            json.loads(args.dimensions_json), args.feedback,
        )
        json.dump(result, sys.stdout, indent=2)

    elif args.command == "add-message":
        result = add_agent_message(
            args.db_path, args.from_agent, args.phase, args.iteration,
            args.message_type, args.content, args.to_agent,
            json.loads(args.metadata_json),
        )
        json.dump(result, sys.stdout, indent=2)

    elif args.command == "query":
        papers = query_papers(args.db_path, args.status, args.min_relevance)
        json.dump(papers, sys.stdout, indent=2)

    elif args.command == "query-messages":
        messages = query_messages(args.db_path, args.phase, args.to_agent, args.message_type)
        json.dump(messages, sys.stdout, indent=2)

    elif args.command == "add-evidence":
        result = add_evidence(args.db_path, args.paper_id, json.loads(args.evidence_json))
        json.dump(result, sys.stdout, indent=2)

    elif args.command == "query-evidence":
        results = query_evidence(args.db_path, args.paper_id, args.metric, args.evidence_type)
        json.dump(results, sys.stdout, indent=2)

    elif args.command == "evidence-matrix":
        matrix = evidence_matrix(args.db_path, args.metric)
        json.dump(matrix, sys.stdout, indent=2)

    elif args.command == "quality-history":
        history = get_quality_history(args.db_path, args.phase)
        json.dump(history, sys.stdout, indent=2)

    elif args.command == "stats":
        stats = get_stats(args.db_path)
        json.dump(stats, sys.stdout, indent=2)

    elif args.command == "export":
        papers = query_papers(args.db_path, args.status)
        json.dump(papers, sys.stdout, indent=2)

    print()


if __name__ == "__main__":
    main()
