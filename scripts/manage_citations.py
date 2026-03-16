#!/usr/bin/env python3
"""
BibTeX citation manager for the Academic Research Loop plugin.

Handles BibTeX key generation, entry creation, deduplication, and validation.
No external dependencies — uses only Python stdlib.

Usage:
    python3 manage_citations.py generate-key --title "Paper Title" --authors '["Author A"]' --year 2024
    python3 manage_citations.py add --paper-json '{"title":...}' --bib-file references.bib
    python3 manage_citations.py validate --bib-file references.bib [--draft-file draft.md]
    python3 manage_citations.py list --bib-file references.bib
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


def normalize_ascii(text: str) -> str:
    """Convert unicode text to closest ASCII representation."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def extract_last_name(author: str) -> str:
    """Extract last name from an author string.

    Handles formats:
        "John Smith" -> "smith"
        "Smith, John" -> "smith"
        "J. Smith" -> "smith"
        "Smith" -> "smith"
    """
    author = author.strip()
    if not author:
        return "unknown"

    if "," in author:
        last_name = author.split(",")[0].strip()
    else:
        parts = author.split()
        last_name = parts[-1] if parts else "unknown"

    return normalize_ascii(last_name).lower()


def generate_bibtex_key(title: str, authors: list[str],
                        year: int | None) -> str:
    """Generate a BibTeX citation key: firstauthorlastname + year + firsttitleword.

    Examples:
        ("Large Language Models", ["John Smith"], 2024) -> "smith2024large"
        ("Attention Is All You Need", ["A. Vaswani"], 2017) -> "vaswani2017attention"
    """
    last_name = extract_last_name(authors[0]) if authors else "unknown"

    # Clean last name to only alphanumeric
    last_name = re.sub(r"[^a-z]", "", last_name)
    if not last_name:
        last_name = "unknown"

    year_str = str(year) if year else "nd"

    # First significant word from title (skip articles and prepositions)
    skip_words = {"a", "an", "the", "of", "for", "in", "on", "to", "and",
                  "with", "by", "from", "at", "is", "are", "was", "were"}
    title_words = re.findall(r"[a-zA-Z]+", title)
    first_word = "untitled"
    for word in title_words:
        if word.lower() not in skip_words:
            first_word = word.lower()
            break

    return f"{last_name}{year_str}{first_word}"


def format_bibtex_authors(authors: list[str]) -> str:
    """Format author list for BibTeX: 'Last, First and Last, First'."""
    formatted = []
    for author in authors:
        author = author.strip()
        if "," in author:
            formatted.append(author)
        else:
            parts = author.split()
            if len(parts) >= 2:
                formatted.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
            else:
                formatted.append(author)
    return " and ".join(formatted)


def escape_bibtex(text: str) -> str:
    """Escape special BibTeX characters."""
    # Replace & with \& but not if already escaped
    text = re.sub(r"(?<!\\)&", r"\\&", text)
    text = re.sub(r"(?<!\\)%", r"\\%", text)
    text = re.sub(r"(?<!\\)#", r"\\#", text)
    return text


def detect_entry_type(paper: dict) -> str:
    """Detect BibTeX entry type based on paper metadata."""
    venue = (paper.get("venue") or "").lower()

    conference_keywords = ["conference", "proceedings", "workshop", "symposium",
                           "neurips", "icml", "iclr", "aaai", "cvpr", "acl",
                           "emnlp", "naacl", "sigir", "www", "kdd"]
    if any(kw in venue for kw in conference_keywords):
        return "inproceedings"

    journal_keywords = ["journal", "transactions", "review", "letters",
                        "nature", "science", "plos", "ieee", "acm"]
    if any(kw in venue for kw in journal_keywords):
        return "article"

    # Arxiv preprints
    arxiv_id = (paper.get("external_ids") or {}).get("arxiv")
    if arxiv_id:
        return "misc"

    return "article"


def format_bibtex_entry(paper: dict, key: str) -> str:
    """Format a single paper as a BibTeX entry."""
    entry_type = detect_entry_type(paper)
    title = escape_bibtex(paper.get("title", ""))
    authors = format_bibtex_authors(paper.get("authors", []))
    year = paper.get("year", "")
    venue = escape_bibtex(paper.get("venue") or "")
    doi = (paper.get("external_ids") or {}).get("doi") or ""
    arxiv_id = (paper.get("external_ids") or {}).get("arxiv") or ""
    url = paper.get("web_url") or paper.get("pdf_url") or ""

    lines = [f"@{entry_type}{{{key},"]
    lines.append(f"  title     = {{{title}}},")
    lines.append(f"  author    = {{{authors}}},")

    if year:
        lines.append(f"  year      = {{{year}}},")

    if entry_type == "inproceedings" and venue:
        lines.append(f"  booktitle = {{{venue}}},")
    elif entry_type == "article" and venue:
        lines.append(f"  journal   = {{{venue}}},")

    if doi:
        lines.append(f"  doi       = {{{doi}}},")
    if arxiv_id:
        lines.append(f"  eprint    = {{{arxiv_id}}},")
        lines.append(f"  archiveprefix = {{arXiv}},")
    if url:
        lines.append(f"  url       = {{{url}}},")

    lines.append("}")
    return "\n".join(lines)


def parse_bib_file(bib_path: str) -> dict[str, str]:
    """Parse a BibTeX file and return dict of key -> raw entry text."""
    path = Path(bib_path)
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8")
    entries = {}

    # Match @type{key, ... } blocks
    pattern = r"(@\w+\{([^,]+),.*?\n\})"
    for match in re.finditer(pattern, content, re.DOTALL):
        full_entry = match.group(1)
        key = match.group(2).strip()
        entries[key] = full_entry

    return entries


def extract_ids_from_entry(entry_text: str) -> tuple[str | None, str | None]:
    """Extract DOI and ArXiv ID from a BibTeX entry."""
    doi_match = re.search(r"doi\s*=\s*\{([^}]+)\}", entry_text, re.IGNORECASE)
    arxiv_match = re.search(r"eprint\s*=\s*\{([^}]+)\}", entry_text, re.IGNORECASE)

    doi = doi_match.group(1) if doi_match else None
    arxiv_id = arxiv_match.group(1) if arxiv_match else None

    return doi, arxiv_id


def is_duplicate(paper: dict, existing_entries: dict[str, str]) -> str | None:
    """Check if paper is a duplicate of an existing entry. Returns existing key or None."""
    paper_doi = (paper.get("external_ids") or {}).get("doi")
    paper_arxiv = (paper.get("external_ids") or {}).get("arxiv")

    for key, entry_text in existing_entries.items():
        existing_doi, existing_arxiv = extract_ids_from_entry(entry_text)

        if paper_doi and existing_doi and paper_doi.lower() == existing_doi.lower():
            return key
        if paper_arxiv and existing_arxiv and paper_arxiv == existing_arxiv:
            return key

    return None


def cmd_generate_key(args: argparse.Namespace) -> None:
    """Handle generate-key subcommand."""
    authors = json.loads(args.authors) if args.authors else []
    key = generate_bibtex_key(args.title, authors, args.year)
    print(key)


def sync_bibtex_key_to_db(db_path: str, paper_id: str, bibtex_key: str) -> None:
    """Update a paper's bibtex_key in the SQLite database.

    This ensures the database stays in sync with references.bib,
    which is critical for the fact-checking pipeline.
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "UPDATE papers SET bibtex_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (bibtex_key, paper_id),
    )
    conn.commit()
    conn.close()


def cmd_add(args: argparse.Namespace) -> None:
    """Handle add subcommand."""
    paper = json.loads(args.paper_json)
    bib_path = args.bib_file

    existing = parse_bib_file(bib_path)

    # Check for duplicates
    dup_key = is_duplicate(paper, existing)
    if dup_key:
        result = {"status": "duplicate", "existing_key": dup_key}
        # Even for duplicates, sync the key to DB if requested
        if args.db_path and args.paper_id:
            sync_bibtex_key_to_db(args.db_path, args.paper_id, dup_key)
            result["synced_to_db"] = True
        json.dump(result, sys.stdout, indent=2)
        print()
        return

    # Generate key
    key = generate_bibtex_key(
        paper.get("title", ""),
        paper.get("authors", []),
        paper.get("year"),
    )

    # Handle key collision by appending suffix
    original_key = key
    suffix = ord("a")
    while key in existing:
        key = f"{original_key}{chr(suffix)}"
        suffix += 1

    # Format and append entry
    entry = format_bibtex_entry(paper, key)

    path = Path(bib_path)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n{entry}\n")

    # Sync bibtex_key to database if DB path provided
    if args.db_path and args.paper_id:
        sync_bibtex_key_to_db(args.db_path, args.paper_id, key)

    result = {"status": "added", "key": key, "synced_to_db": bool(args.db_path)}
    json.dump(result, sys.stdout, indent=2)
    print()


def cmd_validate(args: argparse.Namespace) -> None:
    """Handle validate subcommand."""
    entries = parse_bib_file(args.bib_file)

    issues: list[dict] = []

    # Check each entry for required fields
    for key, entry_text in entries.items():
        required = ["title", "author", "year"]
        for field in required:
            if not re.search(rf"{field}\s*=", entry_text, re.IGNORECASE):
                issues.append({
                    "key": key,
                    "issue": f"missing required field: {field}",
                })

    # Check for citations in draft file if provided
    cited_keys: set[str] = set()
    if args.draft_file:
        draft_path = Path(args.draft_file)
        if draft_path.exists():
            draft_text = draft_path.read_text(encoding="utf-8")
            # Match [@key] or \cite{key} or [@key1; @key2] patterns
            cited_keys.update(re.findall(r"@(\w+)", draft_text))
            cited_keys.update(re.findall(r"\\cite\{(\w+)\}", draft_text))

            # Orphaned references (in bib but not cited)
            for key in entries:
                if key not in cited_keys:
                    issues.append({
                        "key": key,
                        "issue": "entry not cited in draft",
                    })

            # Missing references (cited but not in bib)
            for cited_key in cited_keys:
                if cited_key not in entries:
                    issues.append({
                        "key": cited_key,
                        "issue": "cited in draft but not in bibliography",
                    })

    result = {
        "total_entries": len(entries),
        "total_citations": len(cited_keys),
        "issues": issues,
        "valid": len(issues) == 0,
    }
    json.dump(result, sys.stdout, indent=2)
    print()


def cmd_sync_db(args: argparse.Namespace) -> None:
    """Sync bibtex_keys from .bib file into the SQLite papers table.

    Matches entries by arxiv ID or DOI. Fixes the critical gap where
    bibtex_key is NULL in the database despite existing in references.bib.
    """
    import sqlite3

    entries = parse_bib_file(args.bib_file)
    if not entries:
        json.dump({"status": "error", "message": "no entries in bib file"}, sys.stdout, indent=2)
        print()
        return

    conn = sqlite3.connect(args.db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    synced = 0
    skipped = 0
    not_found = []

    for key, entry_text in entries.items():
        doi, arxiv_id = extract_ids_from_entry(entry_text)

        paper_id = None
        if arxiv_id:
            row = conn.execute(
                "SELECT id FROM papers WHERE external_ids LIKE ?",
                (f'%"arxiv": "{arxiv_id}"%',),
            ).fetchone()
            if row:
                paper_id = row["id"]

        if not paper_id and doi:
            row = conn.execute(
                "SELECT id FROM papers WHERE external_ids LIKE ?",
                (f'%"doi": "{doi}"%',),
            ).fetchone()
            if row:
                paper_id = row["id"]

        if paper_id:
            conn.execute(
                "UPDATE papers SET bibtex_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (key, paper_id),
            )
            synced += 1
        else:
            not_found.append({"key": key, "arxiv": arxiv_id, "doi": doi})
            skipped += 1

    conn.commit()
    conn.close()

    result = {
        "status": "synced",
        "synced": synced,
        "skipped": skipped,
        "not_found": not_found,
    }
    json.dump(result, sys.stdout, indent=2)
    print()


def cmd_list(args: argparse.Namespace) -> None:
    """Handle list subcommand."""
    entries = parse_bib_file(args.bib_file)

    result = []
    for key, entry_text in entries.items():
        title_match = re.search(r"title\s*=\s*\{([^}]+)\}", entry_text)
        year_match = re.search(r"year\s*=\s*\{([^}]+)\}", entry_text)
        author_match = re.search(r"author\s*=\s*\{([^}]+)\}", entry_text)

        result.append({
            "key": key,
            "title": title_match.group(1) if title_match else "",
            "year": year_match.group(1) if year_match else "",
            "authors": author_match.group(1) if author_match else "",
        })

    json.dump(result, sys.stdout, indent=2)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="BibTeX citation manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate-key
    gen_parser = subparsers.add_parser("generate-key",
                                       help="Generate a BibTeX citation key")
    gen_parser.add_argument("--title", required=True)
    gen_parser.add_argument("--authors", default="[]",
                            help='JSON array of author names')
    gen_parser.add_argument("--year", type=int, default=None)

    # add
    add_parser = subparsers.add_parser("add", help="Add a citation to BibTeX file")
    add_parser.add_argument("--paper-json", required=True,
                            help="JSON string of paper object")
    add_parser.add_argument("--bib-file", required=True,
                            help="Path to BibTeX file")
    add_parser.add_argument("--db-path", default=None,
                            help="SQLite DB path — sync bibtex_key to papers table")
    add_parser.add_argument("--paper-id", default=None,
                            help="Paper ID in DB — required with --db-path")

    # validate
    val_parser = subparsers.add_parser("validate",
                                       help="Validate BibTeX file and cross-check with draft")
    val_parser.add_argument("--bib-file", required=True)
    val_parser.add_argument("--draft-file", default=None,
                            help="Path to draft Markdown file for cross-referencing")

    # sync-db
    sync_parser = subparsers.add_parser("sync-db",
                                         help="Sync bibtex_keys from .bib file into SQLite DB")
    sync_parser.add_argument("--bib-file", required=True)
    sync_parser.add_argument("--db-path", required=True,
                              help="SQLite database path")

    # list
    list_parser = subparsers.add_parser("list", help="List all entries in BibTeX file")
    list_parser.add_argument("--bib-file", required=True)

    args = parser.parse_args()

    commands = {
        "generate-key": cmd_generate_key,
        "add": cmd_add,
        "validate": cmd_validate,
        "sync-db": cmd_sync_db,
        "list": cmd_list,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
