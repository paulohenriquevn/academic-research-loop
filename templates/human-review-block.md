
## Human Review Mode — Process External Reviews and Produce Revised Versions

**This research loop includes HUMAN REVIEW PROCESSING.**

The system will read structured review files, triage each item, conditionally re-execute pipeline stages, and produce a versioned revision of the paper.

**Reviews directory:** `{{OUTPUT_DIR}}/reviews/`
**Review template:** `{{OUTPUT_DIR}}/reviews/REVIEW-TEMPLATE.md`

---

### Phase 8: Revision from Human Review

Phase 8 activates after Phase 7 (Polish) completes. It processes human-written `REVIEW-N.md` files placed in `{{OUTPUT_DIR}}/reviews/`.

**If no review files exist when Phase 8 starts:** output `<promise>{{COMPLETION_PROMISE}}</promise>` to complete the loop. The human can add reviews later and re-run.

#### Step 1: Version the Current Paper

Before any revision:
1. Determine the next version number N (start at 1)
2. Copy `final.md` → `final-v{N}.md` as a snapshot
3. Copy `final.tex` → `final-v{N}.tex` if it exists

#### Step 2: Triage Reviews

Launch the **review-handler** agent:
1. Reads ALL unprocessed `REVIEW-*.md` files from `{{OUTPUT_DIR}}/reviews/`
2. Parses each review item (R{N}.1, R{N}.2, etc.)
3. Classifies each item into an action type:
   - **REVISE** — rewrite text with existing evidence
   - **RE_DISCOVER** — search for more papers on a gap
   - **RE_SYNTHESIZE** — rework synthesis themes with existing/new evidence
   - **EXPERIMENT** — design and run new experiments
   - **ACKNOWLEDGED** — log but no action needed
4. Produces `{{OUTPUT_DIR}}/state/revision_plan.md`
5. Records each item in the database as `message_type: review_item`

#### Step 3: Execute Actions (Conditional — Agent Decides)

Execute actions in dependency order. **Not all steps run every time — only what the review demands.**

**3a. RE_DISCOVER (if any items require it):**
- Run search scripts with new queries derived from the review
- Screen and analyze new papers following Phase 1-3 protocols
- Add new papers to the database

**3b. EXPERIMENT (if any items require it AND experiments are feasible):**
- Launch experiment-designer to check hardware and propose experiments
- Launch experiment-coder to execute (Autoresearch: write → run → evaluate)
- Store results as `evidence_type="empirical"` in the database

**3c. RE_SYNTHESIZE (if any items require it):**
- Launch synthesis-writer with constraints from the review
- Update synthesis.md, evidence matrix, and corpus table as needed

**3d. REVISE (most common action):**
- Launch **revision-writer** agent for each REVISE item
- Revision-writer reads the review, the current paper, and the database
- Produces revised sections at `{{OUTPUT_DIR}}/state/revision_sections.md`
- Integrate revised sections into `final.md`

**3e. ACKNOWLEDGED:**
- Record justification in the database
- No revision needed

#### Step 4: Produce Revision Response

Write `{{OUTPUT_DIR}}/reviews/REVIEW-RESPONSE-{N}.md`:

```markdown
# Response to REVIEW-{N}

**Revision version:** v{M}
**Date:** YYYY-MM-DD
**Items addressed:** X of Y

---

## R{N}.1 — [title]

**Action taken:** REVISE | RE_DISCOVER | RE_SYNTHESIZE | EXPERIMENT | ACKNOWLEDGED
**Status:** resolved | partially_resolved | deferred
**Changes:**
- [Specific change 1]
- [Specific change 2]

**Acceptance criteria:**
- [x] Criterion 1 — [how it was met]
- [x] Criterion 2 — [how it was met]
```

#### Step 5: Quality Gate

Launch the **quality-evaluator** agent with the Phase 8 rubric:
- **Completeness** (0.3): Are all critical and major review items addressed?
- **Accuracy** (0.25): Do revisions actually fix the issues identified?
- **Regression** (0.2): Did revisions introduce new problems or break existing content?
- **Acceptance criteria** (0.25): Do resolutions meet the acceptance criteria from the review?
- **Threshold:** 0.75

If FAILED: re-run revision for unresolved items.
If PASSED: proceed to finalization.

#### Step 6: Finalize Version

1. Run fact-checker on the revised paper
2. Run cross-validator on the revised paper
3. Re-export LaTeX if changes are significant
4. Update the version: `final.md` now contains the revised version
5. Record the revision in the database:
   ```bash
   python3 {{PLUGIN_ROOT}}/scripts/paper_database.py add-message \
     --db-path {{OUTPUT_DIR}}/research.db \
     --from-agent revision-writer \
     --phase 8 --iteration N \
     --message-type decision \
     --content "Revision v{M} complete. Addressed X of Y review items." \
     --metadata-json '{"version": M, "review_file": "REVIEW-N.md", "items_resolved": X, "items_total": Y}'
   ```

**Completion:** When ALL of the following are true:
- All REVIEW files have been processed
- All critical items are resolved
- Quality gate passes
- Revision response written
- Versioned snapshot exists

Output `<promise>{{COMPLETION_PROMISE}}</promise>`

---

### Phase 8 in Research Team

| Role | Agent | Specialty |
|------|-------|-----------|
| **Review Handler** | `review-handler` | Triages review items, classifies actions, produces revision plan |
| **Revision Writer** | `revision-writer` | Rewrites sections to address feedback, maintains epistemic rigor |

Plus existing agents as needed: `synthesis-writer` (for RE_SYNTHESIZE), `experiment-designer` + `experiment-coder` (for EXPERIMENT), `fact-checker`, `cross-validator`, `quality-evaluator`.
