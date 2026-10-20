"""Isolated runner files shared by support-script tests."""

import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    for key in (
        "GITHUB_ENV",
        "GITHUB_OUTPUT",
        "GITHUB_STATE",
        "GITHUB_PATH",
        "GITHUB_STEP_SUMMARY",
        "GITHUB_ARTIFACTS",
        "GITHUB_ARTIFACTS_LIST",
    ):
        path = tmp_path / key
        path.touch()
        monkeypatch.setenv(key, str(path))
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"action": "test"}), encoding="utf-8")
    for key, value in {
        "GITHUB_WORKSPACE": str(root),
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_PATH": str(event),
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_ACTOR": "fixture",
        "INPUT_SHOWCASE_TEXT": "  explicit fixture  ",
        "INPUT_SHOWCASE_FLAG": "true",
        "INPUT_SHOWCASE_LINES": "first\n世界",
    }.items():
        monkeypatch.setenv(key, value)
    for key in (
        "INPUT_SHOWCASE_MISSING",
        "GH_UTILS_INTEGRATION_VALUE",
        "ARTIFACTS_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)
    return root


def propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.file_command_helpers import parse_records

    output = parse_records(Path(os.environ["GITHUB_OUTPUT"]).read_bytes())
    for key, name in (
        ("OUTPUT_VALUE", "multiline"),
        ("OUTPUT_NUMBER", "number"),
        ("OUTPUT_EMPTY", "empty"),
        ("OUTPUT_UNICODE", "unicode"),
        ("OUTPUT_JSON", "json"),
        ("ARTIFACTS_ENABLED", "enabled"),
    ):
        monkeypatch.setenv(key, output.get(name, ""))
    for key, value in parse_records(
        Path(os.environ["GITHUB_ENV"]).read_bytes()
    ).items():
        monkeypatch.setenv(key, value)
    entries = Path(os.environ["GITHUB_PATH"]).read_text(encoding="utf-8").splitlines()
    monkeypatch.setenv(
        "PATH", os.pathsep.join([*reversed(entries), os.environ["PATH"]])
    )
