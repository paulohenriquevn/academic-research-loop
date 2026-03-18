#!/bin/bash

# Unit tests for the academic research loop stop hook.
# Tests state file parsing, phase advancement, completion detection, and error handling.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK_SCRIPT="$SCRIPT_DIR/../hooks/stop-hook.sh"

PASS=0
FAIL=0
TOTAL=0

# Colors
GREEN="\033[0;32m"
RED="\033[0;31m"
RESET="\033[0m"

assert_exit_code() {
  local test_name="$1"
  local expected="$2"
  local actual="$3"
  TOTAL=$((TOTAL + 1))
  if [[ "$actual" -eq "$expected" ]]; then
    echo -e "  ${GREEN}PASS${RESET} $test_name"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}FAIL${RESET} $test_name (expected exit $expected, got $actual)"
    FAIL=$((FAIL + 1))
  fi
}

assert_contains() {
  local test_name="$1"
  local needle="$2"
  local haystack="$3"
  TOTAL=$((TOTAL + 1))
  if echo "$haystack" | grep -q "$needle"; then
    echo -e "  ${GREEN}PASS${RESET} $test_name"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}FAIL${RESET} $test_name (expected to contain: '$needle')"
    FAIL=$((FAIL + 1))
  fi
}

assert_not_contains() {
  local test_name="$1"
  local needle="$2"
  local haystack="$3"
  TOTAL=$((TOTAL + 1))
  if ! echo "$haystack" | grep -q "$needle"; then
    echo -e "  ${GREEN}PASS${RESET} $test_name"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}FAIL${RESET} $test_name (expected NOT to contain: '$needle')"
    FAIL=$((FAIL + 1))
  fi
}

# ---------------------------------------------------------------------------
# Setup / teardown
# ---------------------------------------------------------------------------
TMPDIR_BASE=$(mktemp -d)
cleanup() { rm -rf "$TMPDIR_BASE"; }
trap cleanup EXIT

setup_test() {
  local test_dir="$TMPDIR_BASE/$1"
  mkdir -p "$test_dir/.claude"
  echo "$test_dir"
}

create_state_file() {
  local dir="$1"
  local phase="${2:-1}"
  local phase_iter="${3:-1}"
  local global_iter="${4:-1}"
  local max_iter="${5:-50}"
  local promise="${6:-RESEARCH COMPLETE}"
  local experiments="${7:-false}"
  local human_review="${8:-false}"

  # Lookup phase name
  local phase_name="discovery"
  case "$phase" in
    1) phase_name="discovery" ;;
    2) phase_name="screening" ;;
    3) phase_name="analysis" ;;
    4) phase_name="synthesis" ;;
    5) phase_name="writing" ;;
    6) phase_name="review" ;;
    7) phase_name="polish" ;;
    8) phase_name="revision" ;;
  esac

  cat > "$dir/.claude/research-loop.local.md" <<EOF
---
active: true
topic: "Test Topic"
current_phase: $phase
phase_name: "$phase_name"
phase_iteration: $phase_iter
global_iteration: $global_iter
max_global_iterations: $max_iter
completion_promise: "$promise"
started_at: "2026-03-16T10:00:00Z"
output_dir: "./research-output"
min_papers: 10
papers_found: 5
papers_screened: 0
papers_analyzed: 0
experiments_enabled: $experiments
human_review_enabled: $human_review
---

Research prompt text here
EOF
}

# Helper to init DB with optional evidence and quality scores
init_test_db() {
  local dir="$1"
  mkdir -p "$dir/research-output"
  python3 "$SCRIPT_DIR/../scripts/paper_database.py" init --db-path "$dir/research-output/research.db" > /dev/null 2>&1
}

add_test_evidence() {
  local dir="$1"
  local evidence_type="${2:-measured}"
  python3 "$SCRIPT_DIR/../scripts/paper_database.py" add-paper --db-path "$dir/research-output/research.db" --paper-json '{"id":"t1","source":"arxiv","title":"Test","authors":[],"external_ids":{}}' > /dev/null 2>&1 || true
  python3 "$SCRIPT_DIR/../scripts/paper_database.py" add-evidence --db-path "$dir/research-output/research.db" --paper-id t1 --evidence-json "{\"metric\":\"TTFA\",\"value\":100,\"evidence_type\":\"$evidence_type\"}" > /dev/null 2>&1
}

add_test_quality_score() {
  local dir="$1"
  local phase="$2"
  local phase_name="test"
  case "$phase" in
    2) phase_name="screening" ;;
    3) phase_name="analysis" ;;
    4) phase_name="synthesis" ;;
    5) phase_name="writing" ;;
    6) phase_name="review" ;;
    8) phase_name="revision" ;;
  esac
  python3 "$SCRIPT_DIR/../scripts/paper_database.py" add-quality-score --db-path "$dir/research-output/research.db" --phase "$phase" --phase-name "$phase_name" --iteration 1 --score 0.85 --threshold 0.6 --dimensions-json '{"completeness":0.9}' --feedback "good" > /dev/null 2>&1
}

create_transcript() {
  local dir="$1"
  local assistant_text="${2:-I finished some work.}"
  local transcript_file="$dir/transcript.jsonl"

  cat > "$transcript_file" <<EOF
{"role":"user","message":{"content":[{"type":"text","text":"Start research"}]}}
{"role":"assistant","message":{"content":[{"type":"text","text":"$assistant_text"}]}}
EOF
  echo "$transcript_file"
}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
echo "=== Stop Hook Tests ==="
echo ""

# Test 1: No state file → allow exit
echo "Test: No state file allows exit"
TEST_DIR=$(setup_test "no_state")
TRANSCRIPT=$(create_transcript "$TEST_DIR")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
EXIT_CODE=$?
assert_exit_code "exit code is 0" 0 $EXIT_CODE
assert_not_contains "no block decision" "block" "$OUTPUT"

# Test 2: Max global iterations reached → allow exit
echo ""
echo "Test: Max iterations reached allows exit"
TEST_DIR=$(setup_test "max_iter")
create_state_file "$TEST_DIR" 3 1 50 50
TRANSCRIPT=$(create_transcript "$TEST_DIR")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "reports max iterations" "Max global iterations" "$OUTPUT"

# Test 3: Completion promise detected → allow exit
echo ""
echo "Test: Completion promise detected allows exit"
TEST_DIR=$(setup_test "promise")
create_state_file "$TEST_DIR" 7 1 10 50 "RESEARCH COMPLETE"
TRANSCRIPT=$(create_transcript "$TEST_DIR" "The research is done. <promise>RESEARCH COMPLETE</promise>")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "reports completion" "Research loop complete" "$OUTPUT"

# Test 4: Normal iteration → block exit and re-inject prompt
echo ""
echo "Test: Normal iteration blocks exit"
TEST_DIR=$(setup_test "normal")
create_state_file "$TEST_DIR" 1 1 1 50
TRANSCRIPT=$(create_transcript "$TEST_DIR" "I searched for some papers.")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "blocks exit" '"decision": "block"' "$OUTPUT"
assert_contains "contains prompt" "Research prompt text here" "$OUTPUT"
assert_contains "has system message" "systemMessage" "$OUTPUT"

# Test 5: Phase completion marker → advances phase
echo ""
echo "Test: Phase completion marker advances phase"
TEST_DIR=$(setup_test "phase_advance")
create_state_file "$TEST_DIR" 1 1 1 50
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Found papers. <!-- PHASE_1_COMPLETE -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
# State file should now show phase 2
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase advanced to 2" "2" "$STATE_PHASE"

# Test 6: Phase timeout → forced advancement
echo ""
echo "Test: Phase timeout forces advancement"
TEST_DIR=$(setup_test "phase_timeout")
create_state_file "$TEST_DIR" 1 3 3 50  # phase_iteration=3, which is max for phase 1
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Still searching...")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "forced advance warning" "forced advancement" "$OUTPUT"

# Test 7: Paper counter update from output
echo ""
echo "Test: Paper counters updated from output"
TEST_DIR=$(setup_test "counters")
create_state_file "$TEST_DIR" 1 1 1 50
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Found 15 papers <!-- PAPERS_FOUND:15 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
FOUND=$(grep "papers_found:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/papers_found: *//')
assert_contains "papers_found updated to 15" "15" "$FOUND"

# Test 8: Corrupted state file → stops gracefully
echo ""
echo "Test: Corrupted state file stops gracefully"
TEST_DIR=$(setup_test "corrupted")
mkdir -p "$TEST_DIR/.claude"
cat > "$TEST_DIR/.claude/research-loop.local.md" <<'EOF'
---
active: true
topic: "Test"
current_phase: invalid
phase_name: "discovery"
phase_iteration: abc
global_iteration: 1
max_global_iterations: 50
completion_promise: "TEST"
started_at: "2026-01-01"
output_dir: "./research-output"
min_papers: 10
papers_found: 0
papers_screened: 0
papers_analyzed: 0
experiments_enabled: false
human_review_enabled: false
---

Prompt
EOF
TRANSCRIPT=$(create_transcript "$TEST_DIR")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "reports corruption" "corrupted" "$OUTPUT"

# Test 9: Global iteration counter increments
echo ""
echo "Test: Global iteration increments correctly"
TEST_DIR=$(setup_test "iter_increment")
create_state_file "$TEST_DIR" 2 1 5 50
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Working on screening.")
cd "$TEST_DIR"
echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" > /dev/null 2>&1 || true
GLOBAL=$(grep "global_iteration:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/global_iteration: *//')
assert_contains "global iteration is 6" "6" "$GLOBAL"

# Test 10: All phases complete without promise → stops (requires evidence in DB to pass hard block)
echo ""
echo "Test: Phase 7 complete without promise stops loop"
TEST_DIR=$(setup_test "all_phases")
create_state_file "$TEST_DIR" 7 1 18 50
# Create DB with evidence so hard block doesn't prevent advancement
init_test_db "$TEST_DIR"
add_test_evidence "$TEST_DIR"
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Paper is ready. <!-- PHASE_7_COMPLETE -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "reports all phases complete" "All 7 phases complete" "$OUTPUT"

# ===========================================================================
# HARD BLOCK TESTS
# ===========================================================================
echo ""
echo "=== Hard Block Tests ==="

# Test 11: Evidence hard block — Phase 3 cannot advance without evidence in DB
echo ""
echo "Test: Evidence hard block prevents Phase 3 advancement without evidence"
TEST_DIR=$(setup_test "evidence_block")
create_state_file "$TEST_DIR" 3 1 5 50
init_test_db "$TEST_DIR"
# No evidence added — should block
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Analysis done. <!-- PHASE_3_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "hard block activated" "HARD BLOCK" "$OUTPUT"
# Phase should NOT have advanced
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase stays at 3" "3" "$STATE_PHASE"

# Test 12: Evidence hard block passes when evidence exists
echo ""
echo "Test: Evidence hard block passes with evidence in DB"
TEST_DIR=$(setup_test "evidence_pass")
create_state_file "$TEST_DIR" 3 1 5 50
init_test_db "$TEST_DIR"
add_test_evidence "$TEST_DIR"
add_test_quality_score "$TEST_DIR" 3
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Analysis done. <!-- PHASE_3_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_not_contains "no hard block" "HARD BLOCK" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase advanced to 4" "4" "$STATE_PHASE"

# Test 13: Experiment scripts hard block — Phase 4 with experiments_enabled but no scripts
echo ""
echo "Test: Experiment scripts hard block prevents Phase 4 advancement"
TEST_DIR=$(setup_test "exp_scripts_block")
create_state_file "$TEST_DIR" 4 1 5 50 "RESEARCH COMPLETE" true
init_test_db "$TEST_DIR"
add_test_evidence "$TEST_DIR"
# No experiment scripts — should block
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Synthesis done. <!-- PHASE_4_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "experiment scripts hard block" "HARD BLOCK" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase stays at 4" "4" "$STATE_PHASE"

# Test 14: Experiment results hard block — scripts exist but no results
echo ""
echo "Test: Experiment results hard block prevents Phase 4 advancement"
TEST_DIR=$(setup_test "exp_results_block")
create_state_file "$TEST_DIR" 4 1 5 50 "RESEARCH COMPLETE" true
init_test_db "$TEST_DIR"
add_test_evidence "$TEST_DIR"
# Create experiment script but no results
mkdir -p "$TEST_DIR/research-output/experiments"
echo "print('test')" > "$TEST_DIR/research-output/experiments/exp_test.py"
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Synthesis done. <!-- PHASE_4_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "experiment results hard block" "HARD BLOCK" "$OUTPUT"
assert_contains "mentions results missing" "0 results" "$OUTPUT"

# Test 15: Empirical evidence hard block — scripts+results exist but no empirical evidence in DB
echo ""
echo "Test: Empirical evidence hard block prevents Phase 4 advancement"
TEST_DIR=$(setup_test "empirical_block")
create_state_file "$TEST_DIR" 4 1 5 50 "RESEARCH COMPLETE" true
init_test_db "$TEST_DIR"
add_test_evidence "$TEST_DIR" "measured"  # measured, not empirical
# Create experiment script AND results
mkdir -p "$TEST_DIR/research-output/experiments/results"
echo "print('test')" > "$TEST_DIR/research-output/experiments/exp_test.py"
echo '{"result": 42}' > "$TEST_DIR/research-output/experiments/results/exp_test_results.json"
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Synthesis done. <!-- PHASE_4_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "empirical evidence hard block" "HARD BLOCK" "$OUTPUT"
assert_contains "mentions empirical" "empirical" "$OUTPUT"

# Test 16: Experiments pass when all requirements met (including POC)
echo ""
echo "Test: Experiments hard block passes with scripts + results + empirical evidence + POC"
TEST_DIR=$(setup_test "exp_pass")
create_state_file "$TEST_DIR" 4 1 5 50 "RESEARCH COMPLETE" true
init_test_db "$TEST_DIR"
add_test_evidence "$TEST_DIR" "measured"
add_test_evidence "$TEST_DIR" "empirical"  # Add empirical evidence
add_test_quality_score "$TEST_DIR" 4
# Create experiment script AND results
mkdir -p "$TEST_DIR/research-output/experiments/results"
echo "print('test')" > "$TEST_DIR/research-output/experiments/exp_test.py"
echo '{"result": 42}' > "$TEST_DIR/research-output/experiments/results/exp_test_results.json"
# Create POC with demo.py and tests (required when experiments_enabled=true)
mkdir -p "$TEST_DIR/research-output/poc/tests"
echo "print('main')" > "$TEST_DIR/research-output/poc/main.py"
echo "print('demo')" > "$TEST_DIR/research-output/poc/demo.py"
echo "def test_main(): pass" > "$TEST_DIR/research-output/poc/tests/test_main.py"
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Synthesis done. <!-- PHASE_4_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_not_contains "no hard block" "HARD BLOCK" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase advanced to 5" "5" "$STATE_PHASE"

# Test 17: Quality score hard block — Phase 2 cannot advance without quality score in DB
echo ""
echo "Test: Quality score hard block prevents Phase 2 advancement"
TEST_DIR=$(setup_test "qs_block")
create_state_file "$TEST_DIR" 2 1 5 50
init_test_db "$TEST_DIR"
# No quality score added — should block (phase 2 has gate)
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Screening done. <!-- PHASE_2_COMPLETE --> <!-- QUALITY_SCORE:0.75 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "quality score hard block" "HARD BLOCK" "$OUTPUT"
assert_contains "mentions quality score" "quality score" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase stays at 2" "2" "$STATE_PHASE"

# Test 18: Quality score hard block passes with quality score in DB
echo ""
echo "Test: Quality score hard block passes with score in DB"
TEST_DIR=$(setup_test "qs_pass")
create_state_file "$TEST_DIR" 2 1 5 50
init_test_db "$TEST_DIR"
add_test_quality_score "$TEST_DIR" 2
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Screening done. <!-- PHASE_2_COMPLETE --> <!-- QUALITY_SCORE:0.75 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_not_contains "no hard block" "HARD BLOCK" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase advanced to 3" "3" "$STATE_PHASE"

# Test 19: Hard block prevents forced advancement too
echo ""
echo "Test: Hard block prevents forced advancement (timeout cannot bypass)"
TEST_DIR=$(setup_test "block_vs_timeout")
create_state_file "$TEST_DIR" 3 5 10 50  # phase_iteration=5 >= max(5) → would force advance
init_test_db "$TEST_DIR"
# No evidence — hard block should win over timeout
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Still working...")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "hard block beats timeout" "HARD BLOCK" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase stays at 3 despite timeout" "3" "$STATE_PHASE"

# Test 20: Experiments not enabled — no experiment hard blocks
echo ""
echo "Test: Experiments disabled skips experiment hard blocks"
TEST_DIR=$(setup_test "exp_disabled")
create_state_file "$TEST_DIR" 4 1 5 50 "RESEARCH COMPLETE" false
init_test_db "$TEST_DIR"
add_test_evidence "$TEST_DIR"
add_test_quality_score "$TEST_DIR" 4
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Synthesis done. <!-- PHASE_4_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_not_contains "no hard block when experiments disabled" "HARD BLOCK" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase advanced to 5" "5" "$STATE_PHASE"

# Test 21: Phase 1 (no gate) has no quality score block
echo ""
echo "Test: Phase 1 has no quality score hard block"
TEST_DIR=$(setup_test "phase1_no_block")
create_state_file "$TEST_DIR" 1 1 1 50
# No DB at all — phase 1 should still advance (no evidence block for phase < 3, no QS gate)
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Found papers. <!-- PHASE_1_COMPLETE -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_not_contains "no hard block for phase 1" "HARD BLOCK" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase advanced to 2" "2" "$STATE_PHASE"

# ===========================================================================
# POC HARD BLOCK TESTS
# ===========================================================================
echo ""
echo "=== POC Hard Block Tests ==="

# Helper: set up experiment prerequisites so POC blocks can be reached
setup_experiment_prereqs() {
  local dir="$1"
  init_test_db "$dir"
  add_test_evidence "$dir" "measured"
  add_test_evidence "$dir" "empirical"
  mkdir -p "$dir/research-output/experiments/results"
  echo "print('test')" > "$dir/research-output/experiments/exp_test.py"
  echo '{"result": 42}' > "$dir/research-output/experiments/results/exp_test_results.json"
}

# Test 22: POC hard block — Phase 4 with experiments enabled but no POC files
echo ""
echo "Test: POC hard block prevents Phase 4 advancement without POC"
TEST_DIR=$(setup_test "poc_block")
create_state_file "$TEST_DIR" 4 1 5 50 "RESEARCH COMPLETE" true
setup_experiment_prereqs "$TEST_DIR"
# No POC directory — should block
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Synthesis done. <!-- PHASE_4_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "poc hard block activated" "HARD BLOCK" "$OUTPUT"
assert_contains "mentions POC" "POC" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase stays at 4" "4" "$STATE_PHASE"

# Test 23: POC demo.py hard block — POC files exist but no demo.py
echo ""
echo "Test: POC demo.py hard block prevents advancement without demo.py"
TEST_DIR=$(setup_test "poc_no_demo")
create_state_file "$TEST_DIR" 4 1 5 50 "RESEARCH COMPLETE" true
setup_experiment_prereqs "$TEST_DIR"
mkdir -p "$TEST_DIR/research-output/poc"
echo "print('main')" > "$TEST_DIR/research-output/poc/main.py"
# No demo.py — should block
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Synthesis done. <!-- PHASE_4_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "demo.py hard block" "HARD BLOCK" "$OUTPUT"
assert_contains "mentions demo.py" "demo.py" "$OUTPUT"

# Test 24: POC tests hard block — POC exists with demo.py but no test files
echo ""
echo "Test: POC tests hard block prevents advancement without tests"
TEST_DIR=$(setup_test "poc_no_tests")
create_state_file "$TEST_DIR" 4 1 5 50 "RESEARCH COMPLETE" true
setup_experiment_prereqs "$TEST_DIR"
mkdir -p "$TEST_DIR/research-output/poc/tests"
echo "print('main')" > "$TEST_DIR/research-output/poc/main.py"
echo "print('demo')" > "$TEST_DIR/research-output/poc/demo.py"
# No test files — should block
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Synthesis done. <!-- PHASE_4_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "tests hard block" "HARD BLOCK" "$OUTPUT"
assert_contains "mentions test" "test" "$OUTPUT"

# Test 25: POC hard block passes with all requirements met
echo ""
echo "Test: POC hard block passes with all requirements"
TEST_DIR=$(setup_test "poc_pass")
create_state_file "$TEST_DIR" 4 1 5 50 "RESEARCH COMPLETE" true
setup_experiment_prereqs "$TEST_DIR"
add_test_quality_score "$TEST_DIR" 4
mkdir -p "$TEST_DIR/research-output/poc/tests"
echo "print('main')" > "$TEST_DIR/research-output/poc/main.py"
echo "print('demo')" > "$TEST_DIR/research-output/poc/demo.py"
echo "def test_main(): pass" > "$TEST_DIR/research-output/poc/tests/test_main.py"
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Synthesis done. <!-- PHASE_4_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_not_contains "no hard block with full POC" "HARD BLOCK" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase advanced to 5" "5" "$STATE_PHASE"

# Test 26: POC hard block skipped when experiments disabled
echo ""
echo "Test: POC hard block skipped when experiments disabled"
TEST_DIR=$(setup_test "poc_disabled")
create_state_file "$TEST_DIR" 4 1 5 50 "RESEARCH COMPLETE" false
init_test_db "$TEST_DIR"
add_test_evidence "$TEST_DIR"
add_test_quality_score "$TEST_DIR" 4
# No POC at all — but experiments disabled so no block
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Synthesis done. <!-- PHASE_4_COMPLETE --> <!-- QUALITY_SCORE:0.85 --> <!-- QUALITY_PASSED:1 -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_not_contains "no POC block when experiments disabled" "HARD BLOCK" "$OUTPUT"
STATE_PHASE=$(grep "current_phase:" "$TEST_DIR/.claude/research-loop.local.md" | sed 's/current_phase: *//')
assert_contains "phase advanced to 5" "5" "$STATE_PHASE"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "==================================="
echo -e "Results: ${GREEN}$PASS passed${RESET}, ${RED}$FAIL failed${RESET} / $TOTAL total"
echo "==================================="

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
