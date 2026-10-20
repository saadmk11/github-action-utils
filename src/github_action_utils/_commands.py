"""Serialize and emit stdout workflow commands."""

import subprocess
import sys
from typing import BinaryIO, cast

from ._environment import is_github_action
from ._serialization import escape_data

_RESERVED_STOP_TOKENS = frozenset(
    (
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
        "debug",
        "warning",
        "error",
        "notice",
        "group",
        "endgroup",
        "echo",
    )
)


def _emit(message: str, use_subprocess: bool = False) -> None:
    """Write a line portably without shell interpolation or echo flags."""
    if use_subprocess:
        sys.stdout.flush()
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import shutil, sys; shutil.copyfileobj(sys.stdin.buffer, sys.stdout.buffer)",
            ],
            input=(message + "\n").encode("utf-8"),
            check=True,
        )
    else:
        buffer = cast(BinaryIO | None, getattr(sys.stdout, "buffer", None))
        if is_github_action() and buffer is not None:
            # Windows redirected Python streams can default to an ANSI encoding.
            # The runner consumes UTF-8. Flush text before bypassing its encoding.
            data = (message + "\n").encode("utf-8")
            sys.stdout.flush()
            buffer.write(data)
            sys.stdout.flush()
        else:
            # Respect redirected text-only streams and ordinary local consoles.
            print(message, flush=True)


def _validate_matcher_selector(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("Matcher selector must be a string")
    if not value or "\0" in value:
        raise ValueError("Matcher selector must be nonempty and contain no NUL")


def _validate_stop_token(token: str) -> None:
    """Require an unambiguous command identifier that the runner can resume."""
    if not isinstance(token, str):
        raise TypeError("Stop token must be a string")
    if (
        not token
        or any(part in token for part in (" ", "\r", "\n", "\0", "::"))
        or token.endswith(":")
    ):
        raise ValueError(
            "Stop token cannot be represented as an unambiguous command name"
        )
    if token.lower() in _RESERVED_STOP_TOKENS:
        raise ValueError("Stop token cannot be a reserved workflow command name")


def print_command(
    command: str,
    message: str,
    options: str | None = "",
    use_subprocess: bool = False,
    escape_message: bool = True,
) -> None:
    """Emit a command after applying stdout-only message escaping."""
    if escape_message:
        message = escape_data(message)
    _emit(f"::{command} {options or ''}::{message}", use_subprocess)
