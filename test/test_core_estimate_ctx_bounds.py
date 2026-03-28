# test/test_core_estimate_ctx_bounds.py
# Tests for estimate_ctx_bounds() — context search bound estimation from
# model file size and available system memory.

import subprocess
from unittest.mock import patch, MagicMock
from llama_optimus.core import estimate_ctx_bounds


# ── helpers ───────────────────────────────────────────────────────────────────

_4GiB = 4 * 1024 ** 3
_16GiB = 16 * 1024 ** 3


def _nvidia_smi_result(free_mib=16000):
    """Mock subprocess.run result for nvidia-smi returning free_mib MiB."""
    mock = MagicMock()
    mock.stdout = f"{free_mib}\n"
    mock.returncode = 0
    return mock


# ── fallback behaviour ────────────────────────────────────────────────────────

def test_fallback_when_all_memory_probes_fail():
    """When all memory probes raise, _get_available_memory_bytes uses the 8 GiB
    hardcoded fallback and estimate_ctx_bounds still returns a valid (min, max) tuple."""
    with patch("llama_optimus.core.subprocess.run", side_effect=Exception("no tools")), \
         patch("builtins.open", side_effect=OSError("no /proc")), \
         patch("os.path.getsize", return_value=_4GiB):
        min_ctx, max_ctx = estimate_ctx_bounds("model.gguf")
    assert min_ctx == 512
    assert max_ctx > 0
    assert max_ctx % 512 == 0


def test_fallback_on_model_getsize_error():
    """OSError from os.path.getsize returns (512, 131072) fallback."""
    with patch("os.path.getsize", side_effect=OSError("not found")):
        min_ctx, max_ctx = estimate_ctx_bounds("model.gguf")
    assert min_ctx == 512
    assert max_ctx == 131072


def test_fallback_when_headroom_zero():
    """If available memory ≤ model size + overhead, returns fallback."""
    tiny_available = 100 * 1024 * 1024   # 100 MiB — less than model + overhead
    with patch("llama_optimus.core._get_available_memory_bytes", return_value=tiny_available), \
         patch("os.path.getsize", return_value=_4GiB):
        min_ctx, max_ctx = estimate_ctx_bounds("model.gguf")
    assert min_ctx == 512
    assert max_ctx == 131072


# ── correct values ────────────────────────────────────────────────────────────

def test_nvidia_smi_path_returns_valid_bounds():
    """nvidia-smi 16 GiB free, 4 GiB model → valid (512, max_ctx)."""
    with patch("llama_optimus.core._get_available_memory_bytes", return_value=_16GiB), \
         patch("os.path.getsize", return_value=_4GiB):
        min_ctx, max_ctx = estimate_ctx_bounds("model.gguf")
    assert min_ctx == 512
    assert max_ctx > 0
    assert max_ctx <= 1_048_576


def test_min_ctx_always_512():
    """min_ctx is always 512 regardless of inputs."""
    with patch("llama_optimus.core._get_available_memory_bytes", return_value=_16GiB), \
         patch("os.path.getsize", return_value=_4GiB):
        min_ctx, _ = estimate_ctx_bounds("model.gguf")
    assert min_ctx == 512


def test_max_ctx_is_multiple_of_512():
    """max_ctx must always be a multiple of 512."""
    with patch("llama_optimus.core._get_available_memory_bytes", return_value=_16GiB), \
         patch("os.path.getsize", return_value=_4GiB):
        _, max_ctx = estimate_ctx_bounds("model.gguf")
    assert max_ctx % 512 == 0


def test_max_ctx_capped_at_1m():
    """max_ctx never exceeds 1 048 576 (1 M tokens)."""
    huge_available = 1024 * 1024 ** 3  # 1 TiB
    with patch("llama_optimus.core._get_available_memory_bytes", return_value=huge_available), \
         patch("os.path.getsize", return_value=_4GiB):
        _, max_ctx = estimate_ctx_bounds("model.gguf")
    assert max_ctx <= 1_048_576


# ── KV type scaling ───────────────────────────────────────────────────────────

def test_q4_0_gives_larger_max_ctx_than_f16():
    """q4_0 KV uses ~0.28× the memory of f16, so max_ctx should be ~3.5× larger."""
    with patch("llama_optimus.core._get_available_memory_bytes", return_value=_16GiB), \
         patch("os.path.getsize", return_value=_4GiB):
        _, max_f16  = estimate_ctx_bounds("model.gguf", cache_type_k=None,    cache_type_v=None)
        _, max_q4_0 = estimate_ctx_bounds("model.gguf", cache_type_k="q4_0", cache_type_v="q4_0")
    assert max_q4_0 > max_f16


def test_q8_0_gives_larger_max_ctx_than_f16():
    """q8_0 KV uses ~0.53× the memory of f16, so max_ctx should be ~2× larger."""
    with patch("llama_optimus.core._get_available_memory_bytes", return_value=_16GiB), \
         patch("os.path.getsize", return_value=_4GiB):
        _, max_f16  = estimate_ctx_bounds("model.gguf", cache_type_k=None,    cache_type_v=None)
        _, max_q8_0 = estimate_ctx_bounds("model.gguf", cache_type_k="q8_0", cache_type_v="q8_0")
    assert max_q8_0 > max_f16
