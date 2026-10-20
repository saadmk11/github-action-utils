"""Regressions for command serialization, ordering, tokens, and command wrappers."""

import io
import os
import subprocess
import sys
import uuid
from collections.abc import Callable
from contextlib import redirect_stdout
from unittest import mock

import pytest

import github_action_utils as gha

from ._types import LegacyValue, MatcherOptions
from .command_helpers import parse_command


@pytest.mark.parametrize(
    "message",
    [
        "",
        "plain",
        "100% %0A %0D %25 %250A",
        "a\rb",
        "a\nb",
        "a\r\nb\n",
        "héllo 世界",
        "first\n::warning::synthetic-second-command",
    ],
)
@pytest.mark.parametrize("use_subprocess", [False, True])
def test_command_data_round_trip(
    capfd: pytest.CaptureFixture[str], message: str, use_subprocess: bool
) -> None:
    gha.notice(message, use_subprocess=use_subprocess)
    assert parse_command(capfd.readouterr().out) == ("notice", {}, message)


@pytest.mark.parametrize("helper", ["echo", "notice"])
@pytest.mark.parametrize("use_subprocess", [False, True])
def test_runner_stdout_uses_utf8_with_ansi_python_streams(
    helper: str, use_subprocess: bool
) -> None:
    value = "héllo 世界"
    code = f"import github_action_utils as g; g.{helper}({value!r}, use_subprocess={use_subprocess!r})"
    environment = dict(
        os.environ,
        GITHUB_ACTIONS="true",
        COMMANDS_USE_SUBPROCESS="",
        PYTHONIOENCODING="cp1252",
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    record = result.stdout.decode("utf-8")
    if helper == "notice":
        assert parse_command(record) == ("notice", {}, value)
    else:
        assert record == value + "\n"


def test_runner_emission_respects_text_only_capture() -> None:
    output = io.StringIO()
    with (
        mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}),
        redirect_stdout(output),
    ):
        gha.notice("世界")
    assert parse_command(output.getvalue()) == ("notice", {}, "世界")


@pytest.mark.parametrize("helper", ["notice", "warning", "error"])
@pytest.mark.parametrize("use_subprocess", [False, True])
def test_annotation_properties_round_trip(
    capfd: pytest.CaptureFixture[str], helper: str, use_subprocess: bool
) -> None:
    value = "a:b,c%0A\r\n世界"
    getattr(gha, helper)(
        value,
        title=value,
        file=value,
        line=1,
        col=2,
        end_column=4,
        end_line=3,
        use_subprocess=use_subprocess,
    )
    command, options, message = parse_command(capfd.readouterr().out)
    assert command == helper and message == value
    assert options == {
        "title": value,
        "file": value,
        "line": "1",
        "col": "2",
        "endColumn": "4",
        "endLine": "3",
    }


@pytest.mark.parametrize(
    "token",
    [
        "test token",
        "a::b",
        "trailing:",
        "a\rb",
        "a\nb",
        "a\0b",
        "stop-commands",
        "pause-logging",
        "internal-set-repo-path",
        "set-env",
        "set-output",
        "save-state",
        "add-mask",
        "add-path",
        "add-matcher",
        "remove-matcher",
        "DEBUG",
        "warning",
        "error",
        "notice",
        "group",
        "endgroup",
        "EcHo",
    ],
)
@pytest.mark.parametrize("helper", [gha.begin_stop_commands, gha.end_stop_commands])
def test_invalid_stop_tokens_emit_nothing(
    capfd: pytest.CaptureFixture[str], token: str, helper: Callable[[str], str | None]
) -> None:
    with pytest.raises(ValueError, match="Stop token"):
        helper(token)
    assert capfd.readouterr().out == ""


def test_empty_end_token_is_rejected(capfd: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(ValueError):
        gha.end_stop_commands("")
    assert capfd.readouterr().out == ""


@pytest.mark.parametrize("token", [True, ["nonempty"], object()])
def test_non_string_stop_token(
    capfd: pytest.CaptureFixture[str], token: object
) -> None:
    for helper in (gha.begin_stop_commands, gha.end_stop_commands):
        with pytest.raises(TypeError, match="Stop token"):
            helper(token)  # type: ignore[arg-type]  # Deliberately invalid runtime input.
    assert capfd.readouterr().out == ""


def test_random_stop_tokens_resume(capfd: pytest.CaptureFixture[str]) -> None:
    tokens = set()
    for _ in range(3):
        token = gha.begin_stop_commands()
        assert uuid.UUID(token).version == 4
        assert parse_command(capfd.readouterr().out) == ("stop-commands", {}, token)
        gha.end_stop_commands(token)
        assert parse_command(capfd.readouterr().out) == (token, {}, "")
        tokens.add(token)
    assert len(tokens) == 3


@pytest.mark.parametrize(
    "helper,argument,command",
    [
        ("add_mask", "AUDIT_DUMMY_VALUE", "add-mask"),
        ("start_group", "group-title", "group"),
        ("begin_stop_commands", "safe-token", "stop-commands"),
    ],
)
@pytest.mark.parametrize("use_subprocess", [False, True])
def test_commands_precede_unrelated_child_output(
    helper: str, argument: str, command: str, use_subprocess: bool
) -> None:
    # Capture a fresh interpreter through a pipe: pytest's own capture can flush
    # streams and hide the buffering bug. Never use a real secret here.
    code = (
        "import subprocess, sys, github_action_utils as g\n"
        f"g.{helper}({argument!r}, use_subprocess={use_subprocess!r})\n"
        "subprocess.run([sys.executable, '-c', \"print('AUDIT_DUMMY_VALUE')\"], check=True)\n"
    )
    environment = dict(os.environ, COMMANDS_USE_SUBPROCESS="")
    environment.pop("PYTHONUNBUFFERED", None)
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        check=True,
    )
    records = result.stdout.decode("utf-8").splitlines(keepends=True)
    assert len(records) == 2
    assert parse_command(records[0]) == (command, {}, argument)
    assert records[1].rstrip("\r\n") == "AUDIT_DUMMY_VALUE"


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("use_subprocess", [False, True])
def test_command_echo(
    capfd: pytest.CaptureFixture[str], enabled: bool, use_subprocess: bool
) -> None:
    gha.set_command_echo(enabled, use_subprocess=use_subprocess)
    assert parse_command(capfd.readouterr().out) == (
        "echo",
        {},
        "on" if enabled else "off",
    )
    gha.echo("plain")
    assert capfd.readouterr().out == "plain\n"


@pytest.mark.parametrize("value", ["false", 0, 1, None])
def test_command_echo_rejects_non_bool(
    capfd: pytest.CaptureFixture[str], value: LegacyValue
) -> None:
    with pytest.raises(TypeError, match="boolean"):
        gha.set_command_echo(value)  # type: ignore[arg-type]  # Deliberately invalid runtime input.
    assert capfd.readouterr().out == ""


@pytest.mark.parametrize("use_subprocess", [False, True])
def test_fail_exits_after_annotation_and_cleanup(use_subprocess: bool) -> None:
    code = (
        "import github_action_utils as g\n"
        "with g.group('cleanup'):\n"
        f"    g.fail('failed%0A\\nmessage', use_subprocess={use_subprocess!r})\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True)
    assert result.returncode == 1
    records = result.stdout.decode("utf-8").splitlines(keepends=True)
    assert parse_command(records[1]) == ("error", {}, "failed%0A\nmessage")
    assert parse_command(records[2]) == ("endgroup", {}, "")
    control = subprocess.run(
        [
            sys.executable,
            "-c",
            "import github_action_utils as g; g.error('annotation only')",
        ],
        capture_output=True,
    )
    assert control.returncode == 0


@pytest.mark.parametrize("use_subprocess", [False, True])
def test_matcher_commands(
    capfd: pytest.CaptureFixture[str], use_subprocess: bool
) -> None:
    path = "./matchers/a,b:%0A\n世界.json"
    owner = "owner,:\r\n%0A"
    gha.add_problem_matcher(path, use_subprocess=use_subprocess)
    assert parse_command(capfd.readouterr().out) == ("add-matcher", {}, path)
    gha.remove_problem_matcher(owner=owner, use_subprocess=use_subprocess)
    assert parse_command(capfd.readouterr().out) == (
        "remove-matcher",
        {"owner": owner},
        "",
    )
    gha.remove_problem_matcher(path=path, use_subprocess=use_subprocess)
    assert parse_command(capfd.readouterr().out) == ("remove-matcher", {}, path)


@pytest.mark.parametrize(
    "options",
    [{}, {"owner": "x", "path": "x"}, {"owner": ""}, {"path": ""}, {"path": "\0"}],
)
def test_invalid_matcher_removal(
    capfd: pytest.CaptureFixture[str], options: MatcherOptions
) -> None:
    with pytest.raises(ValueError):
        gha.remove_problem_matcher(**options)
    assert capfd.readouterr().out == ""


@pytest.mark.parametrize("value", ["", "\0", 123])
def test_invalid_matcher_registration(
    capfd: pytest.CaptureFixture[str], value: LegacyValue
) -> None:
    with pytest.raises((ValueError, TypeError)):
        gha.add_problem_matcher(value)  # type: ignore[arg-type]  # Deliberately invalid runtime input.
    assert capfd.readouterr().out == ""


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", False),
        ("false", True),
        ("0", True),
        ("  ", True),
        ("arbitrary", True),
    ],
)
def test_subprocess_environment_flag(value: str, expected: bool) -> None:
    environment = dict(os.environ, COMMANDS_USE_SUBPROCESS=value)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import warnings; warnings.simplefilter('always'); import github_action_utils as g; print(g.COMMANDS_USE_SUBPROCESS)",
        ],
        env=environment,
        capture_output=True,
        check=True,
    )
    assert result.stdout.decode().strip() == str(expected)
    assert not result.stderr


def test_module_flag_assignment_affects_each_emitter(
    capfd: pytest.CaptureFixture[str],
) -> None:
    captured = io.StringIO()
    with (
        mock.patch.object(gha, "COMMANDS_USE_SUBPROCESS", True),
        redirect_stdout(captured),
    ):
        gha.echo("flag text")
        gha.notice("flag command")
    assert captured.getvalue() == ""
    gha._print_command("debug", "already%0Aescaped", escape_message=False)
    assert (
        capfd.readouterr().out
        == "flag text\n::notice ::flag command\n::debug ::already%0Aescaped\n"
    )


def test_subprocess_streams_values_larger_than_argv_limits(
    capfd: pytest.CaptureFixture[str],
) -> None:
    value = "世界\0" * 100_000
    gha.echo(value, use_subprocess=True)
    assert capfd.readouterr().out == value + "\n"


@pytest.mark.parametrize(
    "helper,command",
    [
        ("debug", "debug"),
        ("notice", "notice"),
        ("warning", "warning"),
        ("error", "error"),
        ("start_group", "group"),
        ("add_mask", "add-mask"),
    ],
)
@pytest.mark.parametrize("use_subprocess", [False, True])
def test_command_wrappers(
    capfd: pytest.CaptureFixture[str], helper: str, command: str, use_subprocess: bool
) -> None:
    getattr(gha, helper)("fixture", use_subprocess=use_subprocess)
    assert parse_command(capfd.readouterr().out) == (command, {}, "fixture")
