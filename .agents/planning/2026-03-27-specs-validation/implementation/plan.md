# Implementation Plan: Apply Corrected Specs to Repository

## Progress Checklist

- [ ] Step 1: Verify corrected specs are complete and accurate
- [ ] Step 2: Replace spec documents in `.agents/planning/llama-optimus-specs/`
- [ ] Step 3: Update INDEX.md and SUMMARY.md in the specs directory
- [ ] Step 4: Fix known outstanding code issues (optional, separate task)
- [ ] Step 5: Validate final state and confirm accuracy

---

## Step 1: Verify Corrected Specs Are Complete and Accurate

**Objective:** Confirm all 6 corrected spec documents exist, cover all modules, and have no broken
cross-references before replacing the originals.

**Implementation Guidance:**
- Check that all 6 files exist in `corrected-specs/`: `1-overview.md` through `6-design-decisions-and-testing.md`
- Spot-check that `5-api-specification.md` documents all 5 public functions: `estimate_max_ngl`,
  `run_llama_bench_with_csv`, `run_optimization`, `warmup_until_stable`, and the 3 objective functions
- Confirm the 5 known outstanding issues are listed in `corrected-specs/INDEX.md`
- Verify the `OVERRIDE_PATTERNS` import path correction is present in `5-api-specification.md`

**Test Requirements:**
- All 6 files exist: `ls corrected-specs/` shows expected filenames
- `grep "OVERRIDE_PATTERNS" corrected-specs/5-api-specification.md` returns the corrected import path
- `grep "delete=False" corrected-specs/` finds the temp file documentation
- `grep "CalledProcessError" corrected-specs/` finds the subprocess failure documentation

**Integration:** This step has no dependencies — it validates the output of the research phase.

**Demo:** Running the grep checks above returns non-empty results, confirming key corrections are present.

---

## Step 2: Replace Spec Documents in `.agents/planning/llama-optimus-specs/`

**Objective:** Overwrite the 6 original spec files with the corrected versions.

**Implementation Guidance:**
- Copy each corrected file over the corresponding original:
  ```
  corrected-specs/1-overview.md             → llama-optimus-specs/1-overview.md
  corrected-specs/2-functional-requirements.md → llama-optimus-specs/2-functional-requirements.md
  corrected-specs/3-technical-architecture.md  → llama-optimus-specs/3-technical-architecture.md
  corrected-specs/4-cli-interface.md           → llama-optimus-specs/4-cli-interface.md
  corrected-specs/5-api-specification.md       → llama-optimus-specs/5-api-specification.md
  corrected-specs/6-design-decisions-and-testing.md → llama-optimus-specs/6-design-decisions-and-testing.md
  ```
- Do NOT overwrite `INDEX.md` yet — update it separately in Step 3
- Do NOT delete `SUMMARY.md` — it will be updated in Step 3

**Test Requirements:**
- After copy, `diff corrected-specs/1-overview.md llama-optimus-specs/1-overview.md` returns empty (files are identical)
- Repeat for all 6 files

**Integration:** Depends on Step 1 completing successfully — only replace once verified.

**Demo:** `cat llama-optimus-specs/2-functional-requirements.md | grep "CalledProcessError"` returns a match,
confirming the corrected error handling documentation is live.

---

## Step 3: Update INDEX.md and SUMMARY.md

**Objective:** Bring the navigation and summary documents in line with the corrected spec content.

**Implementation Guidance:**
- **INDEX.md**: Replace with `corrected-specs/INDEX.md` — it was rewritten to reflect the corrected docs
  and includes the "Key Corrections Made" and "Known Outstanding Issues" sections
- **SUMMARY.md**: Review the existing SUMMARY.md against the new content. Key updates needed:
  - Error handling section — document that subprocess failures raise, not return 0.0
  - API exports — note that `OVERRIDE_PATTERNS` must be imported from `override_patterns` module
  - Testing section — confirm minimal test coverage is documented accurately

**Test Requirements:**
- `grep "Known Outstanding Issues" llama-optimus-specs/INDEX.md` returns a match
- `grep "CalledProcessError\|delete=False\|OVERRIDE_PATTERNS" llama-optimus-specs/INDEX.md` returns matches

**Integration:** Depends on Step 2 — the INDEX must be updated after the content files are in place to
ensure all cross-references are valid.

**Demo:** Opening `llama-optimus-specs/INDEX.md` shows the "Key Corrections Made" table listing all 6 major fixes.

---

## Step 4: Fix Known Outstanding Code Issues (Optional)

**Objective:** Address the 5 known bugs/inconsistencies found during the audit.

> **Note:** These are code fixes, not documentation fixes. They are out of scope for the spec validation
> task but documented here for completeness. Each should be a separate PR/commit.

**Issues and Fixes:**

| # | File | Issue | Fix |
|---|------|-------|-----|
| 4a | `src/llama_optimus/__init__.py` | `OVERRIDE_PATTERNS` not exported | Add import and export |
| 4b | `src/llama_optimus/core.py` | Temp CSV files use `delete=False` and are never cleaned up | Add explicit `os.unlink()` after use or use context manager |
| 4c | `src/llama_optimus/core.py` | Debug `print()` calls in objective functions | Add `verbose` parameter or remove prints |
| 4d | `src/llama_optimus/cli.py` | Help text says `min_runs=3`, code enforces 4 | Fix help text to say `min_runs=4` |
| 4e | `src/llama_optimus/core.py` | Subprocess failure in comparison benchmarks crashes silently | Add try/except with user-friendly error message |

**Test Requirements (per sub-issue):**
- 4a: `python -c "from llama_optimus import OVERRIDE_PATTERNS; print(type(OVERRIDE_PATTERNS))"` succeeds
- 4b: After optimization run, no `.csv` files remain in `tempfile.gettempdir()`
- 4c: Running optimization produces no `cmd_1:` / `cmd_2:` / `cmd_3:` lines unless `--verbose` is passed
- 4d: `llama-optimus --help | grep min_runs` shows `4`, not `3`
- 4e: When llama-bench returns non-zero exit code, user sees a descriptive error message

**Integration:** These are independent code fixes. Each builds on the unchanged base without affecting others.
They are NOT required to complete the spec validation task.

**Demo (for 4a):** `python -c "from llama_optimus import OVERRIDE_PATTERNS; print(len(OVERRIDE_PATTERNS))"` prints
the number of override patterns without ImportError.

---

## Step 5: Validate Final State and Confirm Accuracy

**Objective:** Confirm that the deployed corrected specs accurately reflect the v0.1.9 codebase and that
the implementation is complete.

**Implementation Guidance:**
- Run the completeness spot-check:
  - All 5 public functions documented in `5-api-specification.md`
  - All CLI arguments documented in `4-cli-interface.md`
  - All 3 platforms documented in `1-overview.md`
- Run the accuracy spot-check:
  - Pick 2–3 function signatures from `5-api-specification.md` and verify against actual source
  - Confirm error handling behavior in `2-functional-requirements.md` matches `core.py`
- Check that the "Known Outstanding Issues" list in `INDEX.md` still matches the actual code

**Test Requirements:**
- `grep "estimate_max_ngl\|run_llama_bench_with_csv\|run_optimization\|warmup_until_stable" llama-optimus-specs/5-api-specification.md | wc -l` returns ≥ 4
- `grep "\-\-llama-bin\|\-\-model\|\-\-trials\|\-\-metric" llama-optimus-specs/4-cli-interface.md | wc -l` returns ≥ 4
- No `diff` output between `corrected-specs/*.md` and `llama-optimus-specs/*.md` (except INDEX/SUMMARY)

**Integration:** Depends on Steps 2 and 3 being complete.

**Demo:** A final `diff -r corrected-specs/ llama-optimus-specs/` (excluding INDEX/SUMMARY) shows no differences,
confirming the corrected specs are fully deployed.
