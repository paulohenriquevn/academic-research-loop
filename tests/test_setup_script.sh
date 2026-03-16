#!/bin/bash

# Unit tests for the setup-research-loop.sh script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_SCRIPT="$SCRIPT_DIR/../scripts/setup-research-loop.sh"

PASS=0
FAIL=0
TOTAL=0

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

assert_file_exists() {
  local test_name="$1"
  local filepath="$2"
  TOTAL=$((TOTAL + 1))
  if [[ -f "$filepath" ]]; then
    echo -e "  ${GREEN}PASS${RESET} $test_name"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}FAIL${RESET} $test_name (file not found: $filepath)"
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

TMPDIR_BASE=$(mktemp -d)
cleanup() { rm -rf "$TMPDIR_BASE"; }
trap cleanup EXIT

echo "=== Setup Script Tests ==="
echo ""

# Test 1: No arguments → error
echo "Test: No arguments shows error"
TEST_DIR="$TMPDIR_BASE/no_args"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
EXIT_CODE=0
OUTPUT=$(bash "$SETUP_SCRIPT" 2>&1) || EXIT_CODE=$?
assert_exit_code "exits with error" 1 $EXIT_CODE
assert_contains "shows error message" "No research topic" "$OUTPUT"

# Test 2: Help flag → shows help
echo ""
echo "Test: --help shows usage"
TEST_DIR="$TMPDIR_BASE/help"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
OUTPUT=$(bash "$SETUP_SCRIPT" --help 2>&1 || true)
assert_contains "shows usage" "USAGE" "$OUTPUT"
assert_contains "shows phases" "Discovery" "$OUTPUT"

# Test 3: Valid topic → creates state file and output dir
echo ""
echo "Test: Valid topic creates state file"
TEST_DIR="$TMPDIR_BASE/valid"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
OUTPUT=$(bash "$SETUP_SCRIPT" Test research topic 2>&1 || true)
assert_file_exists "state file created" "$TEST_DIR/.claude/research-loop.local.md"
assert_file_exists "candidates.json created" "$TEST_DIR/research-output/state/candidates.json"
assert_file_exists "shortlist.json created" "$TEST_DIR/research-output/state/shortlist.json"
assert_file_exists "references.bib created" "$TEST_DIR/research-output/references.bib"

STATE=$(cat "$TEST_DIR/.claude/research-loop.local.md")
assert_contains "topic in state" "Test research topic" "$STATE"
assert_contains "phase 1 in state" "current_phase: 1" "$STATE"
assert_contains "iteration 1 in state" "global_iteration: 1" "$STATE"

# Test 4: Custom options → reflected in state
echo ""
echo "Test: Custom options reflected in state"
TEST_DIR="$TMPDIR_BASE/custom"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
OUTPUT=$(bash "$SETUP_SCRIPT" Custom topic --max-iterations 30 --min-papers 15 --output-dir ./custom-output 2>&1 || true)
STATE=$(cat "$TEST_DIR/.claude/research-loop.local.md")
assert_contains "max iterations" "max_global_iterations: 30" "$STATE"
assert_contains "min papers" "min_papers: 15" "$STATE"
assert_contains "output dir" "output_dir: \"./custom-output\"" "$STATE"
assert_file_exists "custom output dir" "$TEST_DIR/custom-output/state/candidates.json"

# Test 5: Invalid --max-iterations → error
echo ""
echo "Test: Invalid --max-iterations shows error"
TEST_DIR="$TMPDIR_BASE/bad_iter"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
EXIT_CODE=0
OUTPUT=$(bash "$SETUP_SCRIPT" Topic --max-iterations abc 2>&1) || EXIT_CODE=$?
assert_exit_code "exits with error" 1 $EXIT_CODE
assert_contains "error message" "requires a positive integer" "$OUTPUT"

# Test 6: Invalid --min-papers 0 → error
echo ""
echo "Test: --min-papers 0 shows error"
TEST_DIR="$TMPDIR_BASE/bad_papers"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
EXIT_CODE=0
OUTPUT=$(bash "$SETUP_SCRIPT" Topic --min-papers 0 2>&1) || EXIT_CODE=$?
assert_exit_code "exits with error" 1 $EXIT_CODE

# ---------------------------------------------------------------------------
echo ""
echo "==================================="
echo -e "Results: ${GREEN}$PASS passed${RESET}, ${RED}$FAIL failed${RESET} / $TOTAL total"
echo "==================================="

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
