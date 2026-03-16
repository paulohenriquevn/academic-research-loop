
## Applied Research Mode — Codebase-Aware Pipeline

**This research loop is operating in APPLIED RESEARCH mode.**

You are not writing a general literature survey. You are conducting **applied research** that bridges academic literature with a specific software project. Every phase is modified to connect findings to the codebase.

**Codebase path:** `{{CODEBASE_PATH}}`
**Codebase analysis:** `{{OUTPUT_DIR}}/state/codebase_analysis.md`
**Gap analysis:** `{{OUTPUT_DIR}}/state/gap_analysis.md`

---

### Phase 1 Modification: Codebase-First Discovery

**BEFORE searching papers**, launch the **codebase-analyzer** agent to analyze the project at `{{CODEBASE_PATH}}`.

The codebase-analyzer:
1. Reads all source files, docs, and architecture documents
2. Produces a structured component map at `{{OUTPUT_DIR}}/state/codebase_analysis.md`
3. Derives research questions mapped to specific components
4. Suggests search queries optimized for each component's needs

**AFTER the codebase analysis**, use the derived search queries (not generic topic queries) for paper discovery. The search queries should target the specific open questions identified in each component.

Example: If the codebase has a `streaming-asr-service` with a <100ms latency constraint, search for "streaming ASR partial hypothesis latency" — not just "speech recognition."

---

### Phase 2 Modification: Component-Aware Screening

When scoring papers, add a **codebase relevance dimension**:

- **5**: Directly solves an open question for a specific component
- **4**: Proposes a technique applicable to a component with adaptation
- **3**: Provides theoretical background relevant to a component
- **2**: Tangentially related to the project domain
- **1**: Not relevant to any codebase component

Include in the relevance rationale WHICH component(s) the paper maps to:
```
"relevance_rationale": "Directly addresses RQ3 (turn-taking prediction) for dialogue-core component. Proposes transformer-based endpoint predictor with 15ms inference. Meets <20ms constraint."
```

---

### Phase 3 Modification: Implementation-Mapped Analysis

Each paper analysis MUST include an additional section:

```markdown
## Codebase Mapping

**Target component(s):** [component name from codebase_analysis.md]
**Research question addressed:** [RQ# from codebase_analysis.md]
**Technique applicability:**
- Meets constraints: [yes/no — compare paper's latency/accuracy/etc against component constraints]
- Required adaptations: [what would change to fit the codebase architecture]
- Integration complexity: [low/medium/high — how hard to integrate]
**Implementation notes:**
- [specific technical notes about how this would work in the codebase]
```

---

### Phase 4 Modification: Gap Analysis

After the synthesis is complete, launch the **gap-analyzer** agent. This agent:

1. Reads the codebase analysis and the literature synthesis
2. Builds a gap matrix: each component × relevant papers × gap severity
3. Classifies gaps as: Solved, Partial, Open, or Conflicting
4. Generates implementation recommendations for each component
5. Identifies where the project could contribute back to academia
6. Saves to `{{OUTPUT_DIR}}/state/gap_analysis.md`

The outline architect MUST incorporate the gap analysis into the survey outline, including:
- A "Gap Analysis" section mapping components to literature
- An "Implementation Recommendations" section
- A "Research Contribution Opportunities" section

---

### Phase 5 Modification: Applied Writing

The survey paper MUST include these additional sections:

1. **System Context** (after Introduction): Describe the target system architecture, its components, and constraints. This grounds the entire survey in a concrete engineering problem.

2. **Component-Literature Mapping** (after Synthesis/Taxonomy): A table showing which papers address which system components, gap type, and recommendation.

   | Component | Papers | Gap Type | Recommendation |
   |-----------|--------|----------|----------------|
   | ... | [@key1, @key2] | Solved | Implement X |
   | ... | [@key3] | Partial | Adapt Y |
   | ... | — | Open | Original research |

3. **Implementation Recommendations** (after Research Gaps): For each component with Solved/Partial gaps, provide specific implementation guidance citing papers.

4. **Proposed Benchmarks** (after Implementation Recommendations): Concrete benchmarks the project should run to validate chosen approaches. Include metrics, baselines, and targets from the codebase constraints.

5. **Research Contribution Opportunities** (before Conclusion): Where this project could produce novel academic contributions — new benchmarks, domain-specific adaptations, empirical comparisons the literature lacks.

---

### Phase 6 Modification: Applied Review

The fact-checker and academic-reviewer MUST additionally verify:
- Every codebase component from `codebase_analysis.md` is addressed in the paper
- Gap classifications are consistent with paper analyses
- Implementation recommendations are grounded in cited papers (no unsupported claims)
- Proposed benchmarks are concrete and feasible given the codebase constraints

---

### Phase 7 Modification: Applied Figures

The figure-generator MUST include an additional figure:

**`figure_4_component_mapping.svg`** — Architecture diagram showing:
- Codebase components as boxes
- Papers mapped to each component (colored by gap type: green=solved, yellow=partial, red=open)
- Data flow between components
- Latency budgets annotated on each connection

---

### Applied Research Paper Template

Use this extended structure for the survey (in addition to the base template):

```
1. Introduction (motivation + system context)
2. Background (task definition + system architecture)
3-N. Thematic sections (as in base survey)
N+1. Component-Literature Mapping & Gap Analysis
N+2. Implementation Recommendations
N+3. Proposed Benchmarks
N+4. Research Contribution Opportunities
N+5. Conclusion (with limitations)
```
