
## Experimentation Mode — Run Real Experiments

**This research loop includes EMPIRICAL EXPERIMENTATION.**

The system will design experiments, write code, execute it, and include empirical results in the paper. This follows the Autoresearch pattern: write code → execute → evaluate → keep/discard → iterate.

**Experiments directory:** `{{OUTPUT_DIR}}/experiments/`
**Results directory:** `{{OUTPUT_DIR}}/experiments/results/`

---

### Phase 4 Extension: Experimentation (after Synthesis, before Outline)

After the synthesis and evidence matrix are complete, run experiments to fill empirical gaps.

#### Step 1: Design Experiments

Launch the **experiment-designer** agent:
1. Reads the evidence matrix and gap analysis (if applied research mode)
2. Checks available hardware (GPU, VRAM, installed packages)
3. Designs experiments prioritized by: gap severity × feasibility × runtime
4. Produces `{{OUTPUT_DIR}}/state/experiment_plan.md`

**Constraints:**
- Only propose experiments that can run on available hardware
- Prefer experiments that finish in <30 minutes
- Every experiment must have a baseline comparison
- Every experiment must produce exact numeric results

#### Step 2: Execute Experiments (Autoresearch)

Launch the **experiment-coder** agent:
1. Reads the experiment plan
2. For each experiment:
   a. Writes a self-contained Python script at `{{OUTPUT_DIR}}/experiments/exp_N.py`
   b. Installs missing pip dependencies
   c. Executes the script with timeout
   d. Checks results JSON for validity
   e. If failed: diagnoses, fixes, retries (max 3 retries)
   f. If succeeded: stores results in evidence DB as `evidence_type="empirical"`
3. Generates experiment report at `{{OUTPUT_DIR}}/experiments/experiment_report.md`

**Evidence type:** Local experiments are stored as `"empirical"` in the evidence DB, distinct from `"measured"` (paper-reported) results. The paper MUST distinguish between paper-reported and locally-reproduced evidence.

#### Step 3: Incorporate Results

After experiments complete:
1. Update the evidence matrix with empirical results
2. The outline architect incorporates an "Empirical Validation" section
3. The section writer presents local results with appropriate caveats:
   - Hardware used (GPU model, VRAM)
   - Number of samples
   - Random seed
   - Whether results reproduce paper-reported values
   - Limitations of local setup vs. paper's setup

---

### Phase 5 Extension: Writing with Empirical Results

The survey paper MUST include an additional section:

**"Empirical Validation"** (after the evidence summary):
- Which experiments were run and why (gap-driven)
- Setup: hardware, software versions, seeds
- Results tables with both paper-reported and locally-measured values side by side
- Analysis: do local results confirm, contradict, or extend paper claims?
- Limitations of local experiments (hardware, dataset size, statistical significance)

Example table format:
```markdown
| System | F1 (Paper) | F1 (Local) | Latency (Paper) | Latency (Local) | Conditions |
|--------|-----------|-----------|----------------|----------------|-----------|
| LoRA-Guard | 0.94 [MEASURED] | 0.91 [EMPIRICAL] | 12ms [MEASURED] | 15ms [EMPIRICAL] | Paper: A100; Local: RTX 3060 |
```

---

### Phase 6 Extension: Review with Experiment Audit

The academic-reviewer MUST additionally verify:
- Experiments address gaps identified in the evidence matrix
- Results are reported with appropriate caveats (hardware differences, sample sizes)
- Paper-reported vs locally-measured results are NEVER conflated
- Statistical significance is assessed where applicable
- Failed experiments are documented, not hidden

---

### Phase 7 Extension: Experiment Figures

The figure-generator MUST include:

**`figure_5_empirical.svg`** — Comparison chart showing paper-reported vs locally-measured results side by side, with hardware annotations.
