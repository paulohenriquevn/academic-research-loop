---
description: "View current academic research loop status"
allowed-tools: ["Bash(test -f .claude/research-loop.local.md:*)", "Read(.claude/research-loop.local.md)", "Bash(ls:*)", "Bash(wc:*)", "Bash(cat:*)"]
hide-from-slash-command-tool: "true"
---

# Research Loop Status

Check and display the current research loop status:

1. Check if `.claude/research-loop.local.md` exists: `test -f .claude/research-loop.local.md && echo "EXISTS" || echo "NOT_FOUND"`

2. **If NOT_FOUND**: Say "No active research loop."

3. **If EXISTS**:
   - Read `.claude/research-loop.local.md` to get all state fields
   - Check the output directory for generated files
   - Display a formatted status report:

```
📚 Research Loop Status
━━━━━━━━━━━━━━━━━━━━━━
Topic:            [topic]
Phase:            [N]/7 — [phase_name]
Phase iteration:  [phase_iteration]/[phase_max]
Global iteration: [global_iteration]/[max_global_iterations]
Started:          [started_at]

Papers:
  Found:     [papers_found]
  Screened:  [papers_screened]
  Analyzed:  [papers_analyzed]

Output directory: [output_dir]
  candidates.json: [exists/missing]
  shortlist.json:  [exists/missing]
  analyses/:       [N files]
  synthesis.md:    [exists/missing]
  draft.md:        [exists/missing]
  references.bib:  [N entries]
  final.md:        [exists/missing]
```
