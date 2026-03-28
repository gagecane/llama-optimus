# test/test_core_estimate_max_ctx.py
# Tests for estimate_max_ctx() — binary search for max context before OOM.

import subprocess
from unittest.mock import patch, call, MagicMock
from llama_optimus.core import estimate_max_ctx


# ── helpers ───────────────────────────────────────────────────────────────────

def _always_pass(*args, **kwargs):
    """subprocess.run side-effect that always succeeds."""
    return MagicMock(returncode=0)


def _always_fail(*args, **kwargs):
    """subprocess.run side-effect that always raises CalledProcessError."""
    raise subprocess.CalledProcessError(1, args[0])


def _fail_above(threshold):
    """Returns a side-effect that succeeds for ctx ≤ threshold, fails above."""
    def side_effect(cmd, *args, **kwargs):
        idx = cmd.index("-c") + 1 if "-c" in cmd else None
        if idx is None:
            return MagicMock(returncode=0)
        ctx = int(cmd[idx])
        if ctx > threshold:
            raise subprocess.CalledProcessError(1, cmd)
        return MagicMock(returncode=0)
    return side_effect


# ── convergence ───────────────────────────────────────────────────────────────

def test_always_pass_returns_max_ctx():
    """When every probe succeeds, estimate_max_ctx returns max_ctx (aligned)."""
    with patch("llama_optimus.core.subprocess.run", side_effect=_always_pass):
        result = estimate_max_ctx("llama-bench", "model.gguf", ngl=10,
                                  min_ctx=512, max_ctx=4096, ctx_step=512)
    assert result == 4096


def test_always_fail_returns_min_ctx():
    """When every probe fails, estimate_max_ctx returns min_ctx."""
    with patch("llama_optimus.core.subprocess.run", side_effect=_always_fail):
        result = estimate_max_ctx("llama-bench", "model.gguf", ngl=10,
                                  min_ctx=512, max_ctx=4096, ctx_step=512)
    assert result == 512


def test_converges_to_threshold():
    """Succeeds for ctx ≤ 32768, fails above → result is 32768."""
    with patch("llama_optimus.core.subprocess.run", side_effect=_fail_above(32768)):
        result = estimate_max_ctx("llama-bench", "model.gguf", ngl=10,
                                  min_ctx=512, max_ctx=65536, ctx_step=512)
    assert result == 32768


def test_result_is_multiple_of_ctx_step():
    """Returned value is always a multiple of ctx_step."""
    with patch("llama_optimus.core.subprocess.run", side_effect=_fail_above(20000)):
        result = estimate_max_ctx("llama-bench", "model.gguf", ngl=10,
                                  min_ctx=512, max_ctx=65536, ctx_step=512)
    assert result % 512 == 0


# ── command construction ──────────────────────────────────────────────────────

def test_cmd_includes_minus_c():
    """-c flag must appear in the probe command."""
    captured = []

    def capture(cmd, *args, **kwargs):
        captured.append(list(cmd))
        return MagicMock(returncode=0)

    with patch("llama_optimus.core.subprocess.run", side_effect=capture):
        estimate_max_ctx("llama-bench", "model.gguf", ngl=10,
                         min_ctx=512, max_ctx=1024, ctx_step=512)

    assert captured, "subprocess.run was never called"
    for cmd in captured:
        assert "-c" in cmd, f"-c not found in cmd: {cmd}"


def test_cmd_includes_n1_r1():
    """-n 1 -r 1 must appear in every probe (minimal workload)."""
    captured = []

    def capture(cmd, *args, **kwargs):
        captured.append(list(cmd))
        return MagicMock(returncode=0)

    with patch("llama_optimus.core.subprocess.run", side_effect=capture):
        estimate_max_ctx("llama-bench", "model.gguf", ngl=10,
                         min_ctx=512, max_ctx=1024, ctx_step=512)

    for cmd in captured:
        assert "-n" in cmd and cmd[cmd.index("-n") + 1] == "1", f"-n 1 not in cmd: {cmd}"
        assert "-r" in cmd and cmd[cmd.index("-r") + 1] == "1", f"-r 1 not in cmd: {cmd}"


def test_ctk_injected_when_set():
    """-ctk flag appears in command when cache_type_k is provided."""
    captured = []

    def capture(cmd, *args, **kwargs):
        captured.append(list(cmd))
        return MagicMock(returncode=0)

    with patch("llama_optimus.core.subprocess.run", side_effect=capture):
        estimate_max_ctx("llama-bench", "model.gguf", ngl=10,
                         min_ctx=512, max_ctx=1024, ctx_step=512,
                         cache_type_k="q8_0")

    assert captured
    cmd = captured[0]
    assert "-ctk" in cmd, f"-ctk not in cmd: {cmd}"
    assert cmd[cmd.index("-ctk") + 1] == "q8_0"


def test_ctv_injected_when_set():
    """-ctv flag appears in command when cache_type_v is provided."""
    captured = []

    def capture(cmd, *args, **kwargs):
        captured.append(list(cmd))
        return MagicMock(returncode=0)

    with patch("llama_optimus.core.subprocess.run", side_effect=capture):
        estimate_max_ctx("llama-bench", "model.gguf", ngl=10,
                         min_ctx=512, max_ctx=1024, ctx_step=512,
                         cache_type_v="q4_0")

    assert captured
    cmd = captured[0]
    assert "-ctv" in cmd, f"-ctv not in cmd: {cmd}"
    assert cmd[cmd.index("-ctv") + 1] == "q4_0"


def test_no_ctk_ctv_when_none():
    """Neither -ctk nor -ctv appears when both params are None."""
    captured = []

    def capture(cmd, *args, **kwargs):
        captured.append(list(cmd))
        return MagicMock(returncode=0)

    with patch("llama_optimus.core.subprocess.run", side_effect=capture):
        estimate_max_ctx("llama-bench", "model.gguf", ngl=10,
                         min_ctx=512, max_ctx=1024, ctx_step=512)

    assert captured
    for cmd in captured:
        assert "-ctk" not in cmd, f"-ctk found when not expected: {cmd}"
        assert "-ctv" not in cmd, f"-ctv found when not expected: {cmd}"


def test_timeout_passed_to_subprocess():
    """subprocess.run is called with timeout=620."""
    captured_kwargs = []

    def capture(cmd, *args, **kwargs):
        captured_kwargs.append(kwargs)
        return MagicMock(returncode=0)

    with patch("llama_optimus.core.subprocess.run", side_effect=capture):
        estimate_max_ctx("llama-bench", "model.gguf", ngl=10,
                         min_ctx=512, max_ctx=1024, ctx_step=512)

    assert captured_kwargs
    assert captured_kwargs[0].get("timeout") == 620
