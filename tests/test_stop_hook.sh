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

  cat > "$dir/.claude/research-loop.local.md" <<EOF
---
active: true
topic: "Test Topic"
current_phase: $phase
phase_name: "discovery"
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
---

Research prompt text here
EOF
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

# Test 10: All phases complete without promise → stops
echo ""
echo "Test: Phase 7 complete without promise stops loop"
TEST_DIR=$(setup_test "all_phases")
create_state_file "$TEST_DIR" 7 1 18 50
TRANSCRIPT=$(create_transcript "$TEST_DIR" "Paper is ready. <!-- PHASE_7_COMPLETE -->")
cd "$TEST_DIR"
OUTPUT=$(echo '{"transcript_path":"'"$TRANSCRIPT"'"}' | bash "$HOOK_SCRIPT" 2>&1 || true)
assert_contains "reports all phases complete" "All 7 phases complete" "$OUTPUT"

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
