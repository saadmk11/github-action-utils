# GitHub Action Utils

### Example:

```python
with group_context_manager("My Group"):
    set_output("test_var", "test_value")
    save_state("state", "val")

    debug("Debug message")

    warning(
        "Warning message", title="Warning Title", file="example.py",
        col=1, end_column=2, line=5, end_line=6,
    )
    warning("Another warning message")

    error(
        "Error message", title="Error Title", file="example.py",
        col=1, end_column=2, line=1, end_line=2,
    )
    notice("Another notice message")

    append_job_summary("# Hello World")
    append_job_summary("- Point 1")
    append_job_summary("- Point 2")
```

#### Colorful Grouped Build Log Output
![s3](https://user-images.githubusercontent.com/24854406/180003937-5839856e-09f9-47e7-8b62-f5126a78cad6.png)

#### Log Annotations and Build Summery
![s2](https://user-images.githubusercontent.com/24854406/180003153-99434824-d08c-4a54-9a89-4c6163def1b2.png)

#### Log Annotations Associated with a File
![s](https://user-images.githubusercontent.com/24854406/180003164-12735d03-a452-4bef-96a6-f1dc4298756e.png)
