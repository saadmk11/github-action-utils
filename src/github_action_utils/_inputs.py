"""Read raw, boolean, and multiline action inputs."""

import os


def get_user_input(
    name: str, *, required: bool = False, trim_whitespace: bool = False
) -> str | None:
    """Read an INPUT_* variable, returning None when an optional input is absent.

    Preserve whitespace by default. Required mode rejects missing or empty
    values after trimming. Spaces fall back to underscores; an existing literal
    key takes precedence. Workflow and composite inputs need environment wiring.
    """
    if not isinstance(name, str):
        raise TypeError("Input name must be a string")
    key = "INPUT_" + name.upper()
    value = os.environ.get(key)
    if value is None:
        value = os.environ.get(key.replace(" ", "_"))
    if value is not None and trim_whitespace:
        value = value.strip()
    if required and not value:
        raise ValueError(f"Required input is missing or empty: {name}")
    return value


def get_boolean_input(
    name: str, *, required: bool = False, trim_whitespace: bool = True
) -> bool | None:
    """Parse the six YAML 1.2 true/false spellings; return None if absent.

    Empty strings and other tokens raise ValueError. Trim whitespace by default.
    """
    value = get_user_input(name, required=required, trim_whitespace=trim_whitespace)
    if value is None:
        return None
    match value:
        case "true" | "True" | "TRUE":
            return True
        case "false" | "False" | "FALSE":
            return False
    raise ValueError(f"Input must be a YAML 1.2 boolean: {name}")


def get_multiline_input(
    name: str,
    *,
    required: bool = False,
    trim_whitespace: bool = True,
    keep_empty_lines: bool = False,
) -> list[str]:
    """Split LF/CRLF input into lines, then trim and optionally discard empties.

    Optional missing inputs return an empty list. When empties are retained,
    terminal newlines produce terminal empty items. Required mode needs at
    least one nonempty item after the selected trimming, even if empties are kept.
    """
    value = get_user_input(name, required=required)
    if value is None:
        return []
    lines = value.replace("\r\n", "\n").split("\n")
    if trim_whitespace:
        lines = [line.strip() for line in lines]
    if required and not any(lines):
        raise ValueError(f"Required input has no nonempty lines: {name}")
    if not keep_empty_lines:
        lines = [line for line in lines if line]
    return lines
