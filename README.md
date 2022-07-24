# GitHub Action Utils

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/saadmk11/github-action-utils?style=flat-square)](https://github.com/saadmk11/github-action-utils/releases/latest)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/saadmk11/github-action-utils/Test?label=Test&style=flat-square)
![Codecov](https://img.shields.io/codecov/c/github/saadmk11/github-action-utils?style=flat-square&token=ugjHXbEKib)
[![GitHub](https://img.shields.io/github/license/saadmk11/github-action-utils?style=flat-square)](https://github.com/saadmk11/github-action-utils/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/saadmk11/github-action-utils?color=success&style=flat-square)](https://github.com/saadmk11/github-action-utils/stargazers)

![Actions Workflow Run](https://user-images.githubusercontent.com/24854406/180658147-9cfddcfe-ef51-40bc-8e0f-1949482e6a09.png)


This package is a collection of python functions that can be used to run [GitHub Action Workflow Commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions) from a python script inside an action workflow run.

## Requirements

**Python:** 3.6, 3.7, 3.8, 3.9, 3.10, 3.11

## Installation

Install `github-action-utils` using pip:

```console
pip install github-action-utils
```

## Available Functions

This section documents all the functions provided by `github-action-utils`. The functions in the package should be used inside a workflow run.

### **`echo(message)`**

Prints specified message to the action workflow console.

**example:**

```python
>> from github_action_utils import echo

>> echo("Hello World")

# Output:
# Hello World
```

### **`debug(message)`**

Prints colorful debug message to the action workflow console.
GitHub Actions Docs: [debug](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-debug-message)

**example:**

```python
>> from github_action_utils import debug

>> debug("Hello World")

# Output:
# ::debug ::Hello World
```

### **`notice(message, title=None, file=None, col=None, end_column=None, line=None, end_line=None)`**

Prints colorful notice message to the action workflow console.
GitHub Actions Docs: [notice](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-notice-message)

**example:**

```python
>> from github_action_utils import notice

>> notice(
    "test message",
    title="test title",
    file="abc.py",
    col=1,
    end_column=2,
    line=4,
    end_line=5,
)

# Output:
# ::notice title=test title,file=abc.py,col=1,endColumn=2,line=4,endLine=5::test message=
```

### **`warning(message, title=None, file=None, col=None, end_column=None, line=None, end_line=None)`**

Prints colorful warning message to the action workflow console.
GitHub Actions Docs: [warning](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-warning-message)

**example:**

```python
>> from github_action_utils import warning

>> warning(
    "test message",
    title="test title",
    file="abc.py",
    col=1,
    end_column=2,
    line=4,
    end_line=5,
)

# Output:
# ::warning title=test title,file=abc.py,col=1,endColumn=2,line=4,endLine=5::test message
```

### **`error(message, title=None, file=None, col=None, end_column=None, line=None, end_line=None)`**

Prints colorful error message to the action workflow console.
GitHub Actions Docs: [error](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-error-message)

**example:**

```python
>> from github_action_utils import error

>> error(
    "test message",
    title="test title",
    file="abc.py",
    col=1,
    end_column=2,
    line=4,
    end_line=5,
)

# Output:
# ::error title=test title,file=abc.py,col=1,endColumn=2,line=4,endLine=5::test message
```

### **`set_output(name, value)`**

Sets an action's output parameter for the running workflow.
GitHub Actions Docs: [set_output](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-output-parameter)

**example:**

```python
>> from github_action_utils import set_output

>> set_output("test_name", "test_value",)

# Output:
# ::set-output name=test_name::test_value
```

### **`save_state(name, value)`**

Creates environment variable for sharing state with workflow's pre: or post: actions.
GitHub Actions Docs: [save_state](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#sending-values-to-the-pre-and-post-actions)

**example:**

```python
>> from github_action_utils import save_state

>> save_state("test_name", "test_value",)

# Output:
# ::save-state name=test_name::test_value
```

### **`get_state(name)`**

Gets state environment variable from running workflow.

**example:**

```python
>> from github_action_utils import get_state

>> get_state("test_name")

# Output:
# test_value
```

### **`get_user_input(name)`**

Gets user input from running workflow.

**example:**

```python
>> from github_action_utils import get_user_input

>> get_user_input("my_input")

# Output:
# my value
```

### **`begin_stop_commands(token=None)` and `end_stop_commands(token)`**

Stops processing any workflow commands. This special command allows you to log anything without accidentally running a workflow command.
GitHub Actions Docs: [stop_commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#stopping-and-starting-workflow-commands)

**example:**

```python
>> from github_action_utils import echo, begin_stop_commands, end_stop_commands, stop_commands

>> begin_stop_commands(token="my_token")
>> echo("Hello World")
>> end_stop_commands("my_token")

# Output:
# ::stop-commands ::my_token
# Hello World
# ::my_token::

# ====================
# Using Stop Commands Context Manager
# ====================

>> with stop_commands(token="my_token"):
...   echo("Hello World")

# Output:
# ::stop-commands ::my_token
# Hello World
# ::my_token::
```

### **`start_group(title)` and `end_group()`**

Creates an expandable group in the workflow log.
GitHub Actions Docs: [group](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#grouping-log-lines)

**example:**

```python
>> from github_action_utils import echo, start_group, end_group, group

>> start_group("My Group Title")
>> echo("Hello World")
>> end_group()

# Output:
# ::group ::My Group Title
# Hello World
# ::endgroup::

# ====================
# Using Group Context Manager
# ====================

>> with group("My Group Title"):
...   echo("Hello World")

# Output:
# ::group ::My Group Title
# Hello World
# ::endgroup::
```

### **`add_mask(value)`**

Masking a value prevents a string or variable from being printed in the workflow console.
GitHub Actions Docs: [add_mask](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#masking-a-value-in-log)

**example:**

```python
>> from github_action_utils import add_mask

>> add_mask("test value")

# Output:
# ::add-mask ::test value
```

### **`set_env(name, value)`**

Creates an environment variable by writing this to the `GITHUB_ENV` environment file which is available to any subsequent steps in a workflow job.
GitHub Actions Docs: [set_env](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-environment-variable)

**example:**

```python
>> from github_action_utils import set_env

>> set_env("my_env", "test value")
```

### **`get_workflow_environment_variables()`**

Gets all environment variables from the `GITHUB_ENV` environment file which is available to the workflow.
GitHub Actions Docs: [set_env](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-environment-variable)

**example:**

```python
>> from github_action_utils import get_workflow_environment_variables

>> get_workflow_environment_variables()

# Output:
# {"my_env": "test value"}
```

### **`get_env(name)`**

Gets all environment variables from `os.environ` or the `GITHUB_ENV` environment file which is available to the workflow.
This can also be used to get [environment variables set by GitHub Actions](https://docs.github.com/en/actions/learn-github-actions/environment-variables#default-environment-variables).
GitHub Actions Docs: [set_env](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-environment-variable)

**example:**

```python
>> from github_action_utils import get_env

>> get_env("my_env")
>> get_env("GITHUB_API_URL")

# Output:
# test value
# https://api.github.com
```

### **`append_job_summary(markdown_text)`**

Sets some custom Markdown for each job so that it will be displayed on the summary page of a workflow run.
GitHub Actions Docs: [append_job_summary](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary)

**example:**

```python
>> from github_action_utils import append_job_summary

>> append_job_summary("# test summary")
```


### **`overwrite_job_summary(markdown_text)`**

Clears all content for the current step, and adds new job summary.
GitHub Actions Docs: [overwrite_job_summary](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#overwriting-job-summaries)

**example:**

```python
>> from github_action_utils import overwrite_job_summary

>> overwrite_job_summary("# test summary")
```

### **`remove_job_summary()`**

completely removes job summary for the current step.
GitHub Actions Docs: [remove_job_summary](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#removing-job-summaries)

**example:**

```python
>> from github_action_utils import remove_job_summary

>> remove_job_summary()
```

### **`add_system_path(path)`**

Prepends a directory to the system PATH variable (`GITHUB_PATH`) and automatically makes it available to all subsequent actions in the current job.
GitHub Actions Docs: [add_system_path](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-system-path)

**example:**

```python
>> from github_action_utils import add_system_path

>> add_system_path("var/path/to/file")
```

### **`event_payload()`**

Get GitHub Event payload that triggered the workflow.

More details: [GitHub Actions Event Payload](https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads)

**example:**

```python
>> from github_action_utils import event_payload

>> event_payload()

# Output:
# {"action": "opened", "number": 1, "pull_request": {"url": "https://api.github.com/repos/octocat/Hello-World/pulls/1"}, "repository": {"url": "https://api.github.com/repos/octocat/Hello-World"}, "sender": {"login": "octocat"}...}
```

## Example

### Example Workflow

```yaml
name: run-python-script

on:
  pull_request:
    branches: [ "main" ]

jobs:
  build:

    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python 3.10
      uses: actions/setup-python@v3
      with:
        python-version: "3.10"

    - name: Install dependencies
      run: python -m pip install github-action-utils

    - name: Run Python Script
      shell: python
      run: |
        import github_action_utils as gha_utils

        with gha_utils.group("My Group"):
            gha_utils.error(
                "Error message", title="Error Title", file="example.py",
                col=1, end_column=2, line=1, end_line=2,
            )
            gha_utils.notice("Another notice message")
            gha_utils.append_job_summary("# Hello World")
```

### Example Code

```python
import github_action_utils as gha_utils

with gha_utils.group("My Group"):
    gha_utils.set_output("test_var", "test_value")
    gha_utils.save_state("state", "val")

    gha_utils.debug("Debug message")

    gha_utils.warning(
        "Warning message", title="Warning Title", file="example.py",
        col=1, end_column=2, line=5, end_line=6,
    )
    gha_utils.warning("Another warning message")

    gha_utils.error(
        "Error message", title="Error Title", file="example.py",
        col=1, end_column=2, line=1, end_line=2,
    )
    gha_utils.notice("Another notice message")

    gha_utils.append_job_summary("# Hello World")
    gha_utils.append_job_summary("- Point 1")
    gha_utils.append_job_summary("- Point 2")
```

#### Colorful Grouped Build Log Output
![s3](https://user-images.githubusercontent.com/24854406/180003937-5839856e-09f9-47e7-8b62-f5126a78cad6.png)

#### Log Annotations and Build Summery
![s2](https://user-images.githubusercontent.com/24854406/180003153-99434824-d08c-4a54-9a89-4c6163def1b2.png)

#### Log Annotations Associated with a File
![s](https://user-images.githubusercontent.com/24854406/180003164-12735d03-a452-4bef-96a6-f1dc4298756e.png)


# License

The code in this project is released under the [MIT License](LICENSE).
