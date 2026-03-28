# test/test_core_ctk_ctv_step3.py
# Tests for Step 3: ctk/ctv passthrough in objective_1/2/3 and run_optimization

import pytest
from unittest.mock import patch, MagicMock
from llama_optimus.core import objective_1, objective_2, objective_3


def _make_trial(int_value=1, categorical_value=0):
    """Return a minimal mock optuna trial."""
    trial = MagicMock()
    trial.suggest_int.return_value = int_value
    trial.suggest_categorical.return_value = categorical_value
    return trial


# ── objective_1 ───────────────────────────────────────────────────────────────

def test_objective_1_with_ctk():
    """-ctk flag must appear in command when cache_type_k is set."""
    captured = []

    def fake_bench(cmd, metric):
        captured.append(list(cmd))
        return 1.0

    trial = _make_trial()
    with patch("llama_optimus.core.run_llama_bench_with_csv", side_effect=fake_bench):
        objective_1(trial, n_tokens=10, metric="tg", repeat=1,
                    llama_bench_path="llama-bench", model_path="model.gguf",
                    cache_type_k="q8_0")

    assert captured, "run_llama_bench_with_csv was never called"
    cmd = captured[0]
    assert "-ctk" in cmd, f"-ctk not in cmd: {cmd}"
    assert cmd[cmd.index("-ctk") + 1] == "q8_0"


def test_objective_1_with_ctv():
    """-ctv flag must appear in command when cache_type_v is set."""
    captured = []

    def fake_bench(cmd, metric):
        captured.append(list(cmd))
        return 1.0

    trial = _make_trial()
    with patch("llama_optimus.core.run_llama_bench_with_csv", side_effect=fake_bench):
        objective_1(trial, n_tokens=10, metric="tg", repeat=1,
                    llama_bench_path="llama-bench", model_path="model.gguf",
                    cache_type_v="q4_0")

    assert captured, "run_llama_bench_with_csv was never called"
    cmd = captured[0]
    assert "-ctv" in cmd, f"-ctv not in cmd: {cmd}"
    assert cmd[cmd.index("-ctv") + 1] == "q4_0"


def test_objective_1_none():
    """Neither -ctk nor -ctv should appear when both params are None."""
    captured = []

    def fake_bench(cmd, metric):
        captured.append(list(cmd))
        return 1.0

    trial = _make_trial()
    with patch("llama_optimus.core.run_llama_bench_with_csv", side_effect=fake_bench):
        objective_1(trial, n_tokens=10, metric="tg", repeat=1,
                    llama_bench_path="llama-bench", model_path="model.gguf")

    assert captured, "run_llama_bench_with_csv was never called"
    cmd = captured[0]
    assert "-ctk" not in cmd, f"-ctk found in cmd when absent expected: {cmd}"
    assert "-ctv" not in cmd, f"-ctv found in cmd when absent expected: {cmd}"


# ── objective_2 ───────────────────────────────────────────────────────────────

def test_objective_2_with_ctk():
    """-ctk flag must appear in command when cache_type_k is set."""
    captured = []

    def fake_bench(cmd, metric):
        captured.append(list(cmd))
        return 1.0

    trial = _make_trial(categorical_value=0)
    with patch("llama_optimus.core.run_llama_bench_with_csv", side_effect=fake_bench):
        objective_2(trial, n_tokens=10, metric="tg", repeat=1,
                    llama_bench_path="llama-bench", model_path="model.gguf",
                    override_mode="none", batch=512, u_batch=256,
                    threads=4, gpu_layers=10,
                    cache_type_k="q8_0")

    assert captured, "run_llama_bench_with_csv was never called"
    cmd = captured[0]
    assert "-ctk" in cmd, f"-ctk not in cmd: {cmd}"
    assert cmd[cmd.index("-ctk") + 1] == "q8_0"


def test_objective_2_none():
    """Neither flag should appear when both params are None."""
    captured = []

    def fake_bench(cmd, metric):
        captured.append(list(cmd))
        return 1.0

    trial = _make_trial(categorical_value=0)
    with patch("llama_optimus.core.run_llama_bench_with_csv", side_effect=fake_bench):
        objective_2(trial, n_tokens=10, metric="tg", repeat=1,
                    llama_bench_path="llama-bench", model_path="model.gguf",
                    override_mode="none", batch=512, u_batch=256,
                    threads=4, gpu_layers=10)

    assert captured, "run_llama_bench_with_csv was never called"
    cmd = captured[0]
    assert "-ctk" not in cmd, f"-ctk found when absent expected: {cmd}"
    assert "-ctv" not in cmd, f"-ctv found when absent expected: {cmd}"


# ── objective_3 ───────────────────────────────────────────────────────────────

def test_objective_3_with_ctk():
    """-ctk flag must appear in command when cache_type_k is set."""
    captured = []

    def fake_bench(cmd, metric):
        captured.append(list(cmd))
        return 1.0

    trial = _make_trial(int_value=1, categorical_value=0)
    with patch("llama_optimus.core.run_llama_bench_with_csv", side_effect=fake_bench):
        objective_3(trial, n_tokens=10, metric="tg", repeat=1,
                    llama_bench_path="llama-bench", model_path="model.gguf",
                    override_pattern="none", flash_attn=0, override_mode="none",
                    cache_type_k="q8_0")

    assert captured, "run_llama_bench_with_csv was never called"
    cmd = captured[0]
    assert "-ctk" in cmd, f"-ctk not in cmd: {cmd}"
    assert cmd[cmd.index("-ctk") + 1] == "q8_0"


def test_objective_3_none():
    """Neither flag should appear when both params are None."""
    captured = []

    def fake_bench(cmd, metric):
        captured.append(list(cmd))
        return 1.0

    trial = _make_trial(int_value=1, categorical_value=0)
    with patch("llama_optimus.core.run_llama_bench_with_csv", side_effect=fake_bench):
        objective_3(trial, n_tokens=10, metric="tg", repeat=1,
                    llama_bench_path="llama-bench", model_path="model.gguf",
                    override_pattern="none", flash_attn=0, override_mode="none")

    assert captured, "run_llama_bench_with_csv was never called"
    cmd = captured[0]
    assert "-ctk" not in cmd, f"-ctk found when absent expected: {cmd}"
    assert "-ctv" not in cmd, f"-ctv found when absent expected: {cmd}"
