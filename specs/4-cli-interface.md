# CLI Interface & Configuration

## Command Entry Point

```bash
llama-optimus [OPTIONS]
```

Entry point defined in pyproject.toml: `llama-optimus = "llama_optimus.cli:main"`

## Command-Line Arguments

### Required Arguments
These can be provided via CLI flag, environment variable, or interactive prompt:

#### `--llama-bin` / `LLAMA_BIN`
- **Type:** String (path)
- **Description:** Path to llama.cpp build/bin directory
- **Example:** `/home/user/llama.cpp/build/bin`
- **Environment Variable:** `LLAMA_BIN`
- **Default:** Interactive prompt if not provided
- **Validation:** Must contain `llama-bench` (or `llama-bench.exe` on Windows); file existence checked via Path.is_file()
- **Windows Path:** `{LLAMA_BIN}/Release/llama-bench.exe`
- **Unix Path:** `{LLAMA_BIN}/llama-bench`

#### `--model` / `MODEL_PATH`
- **Type:** String (path)
- **Description:** Path to GGUF model file
- **Example:** `/home/user/models/llama2-13b.gguf`
- **Environment Variable:** `MODEL_PATH`
- **Default:** Interactive prompt if not provided
- **Validation:** Path checked for existence at benchmark time (not at startup)

### Optional Arguments - Optimization Control

#### `--trials`
- **Type:** Integer
- **Default:** 45
- **Range:** 1 to unbounded
- **Description:** Number of Optuna optimization trials per stage (Stages 1 and 3)
- **Impact:** Affects total runtime; 45 trials per stage typical for 30-60 minute run
- **Example:** `--trials 100`

#### `--metric`
- **Type:** Choice: `tg`, `pp`, `mean`
- **Default:** `tg` (token generation)
- **Description:** Which throughput metric to optimize
  - `tg`: Token generation speed (pure inference performance)
  - `pp`: Prompt processing speed (context loading performance)
  - `mean`: Average of both metrics
- **Example:** `--metric mean`

#### `--repeat` / `-r`
- **Type:** Integer
- **Short Form:** `-r`
- **Default:** 3
- **Range:** 1 to unbounded
- **Description:** Number of llama-bench repetitions per configuration (each trial runs this many llama-bench iterations)
- **Guidance:**
  - 1: Quick/dirty assessment (less reliable, ~2 min per trial)
  - 3: Default, balanced (moderately reliable, ~4-6 min per trial)
  - 5+: Robust results (more reliable, ~8+ min per trial)
- **Example:** `-r 5`

#### `--n-tokens`
- **Type:** Integer
- **Default:** 192
- **Range:** 1 to 1000+ (recommended > 70)
- **Description:** Number of tokens used in benchmarking during optimization trials
- **Guidance:**
  - Larger values → more stable measurements (lower variance)
  - Smaller values → faster iteration during optimization
  - Recommended minimum: 70 for reliability
  - For final benchmarking: 256+ recommended
- **Note:** Specifies both generation tokens and prompt tokens (pp uses 2x)
- **Example:** `--n-tokens 256`

### Optional Arguments - Hardware Warmup

#### `--no-warmup`
- **Type:** Boolean flag
- **Default:** Warmup enabled
- **Description:** Skip hardware warmup phase entirely
- **Use Case:** Testing/debugging only
- **Effect:** Removes ~5-10 minutes from total runtime but results less reliable
- **Note:** Even with this flag, optimization still runs; only eliminates pre-optimization stabilization

#### `--n-warmup-runs`
- **Type:** Integer
- **Default:** 35
- **Range:** 1 to unbounded (minimum enforced: 4)
- **Description:** Maximum number of warmup iterations before optimization starts
- **Behavior:** Actual warmup runs = max(requested, 4) (minimum of 4 enforced)
- **Guidance:**
  - Increase if hardware doesn't show thermal stability in 35 runs
  - Decrease if system reaches stability quickly
  - On typical systems, 20-35 runs sufficient
- **Example:** `--n-warmup-runs 50`

#### `--n-warmup-tokens` / `-nwt`
- **Type:** Integer
- **Short Form:** `-nwt`
- **Default:** 128
- **Description:** Number of tokens used in each warmup iteration (both generation and prompt)
- **Guidance:**
  - Increase if not detecting warmup on slow/large systems
  - Decrease for faster warmup on fast systems
  - Match or exceed typical trial token count
- **Example:** `--n-warmup-tokens 256`

### Optional Arguments - GPU Optimization

#### `--ngl-max`
- **Type:** Integer
- **Default:** None (triggers auto-estimation)
- **Description:** Maximum GPU layers to consider in optimization
- **Effect:** If provided, skips GPU layer estimation (binary search)
- **Use Case:** Skip estimation if you already know your max (saves 5-10 minutes)
- **Example:** `--ngl-max 60`
- **Note:** If not provided, estimate_max_ngl() runs before optimization

### Optional Arguments - Advanced Memory Offloading

#### `--override-mode`
- **Type:** Choice: `none`, `scan`, `custom`
- **Default:** `scan`
- **Description:** How to treat `--override-tensor` flag in Stage 2
  - `none`: Don't optimize this parameter (Stage 2 only tests flash_attn, 2 trials instead of 16+)
  - `scan`: Grid search all 8 preset patterns × 2 flash_attn options = 16 trials in Stage 2
  - `custom`: (planned feature, not yet implemented) User provides custom patterns
- **Example:** `--override-mode none`
- **Impact on Stage 2 Trial Count:**
  - `scan` (default): 16 trials (8 patterns × 2 flash_attn values)
  - `none`: 2 trials (only flash_attn 0 and 1)

### Utility Arguments

#### `--version` / `-v`
- **Type:** Boolean flag
- **Short Form:** `-v`
- **Description:** Print version and exit
- **Output:** `llama-optimus v{__version__}` (e.g., "llama-optimus v0.1.9")
- **Example:** `llama-optimus --version`

#### `--help` / `-h`
- **Type:** Boolean flag
- **Short Form:** `-h`
- **Description:** Print help text and exit
- **Includes:** Full argument descriptions, examples, and usage patterns

## Configuration Methods (Priority Order)

1. **CLI Flags** (highest priority)
   ```bash
   llama-optimus --llama-bin /path/to/bin --model /path/to/model.gguf --trials 50
   ```

2. **Environment Variables**
   ```bash
   export LLAMA_BIN=/path/to/bin
   export MODEL_PATH=/path/to/model.gguf
   llama-optimus --trials 50
   ```

3. **Interactive Prompts** (lowest priority)
   ```
   Please, provide the path to your 'llama.cpp/build/bin' > /path/to/bin
   Please, provide the path to your 'ai_model.gguf' > /path/to/model.gguf
   ```

## Usage Examples

### Quick Test Run
```bash
llama-optimus --llama-bin ~/llama.cpp/build/bin \
              --model ~/models/llama2.gguf \
              --trials 5 \
              --repeat 1 \
              --n-tokens 20 \
              --no-warmup
```
- Minimal trials (5) and repetitions (1) for fast iteration
- Skip warmup to save time
- Runtime: ~10-15 minutes
- Good for verifying setup works

### Balanced Run (Recommended)
```bash
llama-optimus --llama-bin ~/llama.cpp/build/bin \
              --model ~/models/llama2.gguf \
              --trials 45 \
              --repeat 3 \
              --n-tokens 192
```
- Default settings
- Runtime: ~30-60 minutes
- Reliable results with warmup

### Robust Optimization
```bash
llama-optimus --llama-bin ~/llama.cpp/build/bin \
              --model ~/models/llama2.gguf \
              --trials 70 \
              --repeat 5 \
              --n-tokens 256 \
              --n-warmup-runs 50
```
- More trials and repetitions
- Larger token counts for stability
- Extended warmup
- Runtime: 90+ minutes
- Best results for publication/comparison

### Focus on Prompt Processing
```bash
llama-optimus --llama-bin ~/llama.cpp/build/bin \
              --model ~/models/llama2.gguf \
              --metric pp \
              --trials 45
```
- Optimize only prompt processing speed
- Good for applications with long context windows

### Skip GPU Layer Estimation
```bash
llama-optimus --llama-bin ~/llama.cpp/build/bin \
              --model ~/models/llama2.gguf \
              --ngl-max 80
```
- Assumes you've determined max GPU layers is 80
- Skips binary search phase
- Saves 5-10 minutes
- Goes directly to warmup and optimization

### Disable Memory Offloading Search
```bash
llama-optimus --llama-bin ~/llama.cpp/build/bin \
              --model ~/models/llama2.gguf \
              --override-mode none
```
- Only optimizes flash-attn in Stage 2 (2 trials)
- Skips override-tensor patterns (saves ~16 trials)
- Faster but less comprehensive for memory-constrained systems

### Environment Variable Setup (Persistent)
```bash
# Create script: set_paths.sh
#!/bin/bash
export LLAMA_BIN=/home/user/llama.cpp/build/bin
export MODEL_PATH=/home/user/models/llama2.gguf

# Use it:
source set_paths.sh
llama-optimus --trials 50 --metric tg
```

## Output Format

### Pre-Optimization Phase Output

```
#################
# LLAMA-OPTIMUS #
#################

Number of CPUs: 16.
Path to 'llama-bench':/path/to/llama-bench
Path to 'model.gguf' file:/path/to/model.gguf

# If --ngl-max provided:
User-specified maximum -ngl set to 80

# Otherwise, GPU layer estimation output:
########################################################################
# Find maximum number of model layers that can be written to your VRAM #
########################################################################

Testing for: -ngl = 75
Testing for: -ngl = 112
Testing for: -ngl = 93
...
Estimated max ngl = 93
Setting maximum -ngl to 93

# If not --no-warmup:
#######################
# Starting warmup...  #
#######################

warmup cmd: ['/path/to/llama-bench', '-t', '16', '-ngl', '93', ...]
Warmup 1: 65.32 tok/s
Warmup performance history: [65.32]
Warmup 2: 68.15 tok/s
Warmup performance history: [65.32, 68.15]
...

##################################
# Starting Optimization Loop...  #
##################################
```

### Optimization Phase Output

Each trial produces output like:

```
cmd_1: ['/path/to/llama-bench', '--batch-size', '256', ...]

Token generation speed: 72.43 tokens/s ; std 2.15
```

Stage summaries:

```
############################################################
# First stage: Initial exploration of parameter space      #
############################################################

Trial 0 finished with value: 72.43 and parameters: {'batch': 256, 'u_batch': 128, ...}
Trial 1 finished with value: 71.23 and parameters: {'batch': 512, 'u_batch': 256, ...}
...
Best config Stage_1: {'batch': 4096, 'u_batch': 1024, 'threads': 8, 'gpu_layers': 93}
Best Stage_1 tg tokens/sec: 73.5

############################################################
# Second stage: Grid search over categorical parameters    #
############################################################

Trial 0 finished with value: 74.12 and parameters: {'flash_attn': 0, 'override_tensor': 'none'}
Trial 1 finished with value: 74.89 and parameters: {'flash_attn': 1, 'override_tensor': 'none'}
...
Best config Stage_2: {'flash_attn': 1, 'override_tensor': 'none'}
Best Stage_2 tg tokens/sec: 74.89

#######################################
# Third stage: Finetune final config  #
#######################################

Trial 0 finished with value: 74.50 and parameters: {'batch': 4096, ...}
...
Best config Stage_3: {'batch': 4096, 'u_batch': 1024, 'threads': 8, 'gpu_layers': 93}
Best Stage_3 tg tokens/sec: 74.95
```

### Result Output

```
You are ready to run a local llama-server:
If you launch llama-server, it will be listening at http://127.0.0.1:8080/ in your browser.

###################################################################
# You can now launch an optimized llama-server.                   #
# just run next lines in your terminal:                           #
###################################################################

LLAMA_BIN=/path/to/bin
MODEL=/path/to/model.gguf

 $LLAMA_BIN/llama-server --model $MODEL -t 8 --batch-size 4096 --ubatch-size 1024 -ngl 93 --flash-attn

########################################################
# Benchmarking your OPTIMIZED configuration            #
# Let's run the following line on terminal:            #
########################################################

/path/to/llama-bench --model /path/to/model.gguf -t 8 --batch-size 4096 --ubatch-size 1024 -ngl 93 --flash-attn 1 -n 128 -p 256 -r 6 --no-warmup --progress

[Benchmark output with CSV results...]

########################################################
# Compare your previous results with NON-OPTIMIZED case#
# Let's run the following line on terminal:            #
########################################################

/path/to/llama-bench --model /path/to/model.gguf -n 128 -p 256 -r 6 --no-warmup --progress

[Default benchmark output...]
```

### Automatic Benchmark Execution

After printing commands, llama-optimus automatically:
1. Executes the optimized benchmark command via `subprocess.run(shlex.split(...), check=True)`
   - **Blocks until complete**
   - **Raises CalledProcessError if command fails**
2. Executes the default benchmark command via `subprocess.run(shlex.split(...), check=True)`
   - **Blocks until complete**
   - **Raises CalledProcessError if command fails**

## Error Handling in CLI

### Path Validation Errors

```
ERROR: llama-bench not found at /path/to/bin/llama-bench
```
- Verify LLAMA_BIN path is correct
- Ensure llama.cpp was built with latest version (>3667)
- Check that the path contains the build/bin directory, not the build directory itself

### Missing Required Paths

```
ERROR: LLAMA_BIN or MODEL_PATH not set. Set via environment variable,
pass via CLI flags, or provide paths just after launching llama-optimus.
Go to your terminal, navigate to your_path_to/llama.cpp/buil/bin and type 'pwd' to resolve the entire path.
Go to your terminal, navigate to your_path_to_AI_models/ and type 'pwd' to resolve the path.
Note: you must pass /path_to_model/model_name.gguf; e.g. your_path_model/gemma3_12B.gguf .
```
- Provide paths via `--llama-bin` and `--model` flags
- Or set `LLAMA_BIN` and `MODEL_PATH` environment variables

### Optimization Failures

```
CalledProcessError: Command '<benchmark command>' returned non-zero exit status
```
- Raised during automatic benchmark execution if benchmark fails
- Check llama-bench output for specific error messages
- Verify model file is accessible and not corrupted
- Check available VRAM and disk space

### Subprocess Timeout

```
subprocess.TimeoutExpired: Command '<benchmark command>' timed out after 820 seconds
```
- Benchmark took longer than 820 seconds
- Try reducing `--n-tokens` to speed up individual trials
- Or increase token count if timeouts are happening frequently (may indicate other issues)

## Exit Codes

- **0**: Successful optimization (including automatic benchmarks)
- **1**: Configuration error, missing paths, or invalid arguments
- **Other**: Subprocess errors (CalledProcessError from failed benchmarks)

## Debug Output

The CLI produces debug output during optimization:

```
cmd_1: ['/path/to/llama-bench', '--batch-size', '256', ...]
cmd_2: ['/path/to/llama-bench', '--batch-size', '256', ...]
cmd_3: ['/path/to/llama-bench', '--batch-size', '256', ...]
warmup cmd: ['/path/to/llama-bench', ...]
Running objective_2 with batch=256, u_batch=128, threads=8, gpu_layers=93
```

These debug prints are not configurable and will appear in stdout regardless of verbosity settings.
