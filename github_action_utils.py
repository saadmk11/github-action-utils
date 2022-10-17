import json
import os
import subprocess
import sys
import uuid
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Dict, Generator, Union
from warnings import warn

if sys.version_info >= (3, 8):
    from typing import Literal

    CommandTypes = Literal[
        "add-mask",
        "debug",
        "error",
        "group",
        "notice",
        "save-state",
        "set-output",
        "stop-commands",
        "warning",
    ]
    LogCommandTypes = Literal["debug", "error", "notice", "warning"]
else:
    CommandTypes = str
    LogCommandTypes = str


ACTION_ENV_DELIMITER: str = "__ENV_DELIMITER__"
COMMAND_MARKER: str = "::"

COMMANDS_USE_SUBPROCESS: bool = bool(os.environ.get("COMMANDS_USE_SUBPROCESS", False))


def _print_command(
    command: CommandTypes,
    command_message: str,
    options_string: Union[str] = "",
    use_subprocess: bool = False,
    escape_message: bool = True,
) -> None:
    """
    Helper function to print GitHub action commands to the shell.
    Docs: https://docs.github.com/en/actions/reference/workflow-commands-for-github-actions

    :param command: command name from `CommandTypes`
    :param command_message: message string
    :param options_string: string containing extra options
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    if escape_message:
        command_message = _escape_data(command_message)

    full_command = (
        f"{COMMAND_MARKER}{command} "
        f"{options_string or ''}"
        f"{COMMAND_MARKER}{command_message}"
    )

    if use_subprocess or COMMANDS_USE_SUBPROCESS:
        subprocess.run(["echo", full_command])
    else:
        print(full_command)


def _make_string(data: Any) -> str:
    """
    Converts a value to a string.

    :param data: data to convert
    :returns: string representation of the value
    """
    if isinstance(data, (list, tuple, dict)):
        return json.dumps(data)
    return str(data)


def _escape_data(data: Any) -> str:
    """
    Removes `%, \r, \n` characters from a string.

    Copied from: https://github.com/actions/runner/blob/407a347f831483f85b88eea0f0ac12f7ddbab5a8/src/Runner.Common/ActionCommand.cs#L19-L24

    :param data: Any type of data to be escaped e.g. string, number, list, dict
    :returns: string after escaping
    """
    return (
        _make_string(data).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    )


def _escape_property(data: Any) -> str:
    """
    Removes `%, \r, \n, :, ,` characters from a string.

    Copied from: https://github.com/actions/runner/blob/407a347f831483f85b88eea0f0ac12f7ddbab5a8/src/Runner.Common/ActionCommand.cs#L26-L33

    :param data: Any type of data to be escaped e.g. string, number, list, dict
    :returns: string after escaping
    """
    return _escape_data(data).replace(":", "%3A").replace(",", "%2C")


def _clean_markdown_string(markdown_string: str) -> str:
    """
    Removes `%25, %0D, %0A` characters from a string.

    :param markdown_string: string with markdown content
    :returns: string after escaping
    """
    return (
        str(markdown_string)
        .replace("%25", "%")
        .replace("%0D", "\r")
        .replace("%0A", "\n")
    )


def _to_camel_case(text: str) -> str:
    """
    Transforms a snake case string to camel case.

    :param text: snake cased string
    :returns: camel cased string
    """
    return f"{text[:1].lower()}{text.title().replace('_', '')[1:]}"


def _build_options_string(**kwargs: Any) -> str:
    return ",".join(
        f"{_to_camel_case(key)}={_escape_property(value)}"
        for key, value in kwargs.items()
        if value is not None
    )


def _build_file_input(name: str, value: Any) -> bytes:
    return (
        f"{_escape_property(name)}"
        f"<<{ACTION_ENV_DELIMITER}\n"
        f"{_escape_data(value)}\n"
        f"{ACTION_ENV_DELIMITER}\n".encode("utf-8")
    )


def set_output(name: str, value: Any, use_subprocess: Union[bool, None] = None) -> None:
    """
    sets out for your workflow using GITHUB_OUTPUT file.

    :param name: name of the output
    :param value: value of the output
    :returns: None
    """
    if use_subprocess is not None:
        warn(
            "Argument `use_subprocess` for `set_output()` is deprecated and "
            "going to be removed in the next version.",
            DeprecationWarning,
        )

    with open(os.environ["GITHUB_OUTPUT"], "ab") as f:
        f.write(_build_file_input(name, value))


def echo(message: Any, use_subprocess: bool = False) -> None:
    """
    prints a message to the GitHub Actions shell.

    Template: {message}
    Example: echo "info message"

    :param message: Any type of message e.g. string, number, list, dict
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    message = str(message)

    if use_subprocess or COMMANDS_USE_SUBPROCESS:
        subprocess.run(["echo", message])
    else:
        print(message)


def debug(message: str, use_subprocess: bool = False) -> None:
    """
    prints a debug message in the GitHub Actions shell.

    Template: ::debug::{message}
    Example: echo "::debug::Set the Octocat variable"

    :param message: message string
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    _print_command(
        "debug", message, use_subprocess=use_subprocess, escape_message=False
    )


def notice(
    message: str,
    title: Union[str, None] = None,
    file: Union[str, None] = None,
    col: Union[int, None] = None,
    end_column: Union[int, None] = None,
    line: Union[int, None] = None,
    end_line: Union[int, None] = None,
    use_subprocess: bool = False,
) -> None:
    """
    prints a notice message in the GitHub Actions shell.

    Template: ::notice file={name},line={line},endLine={endLine},title={title}::{message}
    Example: echo "::notice file=app.js,line=1,col=5,endColumn=7::Missing semicolon"

    :param message: Message to display
    :param title: Custom title
    :param file: Filename in the repository
    :param col: Column number, starting at 1
    :param end_column: End column number
    :param line: Line number, starting at 1
    :param end_line: End line number
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    _print_command(
        "notice",
        message,
        options_string=_build_options_string(
            title=title,
            file=file,
            col=col,
            end_column=end_column,
            line=line,
            end_line=end_line,
        ),
        use_subprocess=use_subprocess,
        escape_message=False,
    )


def warning(
    message: str,
    title: Union[str, None] = None,
    file: Union[str, None] = None,
    col: Union[int, None] = None,
    end_column: Union[int, None] = None,
    line: Union[int, None] = None,
    end_line: Union[int, None] = None,
    use_subprocess: bool = False,
) -> None:
    """
    prints a warning message in the GitHub Actions shell.

    Template: ::warning file={name},line={line},endLine={endLine},title={title}::{message}
    Example: echo "::warning file=app.js,line=1,col=5,endColumn=7::Missing semicolon"

    :param message: Message to display
    :param title: Custom title
    :param file: Filename in the repository
    :param col: Column number, starting at 1
    :param end_column: End column number
    :param line: Line number, starting at 1
    :param end_line: End line number
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    _print_command(
        "warning",
        message,
        options_string=_build_options_string(
            title=title,
            file=file,
            col=col,
            end_column=end_column,
            line=line,
            end_line=end_line,
        ),
        use_subprocess=use_subprocess,
        escape_message=False,
    )


def error(
    message: str,
    title: Union[str, None] = None,
    file: Union[str, None] = None,
    col: Union[int, None] = None,
    end_column: Union[int, None] = None,
    line: Union[int, None] = None,
    end_line: Union[int, None] = None,
    use_subprocess: bool = False,
) -> None:
    """
    prints an error message in the GitHub Actions shell.

    Template: ::error file={name},line={line},endLine={endLine},title={title}::{message}
    Example: echo "::error file=app.js,line=1,col=5,endColumn=7::Missing semicolon"

    :param message: Message to display
    :param title: Custom title
    :param file: Filename in the repository
    :param col: Column number, starting at 1
    :param end_column: End column number
    :param line: Line number, starting at 1
    :param end_line: End line number
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    _print_command(
        "error",
        message,
        options_string=_build_options_string(
            title=title,
            file=file,
            col=col,
            end_column=end_column,
            line=line,
            end_line=end_line,
        ),
        use_subprocess=use_subprocess,
        escape_message=False,
    )


def save_state(name: str, value: Any, use_subprocess: Union[bool, None] = None) -> None:
    """
    sets state for your workflow using $GITHUB_STATE file
    for sharing it with your workflow's pre: or post: actions.

    :param name: Name of the state environment variable (e.g: STATE_{name})
    :param value: value of the state environment variable
    :returns: None
    """
    if use_subprocess is not None:
        warn(
            "Argument `use_subprocess` for `save_state()` is deprecated and "
            "going to be removed in the next version.",
            DeprecationWarning,
        )

    with open(os.environ["GITHUB_STATE"], "ab") as f:
        f.write(_build_file_input(name, value))


def get_state(name: str) -> Union[str, None]:
    """
    gets environment variable value for the state.

    :param name: Name of the state environment variable (e.g: STATE_{name})
    :returns: state value or None
    """
    return os.environ.get(f"STATE_{name}")


def get_user_input(name: str) -> Union[str, None]:
    """
    gets user input from environment variables.

    :param name: Name of the user input
    :returns: input value or None
    """
    return os.environ.get(f"INPUT_{name.upper()}")


def start_group(title: str, use_subprocess: bool = False) -> None:
    """
    creates an expandable group in GitHub Actions log.

    Template: ::group::{title}
    Example: echo "::group::My title"

    :param title: title of the group
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    _print_command("group", title, use_subprocess=use_subprocess, escape_message=False)


def end_group(use_subprocess: bool = False) -> None:
    """
    closes an expandable group in GitHub Actions log.

    Template: ::endgroup::
    Example: echo "::endgroup::"

    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    message = f"{COMMAND_MARKER}endgroup{COMMAND_MARKER}"

    if use_subprocess or COMMANDS_USE_SUBPROCESS:
        subprocess.run(["echo", message])
    else:
        print(message)


@contextmanager
def group(title: str, use_subprocess: bool = False) -> Generator[Any, None, None]:
    """
    creates and closes an expandable group in GitHub Actions log.

    :param title: title of the group
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    start_group(title, use_subprocess=use_subprocess)
    yield
    end_group(use_subprocess=use_subprocess)


def add_mask(value: Any, use_subprocess: bool = False) -> None:
    """
    masking a value prevents a string or variable from being printed in the log.

    Template: ::add-mask::{value}
    Example: echo "::add-mask::Mona The Octocat"

    :param value: value to mask
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    _print_command("add-mask", value, use_subprocess=use_subprocess)


def begin_stop_commands(
    token: Union[str, None] = None, use_subprocess: bool = False
) -> str:
    """
    stops processing any workflow commands between this and `end_stop_commands()`.

    Template: ::stop-commands::{token}
    Example: echo "::stop-commands::12345"

    :param token: token to use for the stop command
    :param use_subprocess: use subprocess module to echo command
    :returns: token
    """
    if not token:
        token = str(uuid.uuid1())

    _print_command(
        "stop-commands", token, escape_message=False, use_subprocess=use_subprocess
    )

    return token


def end_stop_commands(token: str, use_subprocess: bool = False) -> None:
    """
    stops processing any workflow commands between this and `begin_stop_commands()`

    Template: ::{token}::
    Example: echo "::{12345}::"

    :param token: token used for the stop command
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    message = f"{COMMAND_MARKER}{token}{COMMAND_MARKER}"

    if use_subprocess or COMMANDS_USE_SUBPROCESS:
        subprocess.run(["echo", message])
    else:
        print(message)


@contextmanager
def stop_commands(
    token: Union[str, None] = None, use_subprocess: bool = False
) -> Generator[Any, None, None]:
    """
    stops processing GitHub action commands within this context manager.

    :param token: token to use for the stop command
    :param use_subprocess: use subprocess module to echo command
    :returns: None
    """
    stop_token = begin_stop_commands(token=token, use_subprocess=use_subprocess)
    yield
    end_stop_commands(stop_token, use_subprocess=use_subprocess)


def set_env(name: str, value: Any) -> None:
    """
    sets an environment variable for your workflows $GITHUB_ENV file.

    :param name: name of the environment variable
    :param value: value of the environment variable
    :returns: None
    """
    with open(os.environ["GITHUB_ENV"], "ab") as f:
        f.write(_build_file_input(name, value))


def get_workflow_environment_variables() -> Dict[str, Any]:
    """
    get a dictionary of all environment variables set in the GitHub Actions workflow.

    :returns: dictionary of all environment variables
    """
    environment_variable_dict = {}
    marker = f"<<{ACTION_ENV_DELIMITER}"

    with open(os.environ["GITHUB_ENV"], "rb") as file:
        for line in file:
            decoded_line: str = line.decode("utf-8")

            if marker in decoded_line:
                name, *_ = decoded_line.strip().split("<<")

                try:
                    decoded_value = next(file).decode("utf-8").strip()
                except StopIteration:
                    break
            environment_variable_dict[name] = decoded_value
    return environment_variable_dict


def get_env(name: str) -> Any:
    """
    gets the value of an environment variable set in the GitHub Actions workflow.

    :param name: name of the environment variable
    :returns: value of the environment variable or None
    """
    return os.environ.get(name) or get_workflow_environment_variables().get(name)


def append_job_summary(markdown_text: str) -> None:
    """
    appends summery of the job to the GitHub Action Summary page.

    :param markdown_text: string with Markdown text
    :returns: None
    """
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
        f.write(f"{_clean_markdown_string(markdown_text)}\n")


def overwrite_job_summary(markdown_text: str) -> None:
    """
    overwrites summary of the job for the GitHub Action Summary page.

    :param markdown_text: string with Markdown text
    :returns: None
    """
    with open(os.environ["GITHUB_STEP_SUMMARY"], "w") as f:
        f.write(f"{_clean_markdown_string(markdown_text)}\n")


def remove_job_summary() -> None:
    """
    removes summary file for the job.

    :returns: None
    """
    try:
        os.remove(os.environ["GITHUB_STEP_SUMMARY"])
    except (KeyError, FileNotFoundError):
        pass


def add_system_path(path: str) -> None:
    """
    adds a path to the system path (`GITHUB_PATH`).

    :param path: path string to set
    :returns: None
    """
    with open(os.environ["GITHUB_PATH"], "a") as f:
        f.write(f"{path}")


@lru_cache(maxsize=1)
def event_payload() -> Dict[str, Any]:
    """
    gets GitHub event payload data.

    :returns: dictionary of event payload
    """
    with open(os.environ["GITHUB_EVENT_PATH"]) as f:
        data: Dict[str, Any] = json.load(f)
    return data
