"""Read and write UTF-8 runner command files."""

import os
import uuid
from typing import Literal

PathInput = str | os.PathLike[str]


def validate_single_line(value: str, label: str) -> None:
    """Reject values that cannot be represented by exactly one record."""
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    if not value or any(character in value for character in ("\r", "\n", "\0")):
        raise ValueError(f"{label} must be nonempty and contain no CR, LF, or NUL")


def append_line(path: str, value: str) -> None:
    """Encode before opening so encoding errors cannot partially write a record."""
    record = (value + os.linesep).encode("utf-8")
    with open(path, "ab") as file:
        file.write(record)


def _build_file_input(name: str, value: str) -> bytes:
    """Serialize one file command without applying stdout-command escaping.

    Reject names that could create another record. A delimiter absent from both
    the name and value keeps arbitrary text, including terminal newlines, intact.
    Native line endings match the runner's platform-specific file parser.
    """
    if not name or any(part in name for part in ("=", "<<", "\r", "\n", "\0")):
        raise ValueError(
            "File command names must be nonempty and contain no =, <<, CR, LF, or NUL"
        )

    delimiter = f"ghadelimiter_{uuid.uuid4().hex}"
    while delimiter in name or delimiter in value:
        delimiter = f"ghadelimiter_{uuid.uuid4().hex}"
    newline = os.linesep
    # A leading U+FEFF in a name is data, not a UTF-8 file signature.
    prefix = newline if name.startswith("\ufeff") else ""
    return f"{prefix}{name}<<{delimiter}{newline}{value}{newline}{delimiter}{newline}".encode()


def _write_file_command(environment_variable: str, name: str, value: str) -> None:
    """Validate and serialize before opening the runner's append-only file."""
    record = _build_file_input(name, value)
    with open(os.environ[environment_variable], "ab") as file:
        file.write(record)


def _read_file_line(text: str, position: int) -> tuple[str, int, int]:
    """Return a line, the next offset, and its newline length, like the runner.

    Windows accepts CRLF and LF framing. Other runners split only on LF, so a
    carriage return in the value remains data. Avoid universal newline decoding.
    """
    end = text.find("\n", position)
    if end == -1:
        return text[position:], len(text), 0
    if os.name == "nt" and end > position and text[end - 1] == "\r":
        return text[position : end - 1], end + 1, 2
    return text[position:end], end + 1, 1


def get_workflow_environment_variables() -> dict[str, str]:
    """Read simple and multiline records from the current step's GITHUB_ENV.

    Preserve whitespace; later duplicate names win. An unset or empty path
    returns {}. File errors propagate; malformed records raise ValueError.
    """
    path = os.environ.get("GITHUB_ENV")
    if not path:
        return {}
    with open(path, encoding="utf-8-sig", newline="") as file:
        text = file.read()

    values: dict[str, str] = {}
    position = 0
    while position < len(text):
        line, position, _ = _read_file_line(text, position)
        if not line:
            continue
        equals = line.find("=")
        heredoc = line.find("<<")
        if equals >= 0 and (heredoc < 0 or equals < heredoc):
            name, value = line.split("=", 1)
            if not name:
                raise ValueError("Invalid environment record: empty name")
        elif heredoc >= 0:
            name, delimiter = line.split("<<", 1)
            if not name or not delimiter:
                raise ValueError("Invalid environment record: empty name or delimiter")
            start = end = position
            while position < len(text):
                line, position, newline_length = _read_file_line(text, position)
                if line == delimiter:
                    value = text[start:end]
                    break
                if not newline_length:
                    raise ValueError(
                        "Invalid environment record: missing closing delimiter"
                    )
                end = position - newline_length
            else:
                raise ValueError(
                    "Invalid environment record: missing closing delimiter"
                )
        else:
            raise ValueError(
                "Invalid environment record: expected NAME=value or NAME<<delimiter"
            )
        values[name] = value
    return values


def append_job_summary(markdown_text: str) -> None:
    """Append raw Markdown and one LF to this step's summary using UTF-8."""
    _write_summary(markdown_text, "ab")


def overwrite_job_summary(markdown_text: str) -> None:
    """Replace this step's summary with raw Markdown and one LF using UTF-8."""
    _write_summary(markdown_text, "wb")


def _write_summary(markdown_text: str, mode: Literal["ab", "wb"]) -> None:
    # Encode first so invalid text cannot truncate an existing summary.
    data = (str(markdown_text) + "\n").encode("utf-8")
    with open(os.environ["GITHUB_STEP_SUMMARY"], mode) as file:
        file.write(data)


def remove_job_summary() -> None:
    """Remove this step's summary, ignoring an absent path or file."""
    try:
        os.remove(os.environ["GITHUB_STEP_SUMMARY"])
    except (KeyError, FileNotFoundError):
        pass


def add_system_path(path: PathInput, *, strict: bool = False) -> None:
    """Queue directories for later steps without changing this process's PATH.

    Accept strings and text PathLike objects; directories need not exist yet.
    The default preserves legacy CR/LF-separated batches and rejects NUL.
    strict=True requires one nonempty entry without CR, LF, or NUL.
    """
    if strict and not isinstance(path, (str, os.PathLike)):
        raise TypeError("PATH entry must be a string or text PathLike object")
    text = os.fspath(path) if isinstance(path, os.PathLike) else str(path)
    if not isinstance(text, str):
        raise TypeError("PATH entries must use text paths, not bytes")
    if strict:
        validate_single_line(text, "PATH entry")
    elif "\0" in text:
        raise ValueError("PATH entries cannot contain NUL")
    if text and not text.endswith(("\r", "\n")):
        text += os.linesep
    if text.startswith("\ufeff"):
        text = os.linesep + text
    record = text.encode("utf-8")
    with open(os.environ["GITHUB_PATH"], "ab") as file:
        file.write(record)
