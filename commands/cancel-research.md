---
description: "Cancel active academic research loop"
allowed-tools: ["Bash(test -f .claude/research-loop.local.md:*)", "Bash(rm .claude/research-loop.local.md)", "Read(.claude/research-loop.local.md)"]
hide-from-slash-command-tool: "true"
---

# Cancel Research Loop

To cancel the research loop:

1. Check if `.claude/research-loop.local.md` exists using Bash: `test -f .claude/research-loop.local.md && echo "EXISTS" || echo "NOT_FOUND"`

2. **If NOT_FOUND**: Say "No active research loop found."

3. **If EXISTS**:
   - Read `.claude/research-loop.local.md` to get current state (phase, iteration, topic, paper counts)
   - Remove the file using Bash: `rm .claude/research-loop.local.md`
   - Report: "Cancelled research loop for topic '[TOPIC]' (was at phase N/7: PHASE_NAME, global iteration M). Papers found: X, screened: Y, analyzed: Z. Output preserved in OUTPUT_DIR."
