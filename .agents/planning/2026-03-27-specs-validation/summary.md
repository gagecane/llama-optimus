# Project Summary: llama-optimus Specs Validation

**Project:** 2026-03-27-specs-validation
**Completed:** 2026-03-27
**Codebase Version:** 0.1.9

---

## Artifacts Created

```
.agents/planning/2026-03-27-specs-validation/
├── rough-idea.md                          # Original task description
├── idea-honing.md                         # Requirements clarification (6 Q&A)
├── summary.md                             # This document
├── research/
│   ├── specs-claims.md                    # All factual claims extracted from original specs
│   ├── codebase-audit.md                  # Line-by-line audit of actual codebase
│   └── RESEARCH_SUMMARY.md               # Summary of findings and discrepancies
├── design/
│   └── detailed-design.md                 # Validation methodology, discrepancy table, accuracy metrics
├── implementation/
│   └── plan.md                            # 5-step plan to deploy corrected specs (with checklist)
└── corrected-specs/
    ├── INDEX.md                           # Navigation + corrections summary + known issues
    ├── 1-overview.md                      # Corrected: project description, goals, platforms
    ├── 2-functional-requirements.md       # Corrected: error handling, subprocess behavior
    ├── 3-technical-architecture.md        # Corrected: module paths, internal structure
    ├── 4-cli-interface.md                 # Corrected: debug output, warmup minimum
    ├── 5-api-specification.md             # Corrected: OVERRIDE_PATTERNS import path
    └── 6-design-decisions-and-testing.md  # Corrected: temp file behavior, test coverage
```

---

## Design Overview

The validation was a 3-phase process:

1. **Extract Claims** — Catalogued all factual claims from the 6 original spec documents
2. **Audit Codebase** — Read every source file in `src/llama_optimus/` and documented actual behavior
3. **Compare and Correct** — Identified 10 discrepancies, classified by severity, produced corrected docs

**Overall accuracy before:** ~75–90% (depending on category)
**Overall accuracy after:** ~100%

---

## Implementation Plan Overview

The plan (`implementation/plan.md`) has 5 steps:

1. **Verify** corrected specs are complete (grep checks for key corrections)
2. **Replace** the 6 spec files in `.agents/planning/llama-optimus-specs/`
3. **Update** INDEX.md and SUMMARY.md in the specs directory
4. **Fix** 5 known code bugs found during audit (optional, separate task)
5. **Validate** final state with spot-checks and diffs

---

## Key Findings

### 6 Major Corrections
1. `OVERRIDE_PATTERNS` import path — not exported from main package, must use `override_patterns` module
2. Subprocess error behavior — `check=True` means benchmark failures raise `CalledProcessError`, not return 0.0
3. Temp file lifecycle — `delete=False` means CSV files accumulate in OS temp directory
4. Debug output — 4 undocumented `print()` calls in objective functions clutter stdout
5. CSV error handling — subprocess failures raise, only CSV parse failures return 0.0
6. Warmup minimum — help says 3, code enforces 4

### 5 Known Outstanding Code Issues
These are bugs in the code (not the specs). Documented accurately in corrected specs but not yet fixed:
- `OVERRIDE_PATTERNS` not exported from `__init__.py`
- Temp CSV files not cleaned up
- Debug print statements not configurable
- Comparison benchmark failure crashes run without friendly error
- CLI help text wrong about minimum warmup runs

---

## Next Steps

1. **Deploy corrected specs** — Follow `implementation/plan.md` Steps 1–3 to replace the spec files
2. **Fix code bugs** — Address the 5 outstanding issues listed above (Step 4 of the plan, separate PR)
3. **Set up a maintenance workflow** — When code changes, run a quick diff against specs to catch drift

### To Start Implementation

```
ralph run --config presets/pdd-to-code-assist.yml --prompt "Apply corrected specs from .agents/planning/2026-03-27-specs-validation/corrected-specs/ to .agents/planning/llama-optimus-specs/ following the plan in .agents/planning/2026-03-27-specs-validation/implementation/plan.md"
```

Or:
```
ralph run -c ralph.yml -H builtin:pdd-to-code-assist -p "Apply corrected specs from .agents/planning/2026-03-27-specs-validation/corrected-specs/ to .agents/planning/llama-optimus-specs/ following the plan in .agents/planning/2026-03-27-specs-validation/implementation/plan.md"
```
