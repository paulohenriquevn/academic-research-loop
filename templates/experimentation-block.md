
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

#### Step 4: Build Proof-of-Concept System (POC)

After experiments complete successfully, build a functional POC that demonstrates the key findings as a working system.

##### Step 4a: Design POC Architecture

Launch the **poc-architect** agent:
1. Reads experiment results and evidence matrix
2. Selects 1-3 strongest findings to demonstrate
3. Designs a minimal system architecture reusing experiment code
4. Produces `{{OUTPUT_DIR}}/state/poc_spec.md`

**Constraints:**
- POC must be self-contained (no external services, no API keys required)
- Reuse experiment code — don't rewrite what already works
- Keep scope minimal — prove the concept, nothing more

##### Step 4b: Implement POC (Autoresearch)

Launch the **poc-coder** agent:
1. Reads the POC spec
2. Implements components, reusing experiment code where possible
3. Writes tests for each component
4. Writes `demo.py` — an end-to-end demonstration script
5. Runs tests until all pass (max 3 retries per component)
6. Runs demo.py to verify end-to-end functionality
7. Generates POC report at `{{OUTPUT_DIR}}/poc/poc_report.md`

**POC directory structure:**
```
{{OUTPUT_DIR}}/poc/
├── main.py              ← Entry point / orchestrator
├── *.py                 ← Component files
├── tests/
│   └── test_*.py        ← Component tests (pytest)
├── demo.py              ← Demo script (must exit 0 on success)
├── requirements.txt
├── README.md
└── poc_report.md        ← Summary of implementation and results
```

**Hard blocks:** Phase 4 CANNOT advance unless:
- `poc/` directory exists with Python files
- `poc/demo.py` exists
- `poc/tests/test_*.py` files exist

---

### Phase 5 Extension: Writing with Empirical Results and POC

The survey paper MUST include additional sections:

**"Empirical Validation"** (after the evidence summary):
- Which experiments were run and why (gap-driven)
- Setup: hardware, software versions, seeds
- Results tables with both paper-reported and locally-measured values side by side
- Analysis: do local results confirm, contradict, or extend paper claims?
- Limitations of local experiments (hardware, dataset size, statistical significance)

**"Proof-of-Concept System"** (after Empirical Validation):
- Architecture: components and data flow
- How it maps to experiment results (which experiment validated which component)
- Test results summary
- How to run the demo (`python3 poc/demo.py`)
- Limitations: what the POC does NOT cover, what would be needed for production

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
- POC tests pass and demo.py runs successfully
- POC is directly connected to experiment results (components trace to experiments)

---

### Phase 7 Extension: Experiment Figures

The figure-generator MUST include:

**`figure_5_empirical.svg`** — Comparison chart showing paper-reported vs locally-measured results side by side, with hardware annotations.
