"""`.env` loading and the fail-fast key check."""

import os

from typer.testing import CliRunner

from orchbench.cli import app
from orchbench.env import load_dotenv, missing_key


def test_load_dotenv_parses_and_never_overrides(tmp_path, monkeypatch):
    monkeypatch.delenv("OB_A", raising=False)
    monkeypatch.delenv("OB_B", raising=False)
    monkeypatch.delenv("OB_EMPTY", raising=False)
    monkeypatch.setenv("OB_SET", "from-shell")
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n"
        "OB_A=plain\n"
        'export OB_B="quoted value"\n'
        "OB_EMPTY=\n"
        "OB_SET=from-file\n"
        "not a pair\n"
    )
    loaded = load_dotenv(env)
    assert sorted(loaded) == ["OB_A", "OB_B"]
    assert os.environ["OB_A"] == "plain"
    assert os.environ["OB_B"] == "quoted value"
    assert "OB_EMPTY" not in os.environ  # placeholder never masks a missing key
    assert os.environ["OB_SET"] == "from-shell"  # exported vars win


def test_load_dotenv_missing_file_is_noop(tmp_path):
    assert load_dotenv(tmp_path / "nope.env") == []


def test_missing_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert missing_key("anthropic") == "ANTHROPIC_API_KEY"
    assert missing_key("mock") is None
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert missing_key("anthropic") is None


def test_real_run_without_key_fails_fast(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env here
    monkeypatch.setattr("orchbench.cli._PROJECT_ROOT", tmp_path)
    out = tmp_path / "t.json"
    result = CliRunner().invoke(app, ["episodes", "--provider", "anthropic", "--out", str(out)])
    assert result.exit_code == 2
    assert "ANTHROPIC_API_KEY is not set" in result.output
    assert not out.exists()  # no wasted run, no misleading results file
