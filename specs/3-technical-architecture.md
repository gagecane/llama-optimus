# Technical Architecture

## Module Structure

```
src/llama_optimus/
├── __init__.py           # Package initialization, version handling, public exports
├── cli.py               # Command-line interface, argument parsing
├── core.py              # Core optimization logic, benchmarking, Optuna studies
├── search_space.py      # Parameter search space definitions
└── override_patterns.py # Override-tensor pattern presets
```

**Note:** Modules are located under `src/llama_optimus/` directory (not at project root). Installation via setuptools correctly handles this via `package-dir = {"" = "src"}` in pyproject.toml.

## Component Descriptions

### 1. CLI Module (`src/llama_optimus/cli.py`)

**Purpose:** Entry point and command-line argument handling

**Key Functions:**
- `main()`: Orchestrates the entire optimization pipeline from CLI

**Responsibilities:**
- Parse command-line arguments using argparse
- Resolve paths from CLI flags, environment variables, or interactive prompts
- Validate that required tools (llama-bench) exist via Path.is_file()
- Detect operating system and adjust path handling (Windows vs Unix)
- Update SEARCH_SPACE['gpu_layers']['high'] based on GPU layer estimation
- Call warmup_until_stable() if --no-warmup not specified
- Call run_optimization() with validated parameters

**Dependencies:**
- argparse (stdlib)
- os, sys, platform (stdlib)
- pathlib.Path (stdlib)
- Core functions from `core.py`: run_optimization, estimate_max_ngl, warmup_until_stable
- Constants: __version__, OVERRIDE_PATTERNS, SEARCH_SPACE, max_threads

**Environment Variables Supported:**
- `LLAMA_BIN`: Path to llama.cpp/build/bin directory
- `MODEL_PATH`: Path to GGUF model file

**Key Validation:**
- Path existence check for llama-bench via Path().is_file()
- Both llama_bin_path and model_path must be provided (no default)
- Exits with code 1 on validation failure

### 2. Core Module (`src/llama_optimus/core.py`)

**Purpose:** Optimization logic and benchmark execution

**Key Functions:**

#### `estimate_max_ngl(llama_bench_path, model_path, min_ngl=0, max_ngl=SEARCH_SPACE['gpu_layers']['high'])`
- Binary search to find maximum GPU layer count
- Runs minimal llama-bench for each candidate (only 1 token, 1 repetition)
- Prints `"Testing for: -ngl = {mid}"` for each trial
- Returns highest working -ngl value
- Timeout: 620 seconds per trial
- Note: Default max_ngl parameter is dynamic, not hardcoded 149

#### `run_llama_bench_with_csv(cmd, metric)`
- Executes llama-bench command
- Captures stdout as CSV output to temporary file
- Parses pandas DataFrame to extract metric
- Returns numerical throughput score (tokens/sec)
- Raises RuntimeError if subprocess returns non-zero exit code
- Returns 0.0 if expected CSV rows not found (metric extraction fails)
- Prints formatted results to stdout (includes mean, std, and metric name)
- Timeout: 820 seconds
- Temp files created with delete=False and not explicitly cleaned up

#### `objective_1(trial, n_tokens, metric, repeat, llama_bench_path, model_path)`
- Stage 1 objective function for Optuna
- Samples: batch, u_batch, threads, gpu_layers
- Builds llama-bench command with:
  - `--no-warmup` flag (disables llama-bench's internal warmup)
  - Task-specific flags: `-n {n_tokens} -p 0` for tg, `-p {2*n_tokens} -n 0` for pp, `-n {n_tokens} -p {2*n_tokens}` for mean
- Returns throughput metric
- Catches all exceptions and returns 0.0 (prints error message)
- Prints debug output: `cmd_1: [...]` before execution

#### `objective_2(trial, n_tokens, metric, repeat, llama_bench_path, model_path, override_mode, batch, u_batch, threads, gpu_layers)`
- Stage 2 objective function for Optuna (Grid search over categorical parameters)
- Receives fixed numerical parameters: batch, u_batch, threads, gpu_layers
- Samples: flash_attn (always), override_tensor (only if override_mode="scan")
- Builds command with passed numerical parameters (not resampled)
- Only adds `--flash-attn` flag if flash_attn == 1
- Only adds `--override-tensor` flag if override_key != "none"
- Returns throughput metric
- Catches all exceptions and returns 0.0
- Prints debug output: `cmd_2: [...]` before execution

#### `objective_3(trial, n_tokens, metric, repeat, llama_bench_path, model_path, override_pattern, flash_attn, override_mode)`
- Stage 3 objective function for Optuna (Fine-tune with fixed categorical flags)
- Resamples numerical parameters: batch, u_batch, threads, gpu_layers
- Receives fixed categorical flags: override_pattern, flash_attn (parameters, not resampled)
- Adds fixed categorical flags to command (same logic as objective_2)
- Returns throughput metric
- Catches all exceptions and returns 0.0
- Prints debug output: `cmd_3: [...]` before execution
- Note: Despite receiving override_pattern and flash_attn as parameters, also resamples them internally (potential design issue)

#### `warmup_until_stable(llama_bench_path, model_path, metric, ngl, min_runs, n_warmup_runs, n_warmup_tokens, max_threads)`
- Runs preliminary benchmarks to stabilize hardware
- Enforces minimum of 4 warmup runs (overrides n_warmup_runs if < 4)
- Each warmup iteration:
  - Uses max_threads for thread count
  - Uses specified ngl for GPU layers
  - Uses 3 repetitions internally (hardcoded, not configurable)
  - Includes both -n and -p flags for balanced workload
- Tracks performance history list
- Prints: `warmup cmd: [...]` and `Warmup {i+1}: {performance:.2f} tok/s` for each iteration
- Returns performance history list

#### `run_optimization(n_trials, n_tokens, metric, repeat, llama_bench_path, model_path, llama_bin_path, override_mode)`
- Orchestrates 3-stage optimization pipeline
- Stage 1: Creates Optuna study with TPESampler(multivariate=True), runs n_trials
- Stage 2: Creates Optuna study with GridSampler, runs n_override*2 trials if override_mode="scan" else 2 trials
- Stage 3: Creates Optuna study with TPESampler(multivariate=True), runs n_trials
- Prints best configuration and metric after each stage
- Constructs llama-server command with optimized parameters using $LLAMA_BIN and $MODEL variable references
- Constructs two llama-bench commands (optimized and default)
- **CRITICAL:** Executes both benchmark commands via `subprocess.run(shlex.split(...), check=True)`
  - These calls are BLOCKING
  - Will raise CalledProcessError if benchmarks fail
  - Not documented in prior specs as a potential failure point
- Prints all commands to stdout for user reference

**Command Construction (Numerical):**
```python
[
    llama_bench_path,
    "--batch-size", str(batch),
    "--ubatch-size", str(u_batch),
    "--threads", str(threads),
    "-ngl", str(gpu_layers),
    "--model", model_path,
    "-r", str(repeat),
    "-o", "csv",
    "--no-warmup",
    # task-specific flags added after
]
```

**Error Handling Pattern:**
- Catch all exceptions in objective functions
- Print error message to stdout
- Return 0.0 (interpreted as failed trial by Optuna)
- Continue optimization without crashing

### 3. Search Space Module (`src/llama_optimus/search_space.py`)

**Purpose:** Define parameter ranges and categorical options

**Key Variables:**

```python
max_threads = os.cpu_count()  # Auto-detected from system

SEARCH_SPACE = {
    'batch_size': {'low': 8, 'high': 16384},
    'ubatch_size': {'low': 4, 'high': 8192},
    'threads': {'low': 1, 'high': max_threads},  # Auto-detected CPU count
    'gpu_layers': {'low': 0, 'high': 149},       # Dynamically adjusted after estimation
    'flash_attn': [0, 1],
    'override_spc': list(OVERRIDE_PATTERNS.keys())
}
```

**Auto-Detection:**
- `max_threads`: Obtained from `os.cpu_count()`
- `gpu_layers.high`: Initially 149, updated by cli.py after GPU layer estimation

**Dynamic Adjustment:**
- CLI updates SEARCH_SPACE['gpu_layers']['high'] based on estimate_max_ngl() result
- This bounds the search space for Stage 1 and Stage 3 trials

### 4. Override Patterns Module (`src/llama_optimus/override_patterns.py`)

**Purpose:** Pre-defined memory offloading strategies

**Structure:**
- Dictionary mapping pattern names (str) to regex patterns (str)
- Includes "none" option for no override (empty string value)
- Patterns used with `--override-tensor` flag

**Available Patterns:**
```python
OVERRIDE_PATTERNS = {
    "none": "",
    "ffn_cpu_all": r"blk\.\d+\.ffn_.*_exps\.=CPU",
    "ffn_cpu_even": r"blk\.(?:[0-9]*[02468])\.ffn_.*_exps\.=CPU",
    "ffn_cpu_odd": r"blk\.(?:[0-9]*[13579])\.ffn_.*_exps\.=CPU",
    "ffn_cpu_updown": r"blk\.\d+\.ffn_(?:up|down)_exps\.=CPU",
    "ffn_cpu_up": r"blk\.\d+\.ffn_up_exps\.=CPU",
    "ffn_cpu_down": r"blk\.\d+\.ffn_down_exps\.=CPU",
    "ffn_cpu_last_quarter": r"blk\.(6[0-9]|7[0-9])\.ffn_.*_exps\.=CPU",
    "ffn_cpu_from_6": r"blk\.(6|7|8|9|[1-9][0-9]+)\.ffn_.*_exps\.=CPU",
}
```

**Focus:** Patterns target expert FFN tensors for memory offloading on MoE (Mixture of Experts) models

## Package Initialization (`src/llama_optimus/__init__.py`)

**Public API Exports:**
```python
__version__  # Version string from importlib.metadata or fallback "0.1.9"
estimate_max_ngl  # from core
run_llama_bench_with_csv  # from core
run_optimization  # from core
SEARCH_SPACE  # from core
```

**Missing Export:**
- `OVERRIDE_PATTERNS` is NOT exported from __init__.py
- Users must import from: `from llama_optimus.override_patterns import OVERRIDE_PATTERNS`
- Not from: `from llama_optimus import OVERRIDE_PATTERNS` (this will fail)

## Data Flow

### Initialization Phase
```
CLI Arguments (argparse)
    ↓
Path Validation (Path.is_file())
    ↓
Load SEARCH_SPACE, OVERRIDE_PATTERNS
    ↓
Detect OS (platform.system())
```

### Optimization Phase
```
GPU Layer Estimation (if not --ngl-max)
    ↓ (updates SEARCH_SPACE['gpu_layers']['high'])
    ↓
Warmup Phase (if not --no-warmup)
    ↓
Stage 1 Trials (Optuna TPESampler)
    ├─ Sample numerical parameters
    ├─ Build llama-bench command
    ├─ Execute via subprocess (timeout 820s)
    ├─ Parse CSV output
    └─ Return metric to Optuna
    ↓
Extract Best Stage 1 Parameters
    ↓
Stage 2 Trials (Optuna GridSampler)
    ├─ Sample categorical parameters only
    ├─ Build command with fixed numerical + sampled categorical
    ├─ Execute via subprocess (timeout 820s)
    ├─ Parse CSV output
    └─ Return metric to Optuna
    ↓
Extract Best Stage 2 Parameters
    ↓
Stage 3 Trials (Optuna TPESampler with categorical fixed)
    ├─ Resample numerical parameters
    ├─ Build command with fixed categorical + resampled numerical
    ├─ Execute via subprocess (timeout 820s)
    ├─ Parse CSV output
    └─ Return metric to Optuna
    ↓
Extract Best Stage 3 Parameters
    ↓
Construct and Print Output Commands
    ↓
Execute Optimized Benchmark (subprocess.run check=True)
    ↓
Execute Default Benchmark (subprocess.run check=True)
    ↓
Print Comparison Results
```

## Optimization Strategy

### Three-Stage Hierarchical Approach

**Rationale:**
- **Stage 1**: Fast exploration of continuous parameter space (Bayesian)
- **Stage 2**: Systematic search of categorical options (Grid)
- **Stage 3**: Fine-tuning with best categoricals applied (Bayesian)

**Sampler Choices:**

| Stage | Sampler | Reason |
|-------|---------|--------|
| 1 | TPESampler(multivariate=True) | Efficient exploration of continuous space with inter-parameter interactions |
| 2 | GridSampler | Exhaustive coverage of all categorical combinations (deterministic) |
| 3 | TPESampler(multivariate=True) | Further refinement of numerical parameters with categorical constraints |

**Trial Count Distribution:**
- Stage 1: n_trials (default 45, user configurable 1-unbounded)
- Stage 2: n_override * 2 if override_mode="scan" (where n_override = 8 patterns * 2 flash_attn options = 16), else 2
- Stage 3: n_trials (default 45)

### Search Space Optimization

**Batch Size Bounds**: [8, 16384]
- Lower bound: Minimum viable for efficient batching
- Upper bound: Maximum practical on modern GPUs

**Micro-Batch Size Bounds**: [4, 8192]
- Lower bound: Minimum viable sub-batch size
- Upper bound: VRAM-limited for large models
- Constraint: Usually batch >= ubatch (not enforced by code, user responsible)

**Thread Count**: [1, CPU_count]
- Auto-detected from os.cpu_count()
- Range ensures CPU pinning possibilities

**GPU Layers**: [0, estimated_max]
- 0: Pure CPU inference (fallback)
- estimated_max: Determined after binary search (updated in SEARCH_SPACE)
- Default upper bound: 149 (before estimation)

**Flash Attention**: [0, 1]
- Binary choice: disabled (0) or enabled (1)
- Hardware-dependent performance impact
- Only added to command if value == 1

## Benchmark Integration

### CSV Parsing Strategy

**llama-bench Output Format:**
Expected CSV columns:
- `n_gen`: Number of generation tokens (0 if pp only)
- `n_prompt`: Number of prompt tokens (0 if tg only)
- `avg_ts`: Average tokens/sec
- `stddev_ts`: Standard deviation

**Metric Extraction Logic:**
```python
if metric == "tg":
    rows = df[df["n_gen"] > 0]
    value = rows["avg_ts"].iloc[0] if not rows.empty else 0.0
elif metric == "pp":
    rows = df[df["n_prompt"] > 0]
    value = rows["avg_ts"].iloc[0] if not rows.empty else 0.0
else:  # mean
    tg_rows = df[df["n_gen"] > 0]
    pp_rows = df[df["n_prompt"] > 0]
    if not tg_rows.empty and not pp_rows.empty:
        tg_value = tg_rows["avg_ts"].iloc[0]
        pp_value = pp_rows["avg_ts"].iloc[0]
        value = (tg_value + pp_value) / 2
    else:
        value = 0.0
```

## Platform-Specific Handling

### Windows Support
- llama-bench location: `{LLAMA_BIN}/Release/llama-bench.exe`
- Path construction via f-string
- File existence check: `Path(llama_bench_path).is_file()`
- Detected via: `platform.system() == "Windows"`

### Unix/Linux/macOS
- llama-bench location: `{LLAMA_BIN}/llama-bench`
- Same path handling mechanism
- No special extensions needed

## Performance Characteristics

### Time Complexity
- GPU layer estimation: O(log 149) ≈ 7-8 trials
- Single trial: O(1) (constant-time llama-bench execution + CSV parsing)
- Total optimization: O((n_trials_1 + n_trials_2 + n_trials_3) × trial_time)
  - Typical: (45 + 16 + 45) trials × 2-5 minutes per trial ≈ 30-60 minutes

### Space Complexity
- SEARCH_SPACE dict: O(1) constant size
- OVERRIDE_PATTERNS dict: O(8) constant (8 patterns)
- Temporary CSV files: Created per trial, count = num_trials × 2 (stdout + actual file, not deleted)
- In-memory: Optuna study objects, pandas DataFrames

## Dependencies & Requirements

### Python Dependencies
```
optuna>=3.0
pandas
```

### External Dependencies
- llama.cpp (release > 3667 with --no-warmup support)
- GGUF model file (compatible format)
- Python 3.8+ runtime

### System Requirements
- CPU with 4+ cores (recommended)
- GPU with 4GB+ VRAM (for GPU layers > 0)
- 2-10GB free disk space for models
- System temp directory accessible (for temp CSV files)
