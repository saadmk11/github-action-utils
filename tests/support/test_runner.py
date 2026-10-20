"""Artifact fixtures and action main/post subprocesses."""

import os
from pathlib import Path

import pytest

from tests.file_command_helpers import parse_records

STATE_SCRIPT = (
    Path(__file__).resolve().parents[2] / ".github/actions/check-state/check_state.py"
)


def test_javascript_main_post_wrappers(
    runner: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Launch each action hook in a separate process."""
    import subprocess
    import sys

    monkeypatch.setenv(
        "PATH", str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    )
    action = STATE_SCRIPT.parent
    main = subprocess.run(
        ["node", str(action / "main.cjs")], capture_output=True, text=True
    )
    assert main.returncode == 0, main.stdout + main.stderr
    state = parse_records(Path(os.environ["GITHUB_STATE"]).read_bytes())
    monkeypatch.setenv("STATE_from_main", state["from_main"])
    post = subprocess.run(
        ["node", str(action / "post.cjs")], capture_output=True, text=True
    )
    assert post.returncode == 0 and "exact main state" in post.stdout
    monkeypatch.setenv("STATE_from_main", "wrong state")
    failed = subprocess.run(
        ["node", str(action / "post.cjs")], capture_output=True, text=True
    )
    assert failed.returncode == 1
