# test/test_core_ctk_ctv_step4.py
# Tests for Step 4: ctk/ctv appended to final example command strings in run_optimization

import pytest
from unittest.mock import patch, MagicMock
from llama_optimus.core import run_optimization


def _make_run_optimization_mocks():
    """Patch all external calls needed by run_optimization."""
    mock_study = MagicMock()
    mock_study.best_trial.params = {
        "threads": 4,
        "batch": 512,
        "u_batch": 256,
        "gpu_layers": 10,
    }
    mock_study.best_value = 42.0

    mock_best_2 = {
        "override_tensor": "none",
        "flash_attn": 0,
        "threads": 4,
        "batch": 512,
        "u_batch": 256,
        "gpu_layers": 10,
    }

    return mock_study, mock_best_2


def _run_opt(cache_type_k=None, cache_type_v=None):
    """
    Run run_optimization with heavy mocking and return captured print output.
    We capture what gets printed so we can check command strings.
    """
    mock_study = MagicMock()
    mock_study.best_trial.params = {
        "threads": 4,
        "batch": 512,
        "u_batch": 256,
        "gpu_layers": 10,
    }
    mock_study.best_value = 42.0
    mock_study.best_trial.params = {
        "threads": 4,
        "batch": 512,
        "u_batch": 256,
        "gpu_layers": 10,
    }

    # We need to capture the local variables. The cleanest way is to
    # capture what subprocess.run receives AND what gets printed.
    printed = []

    with patch("llama_optimus.core.optuna") as mock_optuna, \
         patch("llama_optimus.core.subprocess.run") as mock_subprocess, \
         patch("builtins.print", side_effect=lambda *a, **kw: printed.append(" ".join(str(x) for x in a))):

        mock_optuna.create_study.return_value = mock_study
        mock_optuna.samplers.TPESampler.return_value = MagicMock()
        mock_optuna.samplers.RandomSampler.return_value = MagicMock()

        # Patch the study to use best_trial.params with our values
        # study_1.best_trial.params has threads/batch/u_batch/gpu_layers
        # study_2.best_trial.params has override_tensor/flash_attn + above
        # study_3.best_trial.params has threads/batch/u_batch/gpu_layers

        def make_study(direction=None, sampler=None):
            s = MagicMock()
            s.best_trial.params = {
                "threads": 4,
                "batch": 512,
                "u_batch": 256,
                "gpu_layers": 10,
                "override_tensor": "none",
                "flash_attn": 0,
            }
            s.best_value = 42.0
            return s

        mock_optuna.create_study.side_effect = make_study

        with patch("llama_optimus.core.run_llama_bench_with_csv", return_value=42.0):
            run_optimization(
                n_trials=1,
                n_tokens=10,
                metric="tg",
                repeat=1,
                llama_bench_path="llama-bench",
                model_path="model.gguf",
                llama_bin_path="/usr/bin",
                override_mode="none",
                cache_type_k=cache_type_k,
                cache_type_v=cache_type_v,
            )

    return printed


def _get_printed_output(cache_type_k=None, cache_type_v=None):
    return "\n".join(_run_opt(cache_type_k=cache_type_k, cache_type_v=cache_type_v))


def test_server_cmd_includes_ctk_ctv():
    """llama_server_cmd must include --cache-type-k and --cache-type-v when set."""
    output = _get_printed_output(cache_type_k="q8_0", cache_type_v="q4_0")
    assert "--cache-type-k q8_0" in output, f"--cache-type-k q8_0 not found in output:\n{output}"
    assert "--cache-type-v q4_0" in output, f"--cache-type-v q4_0 not found in output:\n{output}"


def test_bench_cmd_includes_ctk_ctv():
    """-ctk and -ctv must appear in the llama_bench_cmd display string."""
    output = _get_printed_output(cache_type_k="q8_0", cache_type_v="q4_0")
    assert "-ctk q8_0" in output, f"-ctk q8_0 not found in output:\n{output}"
    assert "-ctv q4_0" in output, f"-ctv q4_0 not found in output:\n{output}"


def test_bench_cmd_default_unchanged():
    """llama_bench_cmd_default must never contain -ctk or -ctv."""
    # We need to inspect the actual string; capture it via subprocess.run args
    subprocess_calls = []

    mock_study = MagicMock()
    mock_study.best_value = 42.0

    def make_study(direction=None, sampler=None):
        s = MagicMock()
        s.best_trial.params = {
            "threads": 4,
            "batch": 512,
            "u_batch": 256,
            "gpu_layers": 10,
            "override_tensor": "none",
            "flash_attn": 0,
        }
        s.best_value = 42.0
        return s

    with patch("llama_optimus.core.optuna") as mock_optuna, \
         patch("llama_optimus.core.subprocess.run") as mock_subprocess, \
         patch("builtins.print"):

        mock_optuna.create_study.side_effect = make_study
        mock_optuna.samplers.TPESampler.return_value = MagicMock()
        mock_optuna.samplers.RandomSampler.return_value = MagicMock()
        mock_subprocess.side_effect = lambda args, **kw: subprocess_calls.append(args)

        with patch("llama_optimus.core.run_llama_bench_with_csv", return_value=42.0):
            run_optimization(
                n_trials=1,
                n_tokens=10,
                metric="tg",
                repeat=1,
                llama_bench_path="llama-bench",
                model_path="model.gguf",
                llama_bin_path="/usr/bin",
                override_mode="none",
                cache_type_k="q8_0",
                cache_type_v="q4_0",
            )

    # subprocess.run is called with shlex.split(llama_bench_cmd) then shlex.split(llama_bench_cmd_default)
    assert len(subprocess_calls) >= 2, f"Expected at least 2 subprocess.run calls, got {len(subprocess_calls)}"
    default_cmd_args = subprocess_calls[-1]  # last call is llama_bench_cmd_default
    default_cmd_str = " ".join(default_cmd_args)
    assert "-ctk" not in default_cmd_str, f"-ctk found in llama_bench_cmd_default: {default_cmd_str}"
    assert "-ctv" not in default_cmd_str, f"-ctv found in llama_bench_cmd_default: {default_cmd_str}"


def test_cmds_none():
    """When both params are None, no cache-type flags appear in any command string."""
    output = _get_printed_output(cache_type_k=None, cache_type_v=None)
    assert "--cache-type-k" not in output, f"--cache-type-k found unexpectedly:\n{output}"
    assert "--cache-type-v" not in output, f"--cache-type-v found unexpectedly:\n{output}"
    assert "-ctk" not in output, f"-ctk found unexpectedly:\n{output}"
    assert "-ctv" not in output, f"-ctv found unexpectedly:\n{output}"
