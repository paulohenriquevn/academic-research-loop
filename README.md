# Academic Research Loop

Autonomous academic research pipeline for Claude Code. Give it a topic, walk away, and come back to a complete literature survey with structured citations.

Combines three ideas:
- **[Ralph Wiggum](https://ghuntley.com/ralph/)** — self-referential AI loop via stop hook
- **[Autoresearch](https://github.com/karpathy/autoresearch)** (Karpathy) — autonomous AI experimentation
- **[Autosearch](https://github.com/FullStackRetrieval-com/RetrievalTutorials)** — multi-agent academic research

## Quick Start

```bash
# In your Claude Code session:
/research-loop Transformer architectures for protein folding
```

That's it. Claude will iterate through 7 phases autonomously, searching real academic databases, analyzing papers, and writing a complete survey.

## How It Works

```
/research-loop "Topic"
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  Phase 1: Discovery    (max 3 iterations)           │
│  Search Arxiv + Semantic Scholar for papers          │
├─────────────────────────────────────────────────────┤
│  Phase 2: Screening    (max 2 iterations)           │
│  Score candidates 1-5, build shortlist               │
├─────────────────────────────────────────────────────┤
│  Phase 3: Analysis     (max 5 iterations)           │
│  Deep-read each paper, extract structured findings   │
├─────────────────────────────────────────────────────┤
│  Phase 4: Synthesis    (max 2 iterations)           │
│  Identify themes, gaps, contradictions               │
├─────────────────────────────────────────────────────┤
│  Phase 5: Writing      (max 3 iterations)           │
│  Draft survey paper with [@citations]                │
├─────────────────────────────────────────────────────┤
│  Phase 6: Review       (max 2 iterations)           │
│  Academic peer-review, fix issues                    │
├─────────────────────────────────────────────────────┤
│  Phase 7: Polish       (max 1 iteration)            │
│  Final formatting, citation validation               │
└─────────────────────────────────────────────────────┘
     │
     ▼
  research-output/final.md  ← Complete survey paper
```

Each iteration, the stop hook intercepts Claude's exit and re-injects the research prompt. Claude reads the state file to know its current phase and sees all previous work on disk. Phases advance automatically via completion markers or timeout.

## Commands

### `/research-loop TOPIC [OPTIONS]`

Start a research loop.

| Option | Default | Description |
|--------|---------|-------------|
| `--max-iterations N` | 50 | Max global iterations before auto-stop |
| `--min-papers N` | 10 | Minimum papers to discover |
| `--output-dir PATH` | `./research-output` | Where output files go |
| `--completion-promise TEXT` | `"RESEARCH COMPLETE"` | Promise text to signal completion |

```bash
/research-loop Transformer architectures for protein folding
/research-loop "LLMs for scientific discovery" --min-papers 15
/research-loop RAG techniques --max-iterations 30 --output-dir ./rag-survey
```

### `/research-status`

View current state: phase, iteration, paper counts, output files.

### `/cancel-research`

Cancel an active loop. Output files are preserved.

### `/help`

Full documentation and examples.

## Output Structure

```
research-output/
├── state/
│   ├── candidates.json          # All discovered papers (full metadata)
│   ├── shortlist.json           # Papers that passed screening (score >= 3)
│   └── analyses/                # Per-paper analysis files
│       ├── paper_001.md
│       ├── paper_002.md
│       └── ...
├── synthesis.md                 # Cross-paper thematic synthesis
├── draft.md                     # Paper draft with citations
├── references.bib               # BibTeX bibliography
└── final.md                     # Polished final paper
```

## Tools

All Python scripts use **only stdlib** (zero `pip install`):

| Script | Purpose |
|--------|---------|
| `search_arxiv.py` | Arxiv API search with retry logic |
| `search_semantic_scholar.py` | Semantic Scholar API with rate limiting |
| `manage_citations.py` | BibTeX generation, dedup, validation |
| `paper_database.py` | SQLite database for papers, analyses, quality scores, agent messages |
| `fetch_paper_content.py` | Multi-strategy content fetcher (ar5iv HTML > Semantic Scholar > Arxiv abstract) |
| `fact_check.py` | Cross-references draft claims against paper database |

### Paper Database (`paper_database.py`)

```bash
# Initialize
python3 scripts/paper_database.py init --db-path research.db

# Add/query papers
python3 scripts/paper_database.py add-paper --db-path research.db --paper-json '{...}'
python3 scripts/paper_database.py query --db-path research.db --status shortlisted --min-relevance 3

# Inter-agent messages
python3 scripts/paper_database.py add-message --db-path research.db \
  --from-agent discovery --phase 1 --iteration 1 --message-type finding --content "..."
python3 scripts/paper_database.py query-messages --db-path research.db --phase 4

# Quality scores
python3 scripts/paper_database.py add-quality-score --db-path research.db \
  --phase 5 --phase-name writing --iteration 1 --score 0.75 --threshold 0.7
python3 scripts/paper_database.py quality-history --db-path research.db

# Stats
python3 scripts/paper_database.py stats --db-path research.db
```

### Content Fetching (`fetch_paper_content.py`)

Multi-strategy paper content retrieval:
1. **ar5iv HTML** — full-text arxiv papers rendered as accessible HTML (best quality)
2. **Semantic Scholar** — extended abstract + TLDR + references
3. **Arxiv abstract page** — fallback to abstract only

```bash
python3 scripts/fetch_paper_content.py --arxiv-id 2401.12345
python3 scripts/fetch_paper_content.py --semantic-scholar-id abc123 --arxiv-id 2401.12345
```

### Fact-Checking (`fact_check.py`)

```bash
python3 scripts/fact_check.py check --draft-file draft.md --db-path research.db
python3 scripts/fact_check.py extract-claims --draft-file draft.md
```

## Research Team & Mandatory Group Meetings

Every iteration begins with a **mandatory group meeting** led by the Chief Researcher. No work proceeds until the meeting is complete and minutes are recorded.

```
┌─────────────────────────────────────────────────────┐
│              MANDATORY GROUP MEETING                │
│                                                     │
│  Chief Researcher (leads)                           │
│    ├── Methods Specialist (report)                  │
│    ├── Theory Specialist (report)                   │
│    └── Applications Specialist (report)             │
│                                                     │
│  → Status review                                    │
│  → Researcher briefings                             │
│  → Discussion & debate                              │
│  → Strategic decisions                              │
│  → Task assignments                                 │
│  → Meeting minutes recorded                         │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
              Phase work begins
```

### Research Team (Core — Every Meeting)

| Role | Agent | Focus |
|------|-------|-------|
| **Chief Researcher** | `chief-researcher` | Leads meetings, strategic decisions, task assignment |
| **Methods Specialist** | `researcher-methods` | Methodology, experimental design, metrics, reproducibility |
| **Theory Specialist** | `researcher-theory` | Theoretical frameworks, formal analysis, conceptual taxonomy |
| **Applications Specialist** | `researcher-applications` | Real-world impact, deployment, industry adoption |

### Task Specialists (Called as needed)

| Agent | Phase | Purpose |
|-------|-------|---------|
| `paper-screener` | 2 | Scores papers for relevance (1-5 scale) |
| `paper-analyzer` | 3 | Deep-reads papers using full-text content |
| `synthesis-writer` | 4 | Identifies themes, gaps, and contradictions |
| `outline-architect` | 4 | Designs survey structure with justified organization |
| `outline-critic` | 4 | Reviews outline for coverage, balance, and flow |
| `writing-instructor` | 5 | Generates per-section writing instructions |
| `section-writer` | 5 | Writes individual sections following instructions |
| `quality-evaluator` | 2-6 | Quality gate — PASS/FAIL decision per phase |
| `fact-checker` | 6 | Verifies citations support claims made |
| `academic-reviewer` | 6 | Peer-review style critique and revision |

## Quality Gates (Autoresearch Keep/Discard)

Phases 2-6 have mandatory quality evaluation before advancing:

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

The evaluator scores against phase-specific rubrics (coverage, depth, citations, coherence). Failed phases repeat with evaluator feedback — this is the Autoresearch keep/discard pattern applied to academic research.

Quality scores are tracked in the SQLite database for the full history of attempts.

## Inter-Agent Communication

Agents communicate through a structured message protocol in the database:

| Type | Purpose | Example |
|------|---------|---------|
| `finding` | Cross-paper observations | "Papers A and B contradict on method X" |
| `instruction` | Directives for downstream agents | Per-section writing instructions |
| `feedback` | Critiques and evaluations | Fact-check results, review notes |
| `question` | Requests for clarification | "Should we include tangential paper C?" |
| `decision` | Architectural decisions | "Using thematic organization for outline" |

Each agent reads messages from previous agents before starting work, ensuring context flows through the pipeline.

## Phase Machine

The stop hook is **phase-aware** — it extends Ralph Wiggum's flat loop with:

- **7 distinct phases** with per-phase iteration limits
- **Automatic phase advancement** via `<!-- PHASE_N_COMPLETE -->` markers
- **Forced advancement** when a phase exhausts its iterations (with warning)
- **Paper counter tracking** via `<!-- PAPERS_FOUND:N -->` markers
- **Enriched system messages** showing phase context and metrics

State is tracked in `.claude/research-loop.local.md` (YAML frontmatter + prompt text).

## Testing

```bash
# All Python tests (106 tests)
python3 -m pytest tests/ -v

# Bash tests (31 tests)
bash tests/test_stop_hook.sh
bash tests/test_setup_script.sh

# Total: 137 tests
```

Test coverage:
- `test_manage_citations.py` — 40 tests (BibTeX generation, dedup, validation)
- `test_search_arxiv.py` — 10 tests (query building, XML parsing, fetch)
- `test_search_semantic_scholar.py` — 9 tests (response parsing, API key, filters)
- `test_paper_database.py` — 27 tests (CRUD, quality scores, agent messages, stats)
- `test_fact_check.py` — 10 tests (claim extraction, support verification, full check)
- `test_fetch_paper_content.py` — 10 tests (HTML extraction, fallback strategies)
- `test_stop_hook.sh` — 13 tests (phase machine, quality gates, corruption handling)
- `test_setup_script.sh` — 18 tests (argument parsing, state file creation, validation)

## Design Decisions

**Why Ralph Wiggum pattern?** The stop hook approach is elegant — no external orchestrator needed. Claude Code's hook system handles the loop natively. The agent sees its own work each iteration, enabling genuine self-improvement.

**Why quality gates (Autoresearch pattern)?** Autonomous research without evaluation is just noise. The keep/discard cycle ensures each phase meets a quality threshold before advancing. Failed phases get evaluator feedback and retry — mimicking how Autoresearch evaluates each experiment against `val_bpb`.

**Why inter-agent messages (Autosearch pattern)?** Isolated agents produce fragmented work. The message protocol ensures context flows: the discovery agent's observations inform the screener, the outline architect's decisions guide the writing instructor, and the fact-checker's findings reach the reviewer.

**Why SQLite?** JSON files don't support concurrent reads, querying, or relationship tracking. SQLite is stdlib (`sqlite3`), battle-tested, and supports the relational model needed for papers → analyses → quality scores → agent messages. WAL mode enables concurrent access.

**Why multi-strategy content fetching?** Abstracts alone produce shallow analysis. ar5iv provides full-text HTML for arxiv papers without PDF parsing. Semantic Scholar adds TLDR and reference lists. The fallback chain ensures maximum content with zero external dependencies.

**Why Python stdlib only?** All scripts use `urllib`, `xml.etree`, `sqlite3`, `json`. Zero `pip install` — works out of the box on Python 3.10+.

**Why 10 agents instead of 4?** Academic research requires specialized roles: screening requires different judgment than writing, which requires different skills than fact-checking. Each agent has a focused rubric and clear inputs/outputs. The writing-instructor → section-writer pipeline ensures per-section quality instead of monolithic drafting.

## Requirements

- Claude Code with plugin support
- Python 3.10+ (for search and citation scripts)
- Internet access (for Arxiv and Semantic Scholar APIs)
- `jq` (used by stop hook for JSON processing)

## Inspiration

> "One day, frontier AI research used to be done by meat computers in between eating, sleeping, having other fun, and synchronizing once in a while using sound wave interconnect in the ritual of 'group meeting'."
> — Andrej Karpathy, March 2026
