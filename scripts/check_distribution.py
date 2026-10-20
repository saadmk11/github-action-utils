"""Check clean distribution installs, external typing, upgrades, and release refs."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
import venv
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

BASELINE_SHA256 = "bc84bac22e8a25ebe86370b08ff2c174960e468e899ffd313cb09d19629acefb"
BASELINE_FILENAME = "github_action_utils-1.1.0-py2.py3-none-any.whl"


BASELINE_URL = "https://files.pythonhosted.org/packages/fd/c8/d2a1c4ac43c9194316b8802b08502712ef242e6f325435409688e760b03a/github_action_utils-1.1.0-py2.py3-none-any.whl"


def require(condition: bool, message: str) -> None:
    """Keep validation enabled under python -O and PYTHONOPTIMIZE."""
    if not condition:
        raise ValueError(message)


def project_version(repository: Path) -> str:
    """Read the single static project version from its standard metadata."""
    value = tomllib.loads((repository / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    if not isinstance(value, str):
        raise ValueError("Project version must be a string")
    return value


def create_environment(workspace: Path) -> tuple[Path, dict[str, str]]:
    """Create a pip-capable environment outside the source import path."""
    workspace.mkdir()
    target = workspace / "venv"
    venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(str(target))
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("MYPYPATH", None)
    environment["PYTHONIOENCODING"] = "utf-8"
    return python, environment


def baseline_wheel(workspace: Path, previous_wheel: Path | None) -> Path:
    """Download the published baseline and verify its PyPI-advertised hash."""
    if previous_wheel is None:
        previous_wheel = workspace / BASELINE_FILENAME
        with urllib.request.urlopen(BASELINE_URL, timeout=30) as response:
            previous_wheel.write_bytes(response.read())
    require(
        hashlib.sha256(previous_wheel.read_bytes()).hexdigest() == BASELINE_SHA256,
        "Published baseline hash mismatch",
    )
    return previous_wheel


def validate_tag(repository: Path, tag: str) -> None:
    """Accept the static version with at most one leading v."""
    expected = project_version(repository)
    require(
        tag in (expected, "v" + expected), "Release tag does not match package version"
    )


def validate_github_release(repository: Path) -> str:
    """Require the caller, tag, checkout, and published release to identify one commit."""
    require(
        os.environ.get("GITHUB_REF_TYPE") == "tag",
        "Run this workflow on a published release tag, not a branch",
    )
    tag = os.environ["GITHUB_REF_NAME"]
    validate_tag(repository, tag)
    environment = dict(os.environ)
    commit = run(
        ["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], repository, environment
    ).strip()
    require(
        commit == os.environ["GITHUB_SHA"],
        "Release tag moved or differs from the workflow commit",
    )
    release = json.loads(
        run(
            ["gh", "release", "view", tag, "--json", "isDraft,tagName"],
            repository,
            environment,
        )
    )
    require(
        isinstance(release, dict)
        and release.get("isDraft") is False
        and release.get("tagName") == tag,
        "Expected a published release for the selected tag",
    )
    return project_version(repository)


def check_upgrade(wheel: Path, workspace: Path, previous_wheel: Path | None) -> None:
    """Upgrade a real 1.1.0 installation, checking names, calls, and old pickles."""
    python, environment = create_environment(workspace)
    previous = str(baseline_wheel(workspace, previous_wheel))
    run(
        [str(python), "-m", "pip", "install", "--no-deps", previous],
        workspace,
        environment,
    )
    run(
        [
            str(python),
            str(
                Path(__file__).resolve().parents[1] / "tests/fixtures/upgrade_before.py"
            ),
        ],
        workspace,
        environment,
    )
    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-index",
            "--upgrade",
            str(wheel),
        ],
        workspace,
        environment,
    )
    run(
        [
            str(python),
            str(
                Path(__file__).resolve().parents[1] / "tests/fixtures/check_install.py"
            ),
            project_version(Path(__file__).resolve().parents[1]),
        ],
        workspace,
        environment,
    )
    run(
        [
            str(python),
            str(
                Path(__file__).resolve().parents[1] / "tests/fixtures/upgrade_after.py"
            ),
        ],
        workspace,
        environment,
    )
    print(
        "Published 1.1.0 upgrade, public calls, old pickles, and module cleanup passed."
    )


def run(command: list[str], cwd: Path, environment: dict[str, str]) -> str:
    """Run a required check and retain diagnostics if it fails."""
    result = subprocess.run(
        command,
        cwd=str(cwd),
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )
    if result.returncode:
        raise RuntimeError("{}\n{}".format(" ".join(command), result.stdout))
    return result.stdout


def check_source_install(source: Path, workspace: Path) -> None:
    """Install the sdist with pip and an isolated build backend."""
    python, environment = create_environment(workspace)
    run(
        [str(python), "-m", "pip", "install", "--no-deps", str(source)],
        workspace,
        environment,
    )
    run(
        [
            str(python),
            str(
                Path(__file__).resolve().parents[1] / "tests/fixtures/check_install.py"
            ),
            project_version(Path(__file__).resolve().parents[1]),
        ],
        workspace,
        environment,
    )


def check_wheel(wheel: Path, workspace: Path, repository: Path) -> None:
    """Test a rebuilt wheel outside the checkout and check its public types."""
    python, environment = create_environment(workspace)
    run(
        [str(python), "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)],
        workspace,
        environment,
    )
    run(
        [
            str(python),
            str(
                Path(__file__).resolve().parents[1] / "tests/fixtures/check_install.py"
            ),
            project_version(Path(__file__).resolve().parents[1]),
        ],
        workspace,
        environment,
    )
    requirements = workspace / "test-requirements.txt"
    run(
        [
            "uv",
            "export",
            "--locked",
            "--only-group",
            "test",
            "--no-header",
            "--output-file",
            str(requirements),
        ],
        repository,
        environment,
    )
    run(
        ["uv", "pip", "install", "--python", str(python), "-r", str(requirements)],
        workspace,
        environment,
    )
    shutil.copytree(str(repository / "tests"), str(workspace / "tests"))
    print(
        run(
            [
                str(python),
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests",
                "--ignore=tests/support",
            ],
            workspace,
            environment,
        ).strip()
    )

    check_consumers(python, workspace, repository, environment)


def check_consumers(
    python: Path, workspace: Path, repository: Path, environment: dict[str, str]
) -> None:
    """Check valid and invalid consumers against an installed wheel."""
    for kind in ("valid", "invalid"):
        shutil.copyfile(
            str(repository / "tests" / "typing" / (kind + ".txt")),
            str(workspace / "consumer.py"),
        )
        error_lines = [
            line_number
            for line_number, line in enumerate(
                (workspace / "consumer.py").read_text(encoding="utf-8").splitlines(), 1
            )
            if line.endswith("# error")
        ]
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "--strict",
                "--no-incremental",
                "--python-executable",
                str(python),
                "consumer.py",
            ],
            cwd=str(workspace),
            env=environment,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
        )
        if kind == "valid":
            require(result.returncode == 0, result.stdout)
        else:
            # Reject every marked statement, not merely a failed import.
            require(result.returncode != 0, "Invalid consumer unexpectedly passed")
            require(bool(error_lines), "Invalid consumer has no marked type errors")
            for line in error_lines:
                require(f"consumer.py:{line}:" in result.stdout, result.stdout)
        print(f"mypy: {kind} consumer checked")


def main(argv: Sequence[str] | None = None) -> None:
    """Check built distributions or validate a release."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default="dist")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--published-version")
    mode.add_argument("--github-release", action="store_true")
    parser.add_argument("--previous-wheel", type=Path)
    arguments = parser.parse_args(argv)
    repository = Path(__file__).resolve().parents[1]
    if arguments.github_release:
        release_version = validate_github_release(repository)
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"version={release_version}\n")
        return
    if arguments.published_version:
        import github_action_utils as gha

        require(
            version("github-action-utils") == arguments.published_version,
            "Installed version differs from the expected release",
        )
        require(Path(gha.__file__).with_name("py.typed").is_file(), "Missing py.typed")
        return
    directory = Path(arguments.directory).resolve()
    wheels = list(directory.glob("*.whl"))
    sources = list(directory.glob("*.tar.gz"))
    require(len(wheels) == len(sources) == 1, "Expected one wheel and one sdist")
    with tempfile.TemporaryDirectory(
        prefix="github-action-utils-install-"
    ) as temporary:
        workspace = Path(temporary)
        check_source_install(sources[0], workspace / "pip-source")
        unpacked = workspace / "source"
        shutil.unpack_archive(str(sources[0]), str(unpacked), filter="data")
        rebuilt = workspace / "rebuilt"
        run(
            [
                "uv",
                "build",
                "--wheel",
                "--out-dir",
                str(rebuilt),
                str(next(unpacked.iterdir())),
            ],
            workspace,
            dict(os.environ),
        )
        check_wheel(next(rebuilt.glob("*.whl")), workspace / "sdist-wheel", repository)
        previous = (
            arguments.previous_wheel.resolve() if arguments.previous_wheel else None
        )
        check_upgrade(wheels[0], workspace / "upgrade", previous)
    (directory / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in (*wheels, *sources)
        ),
        encoding="utf-8",
    )
    print("Distribution checks passed.")


if __name__ == "__main__":
    main()
