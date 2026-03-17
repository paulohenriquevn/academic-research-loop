# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Human review mode via `--human-review` flag — processes structured REVIEW-N.md files and produces versioned paper revisions (#REVIEW-1)
- Review handler agent (`agents/review-handler.md`) — triages review items into 5 action types: REVISE, RE_DISCOVER, RE_SYNTHESIZE, EXPERIMENT, ACKNOWLEDGED (#REVIEW-2)
- Revision writer agent (`agents/revision-writer.md`) — rewrites specific sections to address feedback while maintaining epistemic rigor (#REVIEW-3)
- Human review block template (`templates/human-review-block.md`) — Phase 8 instructions for conditional re-execution based on review content (#REVIEW-4)
- Review template (`templates/review-template.md`) — structured format with severity, category, acceptance criteria per item (#REVIEW-5)
- Reviews table in database (`paper_database.py`) — tracks review items with severity, category, action_type, status, resolution (#REVIEW-6)
- DB commands: `add-review`, `update-review`, `query-reviews`, `review-stats` (#REVIEW-6)
- Agent message types: `review_item`, `revision` for Phase 8 communication (#REVIEW-7)
- Quality evaluator Phase 8 rubric: completeness, accuracy, regression, acceptance criteria (threshold 0.75) (#REVIEW-8)
- Paper versioning: `final-v{N}.md` snapshots before each revision round (#REVIEW-9)
- Phase 8 (revision) in stop-hook state machine with review-wait mechanism (#REVIEW-10)
- 24 tests for review feature: CRUD, CLI, stats, schema validation (`tests/test_review_feature.py`) (#REVIEW-11)
- Snowball search commands in `search_semantic_scholar.py`: `citations` (forward) and `references` (backward) via S2 Graph API (#DISC-7)

### Changed
- **CRITICAL:** Stop hook now enforces HARD BLOCKS that prevent phase advancement without mandatory work — agent cannot bypass (#ENFORCE-1):
  - Phase 3→4: evidence table MUST have >0 entries (evidence-extractor MUST run)
  - Phase 3→4: quality_scores table MUST have phase 3 entry
  - Phase 4→5: if experiments_enabled, experiment scripts AND results MUST exist
  - Phase 2-6: quality_scores MUST exist for every gated phase
  - Hard blocks override forced advancement (timeout) — the agent is stuck until the work is done
- Phase 1 discovery now requires minimum 8 diverse queries: solution-oriented, problem-oriented, AND component queries (#DISC-1)
- Phase 1 now mandates snowball search (forward + backward citations) on top 5 papers — catches papers using different terminology (#DISC-2)
- Rate-limited queries must be retried, not skipped — skipped queries are automatic Phase 1 quality gate FAIL (#DISC-3)
- Default max results increased from 10 to 20 for both ArXiv and Semantic Scholar scripts (#DISC-4)
- Semantic Scholar retry logic strengthened: 5 retries (was 3), 5s base delay (was 2s) (#DISC-5)
- Phase 1 quality gate threshold raised from 0.6 to 0.7 with new dimensions: query diversity (0.25), snowball search (0.20) (#DISC-6)
- Phase 8 quality gate threshold raised from 0.75 to 0.80 with mandatory numeric verification dimension (0.25) (#REVIEW-12)
- Revision-writer now BLOCKS on unverified numbers — must run experiment or remove claim, cannot proceed (#REVIEW-13)
- EXPERIMENT action type now requires actual execution on available hardware, not just design (#REVIEW-14)

### Added (previous)
- Experimentation mode via `--experiments` flag — writes code, executes benchmarks, trains models, stores empirical results (#EXP-1)
- Experiment designer agent (`agents/experiment-designer.md`) — reads gaps, checks hardware, proposes feasible experiments with runtime estimates (#EXP-2)
- Experiment coder agent (`agents/experiment-coder.md`) — Autoresearch pattern: writes scripts, executes, evaluates, keep/discard, max 3 retries (#EXP-3)
- Experimentation block template (`templates/experimentation-block.md`) — modifies Phase 4 to include experiment execution after synthesis (#EXP-4)
- Phase 4 max iterations increased from 3 to 6 when `--experiments` is enabled (#EXP-5)
- `evidence_type="empirical"` in evidence table distinguishes local experiments from paper-reported results (#EXP-6)
- Evidence extractor agent (`agents/evidence-extractor.md`) — obsessively extracts every quantitative result from papers: metrics, baselines, ablations, scaling, experimental conditions (#EVIDENCE-1)
- Evidence table in database (`paper_database.py`) — structured storage: metric, value, dataset, baseline, conditions, evidence_type, source_location. CLI: `add-evidence`, `query-evidence`, `evidence-matrix` (#EVIDENCE-2)
- Evidence matrix generation in Phase 4 — cross-paper comparison using ONLY measured values, organized by metric × system (#EVIDENCE-3)
- Paper template section "Quantitative Evidence Summary" with cross-paper matrix, ablation evidence, scaling evidence, and experimental gaps (#EVIDENCE-4)
- `state/evidence/` directory for per-paper evidence extraction files (#EVIDENCE-5)
- PRISMA-like search methodology tracking in Phase 1 — queries, databases, inclusion/exclusion criteria, screening funnel logged to `state/methodology.md` (#RIGOR-1)
- Evidence classification system: every finding tagged [MEASURED], [INFERRED], [HYPOTHESIZED], or [ARCHITECTURAL] — enforced in paper-analyzer, section-writer, fact-checker, and academic-reviewer (#RIGOR-2)
- Structured corpus table generation in Phase 4 — standardized variable extraction across all papers with evidence strength per row (#RIGOR-3)
- Epistemic calibration in section-writer — language strength must match evidence tag (e.g., "demonstrates" only for [MEASURED]) (#RIGOR-4)
- Overclaiming detection in academic-reviewer — flags heterogeneous comparisons, implicit domain transfers, and assertiveness exceeding evidence (#RIGOR-5)
- Quality evaluator now includes `epistemic_calibration`, `corpus_table`, `overclaiming_fixed`, and `confound_treatment` dimensions (#RIGOR-6)
- Paper template includes: genre declaration, search methodology section, structured corpus table, evidence labels on comparison tables (#RIGOR-7)
- Applied research mode via `--codebase PATH` flag on `/research-loop` — analyzes a project codebase and maps literature to its components (#APPLIED-1)
- Codebase analyzer agent (`agents/codebase-analyzer.md`) — reads source code and docs, extracts component map, derives research questions per module (#APPLIED-2)
- Gap analyzer agent (`agents/gap-analyzer.md`) — compares literature synthesis against codebase components, classifies gaps as Solved/Partial/Open/Conflicting (#APPLIED-3)
- Applied research block template (`templates/applied-research-block.md`) — modifies all 7 phases for codebase-aware behavior when `--codebase` is set (#APPLIED-4)
- Paper template sections for applied mode: Component-Literature Mapping, Gap Matrix, Implementation Recommendations, Proposed Benchmarks, Research Contribution Opportunities (#APPLIED-5)

### Added (previous)
- Figure generation agent (`agents/figure-generator.md`) — writes Python scripts to generate publication-quality SVG figures using the Autoresearch keep/discard pattern (#MIT-1)
- Cross-validation agent (`agents/cross-validator.md`) — writes and executes validation scripts checking bibtex_key integrity, citation coverage, word count, figure refs, meeting minutes (#MIT-2)
- LaTeX export agent (`agents/latex-exporter.md`) — writes Markdown-to-LaTeX converter scripts producing submission-ready `.tex` files (#MIT-3)
- SVG utility library (`scripts/svg_utils.py`) — thin primitives (SvgCanvas, draw_axes, draw_legend, nice_ticks) for figure-generator agent to build on (#MIT-1)
- `manage_citations.py sync-db` command — retroactively syncs bibtex_keys from `.bib` file to SQLite papers table by matching arxiv IDs and DOIs (#FIX-1)
- `manage_citations.py add --db-path --paper-id` — auto-syncs bibtex_key to DB when adding a citation entry (#FIX-1)
- `fact_check.py --bib-file` parameter — enables self-healing of NULL bibtex_keys before fact-checking (#FIX-2)
- Tests for `svg_utils.py` — 33 tests covering all SVG primitives and helpers (#MIT-1)
- Tests for `sync_bibtex_key_to_db` and `cmd_sync_db` — 4 tests covering DB sync flow (#FIX-1)

### Changed
- Phase 7 (Polish) in `research-prompt.md` — expanded from basic formatting to full MIT-level output pipeline: figure generation, cross-validation, LaTeX export, deliverable manifest verification (#MIT-4)
- `paper-template.md` — upgraded to MIT-level structure with figure placeholders, word count targets, self-limitations section, structured abstract format (#MIT-5)
- `quality-evaluator.md` — dimensions field is now REQUIRED for both PASS and FAIL decisions; feedback must be substantive on PASS (#FIX-3)
- `fact_check.py` — self-healing mechanism: auto-syncs NULL bibtex_keys from `.bib` before loading papers; warns loudly instead of silently reporting 134 missing refs (#FIX-2)
- Phase 3 instructions in `research-prompt.md` — `manage_citations.py add` now includes `--db-path` and `--paper-id` to prevent NULL bibtex_key (#FIX-1)

### Fixed
- Stop hook bash tests failing due to missing `experiments_enabled` and `human_review_enabled` fields in test state files (#FIX-4)
- bibtex_key never synced to SQLite papers table — root cause of fact-check reporting 100% missing references (#FIX-1)
- fact_check.py silently degraded with NULL bibtex_keys instead of failing loudly or self-healing (#FIX-2)
- quality-evaluator returned empty dimensions `{}` for passing phases, making quality audit impossible (#FIX-3)
