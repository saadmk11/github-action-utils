"""Narrow test decoder for the runner's V2 stdout protocol.

Based on actions/runner b22b4bfead1623f77d7a76f811f4aacb24da313a,
src/Runner.Common/ActionCommand.cs (TryParseV2 and escape mappings). It does not
simulate runner execution, masking, or rendering; hosted checks remain separate.
"""


def _decode(value: str, properties: bool = False) -> str:
    mappings = [("%0D", "\r"), ("%0A", "\n")]
    if properties:
        mappings.extend([("%3A", ":"), ("%2C", ",")])
    mappings.append(("%25", "%"))
    for encoded, decoded in mappings:
        value = value.replace(encoded, decoded)
    return value


def parse_command(record: str) -> tuple[str, dict[str, str], str]:
    """Decode one complete physical line independently of the package writer."""
    assert record.endswith("\n") and record.count("\n") == 1
    line = record[:-2] if record.endswith("\r\n") else record[:-1]
    assert "\r" not in line
    line = line.lstrip()
    assert line.startswith("::")
    separator = line.index("::", 2)
    command, _, properties = line[2:separator].partition(" ")
    options = {}
    for item in properties.strip().split(","):
        key, equals, value = item.partition("=")
        if equals and key and value:
            options[key] = _decode(value, properties=True)
    return command, options, _decode(line[separator + 2 :])
