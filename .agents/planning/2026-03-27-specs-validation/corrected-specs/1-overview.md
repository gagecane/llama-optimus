# llama-optimus Project Overview

## Project Summary

**llama-optimus** is a lightweight Python tool that automatically optimizes `llama.cpp` performance flags for maximum throughput on local AI model inference.

**Version:** 0.1.9
**License:** MIT
**Language:** Python 3.8+
**Primary Dependencies:** Optuna (>=3.0), pandas
**Installation:** Available on PyPI via `pip install llama-optimus`

## Purpose & Goals

llama-optimus solves the problem of manual performance tuning for local LLM inference. Instead of manually trying different combinations of `llama.cpp` parameters, the tool:

- **Automates parameter optimization** using Bayesian optimization (Optuna's TPESampler)
- **Finds optimal hardware-specific configurations** in 30-60 minutes instead of hours
- **Maximizes throughput** for either token generation (tg), prompt processing (pp), or both
- **Adapts to diverse hardware** (Apple Silicon, Linux x86, NVIDIA GPU systems, Windows)

## Key Differentiators

1. **Bayesian Optimization** - Uses Optuna's TPESampler for intelligent parameter search instead of random or grid search
2. **Hierarchical Three-Stage Optimization** - Separates numerical parameter tuning from categorical flag scanning
3. **Hardware Warmup Phase** - Ensures benchmarks run under "steady-state" conditions, avoiding misleading cold-start results
4. **Copy-Paste Ready Output** - Produces ready-to-use commands for `llama-server` and `llama-bench`
5. **Automatic GPU Layer Estimation** - Binary search to find maximum GPU layer count for the hardware
6. **Advanced Memory Offloading** - Supports grid search over `--override-tensor` patterns for large models on low-VRAM systems
7. **Grid Search for Categorical Parameters** - Exhaustive testing of all categorical combinations (flash-attn, override patterns)

## Target Users

- **Local LLM enthusiasts** running models with llama.cpp
- **Developers** optimizing inference performance for edge/embedded devices
- **Researchers** benchmarking model performance across different hardware configurations
- **Users with limited VRAM** seeking advanced memory offloading strategies

## Platform Support

- macOS (Apple Silicon & Intel)
- Linux (x86_64)
- Windows (with llama.cpp Release builds)
- Any system with Python 3.8+ and llama.cpp installed (release version > 3667)

## System Architecture Pattern

llama-optimus follows a **performance optimization pipeline** pattern:

```
User Input (paths, hyperparameters)
    ↓
System Warmup Phase (stabilize hardware performance)
    ↓
GPU Layer Estimation (binary search for max -ngl)
    ↓
3-Stage Optimization Loop:
  - Stage 1: Bayesian search over numerical parameters (TPESampler, ~45 trials)
  - Stage 2: Grid search over categorical parameters (GridSampler, ~16-20 trials)
  - Stage 3: Fine-tuning numerical parameters with best categorical flags (TPESampler, ~45 trials)
    ↓
Output Optimization Results
    ↓
Automatic Benchmark Comparison (optimized vs default configurations)
```

## Integration Points

- **llama.cpp**: Uses `llama-bench` for performance measurements
- **Optuna**: Hyperparameter optimization framework (TPESampler, GridSampler)
- **pandas**: CSV parsing for benchmark results
- **subprocess**: Command execution for external tools (llama-bench)
- **argparse**: CLI argument handling
- **Platform detection**: os.platform for Windows/Unix path handling

## Key Success Metrics

- **Performance Improvement**: Target 5-30% throughput improvement over default settings
- **Execution Time**: Complete optimization in 30-60 minutes depending on trial count and hardware
- **Robustness**: Consistent results across multiple runs with hardware warmup phase
- **Usability**: Zero-configuration (env vars or CLI flags) operation with interactive fallback prompts

## External Requirements

- **llama.cpp**: Requires release version > 3667 (includes --no-warmup flag in llama-bench)
- **GGUF Model**: At least one compatible model file
- **Python Runtime**: 3.8 or higher
