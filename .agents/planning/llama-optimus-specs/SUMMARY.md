# llama-optimus Specification Suite - Summary

## Executive Summary

**llama-optimus** is a sophisticated yet lightweight Python-based hyperparameter optimization tool for llama.cpp that uses Bayesian optimization (Optuna) to automatically find the best performance configuration for local LLM inference on any hardware.

Instead of spending hours manually trying different combinations of parameters like batch size, GPU layers, threads, and memory offloading patterns, users run llama-optimus and get copy-paste-ready optimized commands in 30-60 minutes.

**Key Innovation**: Three-stage hierarchical optimization (numerical search → categorical scan → numerical refinement) that balances computational efficiency with search quality.

## Document Map

### 1. **Overview** (`1-overview.md`)
- Project purpose and goals
- Key differentiators
- Target users and platform support
- System architecture pattern
- Success metrics

### 2. **Functional Requirements** (`2-functional-requirements.md`)
- Parameter optimization capabilities
- GPU layer estimation via binary search
- Hardware warmup phase
- Three-stage hierarchical optimization pipeline
- Benchmark execution and metric extraction
- Result reporting and comparison
- Error handling behaviors
- System constraints and limitations

### 3. **Technical Architecture** (`3-technical-architecture.md`)
- Module structure and responsibilities
- Detailed function descriptions
- Data flow diagrams
- Optimization strategy and sampler choices
- Search space bounds and reasoning
- Benchmark integration and CSV parsing
- Platform-specific handling
- Performance characteristics
- Dependency requirements

### 4. **CLI Interface** (`4-cli-interface.md`)
- All command-line arguments (required & optional)
- Configuration method priorities (CLI → env vars → prompts)
- Usage examples for different scenarios
- Output format and what it means
- Error messages and troubleshooting
- Exit codes

### 5. **Python API** (`5-api-specification.md`)
- Public API functions with complete signatures
- Parameter descriptions and examples
- Return value specifications
- Global constants (SEARCH_SPACE, __version__); **Note:** `OVERRIDE_PATTERNS` is NOT exported from the main package — import directly: `from llama_optimus.override_patterns import OVERRIDE_PATTERNS`
- Error handling patterns
- Integration examples
- Type hints and concurrency notes

### 6. **Design Decisions & Testing** (`6-design-decisions-and-testing.md`)
- Rationale for key architectural choices
- Alternatives considered and rejected
- Testing strategy (unit, integration, manual)
- Test scenarios and prerequisites
- Known limitations and edge cases
- Quality assurance practices
- Future improvement opportunities

## Key Design Principles

### 1. Efficiency Through Intelligence
Uses Bayesian optimization (TPESampler) instead of brute-force grid search, reducing trials needed from 1000s to 45-90.

### 2. Robustness Through Pragmatism
Non-working optimization trial configurations fail gracefully (return 0.0) rather than crashing. However, subprocess failures in comparison benchmarks (Stage 3) raise `CalledProcessError` (subprocess check=True). Warmup phase ensures consistent hardware state. Timeouts prevent hangs.

### 3. Usability Through Flexibility
Supports CLI flags, environment variables, and interactive prompts. Works on macOS, Linux, and Windows without code changes. Outputs ready-to-copy commands.

### 4. Quality Through Hierarchy
Separates categorical and numerical optimization to avoid combinatorial explosion while ensuring final refinement with best categorical flags.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Configuration                        │
│  (CLI flags, env vars, or interactive prompts)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│             Path Validation & Binary Search                  │
│          Find max GPU layers via binary search              │
│        (saves time by constraining search bounds)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Hardware Warmup Phase                       │
│    (4-50 iterations to reach steady-state conditions)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│          Stage 1: Bayesian Numerical Search                  │
│  (TPESampler over batch, ubatch, threads, gpu_layers)       │
│         ~45 trials to find promising region                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Stage 2: Categorical Grid Search                     │
│    (GridSampler over flash_attn, override_tensor)           │
│   Holds best Stage 1 parameters constant; tests all combos  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│        Stage 3: Fine-Tuning Numerical Search                │
│      (TPESampler with best categoricals fixed)              │
│      ~45 trials to refine based on categorical choice       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            Automatic Comparison Benchmarking                │
│  (Run optimized config vs default; show improvement %)      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Output Results to User                         │
│  (Best config dict + copy-paste llama-server/bench cmds)    │
└─────────────────────────────────────────────────────────────┘
```

## Core Metrics & Parameters

| Aspect | Details |
|--------|---------|
| **Primary Metric** | Tokens/sec (tg, pp, or mean) |
| **Optimization Method** | Bayesian (Optuna TPESampler) |
| **Parameters Optimized** | batch_size, ubatch_size, threads, gpu_layers, flash_attn, override_tensor |
| **Search Space Size** | Numerical: ~2.5 million × categorical: 10-20 |
| **Trials per Stage** | Stage 1: 45, Stage 2: 2-20, Stage 3: 45 |
| **Total Trials** | 92-110 depending on override_mode |
| **Expected Runtime** | 30-90 minutes (varies by trial count and hardware) |
| **Expected Improvement** | 5-30% over default settings |

## Dependencies

### Python Packages
- **optuna** >= 3.0: Hyperparameter optimization framework
- **pandas**: CSV parsing and data handling

### External Tools
- **llama.cpp**: Inference engine (release > 3667)
- **llama-bench**: Benchmarking tool (included with llama.cpp)

### Runtime
- **Python**: 3.8 or later
- **OS**: macOS, Linux, or Windows
- **CPU**: 4+ cores recommended
- **GPU**: Optional but recommended for GPU optimization

## Feature Completeness

### Fully Implemented ✓
- CLI with flexible argument handling
- Three-stage hierarchical optimization
- GPU layer binary search estimation
- Hardware warmup phase
- Benchmark execution and CSV parsing
- Result reporting with copy-paste commands
- Cross-platform support (Windows/Unix)
- Override-tensor pattern scanning
- Flash attention optimization
- Environment variable configuration
- Error handling and graceful degradation

### Known Outstanding Issues ⚠️
- **Testing**: Only minimal smoke test included (`tests/test_basic.py`); no unit tests for core functions
- **Temp file leak**: CSV temp files created with `delete=False` are never explicitly cleaned up
- **OVERRIDE_PATTERNS export**: Not exported from the main `llama_optimus` package; must import from sub-module
- **Debug prints**: Objective functions contain debug `print()` calls that appear during optimization
- **CLI help text**: `--min-runs` help says `min_runs=3` but code enforces minimum of 4
- Documentation: README is comprehensive but API docs are code-only

### Not Implemented ✗
- Custom override-tensor patterns (reserved for future)
- Cache type optimization (cache-type-k/v)
- Multi-GPU parameters (main-gpu, gpu-split)
- Result persistence and history
- Configuration presets by model
- Async/parallel trial execution
- Hyperparameter tuning of warmup parameters

## Usage Quick Reference

```bash
# Basic usage with environment variables
export LLAMA_BIN=/path/to/llama.cpp/build/bin
export MODEL_PATH=/path/to/model.gguf
llama-optimus

# Quick test (5 min)
llama-optimus --trials 5 --repeat 1 --no-warmup --n-tokens 20

# Balanced (30-45 min)
llama-optimus --trials 45 --repeat 3

# Robust (60+ min)
llama-optimus --trials 70 --repeat 5 --n-tokens 256

# Focus on prompt processing
llama-optimus --metric pp

# Skip GPU layer estimation
llama-optimus --ngl-max 80

# Disable categorical scanning
llama-optimus --override-mode none
```

## File Organization

```
.agents/planning/llama-optimus-specs/
├── 1-overview.md                    # Project overview & goals
├── 2-functional-requirements.md     # What it does
├── 3-technical-architecture.md      # How it's built
├── 4-cli-interface.md              # CLI usage & arguments
├── 5-api-specification.md          # Python API
├── 6-design-decisions-and-testing.md # Design choices & QA
└── SUMMARY.md                       # This file
```

## Success Criteria Met

✓ **Documented What the Code Does**: All major functions, classes, and flows documented
✓ **Explained Design Rationale**: Each major decision includes "why" sections
✓ **Provided Implementation Details**: Technical architecture, data flows, algorithms
✓ **Covered Configuration Options**: All CLI args and env vars documented
✓ **Included Examples**: Usage patterns for different scenarios
✓ **Identified Constraints**: Known limitations, edge cases, and future work
✓ **Reverse-Engineered from Code**: Extracted specifications from actual implementation, not designs

## Revision History

**Generated**: March 27, 2026
**Based on**: llama-optimus v0.1.9
**Repository**: https://github.com/BrunoArsioli/llama-optimus

## Contact & Contribution

- **Original Author**: Bruno Arsioli
- **License**: MIT
- **Issues**: https://github.com/BrunoArsioli/llama-optimus/issues
- **Contributing**: PRs and benchmarks welcome

---

## Document Statistics

| Document | Words | Sections | Key Points |
|----------|-------|----------|-----------|
| Overview | ~800 | 5 | Purpose, goals, architecture |
| Functional Reqs | ~2200 | 8 | All features, requirements, constraints |
| Technical Arch | ~2800 | 7 | Architecture, data flow, algorithms |
| CLI Interface | ~2400 | 6 | Args, config, examples, output |
| API Spec | ~1800 | 5 | Functions, parameters, examples |
| Design & Testing | ~2300 | 5 | Decisions, rationale, testing |
| **Total** | **~12,300** | **~36** | **Complete specification** |

