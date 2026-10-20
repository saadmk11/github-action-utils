"""Release ref and published-release validation."""

import json
from pathlib import Path
from unittest import mock

import pytest

from scripts import check_distribution as dist

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "ref_type,tag,resolved,draft,release_tag",
    [
        ("branch", "v2.0.0", "commit", False, "v2.0.0"),
        ("tag", "vv2.0.0", "commit", False, "vv2.0.0"),
        ("tag", "v2.0.0", "moved", False, "v2.0.0"),
        ("tag", "v2.0.0", "commit", True, "v2.0.0"),
        ("tag", "v2.0.0", "commit", False, "wrong"),
    ],
)
def test_release_gate_rejects_wrong_refs_and_drafts(
    monkeypatch: pytest.MonkeyPatch,
    ref_type: str,
    tag: str,
    resolved: str,
    draft: bool,
    release_tag: str,
) -> None:
    monkeypatch.setenv("GITHUB_REF_TYPE", ref_type)
    monkeypatch.setenv("GITHUB_REF_NAME", tag)
    monkeypatch.setenv("GITHUB_SHA", "commit")
    with mock.patch.object(
        dist,
        "run",
        side_effect=[resolved, json.dumps({"isDraft": draft, "tagName": release_tag})],
    ):
        with pytest.raises(ValueError):
            dist.validate_github_release(ROOT)


def test_release_gate_outputs_exact_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "output"
    for name, value in {
        "GITHUB_REF_TYPE": "tag",
        "GITHUB_REF_NAME": "v2.0.0",
        "GITHUB_SHA": "commit",
        "GITHUB_OUTPUT": str(output),
    }.items():
        monkeypatch.setenv(name, value)
    with mock.patch.object(
        dist, "run", side_effect=["commit\n", '{"isDraft":false,"tagName":"v2.0.0"}']
    ):
        dist.main(["--github-release"])
    assert output.read_text() == "version=2.0.0\n"


def test_release_checks_survive_optimized_python() -> None:
    import os
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-O",
            str(ROOT / "scripts/check_distribution.py"),
            "--github-release",
        ],
        env=dict(os.environ, GITHUB_REF_TYPE="branch"),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "not a branch" in result.stderr
