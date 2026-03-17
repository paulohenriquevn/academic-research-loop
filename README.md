# Academic Research Loop

Autonomous academic research pipeline for Claude Code. Give it a topic, and it produces a publication-quality literature survey with PRISMA methodology, quantitative evidence matrices, SVG figures, and LaTeX export. Optionally, it maps literature to your codebase and runs real experiments.

Combines five ideas:
- **[Ralph Wiggum](https://ghuntley.com/ralph/)** — self-referential AI loop via stop hook
- **[Autoresearch](https://github.com/karpathy/autoresearch)** (Karpathy) — autonomous experimentation: write code, execute, evaluate, keep/discard
- **[Autosearch](https://github.com/FullStackRetrieval-com/RetrievalTutorials)** — multi-agent academic research teams
- **[PRISMA](https://www.prisma-statement.org/)** — systematic review methodology for reproducible search
- **Epistemic rigor** — every claim tagged [MEASURED]/[INFERRED]/[HYPOTHESIZED], enforced across the pipeline

## Installation

### Step 1: Add the marketplace

```
/plugin marketplace add paulohenriquevn/academic-research-loop
```

### Step 2: Install the plugin

```
/plugin install academic-research-loop@academic-research-loop
```

Choose the scope when prompted: **project** (all collaborators), **user** (all your projects), or **local** (just you, gitignored).

### Alternative: Manual settings

Add to `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "academic-research-loop": {
      "source": {
        "source": "github",
        "repo": "paulohenriquevn/academic-research-loop"
      }
    }
  }
}
```

Then restart Claude Code and run `/plugin install academic-research-loop@academic-research-loop`.

## Quick Start

```bash
# Literature survey
/research-loop "Transformer architectures for protein folding"

# Applied research — map literature to your codebase
/research-loop "Voice agent safety" --codebase ~/projects/my-voice-app

# With experiments — write code, run benchmarks, measure results
/research-loop "Lightweight toxicity classifiers" --experiments --min-papers 5

# Full mode — applied research + experiments
/research-loop "Streaming safety" --codebase ~/projects/app --experiments
```

The agent reads your project's `CLAUDE.md` and `README.md` on the first iteration to understand context, hypotheses, and priorities before starting research.

## How It Works

```
/research-loop "Topic"
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│  Step 0: Read CLAUDE.md + README.md for project context      │
├──────────────────────────────────────────────────────────────┤
│  Phase 1: Discovery      (max 3 iter)                        │
│  PRISMA search protocol + ArXiv + Semantic Scholar           │
├──────────────────────────────────────────────────────────────┤
│  Phase 2: Screening      (max 2 iter)                        │
│  Score candidates 1-5, document screening funnel             │
├──────────────────────────────────────────────────────────────┤
│  Phase 3: Analysis       (max 5 iter)                        │
│  Deep-read papers + extract ALL quantitative evidence        │
├──────────────────────────────────────────────────────────────┤
│  Phase 4: Synthesis      (max 3 iter, or 6 with experiments) │
│  Themes, evidence matrix, corpus table, experiments          │
├──────────────────────────────────────────────────────────────┤
│  Phase 5: Writing        (max 4 iter)                        │
│  Draft with epistemic calibration + evidence tables          │
├──────────────────────────────────────────────────────────────┤
│  Phase 6: Review         (max 3 iter)                        │
│  Overclaiming audit, fact-check, peer-review                 │
├──────────────────────────────────────────────────────────────┤
│  Phase 7: Polish         (max 2 iter)                        │
│  Figures, cross-validation, LaTeX export                     │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
  research-output/
  ├── final.md            ← Complete survey (Markdown)
  ├── final.tex           ← LaTeX (submission-ready)
  ├── figures/             ← SVG figures + generation scripts
  ├── experiments/         ← Experiment scripts + results (with --experiments)
  └── research.db         ← All evidence in structured DB
```

Each iteration, the stop hook intercepts Claude's exit and re-injects the research prompt. Phases advance via completion markers or timeout. Quality gates repeat failed phases with evaluator feedback (Autoresearch keep/discard).

## Three Modes

### 1. Literature Survey (default)

```bash
/research-loop "RAG techniques for question answering" --min-papers 15
```

Produces an academic survey with PRISMA methodology, structured corpus table, evidence matrices, and epistemic calibration on every claim.

### 2. Applied Research (`--codebase`)

```bash
/research-loop "Voice agent safety" --codebase ~/projects/my-voice-app
```

Maps literature to a specific codebase. Every phase adapts:

| Phase | Standard Survey | Applied Research |
|-------|----------------|-----------------|
| 1 Discovery | Search by topic | **Codebase analysis first** → queries derived from components |
| 2 Screening | Score by relevance | Score includes **component mapping** |
| 3 Analysis | Paper findings | Findings + **"which module does this help?"** |
| 4 Synthesis | Themes and gaps | **Gap matrix**: component × papers × severity (Solved/Partial/Open/Conflicting) |
| 5 Writing | Survey paper | + **Implementation recs** + **proposed benchmarks** |
| 7 Polish | 3 figures | + **Architecture-paper mapping diagram** |

Additional output: `state/codebase_analysis.md` and `state/gap_analysis.md`.

### 3. Experimentation (`--experiments`)

```bash
/research-loop "Lightweight toxicity classifiers" --experiments --min-papers 5
```

Runs real experiments on your machine. The system:

1. **experiment-designer** — reads evidence gaps, checks your hardware (GPU/CPU, VRAM, packages), proposes feasible experiments with runtime estimates
2. **experiment-coder** (Autoresearch pattern) — writes Python scripts, executes them, captures metrics, retries on failure (max 3)
3. Results stored as `evidence_type="empirical"` — distinct from paper-reported `"measured"` evidence
4. Paper includes **"Empirical Validation"** section with paper-reported vs locally-measured results side by side

Combine with `--codebase` for the full pipeline:

```bash
/research-loop "Streaming safety" --codebase ~/projects/app --experiments
```

## Commands

### `/research-loop TOPIC [OPTIONS]`

| Option | Default | Description |
|--------|---------|-------------|
| `--min-papers N` | 10 | Minimum papers to discover |
| `--max-iterations N` | 50 | Max global iterations before auto-stop |
| `--output-dir PATH` | `./research-output` | Where output files go |
| `--codebase PATH` | *(off)* | Enable applied research — analyze this project and map literature to its components |
| `--experiments` | *(off)* | Enable experimentation — write code, run benchmarks, train models, measure results |
| `--completion-promise TEXT` | `"RESEARCH COMPLETE"` | Promise text to signal completion |

Flags combine freely: `--codebase` + `--experiments` runs the full pipeline.

### `/research-status`

View current state: phase, iteration, paper counts, output files.

### `/cancel-research`

Cancel an active loop. Output files are preserved.

## Output Structure

```
research-output/
├── final.md                     # Complete survey (Markdown)
├── final.tex                    # LaTeX version (submission-ready)
├── references.bib               # BibTeX bibliography
├── research.db                  # SQLite DB (papers, evidence, quality, messages)
├── synthesis.md                 # Cross-paper thematic synthesis
├── draft.md                     # Paper draft with citations
├── figures/                     # Generated SVG figures + scripts
│   ├── figure_1_timeline.svg
│   ├── figure_2_performance.svg
│   ├── figure_3_taxonomy.svg
│   └── gen_figure_*.py
├── experiments/                 # (with --experiments)
│   ├── exp_1_name.py            # Experiment scripts
│   ├── results/
│   │   ├── exp_1_name.json      # Structured results
│   │   └── exp_1_name.log       # Execution logs
│   └── experiment_report.md
└── state/
    ├── methodology.md           # PRISMA search protocol + screening funnel
    ├── corpus_table.md          # Structured corpus table (evidence strength per paper)
    ├── evidence_matrix.md       # Cross-paper comparison (MEASURED only)
    ├── experiment_plan.md       # (with --experiments) designed by experiment-designer
    ├── codebase_analysis.md     # (with --codebase) component map
    ├── gap_analysis.md          # (with --codebase) gap matrix
    ├── validation_report.json   # Cross-validation results
    ├── candidates.json          # All discovered papers
    ├── shortlist.json           # Papers that passed screening
    ├── outline.md               # Survey structure
    ├── analyses/                # Per-paper analysis files
    ├── evidence/                # Per-paper quantitative evidence extraction
    └── meetings/                # Group meeting minutes
```

## Epistemic Rigor System

The pipeline enforces evidence discipline at 6 points — designed in response to MIT peer review feedback.

### Evidence Classification

Every finding in every paper analysis is tagged:

| Tag | Meaning | Allowed language in paper |
|-----|---------|--------------------------|
| **[MEASURED]** | Directly from paper's experiments | "achieves", "demonstrates", "shows" |
| **[INFERRED]** | Reasonable inference, not directly measured | "suggests", "indicates", "likely" |
| **[HYPOTHESIZED]** | Speculative, not tested | "may", "could", "warrants investigation" |
| **[ARCHITECTURAL]** | Design pattern, not empirical | "proposes", "enables in principle" |

### Evidence Extraction Pipeline

```
Phase 3: For EACH paper
  ├── paper-analyzer     → findings tagged [MEASURED/INFERRED/HYPOTHESIZED]
  └── evidence-extractor → EVERY number extracted:
                            metric, value, dataset, baseline, conditions,
                            source_location (Table N, Figure M)
                            → stored in evidence table (DB)
                            → "What Was NOT Measured" documented

Phase 4: Synthesis
  ├── corpus_table.md    → all papers with evidence_strength column
  ├── evidence_matrix    → cross-paper comparison (MEASURED only)
  ├── experimental_gaps  → what nobody measured
  └── experiments        → (with --experiments) run code to fill gaps

Phase 5: Writing
  └── comparison tables use ONLY [MEASURED] values
      estimated values labeled "est." — NEVER presented as results

Phase 6: Review
  ├── fact-checker   → flags "demonstrates" on [HYPOTHESIZED] claims
  └── reviewer       → flags heterogeneous comparisons, missing confounds
```

### PRISMA-like Methodology

Phase 1 documents the search protocol before any papers are found:
- Databases searched (ArXiv, Semantic Scholar) and databases NOT searched (with reasons)
- Every query string with date and result count
- Inclusion/exclusion criteria
- Screening funnel: identified → deduplicated → screened → shortlisted → excluded (with reasons)

### Quality Gate Dimensions

| Dimension | What it checks |
|-----------|---------------|
| `epistemic_calibration` | Claims match evidence strength |
| `corpus_table` | Structured corpus table present with evidence tags |
| `overclaiming_fixed` | No "demonstrates" for [HYPOTHESIZED] |
| `confound_treatment` | Speculative hypotheses have limitation analysis |
| `methodology_documentation` | Search protocol is reproducible |

## Research Team (22 Agents)

### Core Team (Every Iteration)

| Role | Agent | Focus |
|------|-------|-------|
| **Chief Researcher** | `chief-researcher` | Leads mandatory meetings, strategic decisions |
| **Methods Specialist** | `researcher-methods` | Methodology, experimental design, metrics |
| **Theory Specialist** | `researcher-theory` | Theoretical frameworks, formal analysis |
| **Applications Specialist** | `researcher-applications` | Real-world impact, deployment |

### Phase Specialists

| Agent | Phase | Purpose |
|-------|-------|---------|
| `paper-screener` | 2 | Scores papers for relevance (1-5 scale) |
| `paper-analyzer` | 3 | Deep-reads papers, tags evidence strength |
| `evidence-extractor` | 3 | Extracts EVERY quantitative result into DB |
| `synthesis-writer` | 4 | Identifies themes, builds evidence matrix |
| `outline-architect` | 4 | Designs survey structure |
| `outline-critic` | 4 | Reviews outline for coverage and balance |
| `writing-instructor` | 5 | Generates per-section writing instructions |
| `section-writer` | 5 | Writes sections with epistemic calibration |
| `quality-evaluator` | 2-6 | Quality gate with epistemic rigor dimensions |
| `fact-checker` | 6 | Verifies claims, flags overclaiming |
| `academic-reviewer` | 6 | Peer-review: overclaiming audit, confound check |
| `figure-generator` | 7 | Writes scripts to generate SVG figures (Autoresearch) |
| `cross-validator` | 7 | Writes validation scripts, auto-fixes issues |
| `latex-exporter` | 7 | Writes Markdown-to-LaTeX converter |

### Mode-Specific Agents

| Agent | Mode | Purpose |
|-------|------|---------|
| `codebase-analyzer` | `--codebase` | Reads project, extracts component map and research questions |
| `gap-analyzer` | `--codebase` | Maps literature to codebase gaps (Solved/Partial/Open/Conflicting) |
| `experiment-designer` | `--experiments` | Checks hardware, designs feasible experiments with runtime estimates |
| `experiment-coder` | `--experiments` | Autoresearch: writes scripts, executes, evaluates, keep/discard |

## Tools

All Python scripts use **only stdlib** (zero `pip install`):

| Script | Purpose |
|--------|---------|
| `search_arxiv.py` | ArXiv API search with retry logic |
| `search_semantic_scholar.py` | Semantic Scholar API with rate limiting |
| `paper_database.py` | SQLite DB: papers, analyses, evidence, quality scores, agent messages |
| `manage_citations.py` | BibTeX generation, dedup, validation, DB sync |
| `fetch_paper_content.py` | Multi-strategy content fetcher (ar5iv > S2 > abstract) |
| `fact_check.py` | Cross-references claims against evidence DB (self-healing) |
| `svg_utils.py` | SVG primitives for figure-generator agent |

### Evidence Database

```bash
# Add quantitative evidence
python3 scripts/paper_database.py add-evidence --db-path research.db \
  --paper-id ID --evidence-json '{
    "metric": "F1", "value": 0.94, "dataset": "ToxicChat",
    "baseline_name": "Llama Guard 2", "baseline_value": 0.89,
    "conditions": "8B, 4-bit, A100", "evidence_type": "measured",
    "source_location": "Table 2"
  }'

# Query evidence
python3 scripts/paper_database.py query-evidence --db-path research.db --metric F1
python3 scripts/paper_database.py query-evidence --db-path research.db --evidence-type measured

# Cross-paper evidence matrix (MEASURED only)
python3 scripts/paper_database.py evidence-matrix --db-path research.db

# Sync bibtex keys from .bib to DB
python3 scripts/manage_citations.py sync-db --bib-file references.bib --db-path research.db
```

## Quality Gates (Autoresearch Keep/Discard)

```
Phase output → Quality Evaluator → Score 0.0-1.0
                                     │
                     ┌───────────────┤
                     │               │
                  PASS ≥ 0.7      FAIL < 0.7
                     │               │
              Advance to          Repeat phase
              next phase        (discard & retry)
```

Quality scores include per-dimension breakdown:
```json
{
  "phase": 5, "score": 0.82, "decision": "PASS",
  "dimensions": {
    "completeness": 0.85, "citations": 0.90,
    "epistemic_calibration": 0.75, "methodology_documentation": 0.80
  }
}
```

## Testing

```bash
# Python tests (155 tests)
python3 -m pytest tests/ -v

# Bash tests (31 tests)
bash tests/test_stop_hook.sh
bash tests/test_setup_script.sh
```

| Test file | Tests | Coverage |
|-----------|-------|----------|
| `test_paper_database.py` | 36 | CRUD, evidence table, quality scores, messages, stats |
| `test_manage_citations.py` | 44 | BibTeX generation, dedup, validation, sync-db |
| `test_svg_utils.py` | 33 | SVG primitives, axes, legends, nice_ticks |
| `test_search_arxiv.py` | 10 | Query building, XML parsing, fetch |
| `test_search_semantic_scholar.py` | 9 | Response parsing, API key, filters |
| `test_fact_check.py` | 10 | Claim extraction, support verification |
| `test_fetch_paper_content.py` | 10 | HTML extraction, fallback strategies |
| `test_stop_hook.sh` | 13 | Phase machine, quality gates, corruption handling |
| `test_setup_script.sh` | 18 | Argument parsing, state file, validation |

## Local Development

The plugin runs from a **cached copy**. After editing source files:

```bash
# 1. Run tests
python3 -m pytest tests/ -v

# 2. Sync to cache
rsync -av \
  --exclude='.git' --exclude='__pycache__' --exclude='.pytest_cache' \
  ~/Projetos/usemacaw/academic-research-loop/ \
  ~/.claude/plugins/cache/academic-research-loop/academic-research-loop/1.0.0/

# 3. Restart Claude Code session to load changes
```

## Design Decisions

**Why Ralph Wiggum?** No external orchestrator needed. Claude Code's hook system handles the loop natively. The agent sees its own previous work each iteration.

**Why Autoresearch keep/discard?** Autonomous research without evaluation is noise. Failed phases retry with feedback. Phase 7 agents (figure-generator, cross-validator, latex-exporter) and experiment-coder all write code, execute, evaluate, and iterate within themselves.

**Why evidence extraction?** Peer review taught us: "Paper X achieves good results" is worthless. "Paper X achieves 0.94 F1 on ToxicChat (Table 2, 8B model, 4-bit, A100)" is science. Every number traces to a source location.

**Why epistemic classification?** The most common failure in AI surveys is presenting estimates as results. Tagging [MEASURED]/[INFERRED]/[HYPOTHESIZED] at extraction time prevents overclaiming at writing time. The fact-checker and academic-reviewer enforce it.

**Why PRISMA?** "We found 18 relevant papers" means nothing without knowing how. Documenting queries, databases, criteria, and the screening funnel makes the review reproducible and defensible.

**Why experiments?** A survey without empirical validation is speculation. With `--experiments`, the system designs experiments based on evidence gaps, runs them on your hardware, and includes the results alongside paper-reported evidence — clearly distinguished as `[EMPIRICAL]` vs `[MEASURED]`.

**Why project context?** The agent reads `CLAUDE.md` and `README.md` on the first iteration. If your project defines hypotheses, priorities, or constraints, the research adapts to them from the start.

**Why SQLite?** Six tables (papers, analyses, evidence, quality_scores, agent_messages, schema_version) with proper foreign keys. WAL mode for concurrent access. Zero pip dependencies.

**Why 22 agents?** Screening requires different judgment than writing, which requires different skills than evidence extraction, which requires different rigor than fact-checking, which requires different expertise than experiment design. Each agent has a focused rubric.

## Requirements

- Claude Code with plugin support
- Python 3.10+
- Internet access (ArXiv and Semantic Scholar APIs)
- `jq` (used by stop hook for JSON processing)
- For `--experiments`: `torch`, `transformers`, `datasets` (pip packages — installed by experiment-coder as needed)

## Acknowledgments

### [Autoresearch](https://github.com/karpathy/autoresearch) — Andrej Karpathy

> *"One day, frontier AI research used to be done by meat computers in between eating, sleeping, having other fun, and synchronizing once in a while using sound wave interconnect in the ritual of 'group meeting'. That era is long gone."*

Our quality gates, experiment-coder, and Phase 7 code-writing agents are direct adaptations of the Autoresearch pattern.

### [Ralph Wiggum Technique](https://ghuntley.com/ralph/) — Geoffrey Huntley

The stop hook loop mechanism. Our phase-aware extension adds a 7-phase state machine with quality gates and inter-agent communication. The [Claude Code implementation](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum) by Daisy Hollman provided the reference.

### [Autosearch](https://github.com/FullStackRetrieval-com/RetrievalTutorials) — Multi-Agent Academic Research

The multi-agent architecture: specialized roles with mandatory group meetings and inter-agent message protocol.

### Additional Inspirations

- **[Claude Code](https://github.com/anthropics/claude-code)** by Anthropic — plugin system, hook architecture, agent framework
- **[ar5iv](https://ar5iv.labs.arxiv.org/)** — HTML rendering of arxiv papers for full-text analysis
- **[Semantic Scholar API](https://api.semanticscholar.org/)** by Allen AI — academic paper search
- **[PRISMA](https://www.prisma-statement.org/)** — systematic review reporting guidelines

## License

[MIT](LICENSE)
