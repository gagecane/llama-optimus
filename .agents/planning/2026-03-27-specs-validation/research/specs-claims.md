# Existing Specs Claims Summary

## Project Overview
- **Name:** llama-optimus
- **Version:** 0.1.9
- **Purpose:** Automatically optimize llama.cpp performance flags for maximum throughput
- **Language:** Python 3.8+
- **Primary Dependencies:** Optuna, pandas
- **Platforms:** macOS (Apple Silicon & Intel), Linux (x86_64), Windows

## Claimed Module Structure
```
llama_optimus/
├── __init__.py           # Version, public exports
├── cli.py               # Entry point, argument parsing
├── core.py              # Optimization logic, benchmarking
├── search_space.py      # Parameter ranges
└── override_patterns.py # Memory offloading presets
```

## Claimed Core Functions (Public API)
1. `estimate_max_ngl()` - Binary search for max GPU layers
2. `run_llama_bench_with_csv()` - Execute benchmark and extract metric
3. `run_optimization()` - 3-stage optimization orchestrator
4. `warmup_until_stable()` - Hardware warmup phase
5. `objective_1()`, `objective_2()`, `objective_3()` - Stage objectives (internal)

## Claimed Global Exports
- `__version__` - Version string
- `SEARCH_SPACE` - Parameter ranges dictionary
- `OVERRIDE_PATTERNS` - Memory offloading patterns (from override_patterns.py)

## Claimed CLI Arguments (Key ones)
- Required: `--llama-bin`, `--model`
- Optional: `--trials`, `--metric`, `--repeat`, `--n-tokens`, `--no-warmup`, `--ngl-max`, `--override-mode`, etc.
- Utility: `--version`, `--help`

## Claimed 3-Stage Optimization
- Stage 1: TPESampler (Bayesian) - numerical parameters
- Stage 2: GridSampler - categorical parameters (flash_attn, override_tensor)
- Stage 3: TPESampler - refine numerical with best categoricals fixed

## Claimed Features
- Parameter optimization (batch, ubatch, threads, -ngl, flash-attn, override-tensor)
- GPU layer estimation (binary search)
- Hardware warmup (minimum 4 runs enforced)
- Multiple metric optimization (tg, pp, mean)
- Error handling with fallback to 0.0
- Cross-platform path handling (Windows .exe, Unix binary)
- Environment variable configuration (LLAMA_BIN, MODEL_PATH)
- Result comparison (optimized vs default)

## Claimed Testing Status
- Unit test for SEARCH_SPACE structure exists
- No integration tests implemented
- Manual testing approach (requires real hardware, llama-bench)
- Test scenarios documented for: basic functionality, metrics, override modes, warmup, GPU estimation, env vars, cross-platform
