#!/usr/bin/env python3
"""
Multi-strategy paper content fetcher for the Academic Research Loop plugin.

Attempts to fetch full-text content from academic papers using multiple
strategies in order of preference:
  1. ar5iv HTML (arxiv papers rendered as accessible HTML)
  2. Semantic Scholar TLDR + extended abstract
  3. Arxiv abstract page HTML

No external dependencies — uses Python stdlib only.

Usage:
    python3 fetch_paper_content.py --arxiv-id 2401.12345
    python3 fetch_paper_content.py --url "https://arxiv.org/abs/2401.12345"
    python3 fetch_paper_content.py --semantic-scholar-id abc123 --arxiv-id 2401.12345
"""

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request

REQUEST_TIMEOUT = 30


def fetch_ar5iv(arxiv_id: str) -> dict | None:
    """Fetch paper content from ar5iv (HTML rendered arxiv papers).

    ar5iv.labs.arxiv.org renders arxiv papers as accessible HTML,
    which is much easier to parse than PDFs.
    """
    url = f"https://ar5iv.labs.arxiv.org/html/{arxiv_id}"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AcademicResearchLoop/1.0"
        })
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            html_content = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None

    sections = extract_sections_from_html(html_content)

    if not sections:
        return None

    return {
        "source": "ar5iv",
        "url": url,
        "sections": sections,
        "full_text": "\n\n".join(
            f"## {s['heading']}\n{s['text']}" for s in sections
        ),
    }


def extract_sections_from_html(html_content: str) -> list[dict]:
    """Extract section headings and text from ar5iv HTML.

    Uses regex-based extraction (no external HTML parser needed).
    Targets the main content structure of ar5iv pages.
    """
    sections = []

    # Remove script and style blocks
    clean = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL)

    # Find section headings (h2, h3, h4) with their content
    heading_pattern = r"<(h[2-4])[^>]*>(.*?)</\1>"
    headings = list(re.finditer(heading_pattern, clean, re.DOTALL))

    for i, match in enumerate(headings):
        heading_text = strip_html_tags(match.group(2)).strip()

        if not heading_text or len(heading_text) > 200:
            continue

        # Get text between this heading and the next
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(clean)

        section_html = clean[start:end]
        section_text = strip_html_tags(section_html).strip()

        # Collapse whitespace
        section_text = re.sub(r"\s+", " ", section_text)

        if section_text and len(section_text) > 50:
            sections.append({
                "heading": heading_text,
                "text": section_text[:5000],  # Cap at 5000 chars per section
            })

    return sections


def fetch_arxiv_abstract(arxiv_id: str) -> dict | None:
    """Fetch the abstract page from arxiv.org as fallback."""
    url = f"https://arxiv.org/abs/{arxiv_id}"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "AcademicResearchLoop/1.0"
        })
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            html_content = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None

    # Extract abstract
    abstract_match = re.search(
        r'<blockquote class="abstract[^"]*">(.*?)</blockquote>',
        html_content, re.DOTALL,
    )
    abstract = ""
    if abstract_match:
        abstract = strip_html_tags(abstract_match.group(1)).strip()
        abstract = re.sub(r"^Abstract:\s*", "", abstract)

    # Extract title
    title_match = re.search(
        r'<h1 class="title[^"]*">(.*?)</h1>', html_content, re.DOTALL
    )
    title = ""
    if title_match:
        title = strip_html_tags(title_match.group(1)).strip()
        title = re.sub(r"^Title:\s*", "", title)

    if not abstract:
        return None

    return {
        "source": "arxiv_abstract",
        "url": url,
        "title": title,
        "abstract": abstract,
        "full_text": f"## {title}\n\n{abstract}",
    }


def fetch_semantic_scholar_details(paper_id: str) -> dict | None:
    """Fetch extended details from Semantic Scholar API."""
    import os

    fields = "title,abstract,tldr,citationCount,references.title,references.year"
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}?fields={fields}"

    headers = {"User-Agent": "AcademicResearchLoop/1.0"}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    if api_key:
        headers["x-api-key"] = api_key

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None

    abstract = data.get("abstract") or ""
    tldr = (data.get("tldr") or {}).get("text") or ""
    title = data.get("title") or ""

    refs = data.get("references") or []
    ref_titles = [r.get("title", "") for r in refs[:20] if r.get("title")]

    parts = []
    if title:
        parts.append(f"## {title}")
    if tldr:
        parts.append(f"**TLDR:** {tldr}")
    if abstract:
        parts.append(f"### Abstract\n{abstract}")
    if ref_titles:
        parts.append("### Key References\n" + "\n".join(f"- {t}" for t in ref_titles))

    if not parts:
        return None

    return {
        "source": "semantic_scholar",
        "url": f"https://www.semanticscholar.org/paper/{paper_id}",
        "title": title,
        "abstract": abstract,
        "tldr": tldr,
        "references": ref_titles,
        "full_text": "\n\n".join(parts),
    }


def strip_html_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return text


def fetch_content(arxiv_id: str | None = None,
                  semantic_scholar_id: str | None = None,
                  url: str | None = None) -> dict:
    """Try multiple strategies to fetch paper content.

    Returns the best available content with source attribution.
    """
    # Extract arxiv_id from URL if provided
    if url and not arxiv_id:
        match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d+\.\d+)", url)
        if match:
            arxiv_id = match.group(1)

    results = []

    # Strategy 1: ar5iv full HTML (best quality for arxiv papers)
    if arxiv_id:
        content = fetch_ar5iv(arxiv_id)
        if content:
            content["quality"] = "full_text"
            results.append(content)

    # Strategy 2: Semantic Scholar extended details
    if semantic_scholar_id:
        content = fetch_semantic_scholar_details(semantic_scholar_id)
        if content:
            content["quality"] = "abstract_plus"
            results.append(content)

    # Strategy 3: Arxiv abstract page (fallback)
    if arxiv_id and not any(r["source"] == "ar5iv" for r in results):
        content = fetch_arxiv_abstract(arxiv_id)
        if content:
            content["quality"] = "abstract_only"
            results.append(content)

    if not results:
        return {
            "error": "No content could be fetched from any source",
            "strategies_tried": [
                s for s in ["ar5iv", "semantic_scholar", "arxiv_abstract"]
                if (arxiv_id and s != "semantic_scholar") or
                   (semantic_scholar_id and s == "semantic_scholar")
            ],
        }

    # Return best quality result
    quality_order = {"full_text": 0, "abstract_plus": 1, "abstract_only": 2}
    results.sort(key=lambda r: quality_order.get(r.get("quality", ""), 99))

    best = results[0]
    best["alternatives"] = len(results) - 1
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch academic paper content")
    parser.add_argument("--arxiv-id", default=None, help="Arxiv paper ID")
    parser.add_argument("--semantic-scholar-id", default=None,
                        help="Semantic Scholar paper ID")
    parser.add_argument("--url", default=None, help="Paper URL")

    args = parser.parse_args()

    if not any([args.arxiv_id, args.semantic_scholar_id, args.url]):
        print(json.dumps({"error": "Provide at least one of: --arxiv-id, --semantic-scholar-id, --url"}))
        sys.exit(1)

    result = fetch_content(args.arxiv_id, args.semantic_scholar_id, args.url)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
