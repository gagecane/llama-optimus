# Functional Requirements

## Core Functionality

### 1. Parameter Optimization

**Description:** Automatically search the parameter space to find the configuration that maximizes throughput.

**Key Features:**
- Optimize batch size (`--batch-size` / `-b`)
- Optimize micro-batch size (`--ubatch-size` / `-ub`)
- Optimize thread count (`--threads` / `-t`)
- Optimize GPU layer count (`-ngl` / `--n-gpu-layers`)
- Optimize Flash Attention setting (`--flash-attn`)
- Optimize memory offloading patterns (`--override-tensor`)

**Metric Selection:** Users can optimize for:
- **tg** (token generation speed) - pure inference performance
- **pp** (prompt processing speed) - initial context processing
- **mean** - average of both metrics

### 2. GPU Layer Estimation

**Description:** Automatically estimate the maximum number of model layers that can be loaded into GPU/VRAM.

**Process:**
- Binary search between 0 and max possible layers (149 by default)
- For each candidate layer count, run minimal llama-bench workload
- Find the highest value that doesn't crash or timeout
- Return max viable layer count for use as search space upper bound

**User Override:** Users can skip this and provide `--ngl-max` directly.

**Timeout:** 620 seconds per trial

### 3. Hardware Warmup

**Description:** Run preliminary benchmarks to bring hardware to steady-state operating conditions before optimization.

**Rationale:**
- Cold hardware (no thermal throttling, fresh caches, turbo mode) produces misleading results
- Warmup ensures consistent, realistic performance metrics
- Prevents "cold-start advantage" bias in final results

**Process:**
- Run configurable number of warmup iterations (default: 35)
- Each iteration executes llama-bench with max GPU layers and configurable token count
- Minimum 4 warmup runs (enforced, regardless of user input)
- User can skip with `--no-warmup` flag
- Each warmup iteration uses 3 repetitions internally

**Output:** Warmup performance history showing performance for each iteration

### 4. Hierarchical Three-Stage Optimization

#### Stage 1: Initial Numerical Parameter Exploration
- Uses Optuna's TPESampler (Bayesian optimization with multivariate=True)
- Searches over 4 numerical parameters:
  - Batch size [8, 16384]
  - Micro-batch size [4, 8192]
  - Thread count [1, CPU_count]
  - GPU layer count [0, estimated_max]
- Run for configurable number of trials (default: 45)
- Each trial uses specified `-n` tokens for token generation and `-p 0` for prompt processing disabled

#### Stage 2: Categorical Parameter Grid Search
- Uses Optuna's GridSampler (exhaustive grid search)
- Tests all combinations of:
  - Flash Attention (0 or 1)
  - Override-tensor patterns (from preset library, or skipped if --override-mode=none)
- Holds numerical parameters constant (best from Stage 1)
- Grid size: `len(OVERRIDE_PATTERNS) * 2` if override_mode="scan", else 2
- Automatically covers all categorical combinations

#### Stage 3: Fine-Tuning Numerical Parameters
- Returns to TPESampler (Bayesian) with best categorical flags fixed
- Re-optimizes numerical parameters with categorical constraints
- Refines the configuration found in Stage 1
- Same number of trials as Stage 1 (default: 45)
- Each trial uses same `-n` and `-p` configuration as Stage 1

### 5. Benchmark Execution

**Description:** Run llama-bench with specified parameters and extract performance metrics.

**Process:**
- Build llama-bench command with parameter configuration
- Execute with specified number of repetitions (default: 3)
- Capture CSV output to temporary file
- Parse CSV with pandas to extract metric
- Calculate mean and standard deviation
- Print formatted results to stdout

**Metric Extraction:**
- **Token Generation (tg)**: Extract from rows where `n_gen > 0`
- **Prompt Processing (pp)**: Extract from rows where `n_prompt > 0`
- **Mean (mean)**: Average of both tg and pp metrics with combined standard deviation

**Timeout:** 820 seconds per benchmark execution

**Command Structure:** All benchmark commands include `--no-warmup` flag to disable llama-bench's internal warmup (not related to llama-optimus warmup phase).

### 6. Result Reporting

**Output Components:**
1. **Best Configuration Dictionary** - Optimal parameter values from final stage
2. **Performance Score** - Best throughput value achieved (tokens/sec)
3. **llama-server Command** - Ready-to-copy command for running optimized inference server
   - Format: Uses $LLAMA_BIN and $MODEL environment variable references
   - Includes: threads, batch-size, ubatch-size, -ngl, flash-attn (if enabled), override-tensor (if enabled)
4. **llama-bench Commands** - Two commands for comparison:
   - Optimized configuration: Full benchmark command with optimized parameters
   - Default configuration: Baseline benchmark with no optimization flags
5. **Environment Variables** - LLAMA_BIN and MODEL paths printed for reference

### 7. Automatic Comparison Benchmarking

**Automatic Execution:**
After optimization completes, the tool automatically:
1. Executes llama-bench with optimized configuration via `subprocess.run(check=True)`
2. Executes llama-bench with default configuration via `subprocess.run(check=True)`
3. Prints both outputs for direct comparison

**Important:** These subprocess calls are blocking and will raise `CalledProcessError` if the benchmark command fails. The user must have llama-bench executable available and properly configured.

## Non-Functional Behavioral Requirements

### Error Handling

**Optimization Robustness:**
- Non-working configurations in objective functions: Return 0.0 score (treated as failed trial by Optuna)
- Exception printing: Errors are printed to stdout but do not stop optimization
- Timeout protection: 820-second timeout for llama-bench, 620-second timeout for GPU layer estimation
- Missing tools validation: Validates llama-bench exists before starting (checks file existence with Path.is_file())
- Missing paths: Require user to provide paths via CLI flag, env var, or interactive prompt

**Subprocess Failures:**
- If llama-bench returns non-zero exit code: RuntimeError is raised
- If benchmark subprocess times out: subprocess.TimeoutExpired is raised
- If comparison benchmarks fail (Stage 3): The entire run fails with CalledProcessError (subprocess check=True)

**CSV Temp Files:**
- Created with tempfile.NamedTemporaryFile(delete=False)
- File is closed after pandas reads it
- Files are NOT explicitly deleted; rely on OS temp directory cleanup mechanism
- Files accumulate in system temp directory during long optimization runs

### Reproducibility
- Results are deterministic given same hardware and configuration
- Warmup phase ensures consistent starting conditions
- Standard deviation reported alongside mean performance
- Optuna studies are independent, no cross-run state persistence

### User Control
- All parameters configurable via CLI flags or environment variables
- CLI flags override environment variables which override interactive prompts
- Interactive prompts for missing required arguments
- Help text and version information available via --help and --version

## Integration Requirements

### External Tool Integration
- Must locate and execute llama-bench from specified path (with platform-specific extension)
- Must parse CSV output from llama-bench
- Must construct correct command-line arguments for llama-bench
- Cross-platform path handling: Windows uses `{LLAMA_BIN}/Release/llama-bench.exe`, Unix uses `{LLAMA_BIN}/llama-bench`

### Dependency Management
- Optuna 3.0+ required for TPESampler with multivariate option
- pandas required for CSV parsing
- subprocess for command execution
- Python 3.8+ runtime

## Constraints & Limitations

### Known Constraints
- Only optimizes most performance-relevant flags (not all llama.cpp options)
- Does not optimize cache type (`--cache-type-k/v`)
- Does not optimize multi-GPU parameters (`--main-gpu`, `--gpu-split`) on single-GPU systems
- Binary search for GPU layers assumes monotonic degradation (higher -ngl = more VRAM used)
- Grid search for categorical parameters fixed to available presets in OVERRIDE_PATTERNS
- Cannot handle scenario where user provides invalid regex patterns for --override-tensor

### Performance Constraints
- Minimum warmup runs: 4 (enforced regardless of user input)
- Default trial count: 45 per stage (user configurable, 1 to unbounded)
- Minimum tokens for benchmarking: 1 (user configurable, default 192)
- Timeout for benchmark: 820 seconds
- Timeout for GPU estimation: 620 seconds
- Each warmup iteration internally uses 3 repetitions (hardcoded, not configurable)

### Hardware Constraints
- Requires llama.cpp release version > 3667 (with `--no-warmup` flag support)
- Requires at least one compatible GGUF model file
- CPU core count auto-detected via os.cpu_count() for thread range bounds

### Known Issues Not Yet Addressed
- Temp CSV files are not explicitly cleaned up
- Debug print statements are output during optimization (polluting stdout)
- CSV extraction returns 0.0 only if expected rows are missing, not for other pandas errors
