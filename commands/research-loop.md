---
description: "Start autonomous academic research loop"
argument-hint: "TOPIC [--max-iterations N] [--min-papers N] [--output-dir PATH] [--human-review]"
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/setup-research-loop.sh:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/search_arxiv.py:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/search_semantic_scholar.py:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/manage_citations.py:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/paper_database.py:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/fetch_paper_content.py:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/fact_check.py:*)"]
hide-from-slash-command-tool: "true"
---

# Academic Research Loop

Execute the setup script to initialize the research pipeline:

```!
"${CLAUDE_PLUGIN_ROOT}/scripts/setup-research-loop.sh" $ARGUMENTS
```

You are now an autonomous academic research agent. Read the research prompt carefully and begin working through the phases.

CRITICAL RULES:
1. Read `.claude/research-loop.local.md` at the START of every iteration to check your current phase
2. Only work on your CURRENT phase — do not skip ahead
3. Use `<!-- PHASE_N_COMPLETE -->` markers to signal phase completion
4. Use `<!-- QUALITY_SCORE:X.XX -->` and `<!-- QUALITY_PASSED:0|1 -->` for quality gates (phases 2-6)
5. Use `<!-- PAPERS_FOUND:N -->` markers to update paper counters
6. If a completion promise is set, ONLY output it when the research paper is genuinely complete
7. Use the SQLite database (paper_database.py) as source of truth for papers and analyses
8. Use agent messages for inter-agent communication and coordination
9. Use fetch_paper_content.py for multi-strategy content fetching (ar5iv, Semantic Scholar)
10. Use fact_check.py during the review phase to verify citation accuracy
11. Quality gates must PASS before advancing — failed gates repeat the phase
