# test/test_cli_ctk_ctv.py
# Tests for ctk/ctv CLI argument definitions (Step 1: CLI surface only)


def test_help_shows_ctk_ctv():
    """-ctk, --cache-type-k, -ctv, --cache-type-v must appear in the parser's help."""
    import io
    from llama_optimus.cli import build_parser

    parser = build_parser()
    buf = io.StringIO()
    parser.print_help(buf)
    help_text = buf.getvalue()
    assert "-ctk" in help_text, f"'-ctk' not found in help:\n{help_text}"
    assert "--cache-type-k" in help_text, f"'--cache-type-k' not found in help:\n{help_text}"
    assert "-ctv" in help_text, f"'-ctv' not found in help:\n{help_text}"
    assert "--cache-type-v" in help_text, f"'--cache-type-v' not found in help:\n{help_text}"


def test_parse_ctk_ctv_values():
    """Parsing -ctk q8_0 -ctv q4_0 should set args.cache_type_k and args.cache_type_v."""
    from llama_optimus.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["-ctk", "q8_0", "-ctv", "q4_0"])
    assert args.cache_type_k == "q8_0"
    assert args.cache_type_v == "q4_0"


def test_parse_defaults_none():
    """When -ctk/-ctv are not passed, both should default to None."""
    from llama_optimus.cli import build_parser

    parser = build_parser()
    args = parser.parse_args([])
    assert args.cache_type_k is None
    assert args.cache_type_v is None


def test_parse_long_form():
    """Long form --cache-type-k and --cache-type-v should also be accepted."""
    from llama_optimus.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["--cache-type-k", "f16", "--cache-type-v", "q8_0"])
    assert args.cache_type_k == "f16"
    assert args.cache_type_v == "q8_0"
