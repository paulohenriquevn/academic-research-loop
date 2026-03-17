#!/bin/bash

# Academic Research Loop - Phase-Aware Stop Hook
# Extends Ralph Wiggum's stop hook with a 7+1 phase research pipeline.
# Phases: discovery → screening → analysis → synthesis → writing → review → polish [→ revision]

set -euo pipefail

HOOK_INPUT=$(cat)

STATE_FILE=".claude/research-loop.local.md"

if [[ ! -f "$STATE_FILE" ]]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# Parse state file frontmatter
# ---------------------------------------------------------------------------
FRONTMATTER=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$STATE_FILE")

parse_field() {
  local field="$1"
  echo "$FRONTMATTER" | grep "^${field}:" | sed "s/${field}: *//" | sed 's/^"\(.*\)"$/\1/'
}

CURRENT_PHASE=$(parse_field "current_phase")
PHASE_NAME=$(parse_field "phase_name")
PHASE_ITERATION=$(parse_field "phase_iteration")
GLOBAL_ITERATION=$(parse_field "global_iteration")
MAX_GLOBAL_ITERATIONS=$(parse_field "max_global_iterations")
COMPLETION_PROMISE=$(parse_field "completion_promise")
TOPIC=$(parse_field "topic")
OUTPUT_DIR=$(parse_field "output_dir")
PAPERS_FOUND=$(parse_field "papers_found")
PAPERS_SCREENED=$(parse_field "papers_screened")
PAPERS_ANALYZED=$(parse_field "papers_analyzed")
EXPERIMENTS_ENABLED=$(parse_field "experiments_enabled")
HUMAN_REVIEW_ENABLED=$(parse_field "human_review_enabled")

# Phase max iterations (bash associative array)
declare -A PHASE_MAX_ITER
PHASE_MAX_ITER[1]=3   # discovery
PHASE_MAX_ITER[2]=2   # screening
PHASE_MAX_ITER[3]=5   # analysis
PHASE_MAX_ITER[4]=3   # synthesis (outline + critique + revision)
PHASE_MAX_ITER[5]=4   # writing (instructions + per-section writing)
PHASE_MAX_ITER[6]=3   # review (peer review + fact-check + revision)
PHASE_MAX_ITER[7]=2   # polish (figures + cross-validation + LaTeX export)
PHASE_MAX_ITER[8]=5   # revision from human review (triage + actions + revise + quality gate + finalize)

# Extend Phase 4 for experiments
if [[ "$EXPERIMENTS_ENABLED" == "true" ]]; then
  PHASE_MAX_ITER[4]=6   # synthesis + experiment design + experiment execution
fi

# Phase names lookup
declare -A PHASE_NAMES
PHASE_NAMES[1]="discovery"
PHASE_NAMES[2]="screening"
PHASE_NAMES[3]="analysis"
PHASE_NAMES[4]="synthesis"
PHASE_NAMES[5]="writing"
PHASE_NAMES[6]="review"
PHASE_NAMES[7]="polish"
PHASE_NAMES[8]="revision"

# Quality gate: phases that require quality evaluation before advancing
# Format: phase_number -> 1 (requires gate) or 0 (no gate)
declare -A PHASE_QUALITY_GATE
PHASE_QUALITY_GATE[1]=0   # discovery — just counting papers
PHASE_QUALITY_GATE[2]=1   # screening — quality of rationales matters
PHASE_QUALITY_GATE[3]=1   # analysis — depth of analysis matters
PHASE_QUALITY_GATE[4]=1   # synthesis — quality of themes matters
PHASE_QUALITY_GATE[5]=1   # writing — draft quality matters
PHASE_QUALITY_GATE[6]=1   # review — fact-check results matter
PHASE_QUALITY_GATE[7]=0   # polish — final pass, no gate
PHASE_QUALITY_GATE[8]=1   # revision — must meet acceptance criteria

# ---------------------------------------------------------------------------
# Validate numeric fields
# ---------------------------------------------------------------------------
validate_numeric() {
  local field_name="$1"
  local field_value="$2"
  if [[ ! "$field_value" =~ ^[0-9]+$ ]]; then
    echo "⚠️  Research loop: State file corrupted" >&2
    echo "   File: $STATE_FILE" >&2
    echo "   Problem: '$field_name' is not a valid number (got: '$field_value')" >&2
    echo "   Research loop is stopping. Run /research-loop again to start fresh." >&2
    rm "$STATE_FILE"
    exit 0
  fi
}

validate_numeric "current_phase" "$CURRENT_PHASE"
validate_numeric "phase_iteration" "$PHASE_ITERATION"
validate_numeric "global_iteration" "$GLOBAL_ITERATION"
validate_numeric "max_global_iterations" "$MAX_GLOBAL_ITERATIONS"

# ---------------------------------------------------------------------------
# Check global iteration limit
# ---------------------------------------------------------------------------
if [[ $MAX_GLOBAL_ITERATIONS -gt 0 ]] && [[ $GLOBAL_ITERATION -ge $MAX_GLOBAL_ITERATIONS ]]; then
  echo "🛑 Research loop: Max global iterations ($MAX_GLOBAL_ITERATIONS) reached."
  echo "   Topic: $TOPIC"
  echo "   Final phase: $CURRENT_PHASE ($PHASE_NAME)"
  echo "   Papers found: $PAPERS_FOUND | Screened: $PAPERS_SCREENED | Analyzed: $PAPERS_ANALYZED"
  rm "$STATE_FILE"
  exit 0
fi

# ---------------------------------------------------------------------------
# Read transcript and extract last assistant output
# ---------------------------------------------------------------------------
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | jq -r '.transcript_path')

if [[ ! -f "$TRANSCRIPT_PATH" ]]; then
  echo "⚠️  Research loop: Transcript file not found at $TRANSCRIPT_PATH" >&2
  rm "$STATE_FILE"
  exit 0
fi

if ! grep -q '"role":"assistant"' "$TRANSCRIPT_PATH"; then
  echo "⚠️  Research loop: No assistant messages found in transcript" >&2
  rm "$STATE_FILE"
  exit 0
fi

LAST_LINE=$(grep '"role":"assistant"' "$TRANSCRIPT_PATH" | tail -1)
if [[ -z "$LAST_LINE" ]]; then
  echo "⚠️  Research loop: Failed to extract last assistant message" >&2
  rm "$STATE_FILE"
  exit 0
fi

LAST_OUTPUT=$(echo "$LAST_LINE" | jq -r '
  .message.content |
  map(select(.type == "text")) |
  map(.text) |
  join("\n")
' 2>&1)

if [[ $? -ne 0 ]] || [[ -z "$LAST_OUTPUT" ]]; then
  echo "⚠️  Research loop: Failed to parse assistant message" >&2
  rm "$STATE_FILE"
  exit 0
fi

# ---------------------------------------------------------------------------
# Check for completion promise
# ---------------------------------------------------------------------------
if [[ "$COMPLETION_PROMISE" != "null" ]] && [[ -n "$COMPLETION_PROMISE" ]]; then
  PROMISE_TEXT=$(echo "$LAST_OUTPUT" | perl -0777 -pe 's/.*?<promise>(.*?)<\/promise>.*/$1/s; s/^\s+|\s+$//g; s/\s+/ /g' 2>/dev/null || echo "")

  if [[ -n "$PROMISE_TEXT" ]] && [[ "$PROMISE_TEXT" = "$COMPLETION_PROMISE" ]]; then
    echo "✅ Research loop complete: <promise>$COMPLETION_PROMISE</promise>"
    echo "   Topic: $TOPIC"
    echo "   Total iterations: $GLOBAL_ITERATION"
    echo "   Final phase: $CURRENT_PHASE ($PHASE_NAME)"
    echo "   Papers found: $PAPERS_FOUND | Screened: $PAPERS_SCREENED | Analyzed: $PAPERS_ANALYZED"
    echo "   Output: $OUTPUT_DIR/final.md"
    rm "$STATE_FILE"
    exit 0
  fi
fi

# ---------------------------------------------------------------------------
# Detect phase completion markers and update counters from output
# ---------------------------------------------------------------------------
PHASE_ADVANCED=false
FORCED_ADVANCE=false

# Check for explicit phase completion marker: <!-- PHASE_N_COMPLETE -->
if echo "$LAST_OUTPUT" | grep -qE "<!--\s*PHASE_${CURRENT_PHASE}_COMPLETE\s*-->"; then
  PHASE_ADVANCED=true
fi

# Update paper counters from output markers (if present)
# Format: <!-- PAPERS_FOUND:15 --> <!-- PAPERS_SCREENED:10 --> <!-- PAPERS_ANALYZED:8 -->
NEW_FOUND=$(echo "$LAST_OUTPUT" | grep -oP '<!--\s*PAPERS_FOUND:(\d+)\s*-->' | grep -oP '\d+' | tail -1 || echo "")
NEW_SCREENED=$(echo "$LAST_OUTPUT" | grep -oP '<!--\s*PAPERS_SCREENED:(\d+)\s*-->' | grep -oP '\d+' | tail -1 || echo "")
NEW_ANALYZED=$(echo "$LAST_OUTPUT" | grep -oP '<!--\s*PAPERS_ANALYZED:(\d+)\s*-->' | grep -oP '\d+' | tail -1 || echo "")

[[ -n "$NEW_FOUND" ]] && PAPERS_FOUND="$NEW_FOUND"
[[ -n "$NEW_SCREENED" ]] && PAPERS_SCREENED="$NEW_SCREENED"
[[ -n "$NEW_ANALYZED" ]] && PAPERS_ANALYZED="$NEW_ANALYZED"

# ---------------------------------------------------------------------------
# Quality gate: check if phase completion passed quality evaluation
# ---------------------------------------------------------------------------
QUALITY_FAILED=false

if [[ "$PHASE_ADVANCED" == "true" ]]; then
  HAS_GATE=${PHASE_QUALITY_GATE[$CURRENT_PHASE]:-0}

  if [[ "$HAS_GATE" == "1" ]]; then
    # Check for quality score in output: <!-- QUALITY_SCORE:0.75 --> <!-- QUALITY_PASSED:1 -->
    QUALITY_SCORE=$(echo "$LAST_OUTPUT" | grep -oP '<!--\s*QUALITY_SCORE:([\d.]+)\s*-->' | grep -oP '[\d.]+' | tail -1 || echo "")
    QUALITY_PASSED=$(echo "$LAST_OUTPUT" | grep -oP '<!--\s*QUALITY_PASSED:(\d)\s*-->' | grep -oP '\d' | tail -1 || echo "")

    if [[ -n "$QUALITY_PASSED" ]] && [[ "$QUALITY_PASSED" == "0" ]]; then
      # Quality gate FAILED — repeat this phase (Autoresearch discard pattern)
      PHASE_ADVANCED=false
      QUALITY_FAILED=true
    fi
  fi
fi

# Check for phase timeout (forced advancement)
CURRENT_PHASE_MAX=${PHASE_MAX_ITER[$CURRENT_PHASE]:-3}
if [[ "$PHASE_ADVANCED" != "true" ]] && [[ "$QUALITY_FAILED" != "true" ]] && [[ $PHASE_ITERATION -ge $CURRENT_PHASE_MAX ]]; then
  PHASE_ADVANCED=true
  FORCED_ADVANCE=true
fi

# ---------------------------------------------------------------------------
# HARD BLOCKS — verify mandatory work BEFORE allowing phase advancement
# The agent CANNOT bypass these. No evidence = no advancement. Period.
# ---------------------------------------------------------------------------
HARD_BLOCK=false
HARD_BLOCK_MSG=""

if [[ "$PHASE_ADVANCED" == "true" ]]; then
  # Resolve OUTPUT_DIR to absolute path for reliable DB access
  if [[ "$OUTPUT_DIR" == ./* ]] || [[ "$OUTPUT_DIR" != /* ]]; then
    ABS_OUTPUT_DIR="$(pwd)/$OUTPUT_DIR"
  else
    ABS_OUTPUT_DIR="$OUTPUT_DIR"
  fi
  DB_PATH="$ABS_OUTPUT_DIR/research.db"

  # Phase 3 → 4: Evidence table MUST have entries
  if [[ $CURRENT_PHASE -eq 3 ]]; then
    if [[ -f "$DB_PATH" ]]; then
      EVIDENCE_COUNT=$(python3 -c "import sqlite3; db=sqlite3.connect('$DB_PATH'); print(db.execute('SELECT COUNT(*) FROM evidence').fetchone()[0])" 2>/dev/null || echo "0")
    else
      EVIDENCE_COUNT=0
    fi
    if [[ "$EVIDENCE_COUNT" -eq 0 ]]; then
      HARD_BLOCK=true
      HARD_BLOCK_MSG="🚫 HARD BLOCK: Phase 3 cannot advance — evidence table has 0 entries (DB: $DB_PATH). You MUST run the evidence-extractor agent and store quantitative results via paper_database.py add-evidence for EVERY analyzed paper. The paper is WORTHLESS without verified evidence in the database. Do NOT emit PHASE_3_COMPLETE until evidence count > 0."
    fi
  fi

  # Phase 4 → 5: If experiments enabled, experiment scripts AND results MUST exist
  if [[ $CURRENT_PHASE -eq 4 ]] && [[ "$EXPERIMENTS_ENABLED" == "true" ]]; then
    EXP_COUNT=$(find "$ABS_OUTPUT_DIR/experiments" -name "exp*.py" 2>/dev/null | wc -l)
    if [[ "$EXP_COUNT" -eq 0 ]]; then
      HARD_BLOCK=true
      HARD_BLOCK_MSG="🚫 HARD BLOCK: Phase 4 cannot advance — experiments_enabled=true but 0 experiment scripts found in $ABS_OUTPUT_DIR/experiments/. You MUST run experiment-designer + experiment-coder to create AND EXECUTE experiments. Experiments are NOT optional when --experiments is set."
    else
      RESULT_COUNT=$(find "$ABS_OUTPUT_DIR/experiments/results" -name "*.json" -o -name "*.log" 2>/dev/null | wc -l)
      if [[ "$RESULT_COUNT" -eq 0 ]]; then
        HARD_BLOCK=true
        HARD_BLOCK_MSG="🚫 HARD BLOCK: Phase 4 cannot advance — $EXP_COUNT experiment scripts exist but 0 results in $ABS_OUTPUT_DIR/experiments/results/. You MUST EXECUTE the experiments. Run each exp_*.py and store results as evidence_type='empirical'."
      fi
    fi
  fi

  # Phase 4 → 5: Evidence table must have grown (experiments add empirical evidence)
  if [[ $CURRENT_PHASE -eq 4 ]] && [[ "$EXPERIMENTS_ENABLED" == "true" ]] && [[ "$HARD_BLOCK" != "true" ]]; then
    if [[ -f "$DB_PATH" ]]; then
      EMPIRICAL_COUNT=$(python3 -c "import sqlite3; db=sqlite3.connect('$DB_PATH'); print(db.execute(\"SELECT COUNT(*) FROM evidence WHERE evidence_type='empirical'\").fetchone()[0])" 2>/dev/null || echo "0")
    else
      EMPIRICAL_COUNT=0
    fi
    if [[ "$EMPIRICAL_COUNT" -eq 0 ]]; then
      HARD_BLOCK=true
      HARD_BLOCK_MSG="🚫 HARD BLOCK: Phase 4 cannot advance — experiments ran but 0 empirical evidence entries in DB. You MUST store experiment results via paper_database.py add-evidence with evidence_type='empirical'."
    fi
  fi

  # ALL gated phases (2-6): Quality scores MUST exist in DB
  if [[ "$HARD_BLOCK" != "true" ]] && [[ $CURRENT_PHASE -ge 2 ]] && [[ $CURRENT_PHASE -le 6 ]]; then
    HAS_GATE=${PHASE_QUALITY_GATE[$CURRENT_PHASE]:-0}
    if [[ "$HAS_GATE" == "1" ]]; then
      if [[ -f "$DB_PATH" ]]; then
        QS_EXISTS=$(python3 -c "import sqlite3; db=sqlite3.connect('$DB_PATH'); print(db.execute('SELECT COUNT(*) FROM quality_scores WHERE phase=$CURRENT_PHASE').fetchone()[0])" 2>/dev/null || echo "0")
      else
        QS_EXISTS=0
      fi
      if [[ "$QS_EXISTS" -eq 0 ]]; then
        HARD_BLOCK=true
        HARD_BLOCK_MSG="🚫 HARD BLOCK: Phase $CURRENT_PHASE ($PHASE_NAME) cannot advance — no quality score in DB for this phase. You MUST: (1) run quality-evaluator agent, (2) output <!-- QUALITY_SCORE:X.XX --> <!-- QUALITY_PASSED:1 -->, (3) record via paper_database.py add-quality-score --phase $CURRENT_PHASE."
      fi
    fi
  fi

  # If hard blocked, prevent advancement and repeat the phase
  if [[ "$HARD_BLOCK" == "true" ]]; then
    PHASE_ADVANCED=false
    FORCED_ADVANCE=false
    QUALITY_FAILED=false
    echo "🚫 HARD BLOCK ACTIVATED — Phase $CURRENT_PHASE cannot advance. DB: $DB_PATH" >&2
  fi
fi

# Advance phase if needed
MAX_PHASE=7
if [[ "$HUMAN_REVIEW_ENABLED" == "true" ]]; then
  MAX_PHASE=8
fi

if [[ "$PHASE_ADVANCED" == "true" ]]; then
  # When transitioning from Phase 7 to Phase 8, check for review files
  if [[ $CURRENT_PHASE -eq 7 ]] && [[ "$HUMAN_REVIEW_ENABLED" == "true" ]]; then
    REVIEW_COUNT=$(find "$OUTPUT_DIR/reviews" -name "REVIEW-*.md" ! -name "REVIEW-TEMPLATE.md" 2>/dev/null | wc -l)
    if [[ $REVIEW_COUNT -eq 0 ]]; then
      echo "📝 Research loop: Phase 7 complete. Waiting for human reviews."
      echo "   Place REVIEW-N.md files in: $OUTPUT_DIR/reviews/"
      echo "   Template available at: $OUTPUT_DIR/reviews/REVIEW-TEMPLATE.md"
      echo "   Then re-run /research-loop to process reviews."
      rm "$STATE_FILE"
      exit 0
    fi
  fi

  if [[ $CURRENT_PHASE -ge $MAX_PHASE ]]; then
    echo "🛑 Research loop: All $MAX_PHASE phases complete but no completion promise detected."
    echo "   Topic: $TOPIC"
    echo "   Output should be in: $OUTPUT_DIR/final.md"
    rm "$STATE_FILE"
    exit 0
  fi

  CURRENT_PHASE=$((CURRENT_PHASE + 1))
  PHASE_NAME="${PHASE_NAMES[$CURRENT_PHASE]}"
  PHASE_ITERATION=0  # Will be incremented to 1 below
fi

# ---------------------------------------------------------------------------
# Increment counters
# ---------------------------------------------------------------------------
NEXT_GLOBAL=$((GLOBAL_ITERATION + 1))
NEXT_PHASE_ITER=$((PHASE_ITERATION + 1))

# ---------------------------------------------------------------------------
# Extract prompt text (everything after second ---)
# ---------------------------------------------------------------------------
PROMPT_TEXT=$(awk '/^---$/{i++; next} i>=2' "$STATE_FILE")

if [[ -z "$PROMPT_TEXT" ]]; then
  echo "⚠️  Research loop: No prompt text found in state file" >&2
  rm "$STATE_FILE"
  exit 0
fi

# ---------------------------------------------------------------------------
# Update state file atomically
# ---------------------------------------------------------------------------
TEMP_FILE="${STATE_FILE}.tmp.$$"
cat > "$TEMP_FILE" <<EOF
---
active: true
topic: "$TOPIC"
current_phase: $CURRENT_PHASE
phase_name: "$PHASE_NAME"
phase_iteration: $NEXT_PHASE_ITER
global_iteration: $NEXT_GLOBAL
max_global_iterations: $MAX_GLOBAL_ITERATIONS
completion_promise: "$(echo "$COMPLETION_PROMISE" | sed 's/"/\\"/g')"
started_at: "$(parse_field "started_at")"
output_dir: "$OUTPUT_DIR"
min_papers: $(parse_field "min_papers")
papers_found: $PAPERS_FOUND
papers_screened: $PAPERS_SCREENED
papers_analyzed: $PAPERS_ANALYZED
experiments_enabled: ${EXPERIMENTS_ENABLED:-false}
human_review_enabled: ${HUMAN_REVIEW_ENABLED:-false}
---

$PROMPT_TEXT
EOF
mv "$TEMP_FILE" "$STATE_FILE"

# ---------------------------------------------------------------------------
# Build system message with phase context
# ---------------------------------------------------------------------------
PHASE_MAX_FOR_CURRENT=${PHASE_MAX_ITER[$CURRENT_PHASE]:-3}

SYSTEM_MSG="📚 Research Loop | Phase $CURRENT_PHASE/$MAX_PHASE: $PHASE_NAME | Phase iter $NEXT_PHASE_ITER/$PHASE_MAX_FOR_CURRENT | Global iter $NEXT_GLOBAL"
SYSTEM_MSG="$SYSTEM_MSG | Papers: found=$PAPERS_FOUND screened=$PAPERS_SCREENED analyzed=$PAPERS_ANALYZED"
SYSTEM_MSG="$SYSTEM_MSG | ⚠️ MANDATORY: Start with GROUP MEETING (chief-researcher + all specialists) before ANY work"

if [[ "$FORCED_ADVANCE" == "true" ]]; then
  SYSTEM_MSG="$SYSTEM_MSG | ⚠️ Previous phase timed out — forced advancement to $PHASE_NAME"
fi

if [[ "$QUALITY_FAILED" == "true" ]]; then
  SYSTEM_MSG="$SYSTEM_MSG | ❌ Quality gate FAILED — repeating phase. Review evaluator feedback and improve output."
fi

if [[ "$HARD_BLOCK" == "true" ]]; then
  SYSTEM_MSG="$SYSTEM_MSG | $HARD_BLOCK_MSG"
fi

if [[ "$COMPLETION_PROMISE" != "null" ]] && [[ -n "$COMPLETION_PROMISE" ]]; then
  SYSTEM_MSG="$SYSTEM_MSG | To finish: <promise>$COMPLETION_PROMISE</promise> (ONLY when TRUE)"
fi

# ---------------------------------------------------------------------------
# Block exit and re-inject prompt
# ---------------------------------------------------------------------------
jq -n \
  --arg prompt "$PROMPT_TEXT" \
  --arg msg "$SYSTEM_MSG" \
  '{
    "decision": "block",
    "reason": $prompt,
    "systemMessage": $msg
  }'

exit 0
