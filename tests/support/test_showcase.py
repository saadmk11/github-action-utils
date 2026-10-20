"""Showcase execution, failure reports, and configuration cleanup."""

import json
from pathlib import Path
from unittest import mock

import pytest

import github_action_utils as gha
from github_action_utils._serialization import JSONValue
from scripts import showcase
from tests.support.conftest import propagate


def test_full_showcase(runner: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = runner / "reports"
    showcase.main(["summary", "--directory", str(directory)])
    showcase.main(["produce", "--directory", str(directory)])
    report = json.loads((directory / "results-produce.json").read_text())
    assert {result["status"] for result in report["results"]} == {
        "PASS",
        "MANUAL",
        "SKIP",
    }
    assert "Manual review" in (directory / "report-produce.md").read_text()
    propagate(monkeypatch)
    showcase.main(["verify", "--directory", str(directory)])
    verified = json.loads((directory / "results-verify.json").read_text())["results"]
    assert {row["name"] for row in verified} == {
        case.name for case in showcase.CASES if case.phase == "verify"
    }
    assert all(row["status"] != "FAIL" for row in verified)
    showcase.main(["report", "--directory", str(directory)])
    final = json.loads((directory / "results-final.json").read_text())["results"]
    assert {row["name"] for row in final} == {case.name for case in showcase.CASES}
    assert len(final) == len(showcase.CASES)
    assert all(row["status"] != "FAIL" for row in final)


def test_failure_reports(runner: Path) -> None:
    def broken() -> showcase.Observation:
        raise ValueError("fixture failure")

    case = showcase.Case("failing", "produce", (), "must pass", "logs", broken)
    with mock.patch.object(showcase, "CASES", (case,)):
        with pytest.raises(SystemExit, match="1"):
            showcase.main(["produce", "--directory", str(runner)])
    result = json.loads((runner / "results-produce.json").read_text())["results"][0]
    assert result["status"] == "FAIL" and "fixture failure" in result["actual"]


def test_report_survives_summary_failure(
    runner: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_SHA", "caller-commit")
    result = showcase.Result(
        "a|b", (), "one\ntwo", "logs", showcase.Status.FAIL, "observed"
    )
    with mock.patch.object(
        gha, "append_job_summary", side_effect=OSError("summary unavailable")
    ):
        with pytest.raises(OSError):
            showcase.write_reports(runner, (result,), "failed")
    assert "a\\|b" in (runner / "report-failed.md").read_text()
    assert (
        json.loads((runner / "results-failed.json").read_text())["context"]["commit"]
        == "caller-commit"
    )


def test_missing_phase_is_failure(runner: Path) -> None:
    with pytest.raises(SystemExit, match="1"):
        showcase.main(["report", "--directory", str(runner)])
    assert "Missing" in (runner / "report-final.md").read_text()


def test_console_restores_configuration_after_failure(runner: Path) -> None:
    with (
        mock.patch.object(gha, "COMMANDS_USE_SUBPROCESS", True),
        mock.patch.object(gha, "echo", side_effect=OSError("broken stdout")),
    ):
        with pytest.raises(OSError):
            showcase.console()
        assert gha.COMMANDS_USE_SUBPROCESS is True


def test_corrupt_phase_still_writes_a_failed_final_report(runner: Path) -> None:
    (runner / "results-produce.json").write_text("not JSON")
    with pytest.raises(SystemExit, match="1"):
        showcase.main(["report", "--directory", str(runner)])
    assert "Invalid produce report" in (runner / "report-final.md").read_text()


@pytest.mark.parametrize(
    "records",
    [
        [],
        [
            {
                "name": "unknown",
                "apis": [],
                "expected": "e",
                "inspect": "i",
                "status": "PASS",
                "actual": "a",
            }
        ],
    ],
)
def test_unknown_or_missing_report_cases_fail(runner: Path, records: JSONValue) -> None:
    (runner / "results-produce.json").write_text(json.dumps({"results": records}))
    results = showcase.read_reports(runner)
    assert len(results) == len(showcase.CASES)
    assert all(result.status is showcase.Status.FAIL for result in results)
