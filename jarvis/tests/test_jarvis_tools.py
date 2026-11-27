"""Tests for the JARVIS Open WebUI tools, incl. the four review fixes carried
over from JoshTXWC/JARVIS PR #2. Run: python -m pytest jarvis/tests -q"""
import asyncio
import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def yes():
    async def call(_):
        return True
    return call


def no():
    async def call(_):
        return False
    return call


@pytest.fixture
def coding(tmp_path):
    m = load("jarvis_coding")
    t = m.Tools()
    t.valves.ALLOWED_ROOTS = str(tmp_path)
    t.valves.BACKUP_DIR = str(tmp_path / ".bak")
    return m, t


# 1. code_search checks every file against the secret denylist
def test_code_search_skips_secret_files(coding, tmp_path):
    m, t = coding
    (tmp_path / "app.py").write_text("API = 'hello-needle'\n")
    (tmp_path / ".env").write_text("TOKEN=needle-secret\n")
    (tmp_path / "server.key").write_text("needle-key\n")
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "credentials.json").write_text('{"x":"needle-cred"}')
    (tmp_path / "cfg" / ".env.production").write_text("needle-prod")
    out = t.code_search("needle", str(tmp_path))
    assert "app.py" in out
    for bad in ("needle-secret", "needle-key", "needle-cred", "needle-prod"):
        assert bad not in out


def test_code_search_on_a_secret_file_path_is_denied(coding, tmp_path):
    m, t = coding
    (tmp_path / ".env").write_text("TOKEN=needle\n")
    assert "denied" in t.code_search("needle", str(tmp_path / ".env")).lower()


# 2. shell errors on a missing cwd instead of running somewhere else
def test_shell_missing_cwd_errors_and_runs_nothing(tmp_path):
    m = load("jarvis_shell")
    t = m.Tools()
    marker = tmp_path / "ran.txt"
    called = []

    async def approve(ev):
        called.append(ev)
        return True

    out = asyncio.run(t.run_shell(f"echo x > {marker}", cwd=str(tmp_path / "nope"), __event_call__=approve))
    assert "does not exist" in out and "Nothing was run" in out
    assert not marker.exists() and not called  # never even asked
    with pytest.raises(FileNotFoundError):
        m.resolve_cwd(str(tmp_path / "nope"), "~")


def test_shell_runs_in_given_cwd_after_approval(tmp_path):
    m = load("jarvis_shell")
    t = m.Tools()
    out = asyncio.run(t.run_shell("pwd", cwd=str(tmp_path), __event_call__=yes()))
    assert str(tmp_path) in out and "exit code 0" in out
    assert "Cancelled" in asyncio.run(t.run_shell("pwd", cwd=str(tmp_path), __event_call__=no()))
    assert "Cancelled" in asyncio.run(t.run_shell("pwd", cwd=str(tmp_path)))  # no UI = no run
    assert "DENIED" in asyncio.run(t.run_shell("type .env", cwd=str(tmp_path), __event_call__=yes()))


# 3. git_commit_push never resets an existing branch
def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def test_git_commit_push_keeps_existing_branch_commits(coding, tmp_path):
    m, t = coding
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("1")
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "base")
    _git(repo, "checkout", "-q", "-b", "feature")
    (repo / "b.txt").write_text("2")
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "feature work")
    feature_tip = _git(repo, "rev-parse", "feature")
    _git(repo, "checkout", "-q", "main")
    (repo / "c.txt").write_text("3")
    out = asyncio.run(t.git_commit_push(str(repo), "more", "feature", push=False, __event_call__=yes()))
    assert "Refusing" not in out
    log = _git(repo, "log", "--format=%s", "feature")
    assert "feature work" in log and "more" in log  # old commit survived
    assert _git(repo, "rev-parse", "feature~1") == feature_tip
    assert '"-B"' not in (TOOLS / "jarvis_coding.py").read_text()


def test_git_commit_push_refuses_main(coding, tmp_path):
    m, t = coding
    out = asyncio.run(t.git_commit_push(str(tmp_path), "x", "main", __event_call__=yes()))
    assert "Refusing" in out


# 4. edit_file never truncates large files
def test_edit_file_keeps_files_over_10mb_intact(coding, tmp_path):
    m, t = coding
    p = tmp_path / "big.txt"
    body = ("x" * 1023 + "\n") * (12 * 1024)  # 12 MB
    p.write_text("HEADER\n" + body + "TAIL-MARKER\n")
    out = asyncio.run(t.edit_file(str(p), new="HEADER2", old="HEADER\n".rstrip("\n"), __event_call__=yes()))
    assert out.startswith("Edited"), out
    text = p.read_text()
    assert text.startswith("HEADER2\n") and text.endswith("TAIL-MARKER\n")
    assert len(text) == len("HEADER2\n" + body + "TAIL-MARKER\n")


def test_edit_file_refuses_instead_of_truncating_huge_files(coding, tmp_path, monkeypatch):
    m, t = coding
    monkeypatch.setattr(m, "EDIT_FILE_MAX", 1000)
    p = tmp_path / "huge.txt"
    p.write_text("A" * 5000)
    out = asyncio.run(t.edit_file(str(p), new="B", old="A", replace_all=True, __event_call__=yes()))
    assert "not edited" in out
    assert p.read_text() == "A" * 5000


def test_edit_file_needs_approval_and_makes_backup(coding, tmp_path):
    m, t = coding
    p = tmp_path / "f.py"
    p.write_text("a = 1\n")
    assert "Cancelled" in asyncio.run(t.edit_file(str(p), new="a = 2", old="a = 1", __event_call__=no()))
    assert p.read_text() == "a = 1\n"
    asyncio.run(t.edit_file(str(p), new="a = 2", old="a = 1", __event_call__=yes()))
    assert p.read_text() == "a = 2\n"
    assert list((tmp_path / ".bak").glob("f.py.*.bak"))


def test_files_tool_blocks_secrets_and_outside_roots(tmp_path):
    m = load("jarvis_files")
    t = m.Tools()
    t.valves.ALLOWED_ROOTS = str(tmp_path / "root")
    (tmp_path / "root").mkdir()
    (tmp_path / "root" / ".env").write_text("X=1")
    (tmp_path / "root" / "ok.txt").write_text("hello")
    assert t.read_file(str(tmp_path / "root" / "ok.txt")) == "hello"
    assert "denied" in t.read_file(str(tmp_path / "root" / ".env")).lower()
    assert "outside" in t.read_file(str(tmp_path / "other.txt"))
    out = asyncio.run(t.write_file(str(tmp_path / "root" / "n.txt"), "hi", __event_call__=yes()))
    assert out.startswith("Created")


def test_github_parse_and_barehands_status(tmp_path, monkeypatch):
    gh = load("jarvis_github")
    assert gh.parse_repo("https://github.com/JoshTXWC/JARVIS.git") == ("JoshTXWC", "JARVIS")
    bh = load("jarvis_barehands")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    t = bh.Tools()
    t.valves.PORT = 18794
    assert '"installed": false' in t.barehands_status()
    assert "not installed" in t.barehands_open()
