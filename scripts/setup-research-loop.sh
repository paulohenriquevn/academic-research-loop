#!/bin/bash

# Academic Research Loop - Setup Script
# Creates state file and output directory for the research pipeline.

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
TOPIC_PARTS=()
MAX_ITERATIONS=50
COMPLETION_PROMISE="RESEARCH COMPLETE"
MIN_PAPERS=10
OUTPUT_DIR="./research-output"

while [[ $# -gt 0 ]]; do
  case $1 in
    -h|--help)
      cat << 'HELP_EOF'
Academic Research Loop - Autonomous academic research pipeline

USAGE:
  /research-loop [TOPIC...] [OPTIONS]

ARGUMENTS:
  TOPIC...    Research topic or question (can be multiple words without quotes)

OPTIONS:
  --max-iterations <n>           Max global iterations (default: 50)
  --completion-promise '<text>'  Promise phrase (default: "RESEARCH COMPLETE")
  --min-papers <n>               Minimum papers to discover (default: 10)
  --output-dir <path>            Output directory (default: ./research-output)
  -h, --help                     Show this help message

DESCRIPTION:
  Starts an autonomous academic research pipeline that iterates through
  7 phases: discovery, screening, analysis, synthesis, writing, review, polish.

  The agent searches Arxiv and Semantic Scholar for papers, analyzes them,
  synthesizes findings, and produces a complete survey/paper in Markdown
  with BibTeX citations.

PHASES:
  1. Discovery   (max 3 iter)  Search for papers across multiple sources
  2. Screening   (max 2 iter)  Score candidates for relevance
  3. Analysis    (max 5 iter)  Deep-read shortlisted papers
  4. Synthesis   (max 2 iter)  Identify themes, gaps, contradictions
  5. Writing     (max 3 iter)  Draft the paper with citations
  6. Review      (max 2 iter)  Academic peer-review and revision
  7. Polish      (max 1 iter)  Final formatting and citation validation

EXAMPLES:
  /research-loop Transformer architectures for protein folding
  /research-loop "LLMs for scientific discovery" --min-papers 15
  /research-loop RAG techniques --max-iterations 30 --output-dir ./rag-survey

OUTPUT:
  research-output/
  ├── state/candidates.json     All discovered papers
  ├── state/shortlist.json      Screened papers
  ├── state/analyses/           Per-paper analysis files
  ├── synthesis.md              Cross-paper synthesis
  ├── draft.md                  Paper draft
  ├── references.bib            BibTeX bibliography
  └── final.md                  Polished final paper
HELP_EOF
      exit 0
      ;;
    --max-iterations)
      if [[ -z "${2:-}" ]] || ! [[ "$2" =~ ^[0-9]+$ ]]; then
        echo "❌ Error: --max-iterations requires a positive integer (got: '${2:-}')" >&2
        exit 1
      fi
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --completion-promise)
      if [[ -z "${2:-}" ]]; then
        echo "❌ Error: --completion-promise requires a text argument" >&2
        exit 1
      fi
      COMPLETION_PROMISE="$2"
      shift 2
      ;;
    --min-papers)
      if [[ -z "${2:-}" ]] || ! [[ "$2" =~ ^[0-9]+$ ]] || [[ "$2" -eq 0 ]]; then
        echo "❌ Error: --min-papers requires a positive integer (got: '${2:-}')" >&2
        exit 1
      fi
      MIN_PAPERS="$2"
      shift 2
      ;;
    --output-dir)
      if [[ -z "${2:-}" ]]; then
        echo "❌ Error: --output-dir requires a path argument" >&2
        exit 1
      fi
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      TOPIC_PARTS+=("$1")
      shift
      ;;
  esac
done

TOPIC="${TOPIC_PARTS[*]}"

if [[ -z "$TOPIC" ]]; then
  echo "❌ Error: No research topic provided" >&2
  echo "" >&2
  echo "   Examples:" >&2
  echo "     /research-loop Transformer architectures for protein folding" >&2
  echo "     /research-loop LLMs for scientific discovery --min-papers 15" >&2
  echo "" >&2
  echo "   For all options: /research-loop --help" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Resolve research prompt template
# ---------------------------------------------------------------------------
PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROMPT_TEMPLATE="$PLUGIN_ROOT/templates/research-prompt.md"

if [[ ! -f "$PROMPT_TEMPLATE" ]]; then
  echo "❌ Error: Research prompt template not found at $PROMPT_TEMPLATE" >&2
  exit 1
fi

# Replace placeholders in template
RESEARCH_PROMPT=$(sed \
  -e "s|{{TOPIC}}|$TOPIC|g" \
  -e "s|{{OUTPUT_DIR}}|$OUTPUT_DIR|g" \
  -e "s|{{MIN_PAPERS}}|$MIN_PAPERS|g" \
  -e "s|{{COMPLETION_PROMISE}}|$COMPLETION_PROMISE|g" \
  -e "s|{{PLUGIN_ROOT}}|$PLUGIN_ROOT|g" \
  "$PROMPT_TEMPLATE")

# ---------------------------------------------------------------------------
# Create output directory structure
# ---------------------------------------------------------------------------
mkdir -p "$OUTPUT_DIR/state/analyses"
mkdir -p "$OUTPUT_DIR/state/meetings"

# Initialize empty candidates and shortlist if they don't exist
if [[ ! -f "$OUTPUT_DIR/state/candidates.json" ]]; then
  echo "[]" > "$OUTPUT_DIR/state/candidates.json"
fi
if [[ ! -f "$OUTPUT_DIR/state/shortlist.json" ]]; then
  echo "[]" > "$OUTPUT_DIR/state/shortlist.json"
fi

# Initialize empty BibTeX file
if [[ ! -f "$OUTPUT_DIR/references.bib" ]]; then
  cat > "$OUTPUT_DIR/references.bib" <<'BIB_EOF'
% Academic Research Loop - Auto-generated BibTeX bibliography
% Do not edit manually — managed by manage_citations.py

BIB_EOF
fi

# Initialize SQLite database
if [[ ! -f "$OUTPUT_DIR/research.db" ]]; then
  python3 "$PLUGIN_ROOT/scripts/paper_database.py" init --db-path "$OUTPUT_DIR/research.db" > /dev/null
fi

# ---------------------------------------------------------------------------
# Create state file
# ---------------------------------------------------------------------------
mkdir -p .claude

cat > .claude/research-loop.local.md <<EOF
---
active: true
topic: "$TOPIC"
current_phase: 1
phase_name: "discovery"
phase_iteration: 1
global_iteration: 1
max_global_iterations: $MAX_ITERATIONS
completion_promise: "$COMPLETION_PROMISE"
started_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
output_dir: "$OUTPUT_DIR"
min_papers: $MIN_PAPERS
papers_found: 0
papers_screened: 0
papers_analyzed: 0
---

$RESEARCH_PROMPT
EOF

# ---------------------------------------------------------------------------
# Output setup message
# ---------------------------------------------------------------------------
cat <<EOF
📚 Academic Research Loop activated!

Topic: $TOPIC
Output: $OUTPUT_DIR/
Max iterations: $MAX_ITERATIONS
Min papers: $MIN_PAPERS
Completion promise: $COMPLETION_PROMISE

Pipeline phases:
  1. Discovery   — Search Arxiv + Semantic Scholar
  2. Screening   — Score and filter candidates
  3. Analysis    — Deep-read shortlisted papers
  4. Synthesis   — Identify themes and gaps
  5. Writing     — Draft paper with citations
  6. Review      — Academic peer-review
  7. Polish      — Final formatting + bibliography

State: .claude/research-loop.local.md
Monitor: grep 'current_phase\|global_iteration\|papers_' .claude/research-loop.local.md

EOF

echo "═══════════════════════════════════════════════════════════"
echo "CRITICAL — Completion Promise"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "To complete the research, output this EXACT text:"
echo "  <promise>$COMPLETION_PROMISE</promise>"
echo ""
echo "ONLY output this when the research paper is GENUINELY complete."
echo "Do NOT output false promises to exit the loop."
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Starting Phase 1: Discovery..."
echo ""
echo "$RESEARCH_PROMPT"
