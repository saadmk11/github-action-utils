"""Public API compatibility with version 1.1.0."""

import inspect
import os
import warnings
from collections.abc import Generator
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints
from unittest import mock

import pytest

import github_action_utils as gha

from ._types import FileWriter, LegacyValue
from .command_helpers import parse_command

# Original positional/keyword names in order. New options must be optional.
LEGACY_PARAMETERS = {
    "set_output": ("name", "value", "use_subprocess"),
    "save_state": ("name", "value", "use_subprocess"),
    "echo": ("message", "use_subprocess"),
    "debug": ("message", "use_subprocess"),
    "notice": (
        "message",
        "title",
        "file",
        "col",
        "end_column",
        "line",
        "end_line",
        "use_subprocess",
    ),
    "warning": (
        "message",
        "title",
        "file",
        "col",
        "end_column",
        "line",
        "end_line",
        "use_subprocess",
    ),
    "error": (
        "message",
        "title",
        "file",
        "col",
        "end_column",
        "line",
        "end_line",
        "use_subprocess",
    ),
    "get_state": ("name",),
    "get_user_input": ("name",),
    "start_group": ("title", "use_subprocess"),
    "end_group": ("use_subprocess",),
    "group": ("title", "use_subprocess"),
    "add_mask": ("value", "use_subprocess"),
    "begin_stop_commands": ("token", "use_subprocess"),
    "end_stop_commands": ("token", "use_subprocess"),
    "stop_commands": ("token", "use_subprocess"),
    "set_env": ("name", "value"),
    "get_workflow_environment_variables": (),
    "get_env": ("name",),
    "append_job_summary": ("markdown_text",),
    "overwrite_job_summary": ("markdown_text",),
    "remove_job_summary": (),
    "add_system_path": ("path",),
    "event_payload": (),
}


@pytest.mark.parametrize("name,parameters", list(LEGACY_PARAMETERS.items()))
def test_original_public_call_shapes(name: str, parameters: tuple[str, ...]) -> None:
    function = getattr(gha, name)
    signature = inspect.signature(function)
    actual = list(signature.parameters.values())
    assert (
        tuple(parameter.name for parameter in actual[: len(parameters)]) == parameters
    )
    assert all(
        parameter.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
        for parameter in actual[: len(parameters)]
    )
    assert all(
        parameter.default is not inspect.Parameter.empty
        for parameter in actual[len(parameters) :]
    )
    values = [object() for _ in parameters]
    signature.bind(*values)
    signature.bind(**dict(zip(parameters, values, strict=True)))
    for parameter in actual[: len(parameters)]:
        if parameter.name in (
            "title",
            "file",
            "col",
            "end_column",
            "line",
            "end_line",
            "token",
        ):
            assert (
                parameter.default is None
                or parameter.default is inspect.Parameter.empty
            )
        if parameter.name == "use_subprocess":
            assert parameter.default is (
                None if name in ("set_output", "save_state") else False
            )


def test_legacy_constants_and_wildcard_builtin_vars() -> None:
    assert gha.ACTION_ENV_DELIMITER == "__ENV_DELIMITER__"
    assert gha.COMMAND_MARKER == "::"
    namespace: dict[str, object] = {}
    exec(
        "from github_action_utils import *\nclass Example: pass\nsample=Example()\nsample.value=1\nresult=vars(sample)",
        namespace,
    )
    assert namespace["result"] == {"value": 1}
    assert "vars" not in namespace
    from github_action_utils import vars as environment_vars

    assert environment_vars is gha.vars


@pytest.mark.parametrize(
    "helper,variable",
    [(gha.set_output, "GITHUB_OUTPUT"), (gha.save_state, "GITHUB_STATE")],
)
def test_original_deprecation_warning_filters_still_work(
    tmp_path: Path, helper: FileWriter, variable: str
) -> None:
    with mock.patch.dict(os.environ, {variable: str(tmp_path / "commands")}):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            warnings.filterwarnings(
                "ignore", category=DeprecationWarning, module=r"^github_action_utils$"
            )
            helper("name", "value", False)


def test_original_permissive_return_types_remain_compatible() -> None:
    assert get_type_hints(gha.get_env)["return"] is Any
    mapping = get_type_hints(gha.get_workflow_environment_variables)["return"]
    assert get_origin(mapping) is dict
    assert get_args(mapping) == (str, Any)
    for function in (gha.group, gha.stop_commands):
        result = get_type_hints(function)["return"]
        assert get_origin(result) is Generator
        assert get_args(result) == (Any, type(None), type(None))


@pytest.mark.parametrize("value", [None, "", "raw legacy value"])
def test_literal_input_keys_keep_precedence(value: str | None) -> None:
    environment = {"INPUT_OLD_NAME": "normalized"}
    if value is not None:
        environment["INPUT_OLD NAME"] = value
    with mock.patch.dict(os.environ, environment, clear=True):
        assert gha.get_user_input("old name") == (
            "normalized" if value is None else value
        )


def test_empty_input_name_keeps_original_lookup() -> None:
    with mock.patch.dict(os.environ, {}, clear=True):
        assert gha.get_user_input("") is None
    with mock.patch.dict(os.environ, {"INPUT_": "legacy"}, clear=True):
        assert gha.get_user_input("") == "legacy"


@pytest.mark.parametrize(
    "token",
    [
        "release.v1",
        "name=value",
        "semi;colon",
        "single:colon",
        ":prefix",
        "token%0A",
        "世界",
    ],
)
@pytest.mark.parametrize("use_subprocess", [False, True])
def test_working_custom_stop_tokens_remain_supported(
    capfd: pytest.CaptureFixture[str], token: str, use_subprocess: bool
) -> None:
    assert gha.begin_stop_commands(token, use_subprocess=use_subprocess) == token
    assert parse_command(capfd.readouterr().out) == ("stop-commands", {}, token)
    gha.end_stop_commands(token, use_subprocess=use_subprocess)
    assert parse_command(capfd.readouterr().out) == (token, {}, "")


@pytest.mark.parametrize("value", ["", None, False, 0, [], {}])
def test_empty_stop_token_still_generates_a_canonical_uuid(
    capfd: pytest.CaptureFixture[str], value: LegacyValue
) -> None:
    token = gha.begin_stop_commands(value)  # type: ignore[arg-type]  # Deliberately invalid runtime input.
    assert len(token) == 36 and token.count("-") == 4
    assert parse_command(capfd.readouterr().out) == ("stop-commands", {}, token)


@pytest.mark.parametrize(
    "helper,command",
    [
        ("debug", "debug"),
        ("notice", "notice"),
        ("warning", "warning"),
        ("error", "error"),
        ("start_group", "group"),
    ],
)
@pytest.mark.parametrize("value", [["item", True], {"item": False}])
def test_logging_keeps_legacy_string_conversion(
    capfd: pytest.CaptureFixture[str], helper: str, command: str, value: LegacyValue
) -> None:
    getattr(gha, helper)(value)
    assert parse_command(capfd.readouterr().out) == (command, {}, str(value))


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/tmp/already-terminated\n",
        "first\nsecond\n",
        "first\r\nsecond\r\n",
        "first\rsecond",
    ],
)
def test_legacy_path_records_remain_supported(tmp_path: Path, value: str) -> None:
    path = tmp_path / "path-file"
    with mock.patch.dict(os.environ, {"GITHUB_PATH": str(path)}):
        gha.add_system_path(value)
    expected = (
        value if not value or value.endswith(("\r", "\n")) else value + os.linesep
    )
    assert path.read_bytes() == expected.encode("utf-8")


def test_pathlike_and_legacy_value_conversion(tmp_path: Path) -> None:
    path = tmp_path / "path-file"
    entry = tmp_path / "future-directory"
    value: LegacyValue = 123
    with mock.patch.dict(os.environ, {"GITHUB_PATH": str(path)}):
        gha.add_system_path(entry)
        gha.add_system_path(value)  # type: ignore[arg-type]  # Deliberately invalid runtime input.
    assert path.read_bytes() == (str(entry) + os.linesep + "123" + os.linesep).encode(
        "utf-8"
    )
