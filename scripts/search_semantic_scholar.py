#!/usr/bin/env python3
"""
Semantic Scholar API search wrapper for the Academic Research Loop plugin.

Searches the Semantic Scholar public API and returns structured JSON results.
Unauthenticated: 100 requests per 5 minutes.
Authenticated (SEMANTIC_SCHOLAR_API_KEY env var): higher limits.

Usage:
    python3 search_semantic_scholar.py --query "LLM scientific discovery" --max-results 20
    python3 search_semantic_scholar.py --query "attention mechanism" --year 2023-2026
    python3 search_semantic_scholar.py --query "protein folding" --fields-of-study "Computer Science,Biology"
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

S2_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "paperId,title,abstract,authors,year,citationCount,venue,externalIds,url,tldr"
MAX_RETRIES = 5
BASE_RETRY_DELAY_SECONDS = 5.0
REQUEST_TIMEOUT_SECONDS = 30


def fetch_semantic_scholar(query: str, max_results: int,
                           year: str | None = None,
                           fields_of_study: str | None = None) -> list[dict]:
    """Fetch papers from Semantic Scholar API with retry and rate limit handling."""
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")

    params: dict[str, str | int] = {
        "query": query,
        "limit": min(max_results, 100),  # API max per request is 100
        "fields": S2_FIELDS,
    }

    if year:
        params["year"] = year
    if fields_of_study:
        params["fieldsOfStudy"] = fields_of_study

    url = f"{S2_API_URL}?{urllib.parse.urlencode(params)}"

    headers = {"User-Agent": "AcademicResearchLoop/1.0"}
    if api_key:
        headers["x-api-key"] = api_key

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8"))
            return parse_s2_response(data)

        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                delay = BASE_RETRY_DELAY_SECONDS * (2 ** attempt)
                time.sleep(delay)
                continue
            if e.code == 429:
                raise RuntimeError(
                    "Semantic Scholar rate limit exceeded. "
                    "Set SEMANTIC_SCHOLAR_API_KEY for higher limits."
                ) from e
            raise

        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(BASE_RETRY_DELAY_SECONDS)
                continue
            raise


def parse_s2_response(data: dict) -> list[dict]:
    """Parse Semantic Scholar API response into structured paper objects."""
    papers = []

    for item in data.get("data", []):
        if not item.get("title"):
            continue

        authors = [a.get("name", "") for a in (item.get("authors") or []) if a.get("name")]
        external_ids = item.get("externalIds") or {}
        tldr = item.get("tldr") or {}

        abstract = item.get("abstract") or tldr.get("text") or ""

        papers.append({
            "id": item.get("paperId", ""),
            "source": "semantic_scholar",
            "title": item.get("title", ""),
            "authors": authors,
            "abstract": abstract,
            "published": None,
            "updated": None,
            "year": item.get("year"),
            "categories": [],
            "venue": item.get("venue") or None,
            "citation_count": item.get("citationCount"),
            "pdf_url": None,
            "web_url": item.get("url", ""),
            "external_ids": {
                "arxiv": external_ids.get("ArXiv"),
                "doi": external_ids.get("DOI"),
                "semantic_scholar": item.get("paperId"),
            },
            "bibtex_key": None,
            "relevance_score": None,
            "relevance_rationale": None,
            "status": "candidate",
        })

    return papers


def fetch_citations(paper_id: str, direction: str, max_results: int) -> list[dict]:
    """Fetch citing or cited papers for a given paper (snowball search).

    Args:
        paper_id: Semantic Scholar paper ID or ArXiv ID (e.g., "ArXiv:2602.23068")
        direction: "citations" (papers that cite this one) or "references" (papers this one cites)
        max_results: Maximum number of results
    """
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    fields = "paperId,title,abstract,authors,year,citationCount,venue,externalIds,url"
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/{direction}?fields={fields}&limit={min(max_results, 100)}"

    headers = {"User-Agent": "AcademicResearchLoop/1.0"}
    if api_key:
        headers["x-api-key"] = api_key

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8"))

            papers = []
            for item in data.get("data", []):
                cited = item.get("citingPaper" if direction == "citations" else "citedPaper", {})
                if not cited or not cited.get("title"):
                    continue
                authors = [a.get("name", "") for a in (cited.get("authors") or []) if a.get("name")]
                external_ids = cited.get("externalIds") or {}
                papers.append({
                    "id": cited.get("paperId", ""),
                    "source": "semantic_scholar",
                    "title": cited.get("title", ""),
                    "authors": authors,
                    "abstract": cited.get("abstract") or "",
                    "published": None,
                    "updated": None,
                    "year": cited.get("year"),
                    "categories": [],
                    "venue": cited.get("venue") or None,
                    "citation_count": cited.get("citationCount"),
                    "pdf_url": None,
                    "web_url": cited.get("url", ""),
                    "external_ids": {
                        "arxiv": external_ids.get("ArXiv"),
                        "doi": external_ids.get("DOI"),
                        "semantic_scholar": cited.get("paperId"),
                    },
                    "bibtex_key": None,
                    "relevance_score": None,
                    "relevance_rationale": None,
                    "status": "candidate",
                })
            return papers

        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                delay = BASE_RETRY_DELAY_SECONDS * (2 ** attempt)
                time.sleep(delay)
                continue
            if e.code == 429:
                raise RuntimeError(
                    f"Semantic Scholar rate limit exceeded on {direction} lookup. "
                    "Set SEMANTIC_SCHOLAR_API_KEY for higher limits."
                ) from e
            raise
        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(BASE_RETRY_DELAY_SECONDS)
                continue
            raise
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Semantic Scholar for academic papers"
    )
    sub = parser.add_subparsers(dest="command")

    # Default search (backward compatible — no subcommand required)
    parser.add_argument("--query", default=None, help="Search query")
    parser.add_argument("--max-results", type=int, default=20,
                        help="Maximum results (default: 20, max: 100)")
    parser.add_argument("--year", default=None,
                        help="Year range filter (e.g., '2023-2026', '2024')")
    parser.add_argument("--fields-of-study", default=None,
                        help="Comma-separated fields (e.g., 'Computer Science,Biology')")

    # Snowball search subcommands
    cite_p = sub.add_parser("citations", help="Find papers that cite a given paper (forward snowball)")
    cite_p.add_argument("--paper-id", required=True,
                        help="S2 paper ID or ArXiv ID (e.g., 'ArXiv:2602.23068')")
    cite_p.add_argument("--max-results", type=int, default=20)

    ref_p = sub.add_parser("references", help="Find papers cited by a given paper (backward snowball)")
    ref_p.add_argument("--paper-id", required=True,
                        help="S2 paper ID or ArXiv ID (e.g., 'ArXiv:2602.23068')")
    ref_p.add_argument("--max-results", type=int, default=20)

    args = parser.parse_args()

    try:
        if args.command == "citations":
            papers = fetch_citations(args.paper_id, "citations", args.max_results)
        elif args.command == "references":
            papers = fetch_citations(args.paper_id, "references", args.max_results)
        elif args.query:
            papers = fetch_semantic_scholar(
                query=args.query,
                max_results=args.max_results,
                year=args.year,
                fields_of_study=args.fields_of_study,
            )
        else:
            parser.print_help()
            sys.exit(1)

        json.dump(papers, sys.stdout, indent=2, ensure_ascii=False)
        print()

    except urllib.error.HTTPError as e:
        json.dump({"error": f"Semantic Scholar API HTTP error: {e.code} {e.reason}",
                    "papers": []}, sys.stdout, indent=2)
        print()
        sys.exit(1)

    except urllib.error.URLError as e:
        json.dump({"error": f"Network error: {e.reason}", "papers": []},
                  sys.stdout, indent=2)
        print()
        sys.exit(1)

    except RuntimeError as e:
        json.dump({"error": str(e), "papers": []}, sys.stdout, indent=2)
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
