# Design Decisions & Testing Strategy

## Key Design Decisions

### 1. Three-Stage Optimization Architecture

**Decision:** Use hierarchical 3-stage approach (numerical → categorical → numerical)

**Rationale:**
- **Computational Efficiency**: Stage 2 grid search is manageable with fixed numerical parameters
- **Search Quality**: Separating categorical and numerical avoids interaction confounds
- **Practical Results**: Final stage refines numerical params with best categoricals applied
- **Time Balance**: ~45 + ~16 + ~45 trials = manageable 30-120 minute runtime

**Alternatives Considered:**
1. Flat joint search (all parameters together)
   - Rejected: Exponential trial explosion with categorical options
   - Would require 45 × 16 = 720+ trials just for comparison
2. Two-stage (numerical + categorical)
   - Rejected: Misses final refinement opportunity
   - Early categorical decisions might not be optimal without numerical refinement
3. Single Bayesian search with categorical
   - Rejected: Optuna's multivariate TPE less efficient on mixed spaces
   - Grid sampler better for exhaustive categorical coverage

### 2. Binary Search for GPU Layer Estimation

**Decision:** Use binary search instead of linear or exponential search

**Rationale:**
- **Efficiency**: O(log n) vs O(n) for linear search, saves ~6 trials vs ~75
- **Assumption**: GPU layer count is monotonic (higher -ngl = more VRAM needed)
- **Realistic**: Search space (0-149) is small, acceptable timeframe (~15-30 minutes)
- **Deterministic**: Always finds highest viable value

**Limitation:** Assumes monotonic degradation; some hardware edge cases may violate this

**Alternative Provided:** User can skip with `--ngl-max` flag if they know their limit

### 3. Hardware Warmup Phase

**Decision:** Mandatory warmup (minimum 4 runs) before optimization

**Rationale:**
- **Avoiding Cold-Start Bias**: Cold hardware shows misleadingly high performance
  - Fresh turbo boost hasn't throttled
  - Caches are empty
  - Fans haven't turned on
  - Results not representative of real-world usage
- **Real-World Conditions**: Optimization should target steady-state operation
- **Fan Behavior**: Modern hardware throttles significantly after fans activate
- **Reproducibility**: Warmup reduces trial-to-trial variance significantly
- **Duration**: 35 iterations typically brings system to steady-state

**Trade-off:** Adds 5-15 minutes to total runtime

**User Override:** `--no-warmup` flag available for testing/debugging only

**Enforcement:** Minimum 4 runs enforced regardless of user input
- Reasoning: Less than 4 runs insufficient to reach stable state

### 4. GridSampler for Categorical Parameters

**Decision:** Use exhaustive grid search (GridSampler) for categorical variables

**Rationale:**
- **Completeness**: Tests all combinations explicitly (deterministic coverage)
- **Determinism**: Same results regardless of randomness
- **Small Space**: Only 16 combinations total (8 patterns × 2 flash_attn values)
- **Explainability**: Users can understand all tested configurations
- **No Surprises**: Grid search doesn't miss combinations due to sampling luck

**Trade-off:** Doesn't adapt based on results (inflexible)

**Alternative Considered:** Random sampling
- Rejected: Might miss good combinations in small space
- Might repeatedly sample same combination

### 5. Fallback Return of 0.0 on Trial Failure

**Decision:** Objective functions return 0.0 on exception instead of raising

**Rationale:**
- **Robustness**: Non-working configs don't crash the optimization
- **Graceful Degradation**: Optuna treats 0.0 as lowest score (failed trial)
- **Continuation**: Optimization persists and finds viable configs
- **Hardware Anomalies**: Single temporary glitch shouldn't stop entire run

**Trade-off:** Failed trial information is lost (only printed to stdout)

**Alternative Considered:** Raise and halt
- Rejected: Single hardware anomaly shouldn't stop entire optimization
- Entire run would be wasted for a transient issue

### 6. Parameter Range Selection

**Decision:** Use wide default ranges with dynamic adjustment

**Rationale:**

| Parameter | Range | Why |
|-----------|-------|-----|
| batch_size | [8, 16384] | Covers micro to mega-batch scenarios; most systems explore 256-4096 range |
| ubatch_size | [4, 8192] | Covers VRAM-constrained to unrestricted; most systems explore 128-1024 range |
| threads | [1, CPU_count] | Allows pinning to full spectrum; most systems converge to CPU_count |
| gpu_layers | [0, estimated] | 0 for CPU fallback; estimated_max for hardware constraints |

**User Control:** All ranges except threads can be modified before optimization

**Constraint Not Enforced:** batch_size >= ubatch_size (documented but not enforced in code)
- Reasoning: llama.cpp usually requires this, but tool allows exploration
- User responsible for understanding constraints

### 7. Token Count Defaults

**Decision:** Default to 192 tokens with recommendation for larger values

**Rationale:**
- **Speed**: 192 tokens provides fast iteration during optimization (~2-5 min per trial)
- **Stability**: Larger values (256+) provide more stable measurements
- **Compromise**: 192 balances iteration speed with measurement quality
- **Flexibility**: User can increase via `--n-tokens` for more stable final measurement
- **Guidance**: README recommends 512-1024 for final benchmarking

**Trade-off:** Faster iteration vs less stable intermediate results

### 8. CSV Parsing for Metric Extraction

**Decision:** Parse CSV from llama-bench stdout instead of using subprocess flags

**Rationale:**
- **Compatibility**: Works with all llama-bench versions that produce CSV
- **Flexibility**: Can extract multiple metrics from single run
- **Robustness**: CSV format more stable than parsing text output

**Implementation:** Uses pandas for robust CSV parsing

**Error Handling:** Returns 0.0 if expected rows not found in DataFrame
- Subprocess failure: Raises RuntimeError
- CSV parsing issue: Returns 0.0

### 9. Environment Variable Fallback

**Decision:** CLI flags > Environment variables > Interactive prompts

**Rationale:**
- **Flexibility**: Supports different usage patterns
- **CI/CD**: Environment variables for automated runs
- **Interactive**: Prompts for manual usage
- **Explicitness**: CLI flags for one-time runs

**Path Resolution Order:**
```python
path = cli_flag or os.environ.get("VAR") or input("prompt")
```

### 10. Platform-Specific Path Handling

**Decision:** Conditional paths for Windows vs Unix

**Windows Path:**
```python
llama_bench_path = f"{llama_bin_path}/Release/llama-bench.exe"
```

**Unix Path:**
```python
llama_bench_path = f"{llama_bin_path}/llama-bench"
```

**Rationale:**
- llama.cpp's Windows build produces Release subdirectory structure
- Unix build places binaries directly in build/bin
- Detection via `platform.system()`
- Pathlib handles separators automatically

**Limitation:** Only supports Windows Release builds, not Debug builds

### 11. Subprocess Blocking Execution in run_optimization()

**Decision:** Auto-execute comparison benchmarks with `subprocess.run(check=True)`

**Rationale:**
- **Completeness**: Full pipeline includes verification
- **User Convenience**: No need to manually run comparison commands
- **Immediate Feedback**: Results available right after optimization

**Trade-off:**
- Blocking behavior (user can't interrupt benchmarks)
- Failures crash the entire run
- No option to skip benchmarks

**Alternative Considered:** Return commands and let user run them
- Rejected: Less convenient, users would skip comparison

### 12. Debug Print Statements

**Decision:** Include debug output during optimization (cmd_1, cmd_2, cmd_3, warmup cmd)

**Rationale:**
- **Debugging**: Helps users understand what commands are being executed
- **Transparency**: Users can see exact parameters for each trial
- **Reproducibility**: Commands can be manually re-run if needed

**Trade-off:** Pollutes stdout output, makes logs harder to parse

**Note:** Not configurable; always printed

### 13. Temporary File Cleanup Strategy

**Decision:** Create temp files with delete=False, rely on OS cleanup

**Rationale:**
- **Simplicity**: Avoids explicit cleanup code
- **Debugging**: Files remain for investigation if needed
- **OS Handling**: Modern OSes clean temp directories regularly

**Trade-off:**
- Files accumulate during long runs (hundreds per run)
- No explicit cleanup (relies on system temp cleanup)
- Disk space may fill on long-running systems

**Issue:** This violates the documented claim of "immediate cleanup"

## Testing Strategy

### Unit Testing

#### Test: SEARCH_SPACE Structure
```python
def test_search_space_shape():
    from llama_optimus.core import SEARCH_SPACE
    assert isinstance(SEARCH_SPACE, dict)
    assert 'batch_size' in SEARCH_SPACE
    assert 'low' in SEARCH_SPACE['batch_size']
    assert 'high' in SEARCH_SPACE['batch_size']
```

**Status:** Implemented in `test/test_core.py`

**Coverage:** Minimal - only checks SEARCH_SPACE shape, not values

### Integration Testing (Not Implemented)

#### Recommended Tests (Currently Missing):

1. **GPU Layer Estimation**
   - Mock llama-bench with controllable return codes
   - Verify binary search algorithm
   - Test edge cases (all fail, all succeed, timeout)

2. **Benchmark CSV Parsing**
   - Mock llama-bench CSV output
   - Test metric extraction for tg, pp, mean
   - Test error handling (missing rows, malformed CSV)

3. **CLI Argument Parsing**
   - Test valid argument combinations
   - Test override behavior (CLI > env > prompt)
   - Test validation (file existence, path types)

4. **Platform Detection**
   - Mock Windows/Unix systems
   - Verify correct path construction
   - Test executable existence check

5. **Subprocess Execution**
   - Mock subprocess.run and subprocess.TimeoutExpired
   - Test timeout handling
   - Test non-zero exit code handling

### Manual Testing Approach

Current testing relies on manual runs with real llama-bench:

**Prerequisites for Testing:**
1. llama.cpp built and working (release > 3667)
2. GGUF model file available
3. 30-120 minutes per test run depending on settings

**Test Scenarios:**

1. **Basic Functionality**
   ```bash
   llama-optimus --llama-bin /path/bin --model /path/model.gguf \
                 --trials 2 --no-warmup -r 1 --n-tokens 10
   ```
   - Verify it runs without errors
   - Check output format matches specification
   - Confirm best config printed

2. **Metric Selection**
   ```bash
   # Test each metric: tg, pp, mean
   llama-optimus ... --metric tg
   llama-optimus ... --metric pp
   llama-optimus ... --metric mean
   ```
   - Verify different metrics extracted correctly
   - Compare outputs

3. **Override Mode Behavior**
   ```bash
   llama-optimus ... --override-mode scan
   llama-optimus ... --override-mode none
   ```
   - Verify Stage 2 generates correct number of trials
   - Confirm override patterns applied (or skipped)

4. **Warmup Behavior**
   ```bash
   llama-optimus ... --no-warmup
   llama-optimus ... --n-warmup-runs 5
   llama-optimus ... --n-warmup-runs 50
   ```
   - Verify warmup can be skipped
   - Check minimum 4 warmup enforcement

5. **GPU Layer Estimation**
   ```bash
   llama-optimus ...  # Auto-estimate
   llama-optimus ... --ngl-max 80  # Manual override
   ```
   - Verify estimation runs and finds reasonable value
   - Verify override skips estimation

6. **Environment Variable Configuration**
   ```bash
   export LLAMA_BIN=/path/to/bin
   export MODEL_PATH=/path/to/model.gguf
   llama-optimus
   ```
   - Verify env vars are used
   - Check CLI flag override behavior

7. **Cross-Platform**
   - Test on macOS (Apple Silicon & Intel)
   - Test on Linux
   - Test on Windows

### Load Testing (Not Applicable)

llama-optimus is designed for single-instance usage. Not a server; no concurrency testing needed.

### Regression Testing

**Baseline Metrics:**
- GPU layer estimation: 2-5 minutes
- Full optimization with 45 trials: 30-60 minutes (plus warmup and comparison)
- Warmup runs: Complete without hanging
- Final output: Valid llama-server and llama-bench commands

**Regression Checks:**
- Version bumps don't break CLI
- New parameters don't change default behavior
- Output format stays compatible with copy-paste usage

### Error Scenario Testing

#### Missing llama-bench
```bash
llama-optimus --llama-bin /invalid/path --model model.gguf
# Expected: ERROR: llama-bench not found at ...
```

#### Missing Model File
```bash
llama-optimus --llama-bin /valid/path --model /nonexistent/model.gguf
# Expected: Error when benchmark tries to load (at runtime)
```

#### No Paths Provided
```bash
llama-optimus
# Expected: Interactive prompts for paths
```

#### Invalid Metric
```bash
llama-optimus ... --metric invalid
# Expected: argparse error (invalid choice)
```

#### Subprocess Timeout
```bash
# Very slow system or very large token count
llama-optimus --n-tokens 10000 --trials 2
# Expected: subprocess.TimeoutExpired at 820 seconds
```

### Performance Regression Testing

**Success Criteria:**
- Optimization completes without timeout
- Found configuration produces non-zero throughput
- Improvement vs baseline is positive (typical 5-30%)

## Testing Limitations

### Reasons Manual Testing is Dominant

1. **Hardware Dependency**: Results vary drastically by hardware
   - Different GPU/CPU combinations produce different parameter preferences
   - Results not portable across systems
2. **External Tool**: Requires working llama.cpp build
   - Can't mock all behaviors realistically
   - Must use actual llama-bench for realistic testing
3. **Time**: Full test cycle takes 30-120+ minutes
   - Impractical for continuous integration
   - Makes test-driven development difficult
4. **Idempotency**: Results have variance
   - Hard to assert exact values
   - Must check ranges and trends, not specific numbers

### Feasible Improvements

1. **Mock-based Unit Tests**: Test logic without llama-bench
   - Test CLI parsing completely
   - Test CSV extraction with fixture data
   - Test SEARCH_SPACE structure and updates

2. **Fixture Data**: Pre-recorded CSV outputs
   - Create representative llama-bench CSV outputs
   - Test parsing for all metrics
   - Test edge cases (empty rows, malformed CSV)

3. **CLI Integration Tests**: Test argument handling
   - Valid/invalid argument combinations
   - Env var overrides
   - Path validation logic

4. **Docker/Container Tests**: Consistent testing environment
   - Would provide stable hardware baseline
   - Could validate reproducibility
   - Time-consuming to set up

## Quality Assurance Practices

### Code Review Checklist

- [ ] New parameters added to SEARCH_SPACE are documented
- [ ] New objective functions follow error-handling pattern (return 0.0 on exception)
- [ ] CLI changes maintain backward compatibility
- [ ] Platform-specific code tested on target platforms (Windows, Linux, macOS)
- [ ] Output format remains copy-paste compatible
- [ ] Debug statements don't break output format (unlikely since they print to stdout)

### Release Checklist

- [ ] Version bumped in pyproject.toml and __init__.py
- [ ] README updated with breaking changes (if any)
- [ ] New examples added for new features
- [ ] Tested on representative systems (macOS, Linux, Windows)
- [ ] PyPI package created and tested (`pip install llama-optimus`)
- [ ] Tag created in git with version

### Known Limitations & Issues

1. **OVERRIDE_PATTERNS not exported from main package**
   - Users must import from `llama_optimus.override_patterns`
   - Should be fixed in next version

2. **Temp files not explicitly cleaned**
   - Violates documented "immediate cleanup"
   - Accumulates files in OS temp directory
   - Should implement explicit cleanup

3. **Debug prints pollute stdout**
   - Makes machine-parsing of output difficult
   - Should be made configurable or removed

4. **Subprocess failures in run_optimization() not optional**
   - Comparison benchmarks crash run if they fail
   - Should allow skipping or handling gracefully

5. **Minimum warmup enforcement message inconsistent**
   - CLI help mentions "min_runs=3"
   - Code enforces minimum of 4
   - Should clarify to 4 in help text

### Future Improvements

1. **No async/parallel trials**: Could run multiple llama-bench instances
   - Would reduce total runtime by 2-4x
   - Complex to implement reliably

2. **Limited parameter set**: Could expand to cache types, tensor split, etc.
   - Would increase search space and runtime
   - Fewer parameters = faster convergence

3. **No result persistence**: Could save trial history for analysis
   - Would help identify patterns
   - Support for exporting data

4. **No hyperparameter optimization**: Could use Optuna for warmup parameters
   - Could auto-tune --n-warmup-runs
   - Would reduce manual tuning

5. **No model-specific presets**: Could have default configs per model family
   - Would provide warm starts
   - Would speed convergence

6. **Explicit temp file cleanup**: Should delete CSV files after use
   - Would fix disk accumulation issue
   - Implement after pandas reads file

## Edge Cases & Boundary Conditions

### Edge Case: Very Small Model
- Model fully fits in GPU regardless of -ngl setting
- Binary search returns 149 (all layers)
- Optimization still works; other parameters matter

### Edge Case: Very Large Model
- Model doesn't fit any layers in GPU
- Binary search returns 0 (CPU only)
- Optimization focuses on CPU parameters (threads, batch size)

### Edge Case: Single-Core System
- Thread search range: [1, 1]
- Optuna samples only one value
- Other parameters vary normally

### Edge Case: Low VRAM (< 4GB)
- Batch size search may be constrained
- Some configurations might timeout/fail
- Tool continues with other configs (returns 0.0 for failures)

### Edge Case: Extremely Long Token Count (1000+)
- Single benchmark can take 5+ minutes
- Total optimization could exceed 4+ hours
- User should reduce --n-tokens for faster iteration

### Boundary: Timeout at 820 seconds
- Very slow systems might exceed timeout
- Trial returns 0.0 (failure)
- Optimization continues with other configs

### Boundary: 4-Run Warmup Minimum
- User can't request < 4 warmup runs
- Enforced to ensure system stabilization
- --no-warmup flag available to skip entirely

## Known Issues Not Yet Fixed

1. **CSV temp files created with delete=False and never cleaned**
   - Status: Minor (OS cleanup eventually)
   - Impact: Accumulates files during long runs
   - Fix: Use context manager or explicit delete after pandas read

2. **Debug print statements in objectives**
   - Status: Minor (informative but messy)
   - Impact: Pollutes stdout
   - Fix: Make configurable or remove

3. **OVERRIDE_PATTERNS not in main package exports**
   - Status: API Inconsistency
   - Impact: Confuses users about import path
   - Fix: Add to __init__.py imports

4. **Subprocess failures in comparison benchmarks crash run**
   - Status: User-facing issue
   - Impact: Can't recover from network/hardware issues
   - Fix: Wrap in try-except with option to skip

5. **Help text says "min_runs=3" but code enforces 4**
   - Status: Documentation bug
   - Impact: User confusion
   - Fix: Update help text to reflect actual behavior
