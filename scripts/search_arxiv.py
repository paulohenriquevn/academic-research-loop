#!/usr/bin/env python3
"""
Arxiv API search wrapper for the Academic Research Loop plugin.

Searches the Arxiv public API and returns structured JSON results.
No API key required. Rate limit: ~3 requests/second.

Usage:
    python3 search_arxiv.py --query "LLM scientific discovery" --max-results 20
    python3 search_arxiv.py --query "transformer protein" --category cs.CL --sort-by submittedDate
    python3 search_arxiv.py --query "attention mechanism" --max-results 5 --sort-by relevance
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ARXIV_API_URL = "http://export.arxiv.org/api/query"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 30


def build_query(query: str, category: str | None = None) -> str:
    """Build Arxiv search query string with optional category filter."""
    search_query = f"all:{query}"
    if category:
        search_query = f"cat:{category} AND {search_query}"
    return search_query


def fetch_arxiv(query: str, max_results: int, sort_by: str,
                category: str | None = None) -> list[dict]:
    """Fetch papers from Arxiv API with retry logic."""
    search_query = build_query(query, category)

    params = urllib.parse.urlencode({
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending",
    })

    url = f"{ARXIV_API_URL}?{params}"

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "AcademicResearchLoop/1.0"
            })
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                xml_data = response.read().decode("utf-8")
            return parse_arxiv_response(xml_data)

        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                continue
            raise
        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            raise


def parse_arxiv_response(xml_data: str) -> list[dict]:
    """Parse Arxiv Atom XML response into structured paper objects."""
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    root = ET.fromstring(xml_data)
    papers = []

    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        published_el = entry.find("atom:published", ns)
        updated_el = entry.find("atom:updated", ns)

        if title_el is None or summary_el is None:
            continue

        title = " ".join(title_el.text.strip().split())
        abstract = " ".join(summary_el.text.strip().split())

        # Extract Arxiv ID from the entry id URL
        id_el = entry.find("atom:id", ns)
        arxiv_url = id_el.text.strip() if id_el is not None else ""
        arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""

        # Remove version suffix for consistent ID
        arxiv_id_base = arxiv_id.rsplit("v", 1)[0] if "v" in arxiv_id else arxiv_id

        # Authors
        authors = []
        for author_el in entry.findall("atom:author", ns):
            name_el = author_el.find("atom:name", ns)
            if name_el is not None:
                authors.append(name_el.text.strip())

        # Categories
        categories = []
        for cat_el in entry.findall("atom:category", ns):
            term = cat_el.get("term", "")
            if term:
                categories.append(term)

        # PDF link
        pdf_url = ""
        for link_el in entry.findall("atom:link", ns):
            if link_el.get("title") == "pdf":
                pdf_url = link_el.get("href", "")
                break

        # DOI (if available via arxiv namespace)
        doi_el = entry.find("arxiv:doi", ns)
        doi = doi_el.text.strip() if doi_el is not None else None

        published = published_el.text.strip()[:10] if published_el is not None else ""
        updated = updated_el.text.strip()[:10] if updated_el is not None else ""

        papers.append({
            "id": arxiv_id_base,
            "source": "arxiv",
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "published": published,
            "updated": updated,
            "year": int(published[:4]) if published else None,
            "categories": categories,
            "venue": None,
            "citation_count": None,
            "pdf_url": pdf_url,
            "web_url": arxiv_url,
            "external_ids": {
                "arxiv": arxiv_id_base,
                "doi": doi,
            },
            "bibtex_key": None,
            "relevance_score": None,
            "relevance_rationale": None,
            "status": "candidate",
        })

    return papers


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Arxiv for academic papers"
    )
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--max-results", type=int, default=10,
                        help="Maximum results to return (default: 10)")
    parser.add_argument("--category", default=None,
                        help="Arxiv category filter (e.g., cs.CL, cs.AI)")
    parser.add_argument("--sort-by", default="relevance",
                        choices=["relevance", "lastUpdatedDate", "submittedDate"],
                        help="Sort order (default: relevance)")

    args = parser.parse_args()

    try:
        papers = fetch_arxiv(
            query=args.query,
            max_results=args.max_results,
            sort_by=args.sort_by,
            category=args.category,
        )
        json.dump(papers, sys.stdout, indent=2, ensure_ascii=False)
        print()  # trailing newline

    except urllib.error.HTTPError as e:
        json.dump({"error": f"Arxiv API HTTP error: {e.code} {e.reason}",
                    "papers": []}, sys.stdout, indent=2)
        print()
        sys.exit(1)

    except urllib.error.URLError as e:
        json.dump({"error": f"Network error: {e.reason}", "papers": []},
                  sys.stdout, indent=2)
        print()
        sys.exit(1)

    except ET.ParseError as e:
        json.dump({"error": f"Failed to parse Arxiv response: {e}",
                    "papers": []}, sys.stdout, indent=2)
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
