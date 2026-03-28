# Documentation Audit Report: llama-optimus

**Date:** 2026-03-27
**Status:** Found documentation inconsistencies with code implementation

---

## Overview

This audit compares the README.md specifications against the actual implementation in the source code. Several discrepancies were identified in default parameter values and descriptions of optimization stages.

---

## Issues Found

### 1. **Default `--trials` Parameter Mismatch** ❌
- **Location:** README.md line 182
- **Documented:** `--trials` default is 35
- **Actual Code:** cli.py line 28 sets default to **45**
- **Impact:** Users following README will get different behavior than expected
- **Fix:** Update README line 182

```python
# cli.py line 28
parser.add_argument("--trials", type=int, default=45, help="Number of Optuna/optimization trials")
```

---

### 2. **Default `--repeat` (`-r`) Parameter Mismatch** ❌
- **Location:** README.md line 189
- **Documented:** `-r` / `--repeat` default is **2**
- **Actual Code:** cli.py line 38 sets default to **3**
- **Impact:** Users following the README docs will get different repetition behavior
- **Fix:** Update README line 189

```python
# cli.py line 38
parser.add_argument("--repeat", "-r", type=int, default=3, help="Number of llama-bench runs per configuration...")
```

---

### 3. **Default `--n-tokens` Parameter Mismatch** ❌
- **Location:** README.md line 191
- **Documented:** `--n-tokens` default is **60**
- **Actual Code:** cli.py line 41 sets default to **192**
- **Impact:** Benchmark precision will be different than documented
- **Fix:** Update README line 191

```python
# cli.py line 41
parser.add_argument("--n-tokens", type=int, default=192, help="Number of tokens used in llama-bench...")
```

---

### 4. **Default `--n-warmup-runs` Parameter Mismatch** ❌
- **Location:** README.md lines 200 and 303
- **Documented (line 200):** `--warmup-runs` default is **30**
- **Documented (line 303):** "default number of warmup runs (default: 40)"
- **Actual Code:** cli.py line 52 sets default to **35**
- **Impact:** Inconsistent documentation across README; actual code differs from both
- **Fix:**
  - Update README line 200 to "default: 35"
  - Update README line 303 to "default: 35"

```python
# cli.py line 52
parser.add_argument("--n-warmup-runs", type=int, default=35, help="Maximum warm-up iterations before trials...")
```

---

### 5. **README Syntax Error** ❌
- **Location:** README.md line 279
- **Issue:** Code block delimiter is malformed
- **Current:** `` ```bas' ``
- **Should Be:** `` ```bash ``
- **Impact:** Code formatting is broken, making the example hard to read
- **Fix:** Change to proper markdown syntax

```markdown
# Line 279 - BEFORE
Later, for a stable final score, re-run llama-bench with the best flags found (don't forget to warm-up first):
```bas'
llama-bench ... -p 512 -n 256 -r 5 --progress
```

# AFTER
Later, for a stable final score, re-run llama-bench with the best flags found (don't forget to warm-up first):
```bash
llama-bench ... -p 512 -n 256 -r 5 --progress
```
```

---

### 6. **Accuracy Issue: Python Version Requirement** ⚠️
- **Location:** README.md line 41 and pyproject.toml line 14
- **README States:** "Python 3.10+"
- **pyproject.toml States:** `requires-python = ">=3.8"`
- **Issue:** Documentation claims higher requirement than actual code allows
- **Impact:** Users with Python 3.8 or 3.9 might be unnecessarily discouraged
- **Recommendation:** Clarify which version is actually required/tested, or update one source to match the other

---

## Summary Table

| Parameter | README Documented | Actual Code | Status |
|-----------|------------------|------------|--------|
| `--trials` | 35 | 45 | ❌ Mismatch |
| `--repeat` | 2 | 3 | ❌ Mismatch |
| `--n-tokens` | 60 | 192 | ❌ Mismatch |
| `--n-warmup-runs` | 30/40 | 35 | ❌ Mismatch |
| Python version | 3.10+ | 3.8+ | ⚠️ Inconsistent |

---

## Recommended Actions

### Priority: **HIGH**
1. Update all four default parameter values in README.md to match cli.py
2. Fix the README syntax error on line 279

### Priority: **MEDIUM**
3. Clarify Python version requirements (align README and pyproject.toml)

### Priority: **LOW**
4. Consider adding a "Parameters" table in README showing defaults, so it's easier to spot mismatches in future updates

---

## Files Reviewed

- ✅ `README.md` - Main documentation
- ✅ `src/llama_optimus/cli.py` - CLI parameter definitions
- ✅ `pyproject.toml` - Project metadata
- ✅ `src/llama_optimus/core.py` - Core optimization logic
- ✅ `src/llama_optimus/search_space.py` - Parameter search space
- ✅ `src/llama_optimus/override_patterns.py` - Override tensor patterns

---

## Notes

- All code logic appears sound and matches documentation intent (Bayesian optimization with 3 stages)
- No security issues detected
- Documentation is comprehensive overall; these are precision/accuracy issues rather than conceptual problems
