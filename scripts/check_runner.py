"""Integration checks executed across actual GitHub Actions job steps."""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import github_action_utils as gha

VALUE = "héllo 世界\nsecond line: 100% %0A\n\ntrailing line\n"


def integration_paths() -> tuple[Path, Path]:
    """Return the two distinct PATH fixtures used by producer and verifier."""
    root = Path(os.environ["GITHUB_WORKSPACE"]) / ".runner-integration"
    return root / "first বাংলা", root / "second 世界"


def check_commands() -> None:
    """Produce recognizable smoke-test logs; rendering is inspected in CI logs."""
    with gha.group("Protocol smoke: %0A / Unicode 世界"):
        gha.set_command_echo(True)
        gha.add_mask("GH_UTILS_DUMMY_MASK_VALUE")
        subprocess.run(
            [sys.executable, "-c", "print('GH_UTILS_DUMMY_MASK_VALUE')"], check=True
        )
        with gha.stop_commands():
            gha.echo("::warning::GH_UTILS_PLAIN_TEXT_WHILE_STOPPED")
        gha.notice("Commands resumed; literal %0A\nsecond annotation line")
        gha.debug("Debug smoke; literal %0D %25")
        matcher = Path(os.environ["RUNNER_TEMP"]) / "github-action-utils-matcher.json"
        matcher.write_text(
            json.dumps(
                {
                    "problemMatcher": [
                        {
                            "owner": "gh-utils-smoke",
                            "severity": "warning",
                            "pattern": [
                                {
                                    "regexp": "^GH_UTILS_MATCHER_SMOKE: (.*)$",
                                    "message": 1,
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        gha.add_problem_matcher(str(matcher))
        gha.echo("GH_UTILS_MATCHER_SMOKE: matcher is active")
        gha.remove_problem_matcher(owner="gh-utils-smoke")
        gha.echo("GH_UTILS_MATCHER_SMOKE: matcher has been removed")
        gha.add_problem_matcher(str(matcher))
        gha.remove_problem_matcher(path=str(matcher))
        gha.set_command_echo(False)


def main(argv: Sequence[str] | None = None) -> None:
    """Produce or verify values across real runner steps."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    match arguments:
        case ["write"]:
            gha.set_output("multiline", VALUE)
            gha.set_output("number", 42)
            gha.set_output("empty", "")
            gha.set_output("unicode", "বাংলা 世界")
            gha.set_output("json", {"enabled": True})
            gha.set_env("GH_UTILS_INTEGRATION_VALUE", VALUE)
            assert gha.get_env("GH_UTILS_INTEGRATION_VALUE") == VALUE
            assert (
                gha.get_workflow_environment_variables()["GH_UTILS_INTEGRATION_VALUE"]
                == VALUE
            )
            for path in integration_paths():
                path.mkdir(parents=True, exist_ok=True)
                executable = path / (
                    "gh-utils-"
                    + ("first" if path == integration_paths()[0] else "second")
                    + (".cmd" if os.name == "nt" else "")
                )
                executable.write_text(
                    "@echo fixture\n"
                    if os.name == "nt"
                    else "#!/bin/sh\necho fixture\n",
                    encoding="utf-8",
                )
                executable.chmod(0o755)
                gha.add_system_path(str(path))
            markdown = "# Python helper smoke\n\nবাংলা 世界 — literal %0A %0D %25\n"
            gha.overwrite_job_summary(markdown)
            assert Path(os.environ["GITHUB_STEP_SUMMARY"]).read_bytes() == (
                markdown + "\n"
            ).encode("utf-8")
        case ["verify"]:
            assert gha.is_github_action()
            assert gha.vars.github.actions
            assert os.environ["OUTPUT_VALUE"] == VALUE
            assert os.environ["GH_UTILS_INTEGRATION_VALUE"] == VALUE
            assert os.environ["OUTPUT_NUMBER"] == "42"
            assert os.environ["OUTPUT_EMPTY"] == ""
            assert os.environ["OUTPUT_UNICODE"] == "বাংলা 世界"
            assert shutil.which("gh-utils-first")
            assert shutil.which("gh-utils-second")
            assert json.loads(os.environ["OUTPUT_JSON"]) == {"enabled": True}
            assert gha.get_env("GH_UTILS_INTEGRATION_VALUE") == VALUE
            assert gha.vars.github.env == os.environ["GITHUB_ENV"]
            first, second = (
                os.path.normcase(str(path)) for path in integration_paths()
            )
            entries = [
                os.path.normcase(entry)
                for entry in os.environ["PATH"].split(os.pathsep)
            ]
            assert entries.index(second) < entries.index(first)
        case ["commands"]:
            check_commands()
        case _:
            raise ValueError("Expected write, verify, or commands")


if __name__ == "__main__":
    main()
