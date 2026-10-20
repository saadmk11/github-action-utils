# Changelog

## 2.0.0

### Breaking changes

- **Python 3.11 or newer is required.** Support for Python 3.6–3.10 has ended.
- Standard-library and typing names are no longer part of the public API.
  Import them directly from the standard library.
- Output, state, and environment files now store raw values. Literal `%`, `%0A`,
  carriage returns, line breaks, Unicode, and whitespace are preserved instead
  of being percent-encoded.
- Job summaries preserve literal Markdown, including `%25`, `%0D`, and `%0A`.
  These sequences are no longer decoded.
- Log commands escape message text so embedded line breaks cannot introduce
  additional commands. `echo()` continues to print raw text.
- Invalid file-command names and stop tokens raise `ValueError` before writing.
  File-command names must be nonempty and exclude `=`, `<<`, CR, LF, and NUL.
  Malformed pending environment records raise `ValueError`.
- PATH entries containing NUL are rejected. Subprocess failures now propagate
  as `subprocess.CalledProcessError`.

### Added

- Live, read-only environment access through `vars`, `WorkflowVariables`,
  `GitHubVariables`, and `RunnerVariables`. Text values remain strings; flags
  have explicit boolean values. `is_github_action()` detects GitHub Actions.
- `get_boolean_input()` and `get_multiline_input()`, with required-input,
  whitespace, and empty-line options. `get_user_input()` gains optional
  `required` and `trim_whitespace` arguments; its defaults are unchanged.
- `set_command_echo()` for runner command diagnostics and `fail()` for an error
  annotation followed by exit status `1`.
- `add_problem_matcher()` and `remove_problem_matcher()` for tool annotations.
- `declare_file_artifact()`, `declare_oci_artifact()`,
  `get_workflow_artifacts()`, and immutable `ArtifactSubject` metadata. These
  require runner support and record identities without uploading files or images.
- Text `PathLike` support and optional `strict=True` validation in
  `add_system_path()`.
- Inline type annotations and `py.typed` for installed-package type checking.

### Fixed

- Multiline file records use unique, collision-checked delimiters and UTF-8
  without losing leading BOM characters or trailing newlines in values.
- Pending environment reads handle simple and multiline records, leading UTF-8
  BOMs, empty values, and duplicate names. The last value for a name wins.
- `get_env()` preserves an empty process value and returns `None` for missing
  local values. `get_workflow_environment_variables()` returns an empty
  dictionary when the `GITHUB_ENV` path is unset or empty.
- `group()` closes its log group and `stop_commands()` restores command
  processing when the context body raises. Generated stop tokens use UUID4.
- Console output is flushed. Subprocess mode uses the current Python interpreter
  and standard input, avoiding shell interpretation, command-line length limits,
  and platform-specific `echo` behavior.
- PATH writes add missing record terminators while preserving existing batches.
- Input names containing spaces can use underscore-separated `INPUT_*` keys;
  an existing literal key still takes precedence. Hyphens remain unchanged.

### Development and releases

- Move to a `src` package layout, `pyproject.toml`, uv builds and publishing,
  and locked development dependencies. The package has no runtime dependencies.
- Use Python 3.15 for development. CI covers Python 3.11–3.15 on Linux, Windows,
  and macOS, with Ruff, strict mypy, and full statement and branch coverage.
- Check clean wheel/source installs, installed typing, and upgrades from 1.1.0.
  A feature showcase checks cross-step values and action main/post state.
- Publish with PyPI Trusted Publishing after validating the release tag and
  distributions. Verify the published package in a clean environment.

### Upgrading from 1.1.0

1. Update workflows to Python 3.11 or newer, then upgrade the package to 2.0.0.
2. Pass raw values to file writers and job-summary helpers. Remove workarounds
   that manually encode or decode percent sequences and line breaks.
3. Use `echo()` inside `stop_commands()` when printing text that must remain
   literal, including command-looking text.
4. Check custom file-command names and stop tokens against the validation rules
   in the [README](README.md#configuration).
5. Remove the deprecated `use_subprocess` argument from `set_output()` and
   `save_state()`. It remains accepted with a `DeprecationWarning`; both
   functions always write runner files.

Existing package functions, public call signatures, the mutable
`COMMANDS_USE_SUBPROCESS` setting, and event-payload caching remain available.
`set_env()` and PATH changes still apply to later steps; they do not change the
current Python process.

## 1.1.0

- [#13](https://github.com/saadmk11/github-action-utils/pull/13): Write
  `save_state()` and `set_output()` values through runner environment files.

## 1.0.2

- [#9](https://github.com/saadmk11/github-action-utils/pull/9): Forward
  `use_subprocess` when `group()` calls `end_group()`.
- [#10](https://github.com/saadmk11/github-action-utils/pull/10): Reorganize
  the documentation.

## 1.0.1

- [#3](https://github.com/saadmk11/github-action-utils/pull/3): Stop escaping
  log messages.
- [#4](https://github.com/saadmk11/github-action-utils/pull/4): Add subprocess
  mode for workflow commands.
- [#5](https://github.com/saadmk11/github-action-utils/pull/5): Add Changelog CI.
