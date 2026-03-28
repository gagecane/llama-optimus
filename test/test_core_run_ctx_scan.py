# test/test_core_run_ctx_scan.py
# Tests for run_ctx_scan() and _print_ctx_scan_table().

import io
import sys
from unittest.mock import patch, MagicMock, call
from llama_optimus.core import run_ctx_scan


# ── call count / dispatch ─────────────────────────────────────────────────────

def test_single_pair_calls_estimate_once():
    """run_ctx_scan with one KV pair calls estimate_max_ctx exactly once."""
    with patch("llama_optimus.core.estimate_max_ctx", return_value=32768) as mock_est:
        run_ctx_scan("llama-bench", "model.gguf", ngl=10,
                     min_ctx=512, max_ctx=65536,
                     kv_type_pairs=[(None, None)])
    assert mock_est.call_count == 1


def test_three_pairs_calls_estimate_three_times():
    """run_ctx_scan with three pairs calls estimate_max_ctx three times."""
    pairs = [(None, None), ("q8_0", "q8_0"), ("q4_0", "q4_0")]
    with patch("llama_optimus.core.estimate_max_ctx", return_value=32768) as mock_est:
        run_ctx_scan("llama-bench", "model.gguf", ngl=10,
                     min_ctx=512, max_ctx=131072,
                     kv_type_pairs=pairs)
    assert mock_est.call_count == 3


# ── return value ──────────────────────────────────────────────────────────────

def test_returns_dict_with_correct_keys_and_values():
    """Result dict maps (ctk, ctv) tuples to the values returned by estimate_max_ctx."""
    pairs = [(None, None), ("q8_0", "q8_0"), ("q4_0", "q4_0")]
    return_vals = [32768, 65536, 114688]

    with patch("llama_optimus.core.estimate_max_ctx", side_effect=return_vals):
        result = run_ctx_scan("llama-bench", "model.gguf", ngl=10,
                              min_ctx=512, max_ctx=131072,
                              kv_type_pairs=pairs)

    assert result[(None, None)]      == 32768
    assert result[("q8_0", "q8_0")] == 65536
    assert result[("q4_0", "q4_0")] == 114688


# ── table output ──────────────────────────────────────────────────────────────

def test_table_header_printed(capsys):
    """stdout contains the scan results header."""
    with patch("llama_optimus.core.estimate_max_ctx", return_value=32768):
        run_ctx_scan("llama-bench", "model.gguf", ngl=10,
                     min_ctx=512, max_ctx=65536,
                     kv_type_pairs=[(None, None)])
    captured = capsys.readouterr().out
    assert "Context length scan results" in captured


def test_table_contains_kv_type_labels(capsys):
    """stdout contains the KV type labels for every scanned pair."""
    pairs = [(None, None), ("q8_0", "q8_0")]
    with patch("llama_optimus.core.estimate_max_ctx", return_value=32768):
        run_ctx_scan("llama-bench", "model.gguf", ngl=10,
                     min_ctx=512, max_ctx=65536,
                     kv_type_pairs=pairs)
    captured = capsys.readouterr().out
    assert "f16" in captured
    assert "q8_0" in captured


def test_table_contains_token_counts(capsys):
    """stdout contains the max-context token values."""
    pairs = [(None, None), ("q8_0", "q8_0")]
    with patch("llama_optimus.core.estimate_max_ctx", side_effect=[32768, 65536]):
        run_ctx_scan("llama-bench", "model.gguf", ngl=10,
                     min_ctx=512, max_ctx=65536,
                     kv_type_pairs=pairs)
    captured = capsys.readouterr().out
    assert "32" in captured   # 32768 or "32 K" style
    assert "65" in captured   # 65536 or "64 K" style
