# Python API Specification

## Package Imports

### Public API

```python
from llama_optimus import (
    __version__,
    estimate_max_ngl,
    run_llama_bench_with_csv,
    run_optimization,
    SEARCH_SPACE,
)
```

**Note:** `OVERRIDE_PATTERNS` is NOT exported from the main package. Import it directly:
```python
from llama_optimus.override_patterns import OVERRIDE_PATTERNS
```

## Core Functions

### `estimate_max_ngl()`

**Signature:**
```python
def estimate_max_ngl(
    llama_bench_path: str,
    model_path: str,
    min_ngl: int = 0,
    max_ngl: int = SEARCH_SPACE['gpu_layers']['high']
) -> int
```

**Description:** Estimate maximum GPU layers via binary search

**Parameters:**
- `llama_bench_path` (str, required): Full path to llama-bench executable
- `model_path` (str, required): Full path to GGUF model file
- `min_ngl` (int): Starting point for binary search (default: 0)
- `max_ngl` (int): Upper bound for search (default: dynamic from SEARCH_SPACE, initially 149)

**Returns:** Integer representing the highest viable -ngl value

**Behavior:**
- Uses binary search algorithm (O(log n) complexity)
- Tests each candidate by running minimal llama-bench (1 token, 1 repetition)
- Prints `"Testing for: -ngl = {value}"` for each trial
- Returns immediately when search converges
- Each trial has 620-second timeout

**Raises:**
- `subprocess.CalledProcessError`: If llama-bench execution returns non-zero
- `subprocess.TimeoutExpired`: If any trial exceeds 620-second timeout
- `FileNotFoundError`: If llama_bench_path doesn't exist

**Example:**
```python
max_layers = estimate_max_ngl(
    "/path/to/llama.cpp/build/bin/llama-bench",
    "/path/to/model.gguf"
)
print(f"Max -ngl: {max_layers}")  # e.g., "Max -ngl: 93"
```

### `run_llama_bench_with_csv()`

**Signature:**
```python
def run_llama_bench_with_csv(
    cmd: list[str],
    metric: str
) -> float
```

**Description:** Execute llama-bench and extract performance metric from CSV output

**Parameters:**
- `cmd` (list[str]): Command as list of strings
  - First element: path to llama-bench
  - Remaining elements: command-line arguments
- `metric` (str): Which metric to extract
  - `"tg"`: Token generation speed
  - `"pp"`: Prompt processing speed
  - `"mean"`: Average of both

**Returns:** Float representing tokens/sec (or 0.0 if extraction fails)

**Behavior:**
- Executes subprocess with 820-second timeout
- Captures stdout as CSV data
- Writes to temporary file (created with delete=False, not explicitly cleaned)
- Parses CSV with pandas
- Prints formatted results to stdout (including metric name, value, and std dev)
- Returns 0.0 only if expected CSV rows missing

**Raises:**
- `RuntimeError`: If subprocess returns non-zero exit code
- `subprocess.TimeoutExpired`: If execution exceeds 820 seconds
- Pandas exceptions: If CSV parsing fails (not caught, will propagate)

**Example:**
```python
cmd = [
    "/path/to/llama-bench",
    "--batch-size", "256",
    "--ubatch-size", "128",
    "--threads", "8",
    "-ngl", "50",
    "--model", "/path/to/model.gguf",
    "-r", "3",
    "-o", "csv",
    "-n", "128",
    "-p", "0"
]
tokens_per_sec = run_llama_bench_with_csv(cmd, "tg")
print(f"Generation speed: {tokens_per_sec:.2f} tok/s")
```

### `run_optimization()`

**Signature:**
```python
def run_optimization(
    n_trials: int,
    n_tokens: int,
    metric: str,
    repeat: int,
    llama_bench_path: str,
    model_path: str,
    llama_bin_path: str,
    override_mode: str
) -> None
```

**Description:** Orchestrate 3-stage optimization pipeline

**Parameters:**
- `n_trials` (int): Number of trials per stage (Stages 1 and 3; default usage: 45)
- `n_tokens` (int): Tokens used in benchmarking (default: 192)
- `metric` (str): Metric to optimize: "tg", "pp", or "mean"
- `repeat` (int): Repetitions per configuration (default: 3)
- `llama_bench_path` (str): Full path to llama-bench executable
- `model_path` (str): Full path to GGUF model
- `llama_bin_path` (str): Path to llama.cpp build/bin directory
- `override_mode` (str): "none", "scan", or "custom"

**Returns:** None (outputs results to stdout)

**Behavior:**
- Creates 3 Optuna studies with different samplers
- **Stage 1**: TPESampler(multivariate=True) over numerical parameters
- **Stage 2**: GridSampler over categorical parameters
- **Stage 3**: TPESampler(multivariate=True) with categorical constraints
- Prints best configuration after each stage
- Constructs llama-server and llama-bench commands
- **Automatically executes both benchmark commands via subprocess.run(check=True)**
  - These calls BLOCK until completion
  - Will raise CalledProcessError if benchmarks fail
  - Not optional, part of function execution

**Side Effects:**
- Creates temporary CSV files in system temp directory (not cleaned up)
- Prints extensive output to stdout (including debug prints for each trial)
- Executes llama-bench multiple times (30-120+ minutes depending on settings)
- Updates SEARCH_SPACE['gpu_layers']['high'] (global mutable state)

**Raises:**
- `subprocess.CalledProcessError`: From automatic benchmark subprocess calls
- `subprocess.TimeoutExpired`: If any benchmark exceeds timeout
- Optuna exceptions: If study creation/optimization fails

**Example:**
```python
run_optimization(
    n_trials=45,
    n_tokens=192,
    metric="tg",
    repeat=3,
    llama_bench_path="/path/to/llama-bench",
    model_path="/path/to/model.gguf",
    llama_bin_path="/path/to/build/bin",
    override_mode="scan"
)
```

### `warmup_until_stable()`

**Signature:**
```python
def warmup_until_stable(
    llama_bench_path: str,
    model_path: str,
    metric: str,
    ngl: int,
    min_runs: int,
    n_warmup_runs: int,
    n_warmup_tokens: int,
    max_threads: int
) -> list[float]
```

**Description:** Run preliminary benchmarks to stabilize hardware

**Parameters:**
- `llama_bench_path` (str): Full path to llama-bench
- `model_path` (str): Full path to GGUF model
- `metric` (str): Metric to track during warmup
- `ngl` (int): GPU layers to use for warmup
- `min_runs` (int): Minimum warmup iterations (enforced: at least 4)
- `n_warmup_runs` (int): Requested warmup iterations
- `n_warmup_tokens` (int): Tokens per warmup iteration
- `max_threads` (int): Thread count for warmup (typically max CPU count)

**Returns:** List of float values representing performance history (one per iteration)

**Behavior:**
- Enforces minimum of 4 warmup runs (overrides n_warmup_runs if < 4)
- Each warmup iteration:
  - Runs llama-bench with max threads and specified -ngl
  - Uses 3 internal repetitions (hardcoded, not configurable)
  - Includes both -n and -p tokens for balanced workload
  - Has 820-second timeout
- Prints: `warmup cmd: [...]` before starting
- Prints: `Warmup {i+1}: {performance:.2f} tok/s` after each iteration
- Prints: `Warmup performance history: [...]` after each iteration

**Example:**
```python
history = warmup_until_stable(
    llama_bench_path="/path/to/llama-bench",
    model_path="/path/to/model.gguf",
    metric="tg",
    ngl=80,
    min_runs=4,
    n_warmup_runs=35,
    n_warmup_tokens=128,
    max_threads=16
)
print(f"Warmup history: {history}")
# Output: [62.5, 63.1, 63.2, 63.1, ...]
```

## Global Variables / Constants

### `SEARCH_SPACE`

**Type:** `dict[str, Any]`

**Description:** Parameter search space boundaries and categorical options

**Structure:**
```python
SEARCH_SPACE = {
    'batch_size': {
        'low': 8,
        'high': 16384
    },
    'ubatch_size': {
        'low': 4,
        'high': 8192
    },
    'threads': {
        'low': 1,
        'high': <auto-detected CPU count from os.cpu_count()>
    },
    'gpu_layers': {
        'low': 0,
        'high': 149  # Dynamically adjusted after GPU estimation
    },
    'flash_attn': [0, 1],  # Binary choice
    'override_spc': [
        # List of keys from OVERRIDE_PATTERNS (8 keys total)
        'none',
        'ffn_cpu_all',
        'ffn_cpu_even',
        'ffn_cpu_odd',
        'ffn_cpu_updown',
        'ffn_cpu_up',
        'ffn_cpu_down',
        'ffn_cpu_last_quarter',
        'ffn_cpu_from_6',
    ]
}
```

**Modification:**
- `gpu_layers['high']` is dynamically updated after max-ngl estimation in cli.py
- Can be modified before calling run_optimization() to customize search bounds

**Example:**
```python
from llama_optimus import SEARCH_SPACE

# Read initial bounds
min_batch = SEARCH_SPACE['batch_size']['low']  # 8
max_batch = SEARCH_SPACE['batch_size']['high']  # 16384

# Customize bounds before optimization
SEARCH_SPACE['batch_size']['high'] = 8192
SEARCH_SPACE['gpu_layers']['high'] = 80

# Or update after estimation
# (This is done automatically in cli.py)
```

### `OVERRIDE_PATTERNS`

**Type:** `dict[str, str]`

**Description:** Pre-defined memory offloading patterns for --override-tensor flag

**Location:** `llama_optimus.override_patterns`

**Import:**
```python
from llama_optimus.override_patterns import OVERRIDE_PATTERNS
```

**Structure:**
```python
OVERRIDE_PATTERNS = {
    "none": "",  # Empty string means no override
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

**Example:**
```python
from llama_optimus.override_patterns import OVERRIDE_PATTERNS

for pattern_name, pattern_regex in OVERRIDE_PATTERNS.items():
    print(f"{pattern_name}: {pattern_regex}")

# Use a pattern in llama-bench command
pattern = OVERRIDE_PATTERNS["ffn_cpu_all"]
cmd = ["llama-bench", "--override-tensor", pattern, ...]
```

### `__version__`

**Type:** `str`

**Description:** Package version string

**Source:** Loaded from package metadata via importlib.metadata, with fallback to "0.1.9"

**Example:**
```python
from llama_optimus import __version__
print(f"llama-optimus version: {__version__}")  # e.g., "0.1.9"
```

### `max_threads`

**Type:** `int`

**Description:** Auto-detected CPU core count

**Location:** `llama_optimus.search_space`

**Source:** `os.cpu_count()`

**Example:**
```python
from llama_optimus.search_space import max_threads
print(f"System has {max_threads} CPU cores")
```

## Internal Functions (Not Public API)

### `objective_1()`, `objective_2()`, `objective_3()`

**Status:** Implementation detail, not part of public API

**Use:** Called internally by `run_optimization()`

**Caveat:** Subject to change in future versions; do not rely on these in external code

## Error Handling Patterns

### Handling Subprocess Errors

```python
try:
    result = run_llama_bench_with_csv(cmd, metric)
except subprocess.TimeoutExpired:
    print(f"Benchmark timed out (exceeded 820 seconds)")
except RuntimeError as e:
    print(f"Benchmark failed: {e}")
```

### Handling Estimation Errors

```python
try:
    max_ngl = estimate_max_ngl(llama_bench_path, model_path)
except subprocess.TimeoutExpired:
    print("GPU layer estimation timed out")
except subprocess.CalledProcessError:
    print("GPU layer estimation failed")
except FileNotFoundError:
    print("llama-bench not found")
```

### Handling Optimization Failures

```python
try:
    run_optimization(
        n_trials=45,
        n_tokens=192,
        metric="tg",
        repeat=3,
        llama_bench_path=llama_bench_path,
        model_path=model_path,
        llama_bin_path=llama_bin_path,
        override_mode="scan"
    )
except subprocess.CalledProcessError as e:
    print(f"Optimization failed: {e}")
    # This typically occurs during automatic benchmark execution
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Handling Path Errors

```python
from pathlib import Path

if not Path(llama_bench_path).is_file():
    raise FileNotFoundError(f"llama-bench not found at {llama_bench_path}")
```

## Concurrency & Thread Safety

**Status:** Not designed for concurrent usage

**Limitations:**
- Global SEARCH_SPACE dictionary is mutable (not thread-safe)
- Temporary files use tempfile module with unique names
- Subprocess execution is sequential (not parallel)
- Optuna studies are created independently

**Recommendation:** Run llama-optimus instances serially, not in parallel

## Type Hints

The implementation uses minimal explicit type hints in code but follows this pattern:
- Function parameters: Native Python types (str, int, list)
- Return values: float for metrics, int for counts, list for performance history, None for side-effect functions
- No explicit type annotations in function signatures (but documented in docstrings)

## Example Integration

```python
#!/usr/bin/env python3
from llama_optimus import (
    estimate_max_ngl,
    run_optimization,
    SEARCH_SPACE
)
from llama_optimus.override_patterns import OVERRIDE_PATTERNS

# Paths
llama_bench = "/path/to/llama-bench"
model = "/path/to/model.gguf"
llama_bin = "/path/to/build/bin"

# Step 1: Estimate GPU layers
max_ngl = estimate_max_ngl(llama_bench, model)

# Step 2: Update search space
SEARCH_SPACE['gpu_layers']['high'] = max_ngl

# Step 3: Run optimization
try:
    run_optimization(
        n_trials=45,
        n_tokens=192,
        metric="tg",
        repeat=3,
        llama_bench_path=llama_bench,
        model_path=model,
        llama_bin_path=llama_bin,
        override_mode="scan"
    )
except Exception as e:
    print(f"Optimization failed: {e}")
```

## Performance Characteristics

**Single Trial Execution:**
- Command construction: < 1 ms
- Subprocess execution: 2-5 minutes (depends on n_tokens and repeat)
- CSV parsing: < 100 ms
- Total per trial: ~2-5 minutes

**GPU Layer Estimation:**
- Binary search: 7-8 trials maximum
- Total time: 15-30 minutes

**Full Optimization Run:**
- Warmup: 10-15 minutes (35 iterations)
- Stage 1: 90-180 minutes (45 trials × 2-5 min)
- Stage 2: 30-80 minutes (16 trials × 2-5 min)
- Stage 3: 90-180 minutes (45 trials × 2-5 min)
- Comparison benchmarks: 20-30 minutes
- **Total: 30-120+ minutes** depending on configuration

## Memory Usage

- Typical: < 100 MB for SEARCH_SPACE, Optuna studies, and DataFrames
- Temporary CSV files: ~1-10 KB per trial, accumulate on disk (not cleaned)
- Long runs with 100+ trials may accumulate hundreds of MB in temp files
