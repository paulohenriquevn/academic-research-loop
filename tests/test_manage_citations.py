#!/usr/bin/env python3
"""Unit tests for manage_citations.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from manage_citations import (
    detect_entry_type,
    escape_bibtex,
    extract_ids_from_entry,
    extract_last_name,
    format_bibtex_authors,
    format_bibtex_entry,
    generate_bibtex_key,
    is_duplicate,
    normalize_ascii,
    parse_bib_file,
)


class TestNormalizeAscii(unittest.TestCase):
    def test_basic_ascii(self):
        self.assertEqual(normalize_ascii("hello"), "hello")

    def test_accented_characters(self):
        self.assertEqual(normalize_ascii("José"), "Jose")
        self.assertEqual(normalize_ascii("Müller"), "Muller")
        self.assertEqual(normalize_ascii("François"), "Francois")

    def test_empty(self):
        self.assertEqual(normalize_ascii(""), "")


class TestExtractLastName(unittest.TestCase):
    def test_first_last(self):
        self.assertEqual(extract_last_name("John Smith"), "smith")

    def test_last_first_comma(self):
        self.assertEqual(extract_last_name("Smith, John"), "smith")

    def test_initial_last(self):
        self.assertEqual(extract_last_name("J. Smith"), "smith")

    def test_single_name(self):
        self.assertEqual(extract_last_name("Smith"), "smith")

    def test_empty(self):
        self.assertEqual(extract_last_name(""), "unknown")

    def test_accented_name(self):
        self.assertEqual(extract_last_name("José García"), "garcia")

    def test_multiple_parts(self):
        self.assertEqual(extract_last_name("Mary Jane Watson"), "watson")


class TestGenerateBibtexKey(unittest.TestCase):
    def test_standard(self):
        key = generate_bibtex_key("Large Language Models", ["John Smith"], 2024)
        self.assertEqual(key, "smith2024large")

    def test_skip_articles(self):
        key = generate_bibtex_key("The Art of Programming", ["Alice Lee"], 2023)
        self.assertEqual(key, "lee2023art")

    def test_skip_prepositions(self):
        key = generate_bibtex_key("A Survey of Methods", ["Bob Chen"], 2024)
        self.assertEqual(key, "chen2024survey")

    def test_no_authors(self):
        key = generate_bibtex_key("Some Paper", [], 2024)
        self.assertEqual(key, "unknown2024some")

    def test_no_year(self):
        key = generate_bibtex_key("Some Paper", ["Smith"], None)
        self.assertEqual(key, "smithndsome")

    def test_attention_is_all_you_need(self):
        key = generate_bibtex_key(
            "Attention Is All You Need", ["A. Vaswani"], 2017
        )
        self.assertEqual(key, "vaswani2017attention")


class TestFormatBibtexAuthors(unittest.TestCase):
    def test_single_author(self):
        result = format_bibtex_authors(["John Smith"])
        self.assertEqual(result, "Smith, John")

    def test_two_authors(self):
        result = format_bibtex_authors(["John Smith", "Jane Doe"])
        self.assertEqual(result, "Smith, John and Doe, Jane")

    def test_already_comma_format(self):
        result = format_bibtex_authors(["Smith, John"])
        self.assertEqual(result, "Smith, John")


class TestEscapeBibtex(unittest.TestCase):
    def test_ampersand(self):
        self.assertEqual(escape_bibtex("A & B"), "A \\& B")

    def test_percent(self):
        self.assertEqual(escape_bibtex("100%"), "100\\%")

    def test_already_escaped(self):
        self.assertEqual(escape_bibtex("A \\& B"), "A \\& B")

    def test_no_special(self):
        self.assertEqual(escape_bibtex("Normal text"), "Normal text")


class TestDetectEntryType(unittest.TestCase):
    def test_conference(self):
        paper = {"venue": "NeurIPS 2024", "external_ids": {}}
        self.assertEqual(detect_entry_type(paper), "inproceedings")

    def test_journal(self):
        paper = {"venue": "Nature Machine Intelligence", "external_ids": {}}
        self.assertEqual(detect_entry_type(paper), "article")

    def test_arxiv_preprint(self):
        paper = {"venue": "", "external_ids": {"arxiv": "2401.12345"}}
        self.assertEqual(detect_entry_type(paper), "misc")

    def test_workshop(self):
        paper = {"venue": "Workshop on AI Safety", "external_ids": {}}
        self.assertEqual(detect_entry_type(paper), "inproceedings")

    def test_default_article(self):
        paper = {"venue": "", "external_ids": {}}
        self.assertEqual(detect_entry_type(paper), "article")


class TestFormatBibtexEntry(unittest.TestCase):
    def test_full_entry(self):
        paper = {
            "title": "Large Language Models",
            "authors": ["John Smith", "Jane Doe"],
            "year": 2024,
            "venue": "NeurIPS",
            "web_url": "https://example.com",
            "pdf_url": None,
            "external_ids": {"doi": "10.1234/test", "arxiv": "2401.12345"},
        }
        entry = format_bibtex_entry(paper, "smith2024large")
        self.assertIn("@inproceedings{smith2024large,", entry)
        self.assertIn("title     = {Large Language Models}", entry)
        self.assertIn("Smith, John and Doe, Jane", entry)
        self.assertIn("year      = {2024}", entry)
        self.assertIn("booktitle = {NeurIPS}", entry)
        self.assertIn("doi       = {10.1234/test}", entry)
        self.assertIn("eprint    = {2401.12345}", entry)

    def test_minimal_entry(self):
        paper = {
            "title": "Test",
            "authors": ["Author"],
            "year": None,
            "venue": None,
            "web_url": "",
            "pdf_url": None,
            "external_ids": {},
        }
        entry = format_bibtex_entry(paper, "test")
        self.assertIn("@article{test,", entry)
        self.assertIn("title     = {Test}", entry)
        self.assertNotIn("year", entry)


class TestParseBibFile(unittest.TestCase):
    def test_parse_valid(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".bib", delete=False) as f:
            f.write("""
@article{smith2024large,
  title = {Large Language Models},
  author = {Smith, John},
  year = {2024},
}

@inproceedings{doe2023attention,
  title = {Attention},
  author = {Doe, Jane},
  year = {2023},
}
""")
            f.flush()
            entries = parse_bib_file(f.name)

        self.assertEqual(len(entries), 2)
        self.assertIn("smith2024large", entries)
        self.assertIn("doe2023attention", entries)

    def test_parse_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".bib", delete=False) as f:
            f.write("% Empty bib file\n")
            f.flush()
            entries = parse_bib_file(f.name)

        self.assertEqual(entries, {})

    def test_parse_nonexistent(self):
        entries = parse_bib_file("/nonexistent/path.bib")
        self.assertEqual(entries, {})


class TestExtractIdsFromEntry(unittest.TestCase):
    def test_extract_both(self):
        entry = """@article{test,
  doi = {10.1234/test},
  eprint = {2401.12345},
}"""
        doi, arxiv = extract_ids_from_entry(entry)
        self.assertEqual(doi, "10.1234/test")
        self.assertEqual(arxiv, "2401.12345")

    def test_extract_doi_only(self):
        entry = "@article{test,\n  doi = {10.1234/test},\n}"
        doi, arxiv = extract_ids_from_entry(entry)
        self.assertEqual(doi, "10.1234/test")
        self.assertIsNone(arxiv)

    def test_extract_none(self):
        entry = "@article{test,\n  title = {Test},\n}"
        doi, arxiv = extract_ids_from_entry(entry)
        self.assertIsNone(doi)
        self.assertIsNone(arxiv)


class TestIsDuplicate(unittest.TestCase):
    def test_duplicate_by_doi(self):
        paper = {"external_ids": {"doi": "10.1234/test", "arxiv": None}}
        existing = {
            "smith2024": "@article{smith2024,\n  doi = {10.1234/test},\n}"
        }
        result = is_duplicate(paper, existing)
        self.assertEqual(result, "smith2024")

    def test_duplicate_by_arxiv(self):
        paper = {"external_ids": {"doi": None, "arxiv": "2401.12345"}}
        existing = {
            "smith2024": "@article{smith2024,\n  eprint = {2401.12345},\n}"
        }
        result = is_duplicate(paper, existing)
        self.assertEqual(result, "smith2024")

    def test_not_duplicate(self):
        paper = {"external_ids": {"doi": "10.9999/new", "arxiv": "2401.99999"}}
        existing = {
            "smith2024": "@article{smith2024,\n  doi = {10.1234/test},\n}"
        }
        result = is_duplicate(paper, existing)
        self.assertIsNone(result)

    def test_no_ids(self):
        paper = {"external_ids": {"doi": None, "arxiv": None}}
        existing = {"smith2024": "@article{smith2024,\n  doi = {10.1234},\n}"}
        result = is_duplicate(paper, existing)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
