"""Read-only environment views must remain live and safe outside Actions."""

import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

import github_action_utils as gha


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, False),
        ("", False),
        ("false", False),
        ("true", True),
        ("True", False),
        ("0", False),
    ],
)
def test_detection_uses_github_specific_signal(
    value: str | None, expected: bool
) -> None:
    environment = {"CI": "true"}
    if value is not None:
        environment["GITHUB_ACTIONS"] = value
    with mock.patch.dict(os.environ, environment, clear=True):
        assert gha.is_github_action() is expected
        assert gha.vars.github.actions is expected


def test_properties_read_the_current_environment() -> None:
    with mock.patch.dict(os.environ, {}, clear=True):
        assert not gha.is_github_action()
        assert gha.vars.github.actor is None
        os.environ["GITHUB_ACTIONS"] = "true"
        os.environ["GITHUB_ACTOR"] = "first"
        assert gha.is_github_action()
        assert str(gha.vars.github.actor) == "first"
        os.environ["GITHUB_ACTOR"] = "second"
        assert str(gha.vars.github.actor) == "second"
        del os.environ["GITHUB_ACTOR"]
        assert gha.vars.github.actor is None


@pytest.mark.parametrize(
    "value,expected", [(None, False), ("false", False), ("true", True), ("0", False)]
)
def test_boolean_flags_are_parsed_explicitly(value: str | None, expected: bool) -> None:
    environment = {} if value is None else {"CI": value, "GITHUB_REF_PROTECTED": value}
    with mock.patch.dict(os.environ, environment, clear=True):
        assert gha.vars.ci is expected
        assert gha.vars.github.ref_protected is expected


@pytest.mark.parametrize(
    "value,expected", [(None, False), ("1", True), ("0", False), ("true", False)]
)
def test_runner_debug_uses_one(value: str | None, expected: bool) -> None:
    environment = {} if value is None else {"RUNNER_DEBUG": value}
    with mock.patch.dict(os.environ, environment, clear=True):
        assert gha.vars.runner.debug is expected


@pytest.mark.parametrize(
    "namespace,attribute",
    [
        (gha.vars, "ci"),
        (gha.vars, "github"),
        (gha.vars, "runner"),
        (gha.vars.github, "actor"),
        (gha.vars.runner, "debug"),
        (gha.vars.github, "unknown"),
    ],
)
def test_environment_objects_are_read_only(
    namespace: gha.WorkflowVariables | gha.GitHubVariables | gha.RunnerVariables,
    attribute: str,
) -> None:
    with pytest.raises(AttributeError):
        setattr(namespace, attribute, "replacement")


def test_import_does_not_read_an_environment_file(tmp_path: Path) -> None:
    environment = dict(os.environ, GITHUB_ENV=str(tmp_path / "missing"))
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from github_action_utils import vars; assert vars.github is not None",
        ],
        env=environment,
        check=True,
    )


def test_public_exports_are_explicit_and_available() -> None:
    assert all(hasattr(gha, name) for name in gha.__all__)
    assert {"is_github_action", "WorkflowVariables", "set_output"} <= set(gha.__all__)
    assert not {"_build_file_input", "vars"} & set(gha.__all__)


@pytest.mark.parametrize("view", [gha.GitHubVariables(), gha.RunnerVariables()])
def test_every_text_property_is_live(
    view: gha.GitHubVariables | gha.RunnerVariables,
) -> None:
    prefix = "GITHUB_" if isinstance(view, gha.GitHubVariables) else "RUNNER_"
    for name, descriptor in vars(type(view)).items():
        if isinstance(descriptor, property) and name not in (
            "actions",
            "ref_protected",
            "debug",
        ):
            key = prefix + name.upper()
            with mock.patch.dict(os.environ, {}, clear=True):
                assert getattr(view, name) is None, name
                os.environ[key] = "first 世界"
                assert getattr(view, name) == "first 世界", name
                os.environ[key] = ""
                assert getattr(view, name) == "", name
