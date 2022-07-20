# GitHub Action Utils

A collection of python functions that can be used to run [GitHub Action Workflow Commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions) from a python script.

## Example:

### Example Workflow:

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

### Example Code:

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
