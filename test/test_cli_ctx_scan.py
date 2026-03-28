# test/test_cli_ctx_scan.py
# Tests for --ctx-scan CLI flag parsing and main() dispatch.

from unittest.mock import patch, MagicMock
from llama_optimus.cli import build_parser


# ── argument parsing ──────────────────────────────────────────────────────────

def test_ctx_scan_default_false():
    """--ctx-scan defaults to False."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.ctx_scan is False


def test_ctx_scan_flag_sets_true():
    """--ctx-scan sets ctx_scan to True."""
    parser = build_parser()
    args = parser.parse_args(["--ctx-scan"])
    assert args.ctx_scan is True


def test_ctx_min_default():
    """--ctx-min defaults to 512."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.ctx_min == 512


def test_ctx_min_custom():
    """--ctx-min 1024 is parsed as integer 1024."""
    parser = build_parser()
    args = parser.parse_args(["--ctx-min", "1024"])
    assert args.ctx_min == 1024


def test_ctx_max_default_none():
    """--ctx-max defaults to None (auto-estimate)."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.ctx_max is None


def test_ctx_max_custom():
    """--ctx-max 65536 is parsed as integer 65536."""
    parser = build_parser()
    args = parser.parse_args(["--ctx-max", "65536"])
    assert args.ctx_max == 65536


def test_ctx_scan_types_default_none():
    """--ctx-scan-types defaults to None."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.ctx_scan_types is None


def test_ctx_scan_types_parsed_as_string():
    """--ctx-scan-types is stored as a raw string for later splitting."""
    parser = build_parser()
    args = parser.parse_args(["--ctx-scan-types", "f16,q8_0,q4_0"])
    assert args.ctx_scan_types == "f16,q8_0,q4_0"


def test_ctx_scan_help_visible():
    """--ctx-scan and related flags appear in help text."""
    import io
    parser = build_parser()
    buf = io.StringIO()
    parser.print_help(buf)
    help_text = buf.getvalue()
    assert "--ctx-scan" in help_text
    assert "--ctx-min" in help_text
    assert "--ctx-max" in help_text
    assert "--ctx-scan-types" in help_text


# ── main() dispatch ───────────────────────────────────────────────────────────

def _base_patches():
    """Return a dict of patch targets that prevent I/O in main()."""
    return {
        "llama_optimus.cli.Path.is_file":          MagicMock(return_value=True),
        "llama_optimus.cli.os.path.isfile":        MagicMock(return_value=True),
        "llama_optimus.cli.estimate_max_ngl":      MagicMock(return_value=10),
        "llama_optimus.cli.warmup_until_stable":   MagicMock(),
        "llama_optimus.cli.run_optimization":      MagicMock(),
        "llama_optimus.cli.run_ctx_scan":          MagicMock(),
        "llama_optimus.cli.estimate_ctx_bounds":   MagicMock(return_value=(512, 65536)),
    }


def _run_main(argv):
    """Run cli.main() with the given argv list using _base_patches()."""
    from llama_optimus.cli import main
    patches = _base_patches()
    with patch("sys.argv", ["llama-optimus"] + argv):
        with patch.multiple("llama_optimus.cli", **{k.split(".")[-1]: v
                                                    for k, v in patches.items()}):
            try:
                main()
            except SystemExit:
                pass
    return patches


def test_ctx_scan_calls_run_ctx_scan():
    """When --ctx-scan is set, run_ctx_scan must be called."""
    mock_run_ctx_scan    = MagicMock()
    mock_run_optimization = MagicMock()
    mock_estimate_max_ngl = MagicMock(return_value=10)
    mock_estimate_ctx_bounds = MagicMock(return_value=(512, 65536))

    argv = ["--llama-bin", "/fake/bin", "--model", "/fake/model.gguf",
            "--ctx-scan", "--no-warmup"]

    with patch("sys.argv", ["llama-optimus"] + argv), \
         patch("llama_optimus.cli.Path.is_file", return_value=True), \
         patch("llama_optimus.cli.os.path.isfile", return_value=True), \
         patch("llama_optimus.cli.estimate_max_ngl", mock_estimate_max_ngl), \
         patch("llama_optimus.cli.warmup_until_stable", MagicMock()), \
         patch("llama_optimus.cli.run_ctx_scan", mock_run_ctx_scan), \
         patch("llama_optimus.cli.run_optimization", mock_run_optimization), \
         patch("llama_optimus.cli.estimate_ctx_bounds", mock_estimate_ctx_bounds):
        try:
            from llama_optimus.cli import main
            main()
        except SystemExit:
            pass

    assert mock_run_ctx_scan.called, "run_ctx_scan was not called"
    assert not mock_run_optimization.called, "run_optimization should not be called with --ctx-scan"


def test_no_ctx_scan_calls_run_optimization():
    """When --ctx-scan is not set, run_optimization must be called."""
    mock_run_ctx_scan     = MagicMock()
    mock_run_optimization = MagicMock()
    mock_estimate_max_ngl = MagicMock(return_value=10)

    argv = ["--llama-bin", "/fake/bin", "--model", "/fake/model.gguf",
            "--no-warmup", "--trials", "1"]

    with patch("sys.argv", ["llama-optimus"] + argv), \
         patch("llama_optimus.cli.Path.is_file", return_value=True), \
         patch("llama_optimus.cli.os.path.isfile", return_value=True), \
         patch("llama_optimus.cli.estimate_max_ngl", mock_estimate_max_ngl), \
         patch("llama_optimus.cli.warmup_until_stable", MagicMock()), \
         patch("llama_optimus.cli.run_ctx_scan", mock_run_ctx_scan), \
         patch("llama_optimus.cli.run_optimization", mock_run_optimization), \
         patch("llama_optimus.cli.estimate_ctx_bounds", MagicMock(return_value=(512, 65536))):
        try:
            from llama_optimus.cli import main
            main()
        except SystemExit:
            pass

    assert mock_run_optimization.called, "run_optimization was not called"
    assert not mock_run_ctx_scan.called, "run_ctx_scan should not be called without --ctx-scan"


def test_ctx_max_none_triggers_estimate_ctx_bounds():
    """When --ctx-scan is set and --ctx-max is absent, estimate_ctx_bounds is called."""
    mock_estimate_ctx_bounds = MagicMock(return_value=(512, 65536))
    mock_run_ctx_scan        = MagicMock()

    argv = ["--llama-bin", "/fake/bin", "--model", "/fake/model.gguf",
            "--ctx-scan", "--no-warmup"]

    with patch("sys.argv", ["llama-optimus"] + argv), \
         patch("llama_optimus.cli.Path.is_file", return_value=True), \
         patch("llama_optimus.cli.os.path.isfile", return_value=True), \
         patch("llama_optimus.cli.estimate_max_ngl", return_value=10), \
         patch("llama_optimus.cli.warmup_until_stable", MagicMock()), \
         patch("llama_optimus.cli.run_ctx_scan", mock_run_ctx_scan), \
         patch("llama_optimus.cli.run_optimization", MagicMock()), \
         patch("llama_optimus.cli.estimate_ctx_bounds", mock_estimate_ctx_bounds):
        try:
            from llama_optimus.cli import main
            main()
        except SystemExit:
            pass

    assert mock_estimate_ctx_bounds.called, "estimate_ctx_bounds should be called when --ctx-max is absent"


def test_ctx_max_explicit_skips_estimate_ctx_bounds():
    """When --ctx-max is explicitly set, estimate_ctx_bounds should NOT be called."""
    mock_estimate_ctx_bounds = MagicMock(return_value=(512, 65536))
    mock_run_ctx_scan        = MagicMock()

    argv = ["--llama-bin", "/fake/bin", "--model", "/fake/model.gguf",
            "--ctx-scan", "--ctx-max", "65536", "--no-warmup"]

    with patch("sys.argv", ["llama-optimus"] + argv), \
         patch("llama_optimus.cli.Path.is_file", return_value=True), \
         patch("llama_optimus.cli.os.path.isfile", return_value=True), \
         patch("llama_optimus.cli.estimate_max_ngl", return_value=10), \
         patch("llama_optimus.cli.warmup_until_stable", MagicMock()), \
         patch("llama_optimus.cli.run_ctx_scan", mock_run_ctx_scan), \
         patch("llama_optimus.cli.run_optimization", MagicMock()), \
         patch("llama_optimus.cli.estimate_ctx_bounds", mock_estimate_ctx_bounds):
        try:
            from llama_optimus.cli import main
            main()
        except SystemExit:
            pass

    assert not mock_estimate_ctx_bounds.called, "estimate_ctx_bounds should NOT be called when --ctx-max is explicit"
