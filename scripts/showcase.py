"""Exercise the public API on GitHub Actions and write feature reports."""

import argparse
import json
import os
import platform
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from importlib.metadata import version
from pathlib import Path
from typing import cast

import github_action_utils as gha
from github_action_utils._serialization import JSONValue
from scripts import check_artifacts, check_runner


class Status(StrEnum):
    """Automated, manual, and unavailable showcase outcomes."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    MANUAL = "MANUAL"


Observation = tuple[Status, str]


@dataclass(frozen=True, slots=True)
class Case:
    """A feature demonstration and its expected result."""

    name: str
    phase: str
    apis: tuple[str, ...]
    expected: str
    inspect: str
    run: Callable[[], Observation]


@dataclass(frozen=True, slots=True)
class Result:
    """A feature result written to JSON and Markdown."""

    name: str
    apis: tuple[str, ...]
    expected: str
    inspect: str
    status: Status
    actual: str


def console() -> Observation:
    """Show both stdout modes and the assignable public configuration flag."""
    original = gha.COMMANDS_USE_SUBPROCESS
    try:
        for enabled in (False, True):
            gha.COMMANDS_USE_SUBPROCESS = enabled
            gha.echo(f"Console mode subprocess={enabled}: বাংলা 世界, literal %0A")
            gha.debug("Debug visibility requires runner debug logging")
            gha.set_command_echo(True)
            gha.set_command_echo(False)
    finally:
        gha.COMMANDS_USE_SUBPROCESS = original
    return (
        Status.MANUAL,
        "Both modes emitted; inspect Unicode, literal percent text, and debug visibility",
    )


def annotations() -> Observation:
    """Emit intentional demonstration annotations with all position properties."""
    for emit in (gha.notice, gha.warning, gha.error):
        emit(
            "Intentional showcase annotation: 世界 100% %0A",
            title="Helper showcase",
            file="README.md",
            line=1,
            end_line=1,
            col=1,
            end_column=3,
        )
    return (
        Status.MANUAL,
        "Three intentional annotations emitted; no process failure requested",
    )


def failure() -> Observation:
    """Check an expected failure in an isolated child and assert cleanup."""
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import github_action_utils as g\nwith g.group('expected failure cleanup'):\n g.fail('Intentional child failure')",
        ],
        capture_output=True,
        text=True,
    )
    assert child.returncode == 1, child.stdout + child.stderr
    assert "::error" in child.stdout and child.stdout.rstrip().endswith("::endgroup::")
    return (Status.PASS, "Child exited 1 after error annotation and group cleanup")


def commands() -> Observation:
    """Demonstrate groups, masking, command suspension, and problem matchers."""
    gha.start_group("Manual group")
    gha.echo("Inside manual group")
    gha.end_group()
    try:
        with gha.group("Exception cleanup group"):
            raise ValueError("expected cleanup fixture")
    except ValueError:
        pass
    token = gha.begin_stop_commands()
    gha.echo("::warning::PLAIN WHILE COMMANDS ARE SUSPENDED")
    gha.end_stop_commands(token)
    check_runner.check_commands()
    return (
        Status.MANUAL,
        "Groups, exception cleanup, stop/resume, dummy masking, owner/path matcher removal emitted",
    )


def inputs() -> Observation:
    """Use explicit INPUT fixtures that work for fork PRs and manual runs."""
    assert gha.get_user_input("showcase text") == "  explicit fixture  "
    assert gha.get_boolean_input("showcase flag") is True
    assert gha.get_multiline_input("showcase lines") == ["first", "世界"]
    assert gha.get_user_input("showcase missing") is None
    try:
        gha.get_user_input("showcase missing", required=True)
    except ValueError:
        return (
            Status.PASS,
            "Raw, boolean, multiline, optional, and required missing inputs checked",
        )
    raise AssertionError("Required missing input unexpectedly succeeded")


def environment() -> Observation:
    """Inspect allowlisted event/environment values and live read-only properties."""
    assert gha.is_github_action()
    assert isinstance(gha.vars, gha.WorkflowVariables)
    assert isinstance(gha.vars.github, gha.GitHubVariables)
    assert isinstance(gha.vars.runner, gha.RunnerVariables)
    event = gha.event_payload()
    assert event is gha.event_payload()
    gha.event_payload.cache_clear()
    assert gha.event_payload() == event
    action = event.get("action")
    event_action = action if isinstance(action, str) else "(none)"
    original = os.environ.get("GITHUB_ACTOR")
    try:
        os.environ["GITHUB_ACTOR"] = "showcase-live-fixture"
        assert gha.vars.github.actor == "showcase-live-fixture"
        try:
            gha.vars.github.actor = "replacement"  # type: ignore[misc]
        except AttributeError:
            pass
        else:
            raise AssertionError("Environment view was writable")
    finally:
        if original is None:
            del os.environ["GITHUB_ACTOR"]
        else:
            os.environ["GITHUB_ACTOR"] = original
    return (
        Status.PASS,
        f"Actions detected; event={os.environ.get('GITHUB_EVENT_NAME')}; action={event_action}; runner OS={gha.vars.runner.os}; cache and live/read-only views checked",
    )


def produce() -> Observation:
    """Queue exact values and PATH fixtures for a subsequent workflow step."""
    check_runner.main(["write"])
    return (
        Status.PASS,
        "Pending output/env/PATH records written; process lookup and pending environment verified",
    )


def verify() -> Observation:
    """Assert runner-propagated outputs, environment, executable lookup, and order."""
    check_runner.main(["verify"])
    return (
        Status.PASS,
        "Empty/scalar/JSON/Unicode/multiline outputs exact; both executables resolved; last PATH entry first",
    )


def summaries() -> Observation:
    """Demonstrate replacement/deletion on a fixture without erasing the report."""
    original = os.environ.get("GITHUB_STEP_SUMMARY")
    fixture = Path(os.environ["RUNNER_TEMP"]) / "showcase-summary-fixture.md"
    try:
        os.environ["GITHUB_STEP_SUMMARY"] = str(fixture)
        gha.append_job_summary("append 世界 %0A")
        gha.overwrite_job_summary("replace 世界 %0A")
        assert fixture.read_text(encoding="utf-8") == "replace 世界 %0A\n"
        gha.remove_job_summary()
        assert not fixture.exists()
    finally:
        if original is None:
            del os.environ["GITHUB_STEP_SUMMARY"]
        else:
            os.environ["GITHUB_STEP_SUMMARY"] = original
    return (
        Status.PASS,
        "Fixture append/overwrite/remove checked; final report has a separate summary",
    )


def artifacts_produce() -> Observation:
    """Skip unavailable runner support and queue identities only after probing it."""
    available = check_artifacts.probe()
    gha.set_output("enabled", str(available).lower())
    if not available:
        return (
            Status.SKIP,
            "Runner did not provide populated versioned artifact metadata",
        )
    check_artifacts.write()
    return (
        Status.PASS,
        "Version-1 metadata parsed; file and OCI declarations queued for the next step",
    )


def artifacts_verify() -> Observation:
    """Verify later-step digests only when the producer established runner support."""
    if os.environ.get("ARTIFACTS_ENABLED") != "true":
        return (Status.SKIP, "Conditional artifact integration unavailable in producer")
    check_artifacts.verify()
    return (
        Status.PASS,
        "File/OCI names, kinds, and digests verified from runner metadata",
    )


def state() -> Observation:
    """Describe the separate action main/post state check."""
    return (
        Status.MANUAL,
        "The separate check-state action saves in main and asserts exact get_state in post; a failed post hook fails this job",
    )


CASES = (
    Case(
        "console",
        "produce",
        ("echo", "debug", "set_command_echo", "COMMANDS_USE_SUBPROCESS"),
        "Both console modes, Unicode and literal percent text",
        "Console log group; enable runner debug for debug lines",
        console,
    ),
    Case(
        "annotations",
        "produce",
        ("notice", "warning", "error"),
        "Three titled annotations with file/line/column properties",
        "Run annotations and logs",
        annotations,
    ),
    Case(
        "failure",
        "produce",
        ("fail",),
        "Child exits 1 with group cleanup",
        "Structured result",
        failure,
    ),
    Case(
        "commands",
        "produce",
        (
            "start_group",
            "end_group",
            "group",
            "begin_stop_commands",
            "end_stop_commands",
            "stop_commands",
            "add_mask",
            "add_problem_matcher",
            "remove_problem_matcher",
        ),
        "Groups collapse; suspended text stays plain; dummy masks; matcher removed",
        "Groups and matcher/masking log lines",
        commands,
    ),
    Case(
        "inputs",
        "produce",
        ("get_user_input", "get_boolean_input", "get_multiline_input"),
        "Explicit fixtures and required/missing handling",
        "Structured result",
        inputs,
    ),
    Case(
        "environment",
        "produce",
        (
            "event_payload",
            "is_github_action",
            "vars",
            "WorkflowVariables",
            "GitHubVariables",
            "RunnerVariables",
        ),
        "Cached event and live read-only environment properties",
        "Allowlisted event/runner observations",
        environment,
    ),
    Case(
        "file commands",
        "produce",
        (
            "set_output",
            "set_env",
            "get_env",
            "get_workflow_environment_variables",
            "add_system_path",
        ),
        "Pending producer records exact",
        "Producer and subsequent verifier steps",
        produce,
    ),
    Case(
        "cross-step values",
        "verify",
        (),
        "Runner propagates exact values and ordered executable paths",
        "Verifier step",
        verify,
    ),
    Case(
        "summary fixtures",
        "summary",
        ("append_job_summary", "overwrite_job_summary", "remove_job_summary"),
        "Append, replace, remove on a separate fixture",
        "Structured result; final Markdown rendering is manual",
        summaries,
    ),
    Case(
        "artifact declarations",
        "produce",
        (
            "declare_file_artifact",
            "declare_oci_artifact",
            "get_workflow_artifacts",
            "ArtifactSubject",
        ),
        "Versioned feature detection and correctly framed declarations",
        "Producer; SKIP if feature unavailable",
        artifacts_produce,
    ),
    Case(
        "artifact metadata",
        "verify",
        (),
        "Subsequent metadata contains exact file/OCI digests",
        "Verifier; SKIP if feature unavailable",
        artifacts_verify,
    ),
    Case(
        "action state",
        "produce",
        ("save_state", "get_state"),
        "Exact main/post state propagation",
        "Check-state main and post hook logs",
        state,
    ),
)


def write_reports(directory: Path, results: Sequence[Result], phase: str) -> None:
    """Save reports, then append them to the job summary."""
    directory.mkdir(parents=True, exist_ok=True)
    context = {
        "python": platform.python_version(),
        "os": platform.system(),
        "package": version("github-action-utils"),
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "run": f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}",
    }
    (directory / f"results-{phase}.json").write_text(
        json.dumps(
            {"context": context, "results": [asdict(result) for result in results]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Feature showcase",
        "",
        *(f"- {key}: {value}" for key, value in context.items()),
        "",
        "| Feature | Result | Expected | Observation | Inspect |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            "| "
            + " | ".join(
                text.replace("|", "\\|").replace("\n", " ")
                for text in (
                    result.name,
                    result.status.value,
                    result.expected,
                    result.actual,
                    result.inspect,
                )
            )
            + " |"
        )
    lines.extend(
        (
            "",
            "Manual review: groups, annotations, dummy masking, matcher registration/removal, debug visibility, state post-hook logs, and Markdown rendering. MANUAL needs visual inspection; SKIP means runner support was unavailable.",
            "",
        )
    )
    markdown = "\n".join(lines)
    (directory / f"report-{phase}.md").write_text(markdown, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        gha.append_job_summary(markdown)


def parse_result(record: JSONValue) -> Result:
    """Parse and validate a saved result."""
    if not isinstance(record, dict):
        raise ValueError("Showcase result must be an object")
    fields = []
    for key in ("name", "expected", "inspect", "status", "actual"):
        value = record.get(key)
        if not isinstance(value, str):
            raise ValueError("Showcase result text field is missing or invalid")
        fields.append(value)
    apis = record.get("apis")
    if not isinstance(apis, list):
        raise ValueError("Showcase result APIs must be an array")
    names = []
    for value in apis:
        if not isinstance(value, str):
            raise ValueError("Showcase API names must be strings")
        names.append(value)
    return Result(
        fields[0], tuple(names), fields[1], fields[2], Status(fields[3]), fields[4]
    )


def read_reports(directory: Path) -> tuple[Result, ...]:
    """Combine every phase, recording omitted cases as failures in the final table."""
    results: list[Result] = []
    for phase in ("summary", "produce", "verify"):
        path = directory / f"results-{phase}.json"
        if not path.exists():
            continue
        try:
            data = cast(JSONValue, json.loads(path.read_text(encoding="utf-8")))
            if not isinstance(data, dict) or not isinstance(
                records := data.get("results"), list
            ):
                raise ValueError("Showcase report must contain a results array")
            phase_results = tuple(parse_result(record) for record in records)
            expected = {case.name for case in CASES if case.phase == phase}
            if (
                len(phase_results) != len(expected)
                or {result.name for result in phase_results} != expected
            ):
                raise ValueError(
                    "Showcase report has missing, duplicate, or unknown cases"
                )
            results.extend(phase_results)
        except (OSError, ValueError) as error:
            results.extend(
                Result(
                    case.name,
                    case.apis,
                    case.expected,
                    case.inspect,
                    Status.FAIL,
                    f"Invalid {phase} report: {type(error).__name__}",
                )
                for case in CASES
                if case.phase == phase
            )
    completed = {result.name for result in results}
    results.extend(
        Result(
            case.name,
            case.apis,
            case.expected,
            case.inspect,
            Status.FAIL,
            f"Missing {case.phase} result",
        )
        for case in CASES
        if case.name not in completed
    )
    return tuple(results)


def main(argv: Sequence[str] | None = None) -> None:
    """Run every case in a phase, recording failures before failing the process."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("summary", "produce", "verify", "report"))
    parser.add_argument("--directory", type=Path, default=Path("reports/showcase"))
    arguments = parser.parse_args(argv)
    results = (
        list(read_reports(arguments.directory)) if arguments.phase == "report" else []
    )
    for case in CASES:
        if case.phase != arguments.phase:
            continue
        try:
            with gha.group(f"Showcase: {case.name}"):
                observed = case.run()
        except Exception as error:
            observed = (Status.FAIL, f"{type(error).__name__}: {error}")
        results.append(
            Result(
                case.name,
                case.apis,
                case.expected,
                case.inspect,
                observed[0],
                observed[1],
            )
        )
    write_reports(
        arguments.directory,
        tuple(results),
        "final" if arguments.phase == "report" else arguments.phase,
    )
    if any(result.status is Status.FAIL for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
