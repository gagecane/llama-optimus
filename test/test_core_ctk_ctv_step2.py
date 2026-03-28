# test/test_core_ctk_ctv_step2.py
# Tests for Step 2: ctk/ctv passthrough in estimate_max_ngl and warmup_until_stable

from unittest.mock import patch, MagicMock
from llama_optimus.core import estimate_max_ngl, warmup_until_stable


def _make_run_side_effect(returncode=0):
    """Return a mock subprocess.run result."""
    mock_result = MagicMock()
    mock_result.returncode = returncode
    return mock_result


# ── estimate_max_ngl ─────────────────────────────────────────────────────────

def test_estimate_max_ngl_with_ctk():
    """-ctk flag must appear in the subprocess command when cache_type_k is set."""
    captured = []

    def fake_run(cmd, **kwargs):
        captured.append(list(cmd))
        r = MagicMock()
        r.returncode = 0
        return r

    with patch("llama_optimus.core.subprocess.run", side_effect=fake_run):
        estimate_max_ngl(
            llama_bench_path="llama-bench",
            model_path="model.gguf",
            min_ngl=0,
            max_ngl=1,
            cache_type_k="q8_0",
        )

    assert captured, "subprocess.run was never called"
    assert any(
        "-ctk" in cmd and "q8_0" in cmd for cmd in captured
    ), f"-ctk q8_0 not found in any captured cmd: {captured}"
    # verify they are adjacent
    for cmd in captured:
        if "-ctk" in cmd:
            idx = cmd.index("-ctk")
            assert cmd[idx + 1] == "q8_0", f"Expected q8_0 after -ctk, got {cmd[idx+1]}"


def test_estimate_max_ngl_with_ctv():
    """-ctv flag must appear in the subprocess command when cache_type_v is set."""
    captured = []

    def fake_run(cmd, **kwargs):
        captured.append(list(cmd))
        r = MagicMock()
        r.returncode = 0
        return r

    with patch("llama_optimus.core.subprocess.run", side_effect=fake_run):
        estimate_max_ngl(
            llama_bench_path="llama-bench",
            model_path="model.gguf",
            min_ngl=0,
            max_ngl=1,
            cache_type_v="q4_0",
        )

    assert captured, "subprocess.run was never called"
    for cmd in captured:
        if "-ctv" in cmd:
            idx = cmd.index("-ctv")
            assert cmd[idx + 1] == "q4_0"
            return
    raise AssertionError(f"-ctv q4_0 not found in any captured cmd: {captured}")


def test_estimate_max_ngl_none():
    """Neither -ctk nor -ctv should appear when both params are None."""
    captured = []

    def fake_run(cmd, **kwargs):
        captured.append(list(cmd))
        r = MagicMock()
        r.returncode = 0
        return r

    with patch("llama_optimus.core.subprocess.run", side_effect=fake_run):
        estimate_max_ngl(
            llama_bench_path="llama-bench",
            model_path="model.gguf",
            min_ngl=0,
            max_ngl=1,
        )

    for cmd in captured:
        assert "-ctk" not in cmd, f"-ctk found in cmd when it should be absent: {cmd}"
        assert "-ctv" not in cmd, f"-ctv found in cmd when it should be absent: {cmd}"


# ── warmup_until_stable ──────────────────────────────────────────────────────

def test_warmup_with_ctk_ctv():
    """Both -ctk and -ctv flags must appear in cmd_wup when both params are set."""
    captured = []

    def fake_bench(cmd, metric):
        captured.append(list(cmd))
        return 100.0

    with patch("llama_optimus.core.run_llama_bench_with_csv", side_effect=fake_bench):
        warmup_until_stable(
            llama_bench_path="llama-bench",
            model_path="model.gguf",
            metric="tg",
            ngl=1,
            min_runs=1,
            n_warmup_runs=1,
            n_warmup_tokens=10,
            max_threads=4,
            cache_type_k="q8_0",
            cache_type_v="q4_0",
        )

    assert captured, "run_llama_bench_with_csv was never called"
    cmd = captured[0]
    assert "-ctk" in cmd, f"-ctk not in cmd: {cmd}"
    assert "-ctv" in cmd, f"-ctv not in cmd: {cmd}"
    assert cmd[cmd.index("-ctk") + 1] == "q8_0"
    assert cmd[cmd.index("-ctv") + 1] == "q4_0"


def test_warmup_none():
    """Neither flag should appear in cmd_wup when both params are None."""
    captured = []

    def fake_bench(cmd, metric):
        captured.append(list(cmd))
        return 100.0

    with patch("llama_optimus.core.run_llama_bench_with_csv", side_effect=fake_bench):
        warmup_until_stable(
            llama_bench_path="llama-bench",
            model_path="model.gguf",
            metric="tg",
            ngl=1,
            min_runs=1,
            n_warmup_runs=1,
            n_warmup_tokens=10,
            max_threads=4,
        )

    assert captured, "run_llama_bench_with_csv was never called"
    cmd = captured[0]
    assert "-ctk" not in cmd, f"-ctk found in cmd when it should be absent: {cmd}"
    assert "-ctv" not in cmd, f"-ctv found in cmd when it should be absent: {cmd}"
