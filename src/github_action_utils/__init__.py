"""Python helpers for GitHub Actions workflow commands and environment values."""

import json
import os
import uuid
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Dict, Generator, Literal, NoReturn
from warnings import warn

from . import _commands, _files, _serialization
from ._artifacts import (
    ArtifactSubject,
    declare_file_artifact,
    declare_oci_artifact,
    get_workflow_artifacts,
)
from ._environment import (
    GitHubVariables,
    RunnerVariables,
    WorkflowVariables,
    is_github_action,
)
from ._environment import vars as vars
from ._files import (
    add_system_path,
    append_job_summary,
    overwrite_job_summary,
    remove_job_summary,
)
from ._inputs import get_boolean_input, get_multiline_input, get_user_input

__all__ = [
    "ACTION_ENV_DELIMITER",
    "COMMAND_MARKER",
    "COMMANDS_USE_SUBPROCESS",
    "ArtifactSubject",
    "CommandTypes",
    "LogCommandTypes",
    "GitHubVariables",
    "RunnerVariables",
    "WorkflowVariables",
    "add_mask",
    "add_problem_matcher",
    "add_system_path",
    "append_job_summary",
    "begin_stop_commands",
    "debug",
    "declare_file_artifact",
    "declare_oci_artifact",
    "echo",
    "end_group",
    "end_stop_commands",
    "error",
    "event_payload",
    "fail",
    "get_boolean_input",
    "get_env",
    "get_multiline_input",
    "get_state",
    "get_user_input",
    "get_workflow_artifacts",
    "get_workflow_environment_variables",
    "group",
    "is_github_action",
    "notice",
    "overwrite_job_summary",
    "remove_job_summary",
    "remove_problem_matcher",
    "save_state",
    "set_command_echo",
    "set_env",
    "set_output",
    "start_group",
    "stop_commands",
    "warning",
]

CommandTypes = Literal[
    "add-mask",
    "add-matcher",
    "debug",
    "echo",
    "error",
    "group",
    "notice",
    "remove-matcher",
    "save-state",
    "set-output",
    "stop-commands",
    "warning",
]
LogCommandTypes = Literal["debug", "error", "notice", "warning"]
ACTION_ENV_DELIMITER = "__ENV_DELIMITER__"
COMMAND_MARKER = "::"
COMMANDS_USE_SUBPROCESS = bool(os.environ.get("COMMANDS_USE_SUBPROCESS", ""))


def _make_string(data: Any) -> str:  # type: ignore[explicit-any]
    """Convert a value to a string."""
    if isinstance(data, (list, tuple, dict)):
        return json.dumps(data)
    return str(data)


def _to_camel_case(text: str) -> str:
    """Transform a snake case string to camel case."""
    return f"{text[:1].lower()}{text.title().replace('_', '')[1:]}"


def _build_options_string(**kwargs: Any) -> str:  # type: ignore[explicit-any]
    return ",".join(
        f"{_to_camel_case(key)}={_escape_property(value)}"
        for key, value in kwargs.items()
        if value is not None
    )


def set_output(name: str, value: Any, use_subprocess: bool | None = None) -> None:  # type: ignore[explicit-any]
    """Set a step output through GITHUB_OUTPUT, preserving multiline text.

    Lists, tuples, and dictionaries become JSON; other values use str(). Invalid
    names raise ValueError. The deprecated use_subprocess argument emits a warning.
    """
    if use_subprocess is not None:
        warn(
            "Argument `use_subprocess` for `set_output()` is deprecated and "
            "going to be removed in the next version.",
            DeprecationWarning,
            stacklevel=1,
        )

    _write_file_command("GITHUB_OUTPUT", name, value)


def echo(message: Any, use_subprocess: bool = False) -> None:  # type: ignore[explicit-any]
    """Print text to stdout without escaping it."""
    message = str(message)

    _emit(message, use_subprocess=use_subprocess)


def set_command_echo(enabled: bool, use_subprocess: bool = False) -> None:
    """Enable or disable the runner's command echoing for the rest of this step."""
    if not isinstance(enabled, bool):
        raise TypeError("Command echo setting must be a boolean")
    _print_command(
        "echo",
        "on" if enabled else "off",
        use_subprocess=use_subprocess,
    )


def debug(message: str, use_subprocess: bool = False) -> None:
    """Print a debug message in the GitHub Actions shell."""
    _print_command("debug", str(message), use_subprocess=use_subprocess)


def notice(
    message: str,
    title: str | None = None,
    file: str | None = None,
    col: int | None = None,
    end_column: int | None = None,
    line: int | None = None,
    end_line: int | None = None,
    use_subprocess: bool = False,
) -> None:
    """Print a notice message in the GitHub Actions shell."""
    _print_command(
        "notice",
        str(message),
        options_string=_build_options_string(
            title=title,
            file=file,
            col=col,
            end_column=end_column,
            line=line,
            end_line=end_line,
        ),
        use_subprocess=use_subprocess,
    )


def warning(
    message: str,
    title: str | None = None,
    file: str | None = None,
    col: int | None = None,
    end_column: int | None = None,
    line: int | None = None,
    end_line: int | None = None,
    use_subprocess: bool = False,
) -> None:
    """Print a warning message in the GitHub Actions shell."""
    _print_command(
        "warning",
        str(message),
        options_string=_build_options_string(
            title=title,
            file=file,
            col=col,
            end_column=end_column,
            line=line,
            end_line=end_line,
        ),
        use_subprocess=use_subprocess,
    )


def error(
    message: str,
    title: str | None = None,
    file: str | None = None,
    col: int | None = None,
    end_column: int | None = None,
    line: int | None = None,
    end_line: int | None = None,
    use_subprocess: bool = False,
) -> None:
    """Print an error annotation without changing the process exit status."""
    _print_command(
        "error",
        str(message),
        options_string=_build_options_string(
            title=title,
            file=file,
            col=col,
            end_column=end_column,
            line=line,
            end_line=end_line,
        ),
        use_subprocess=use_subprocess,
    )


def fail(message: str, use_subprocess: bool = False) -> NoReturn:
    """Emit an error annotation and raise SystemExit(1)."""
    error(message, use_subprocess=use_subprocess)
    raise SystemExit(1)


def save_state(name: str, value: Any, use_subprocess: bool | None = None) -> None:  # type: ignore[explicit-any]
    """Save state through GITHUB_STATE for a later hook of the same action.

    Value conversion and validation match set_output().
    """
    if use_subprocess is not None:
        warn(
            "Argument `use_subprocess` for `save_state()` is deprecated and "
            "going to be removed in the next version.",
            DeprecationWarning,
            stacklevel=1,
        )

    _write_file_command("GITHUB_STATE", name, value)


def get_state(name: str) -> str | None:
    """Read STATE_name in a later action hook, or return None if it is absent."""
    return os.environ.get(f"STATE_{name}")


def start_group(title: str, use_subprocess: bool = False) -> None:
    """Create an expandable group in GitHub Actions log."""
    _print_command("group", str(title), use_subprocess=use_subprocess)


def end_group(use_subprocess: bool = False) -> None:
    """Close an expandable group in GitHub Actions log."""
    message = f"{COMMAND_MARKER}endgroup{COMMAND_MARKER}"

    _emit(message, use_subprocess=use_subprocess)


@contextmanager
def group(title: str, use_subprocess: bool = False) -> Generator[Any, None, None]:  # type: ignore[explicit-any]
    """Open a titled log group and close it even when the body raises."""
    start_group(title, use_subprocess=use_subprocess)
    try:
        yield
    finally:
        end_group(use_subprocess=use_subprocess)


def add_mask(value: Any, use_subprocess: bool = False) -> None:  # type: ignore[explicit-any]
    """Mask a value to prevent a string or variable from being printed in the log."""
    _print_command("add-mask", _make_string(value), use_subprocess=use_subprocess)


def add_problem_matcher(path: str, use_subprocess: bool = False) -> None:
    """Register a matcher JSON file, resolving relative paths in the workspace."""
    _commands._validate_matcher_selector(path)
    _print_command("add-matcher", path, use_subprocess=use_subprocess)


def remove_problem_matcher(
    *,
    owner: str | None = None,
    path: str | None = None,
    use_subprocess: bool = False,
) -> None:
    """Remove a matcher by exactly one selector: its owner or its JSON file path."""
    if (owner is None) == (path is None):
        raise ValueError("Specify exactly one matcher owner or file path")
    if owner is not None:
        _commands._validate_matcher_selector(owner)
        _print_command(
            "remove-matcher",
            "",
            _build_options_string(owner=owner),
            use_subprocess=use_subprocess,
        )
    else:
        assert path is not None
        _commands._validate_matcher_selector(path)
        _print_command("remove-matcher", path, use_subprocess=use_subprocess)


def begin_stop_commands(token: str | None = None, use_subprocess: bool = False) -> str:
    """Suspend command processing and return its resume token.

    None or an empty string generates a UUID4. Invalid tokens raise ValueError;
    use end_stop_commands() with the returned token to resume processing.
    """
    if not token:
        token = str(uuid.uuid4())
    _commands._validate_stop_token(token)

    _print_command("stop-commands", token, use_subprocess=use_subprocess)

    return token


def end_stop_commands(token: str, use_subprocess: bool = False) -> None:
    """Resume workflow command processing using the token from begin_stop_commands()."""
    _commands._validate_stop_token(token)
    message = f"{COMMAND_MARKER}{token}{COMMAND_MARKER}"

    _emit(message, use_subprocess=use_subprocess)


@contextmanager
def stop_commands(  # type: ignore[explicit-any]
    token: str | None = None, use_subprocess: bool = False
) -> Generator[Any, None, None]:
    """Suspend workflow commands and resume processing even if the body raises."""
    stop_token = begin_stop_commands(token=token, use_subprocess=use_subprocess)
    try:
        yield
    finally:
        end_stop_commands(stop_token, use_subprocess=use_subprocess)


def set_env(name: str, value: Any) -> None:  # type: ignore[explicit-any]
    """Set an environment value for later steps without changing os.environ.

    Value conversion and validation match set_output().
    """
    _write_file_command("GITHUB_ENV", name, value)


def get_env(name: str) -> Any:  # type: ignore[explicit-any]
    """Look up a process variable, then a pending current-step file value.

    Empty process values take precedence. Return None for a missing name;
    unreadable files and malformed records propagate their OSError/ValueError.
    """
    if name in os.environ:
        return os.environ[name]
    return get_workflow_environment_variables().get(name)


@lru_cache(maxsize=1)
def event_payload() -> Dict[str, Any]:  # type: ignore[explicit-any]
    """Read and cache the UTF-8 JSON payload at GITHUB_EVENT_PATH.

    Calls share one mutable value. Use cache_clear() to reload on the next call
    and cache_info() for statistics. File and JSON errors propagate.
    """
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)  # type: ignore[explicit-any]
    return data


def _emit(message: str, use_subprocess: bool = False) -> None:
    """Emit text using the current subprocess setting."""
    _commands._emit(message, use_subprocess or COMMANDS_USE_SUBPROCESS)


def _print_command(
    command: CommandTypes,
    command_message: str,
    options_string: str | None = "",
    use_subprocess: bool = False,
    escape_message: bool = True,
) -> None:
    """Emit a workflow command using the current subprocess setting."""
    _commands.print_command(
        command,
        command_message,
        options_string,
        use_subprocess or COMMANDS_USE_SUBPROCESS,
        escape_message,
    )


def _escape_property(data: Any) -> str:  # type: ignore[explicit-any]
    """Convert and escape a command property value."""
    return _serialization.escape_property(_make_string(data))


def _write_file_command(environment_variable: str, name: str, value: Any) -> None:  # type: ignore[explicit-any]
    """Convert values before opening the runner file."""
    _files._write_file_command(
        environment_variable, _make_string(name), _make_string(value)
    )


def get_workflow_environment_variables() -> Dict[str, Any]:  # type: ignore[explicit-any]
    """Read pending GITHUB_ENV values into a fresh dictionary.

    Later duplicate names win. Return {} without a configured file; malformed
    records raise ValueError and file errors propagate.
    """
    return _files.get_workflow_environment_variables()
