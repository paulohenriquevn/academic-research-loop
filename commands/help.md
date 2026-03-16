---
description: "Explain academic research loop and available commands"
---

# Academic Research Loop Help

Please explain the following to the user:

## What is the Academic Research Loop?

A Claude Code plugin that runs an autonomous academic research pipeline using the Ralph Wiggum loop technique. You give it a research topic, and it iterates through 7 phases — discovering papers, screening them, analyzing findings, synthesizing themes, and writing a complete survey/paper with proper citations.

**Inspired by:**
- **Ralph Wiggum** (Geoffrey Huntley) — self-referential AI loop mechanism
- **Autoresearch** (Andrej Karpathy) — autonomous AI experimentation pattern
- **Autosearch** — multi-agent academic research pipeline

## The 7 Phases

| Phase | Name | What happens | Max iterations |
|-------|------|-------------|---------------|
| 1 | Discovery | Search Arxiv + Semantic Scholar for papers | 3 |
| 2 | Screening | Score candidates for relevance, build shortlist | 2 |
| 3 | Analysis | Deep-read shortlisted papers, extract findings | 5 |
| 4 | Synthesis | Identify themes, gaps, and contradictions | 2 |
| 5 | Writing | Draft the survey/paper with BibTeX citations | 3 |
| 6 | Review | Academic peer-review style critique and revision | 2 |
| 7 | Polish | Final formatting, citation validation, abstract | 1 |

## Available Commands

### /research-loop TOPIC [OPTIONS]

Start a research loop.

```
/research-loop Transformer architectures for protein folding
/research-loop "LLMs for scientific discovery" --min-papers 15
/research-loop RAG techniques --max-iterations 30
```

**Options:**
- `--max-iterations <n>` — Max global iterations (default: 50)
- `--min-papers <n>` — Minimum papers to discover (default: 10)
- `--output-dir <path>` — Output directory (default: ./research-output)
- `--completion-promise <text>` — Custom promise (default: "RESEARCH COMPLETE")

### /research-status

View current research loop status: phase, iteration, paper counts, output files.

### /cancel-research

Cancel an active research loop. Output files are preserved.

## Output Structure

```
research-output/
├── state/
│   ├── candidates.json     — All discovered papers with metadata
│   ├── shortlist.json      — Papers that passed screening
│   └── analyses/           — Per-paper analysis in Markdown
├── synthesis.md            — Cross-paper thematic synthesis
├── draft.md                — Paper draft with citations
├── references.bib          — BibTeX bibliography
└── final.md                — Polished final paper
```

## How It Works

1. The stop hook intercepts Claude's exit after each iteration
2. Claude reads the state file to know its current phase
3. Each iteration advances the research within the current phase
4. Phase completion markers (`<!-- PHASE_N_COMPLETE -->`) trigger phase transitions
5. If a phase exceeds its iteration limit, it's forced to the next phase
6. The loop ends when Claude outputs `<promise>RESEARCH COMPLETE</promise>`

## Search Tools

The plugin includes Python scripts for real API searches:
- `search_arxiv.py` — Searches Arxiv via their public API
- `search_semantic_scholar.py` — Searches Semantic Scholar (supports API key for higher rate limits)
- `manage_citations.py` — Manages BibTeX entries (add, deduplicate, validate)

Set `SEMANTIC_SCHOLAR_API_KEY` environment variable for higher Semantic Scholar rate limits.
