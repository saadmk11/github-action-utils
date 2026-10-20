# GitHub Action Utils

[![PyPI](https://img.shields.io/pypi/v/github-action-utils?style=flat-square)](https://pypi.org/project/github-action-utils/)
[![Tests](https://img.shields.io/github/actions/workflow/status/saadmk11/github-action-utils/test.yaml?branch=main&style=flat-square)](https://github.com/saadmk11/github-action-utils/actions/workflows/test.yaml)
[![License: MIT](https://img.shields.io/github/license/saadmk11/github-action-utils?style=flat-square)](LICENSE)

Use GitHub Actions workflow commands from Python: annotate logs, share values
between steps, read inputs, and write job summaries.

**Python 3.11+ · Linux, Windows, macOS · No runtime dependencies · Typed**

> [!NOTE]
> See the [changelog](CHANGELOG.md) for breaking changes and upgrade instructions.

**Contents**

[Install](#install) · [Quick start](#quick-start) · [Logging](#logging) ·
[Groups and command control](#groups-and-command-control) · [Step data](#step-data) ·
[Inputs](#inputs) · [Environment and events](#environment-and-events) ·
[Action state](#action-state) · [Artifact identities](#artifact-identities) ·
[Configuration](#configuration) · [Development](#development)

## Install

```sh
python -m pip install github-action-utils
```

Or add it to a uv project:

```sh
uv add github-action-utils
```

## Quick start

Create `.github/workflows/demo.yaml`:

```yaml
name: Python workflow commands
on: workflow_dispatch

permissions:
  contents: read

jobs:
  demo:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7
        with:
          python-version: '3.15'
      - run: python -m pip install github-action-utils
      - name: Prepare a result
        id: prepare
        shell: python
        run: |
          import github_action_utils as gha

          with gha.group("Build"):
              gha.notice("Build complete")
              gha.set_output("version", "1.0.0")
              gha.set_env("PACKAGE_NAME", "demo")
              gha.append_job_summary("## Build\n\nVersion: **1.0.0**")
      - name: Use the result in a later step
        env:
          BUILD_VERSION: ${{ steps.prepare.outputs.version }}
        run: |
          printf '%s %s\n' "$PACKAGE_NAME" "$BUILD_VERSION"
```

The examples below use `import github_action_utils as gha`.

## Logging

| Function | Result |
| --- | --- |
| `echo(message)` | Print ordinary text. |
| `debug(message)` | Emit a debug message; enable [step debug logging](https://docs.github.com/en/actions/how-tos/monitor-workflows/enable-debug-logging) to see it. |
| `notice(message, ...)` | Create a notice annotation. |
| `warning(message, ...)` | Create a warning annotation. |
| `error(message, ...)` | Create an error annotation and return normally. |
| `fail(message)` | Emit an error and exit immediately with status `1`. |
| `set_command_echo(enabled)` | Enable or disable the runner's command diagnostics; accepts a `bool`. |

`notice`, `warning`, and `error` accept the same optional annotation properties:
`title`, `file`, `col`, `end_column`, `line`, and `end_line`.

```python
gha.echo("Starting build")
gha.debug("Checking dependencies")
gha.warning("Unused variable", title="Lint", file="src/app.py", line=12, col=5)
gha.notice("Review this block", file="src/app.py", line=20, end_line=24)
```

Use columns for a single line; GitHub drops column properties for annotations
spanning multiple lines. Pass normal text—command helpers handle escaping.
See the [workflow command reference](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands).

## Groups and command control

### Group related logs

```python
with gha.group("Run checks"):
    gha.echo("Checking formatting")
    gha.echo("Checking types")
```

The group closes even if the body raises. For manual control, use
`start_group(title)` and `end_group()`.

### Mask sensitive values

```python
gha.add_mask("example-secret-value")
gha.echo("example-secret-value")  # GitHub displays the registered value as ***.
```

Register masks **before** printing sensitive values.

### Suspend command processing

`echo()` prints raw text, so command-looking text can be interpreted by GitHub.
Use `stop_commands()` when printing text that should stay literal:

```python
with gha.stop_commands():
    gha.echo("::warning::This remains plain text")
```

Processing resumes even if the body raises. For manual control:

```python
token = gha.begin_stop_commands()
try:
    gha.echo("::error::Also plain text")
finally:
    gha.end_stop_commands(token)
```

`stop_commands(token=None)` and `begin_stop_commands(token=None)` generate random
UUID4 tokens by default. Custom tokens must be unique for the run; prefer the
generated token.

### Register problem matchers

Problem matchers turn matching tool output into annotations.

```python
gha.add_problem_matcher(".github/matchers/compiler.json")
try:
    gha.echo("src/app.py:12: Unused variable")
finally:
    gha.remove_problem_matcher(owner="compiler")
```

`remove_problem_matcher(*, owner=None, path=None)` requires **exactly one**
selector. Use `path=".github/matchers/compiler.json"` to remove matchers from a file.
Relative matcher paths resolve against the workspace.

<details>
<summary>Example matcher file: .github/matchers/compiler.json</summary>

```json
{
  "problemMatcher": [{
    "owner": "compiler",
    "severity": "warning",
    "pattern": [{
      "regexp": "^(.+):([0-9]+): (.+)$",
      "file": 1,
      "line": 2,
      "message": 3
    }]
  }]
}
```

See GitHub's [problem matcher guide](https://github.com/actions/toolkit/blob/main/docs/problem-matchers.md).

</details>

## Step data

### Outputs and environment variables

| Function | Behavior |
| --- | --- |
| `set_output(name, value)` | Set an output for later steps using the producing step's `id`. |
| `set_env(name, value)` | Set an environment variable for later steps in the same job. |
| `get_env(name)` | Read the process environment first, then the current step's pending environment file. Missing values return `None`; an empty process value takes precedence. |
| `get_workflow_environment_variables()` | Read pending values from this step's `GITHUB_ENV` file. Returns a fresh dictionary, or `{}` when the path is unset/empty. |

```python
gha.set_output("files", ["app.whl", "app.tar.gz"])
gha.set_env("BUILD_MESSAGE", "First line\nSecond line: 100%")

pending = gha.get_workflow_environment_variables()
message = gha.get_env("BUILD_MESSAGE")
```

Lists, tuples, and dictionaries become JSON; other values use `str()`. File
values preserve Unicode, whitespace, percent signs, and line breaks. Use nonempty
string names without `=`, `<<`, CR, LF, or NUL.

**Scope:** `set_env()` does not change this Python process's `os.environ` or
`gha.vars`. The pending file contains only this step's queued variables. GitHub
protects `GITHUB_*`/`RUNNER_*` variables and blocks `NODE_OPTIONS` through `GITHUB_ENV`.

### Add directories to PATH

```python
from pathlib import Path

gha.add_system_path(Path.cwd() / "tools", strict=True)
```

`add_system_path(path, *, strict=False)` accepts strings and text `PathLike`
objects. Directories become available in **later steps**; the current process's
PATH stays unchanged. A directory need not exist yet. `strict=True` requires one
nonempty entry without CR, LF, or NUL. The default preserves legacy path batches;
NUL is always rejected.

### Write job summaries

| Function | Behavior |
| --- | --- |
| `append_job_summary(markdown_text)` | Append Markdown and a newline. |
| `overwrite_job_summary(markdown_text)` | Replace this step's summary with Markdown and a newline. |
| `remove_job_summary()` | Delete this step's summary; a missing file is harmless. |

```python
gha.append_job_summary(
    "## Results\n\n| Check | Result |\n| --- | --- |\n| Tests | Passed |"
)
```

Markdown is written as raw UTF-8. Replacement and deletion affect the current
step's summary. [GitHub summary documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-job-summary)

## Inputs

These helpers read `INPUT_*` environment variables:

| Function | Missing optional input | Defaults |
| --- | --- | --- |
| `get_user_input(name, ...)` | `None` | `required=False`, `trim_whitespace=False` |
| `get_boolean_input(name, ...)` | `None` | `required=False`, `trim_whitespace=True` |
| `get_multiline_input(name, ...)` | `[]` | `required=False`, `trim_whitespace=True`, `keep_empty_lines=False` |

```python
target = gha.get_user_input("target", required=True, trim_whitespace=True)
enabled = gha.get_boolean_input("enabled")
files = gha.get_multiline_input("files", required=True)
raw_lines = gha.get_multiline_input(
    "template", trim_whitespace=False, keep_empty_lines=True
)
```

- **Raw:** preserves empty strings and whitespace unless trimming is enabled.
- **Boolean:** accepts `true`/`True`/`TRUE` and `false`/`False`/`FALSE`.
  Empty strings and other spellings raise `ValueError`.
- **Multiline:** splits LF/CRLF, optionally trims each line, and optionally keeps
  empty lines—including a final empty line after a terminal newline.
- **Required:** raises `ValueError` for missing/empty input after the selected
  trimming. Multiline input needs at least one nonempty line.

Names are uppercased; spaces fall back to underscores and hyphens are preserved.
For composite actions and workflow inputs, wire values explicitly:

```yaml
- name: Read inputs
  env:
    INPUT_TARGET: ${{ inputs.target }}
  run: python script.py
```

## Environment and events

### Detect GitHub Actions

```python
if gha.is_github_action():
    gha.notice("Running in GitHub Actions")
else:
    print("Running locally")
```

Detection checks `GITHUB_ACTIONS == "true"` on every call. File-writing helpers
need their runner-provided file paths; missing paths raise `KeyError` and file
errors propagate.

### Read live environment views

```python
print(gha.vars.github.repository)  # str or None
print(gha.vars.github.run_number)  # str or None; numbers stay strings
print(gha.vars.runner.os)  # str or None
print(gha.vars.runner.debug)  # bool
```

`vars` reads `os.environ` on access. Properties are read-only; missing text is
`None` and empty text stays `""`. Boolean flags use exact values:

| Property | True when |
| --- | --- |
| `vars.ci`, `vars.github.actions`, `vars.github.ref_protected` | The corresponding environment value is `"true"`. |
| `vars.runner.debug` | `RUNNER_DEBUG` is `"1"`. |

The public classes `WorkflowVariables`, `GitHubVariables`, and `RunnerVariables`
can also be used as type annotations or instantiated as separate views.

<details>
<summary>All environment properties</summary>

Property names map to their uppercase environment names: for example,
`vars.github.run_id` reads `GITHUB_RUN_ID` and `vars.runner.tool_cache` reads
`RUNNER_TOOL_CACHE`.

| View | Properties |
| --- | --- |
| `vars` | `ci`, `github`, `runner` |
| `vars.github` — action | `action`, `action_path`, `action_repository`, `job` |
| `vars.github` — identity | `actor`, `actor_id`, `triggering_actor`, `repository`, `repository_id`, `repository_owner`, `repository_owner_id` |
| `vars.github` — run | `actions`, `workflow`, `workflow_ref`, `workflow_sha`, `run_id`, `run_number`, `run_attempt`, `retention_days` |
| `vars.github` — refs and events | `ref`, `ref_name`, `ref_type`, `ref_protected`, `base_ref`, `head_ref`, `sha`, `event_name`, `event_path` |
| `vars.github` — URLs and files | `api_url`, `graphql_url`, `server_url`, `workspace`, `env`, `output`, `path`, `step_summary`, `artifacts`, `artifacts_list` |
| `vars.runner` | `arch`, `environment`, `name`, `os`, `temp`, `tool_cache`, `debug` |

</details>

This Python view is separate from GitHub's workflow-expression
[`vars` context](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#vars-context),
which holds configuration variables. Import it explicitly (`gha.vars` or
`from github_action_utils import vars`); wildcard imports preserve built-in `vars()`.

### Read the event payload

```python
payload = gha.event_payload()
print(payload.get("action"))

gha.event_payload.cache_clear()  # Reload on the next call.
```

`event_payload()` loads UTF-8 JSON from `GITHUB_EVENT_PATH` and caches the result.
Calls share the same mutable object. Use `.cache_info()` for cache statistics.

## Action state

| Function | Behavior |
| --- | --- |
| `save_state(name, value)` | Save a value for another lifecycle hook of the same action. |
| `get_state(name)` | Read `STATE_<name>` in the receiving hook; returns `None` when absent. |

In the action's **main hook**:

```python
gha.save_state("cleanup_path", "/tmp/build")
```

In its **post hook**:

```python
cleanup_path = gha.get_state("cleanup_path")
```

State uses the same value conversion as [step data](#step-data). It is scoped to
an action's pre/main/post lifecycle. Local actions support main/post hooks.
Use outputs or environment variables to share values between ordinary steps.
[GitHub state documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#sending-values-to-the-pre-and-post-actions)

## Artifact identities

> [!IMPORTANT]
> These APIs need the runner's conditional artifact-file feature. Exposed file
> paths alone do not prove support. Declarations record identities; they do not
> upload files, push images, or sign artifacts.

| Function or type | Behavior |
| --- | --- |
| `declare_file_artifact(path)` | Queue a plain file path. The runner resolves relative paths against the workspace and computes its identity after the step. |
| `declare_oci_artifact(reference)` | Queue an OCI reference with a full `sha256`, `sha384`, or `sha512` digest (64, 96, or 128 hex characters). An `oci://` prefix is optional; digest hex is normalized to lowercase. |
| `get_workflow_artifacts()` | Read fresh version-1 metadata as a tuple of immutable `ArtifactSubject` values. An empty subjects list returns `()`. |
| `ArtifactSubject(name, digest, kind)` | A named tuple with `name`, `digest` (`algorithm:hex`), and `kind` (`"file"` or `"oci"`). |

On a supported runner:

```python
gha.declare_file_artifact("dist/app.whl")
gha.declare_oci_artifact(
    "ghcr.io/example/app@sha256:" + "a" * 64
)  # Use your image's real digest.
```

In a later step:

```python
for subject in gha.get_workflow_artifacts():
    print(subject.name, subject.digest, subject.kind)
```

Missing artifact-file configuration raises `RuntimeError`; empty/malformed or
unsupported metadata raises `ValueError`. File errors propagate. See GitHub's
[artifact command documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#declaring-workflow-artifacts).

## Configuration

Console helpers accept `use_subprocess=False`. To emit a message through a child
Python process without invoking a shell:

```python
gha.echo("Hello", use_subprocess=True)
```

Set `gha.COMMANDS_USE_SUBPROCESS = True` for all console helpers. The global flag
wins over a per-call `False`. The `COMMANDS_USE_SUBPROCESS` environment variable is
read once at import: **any nonempty string enables it**, including `"false"` and
`"0"`. Set the module flag to `False` to disable that global setting.

<details>
<summary>Compatibility and validation details</summary>

- Python 3.11+ is required. Existing 1.1.0 package functions and call signatures
  remain available. See the [upgrade notes](CHANGELOG.md#upgrading-from-110)
  for behavior changes.
- The old boolean `use_subprocess` argument on `set_output()` and `save_state()`
  emits `DeprecationWarning`; both helpers always write runner files.
- Pending environment reads accept simple and multiline records, including a
  leading UTF-8 BOM. Later duplicate names win; malformed records raise `ValueError`.
- File-command names are validated before writing. Artifact declarations also
  reject CR/LF/NUL, `=`, and trailing whitespace.
- Custom stop tokens reject literal spaces, CR/LF/NUL, `::`, trailing `:`, and
  reserved workflow-command names. Invalid tokens are rejected before emission.
- `CommandTypes` and `LogCommandTypes` are public typing aliases.
  `COMMAND_MARKER` and the legacy `ACTION_ENV_DELIMITER` remain available;
  file writers generate their own collision-checked delimiters.

</details>

## Development

Development uses **Python 3.15**, uv, Ruff, strict mypy, pytest, and tox. CI covers
Python 3.11–3.15 on Linux, Windows, and macOS. The
[feature showcase](.github/workflows/showcase.yaml) demonstrates every public
function, with automated checks, manual display checks, and conditional skips.

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, testing, and releases;
[open an issue](https://github.com/saadmk11/github-action-utils/issues) for bugs.
Licensed under [MIT](LICENSE).
