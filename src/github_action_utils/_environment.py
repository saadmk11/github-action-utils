"""Live, read-only GitHub Actions environment values.

Missing text values are None; empty strings stay empty. Boolean properties
compare against the runner's exact flag values.
"""

import os


def is_github_action() -> bool:
    """Return whether the current GITHUB_ACTIONS value is exactly 'true'."""
    return os.environ.get("GITHUB_ACTIONS") == "true"


class GitHubVariables:
    """Read-only GITHUB_* values, with strings retained exactly as supplied."""

    __slots__ = ()

    @property
    def action(self) -> str | None:
        """Current action or step identifier."""
        return os.environ.get("GITHUB_ACTION")

    @property
    def action_path(self) -> str | None:
        """Directory containing the composite action."""
        return os.environ.get("GITHUB_ACTION_PATH")

    @property
    def action_repository(self) -> str | None:
        """Repository containing the current action."""
        return os.environ.get("GITHUB_ACTION_REPOSITORY")

    @property
    def actor(self) -> str | None:
        """Actor whose privileges apply to this run."""
        return os.environ.get("GITHUB_ACTOR")

    @property
    def actor_id(self) -> str | None:
        """Account identifier of the actor."""
        return os.environ.get("GITHUB_ACTOR_ID")

    @property
    def api_url(self) -> str | None:
        """GitHub REST API base URL."""
        return os.environ.get("GITHUB_API_URL")

    @property
    def artifacts(self) -> str | None:
        """File used to declare artifacts for this step."""
        return os.environ.get("GITHUB_ARTIFACTS")

    @property
    def artifacts_list(self) -> str | None:
        """File containing aggregated artifact metadata."""
        return os.environ.get("GITHUB_ARTIFACTS_LIST")

    @property
    def base_ref(self) -> str | None:
        """Base branch for a pull request event."""
        return os.environ.get("GITHUB_BASE_REF")

    @property
    def env(self) -> str | None:
        """Environment command file for the current step."""
        return os.environ.get("GITHUB_ENV")

    @property
    def event_name(self) -> str | None:
        """Event that triggered this workflow."""
        return os.environ.get("GITHUB_EVENT_NAME")

    @property
    def event_path(self) -> str | None:
        """Path to the event payload JSON file."""
        return os.environ.get("GITHUB_EVENT_PATH")

    @property
    def graphql_url(self) -> str | None:
        """GitHub GraphQL API URL."""
        return os.environ.get("GITHUB_GRAPHQL_URL")

    @property
    def head_ref(self) -> str | None:
        """Head branch for a pull request event."""
        return os.environ.get("GITHUB_HEAD_REF")

    @property
    def job(self) -> str | None:
        """Current job identifier."""
        return os.environ.get("GITHUB_JOB")

    @property
    def output(self) -> str | None:
        """Output command file for the current step."""
        return os.environ.get("GITHUB_OUTPUT")

    @property
    def path(self) -> str | None:
        """PATH command file for the current step."""
        return os.environ.get("GITHUB_PATH")

    @property
    def ref(self) -> str | None:
        """Fully qualified reference for the event."""
        return os.environ.get("GITHUB_REF")

    @property
    def ref_name(self) -> str | None:
        """Short reference name."""
        return os.environ.get("GITHUB_REF_NAME")

    @property
    def ref_type(self) -> str | None:
        """Reference kind, such as branch or tag."""
        return os.environ.get("GITHUB_REF_TYPE")

    @property
    def repository(self) -> str | None:
        """Repository in owner/name form."""
        return os.environ.get("GITHUB_REPOSITORY")

    @property
    def repository_id(self) -> str | None:
        """Repository identifier, retained as text."""
        return os.environ.get("GITHUB_REPOSITORY_ID")

    @property
    def repository_owner(self) -> str | None:
        """Repository owner's login."""
        return os.environ.get("GITHUB_REPOSITORY_OWNER")

    @property
    def repository_owner_id(self) -> str | None:
        """Repository owner's account identifier."""
        return os.environ.get("GITHUB_REPOSITORY_OWNER_ID")

    @property
    def retention_days(self) -> str | None:
        """Log and artifact retention period, retained as text."""
        return os.environ.get("GITHUB_RETENTION_DAYS")

    @property
    def run_attempt(self) -> str | None:
        """Run attempt number, retained as text."""
        return os.environ.get("GITHUB_RUN_ATTEMPT")

    @property
    def run_id(self) -> str | None:
        """Workflow run identifier, retained as text."""
        return os.environ.get("GITHUB_RUN_ID")

    @property
    def run_number(self) -> str | None:
        """Workflow run number, retained as text."""
        return os.environ.get("GITHUB_RUN_NUMBER")

    @property
    def server_url(self) -> str | None:
        """GitHub server base URL."""
        return os.environ.get("GITHUB_SERVER_URL")

    @property
    def sha(self) -> str | None:
        """Commit identifier associated with the event."""
        return os.environ.get("GITHUB_SHA")

    @property
    def step_summary(self) -> str | None:
        """Summary file for the current step."""
        return os.environ.get("GITHUB_STEP_SUMMARY")

    @property
    def triggering_actor(self) -> str | None:
        """Actor who initiated this run or rerun."""
        return os.environ.get("GITHUB_TRIGGERING_ACTOR")

    @property
    def workflow(self) -> str | None:
        """Workflow name."""
        return os.environ.get("GITHUB_WORKFLOW")

    @property
    def workflow_ref(self) -> str | None:
        """Workflow file reference."""
        return os.environ.get("GITHUB_WORKFLOW_REF")

    @property
    def workflow_sha(self) -> str | None:
        """Commit containing the workflow file."""
        return os.environ.get("GITHUB_WORKFLOW_SHA")

    @property
    def workspace(self) -> str | None:
        """Workflow working directory."""
        return os.environ.get("GITHUB_WORKSPACE")

    @property
    def actions(self) -> bool:
        """Whether the process is running in GitHub Actions."""
        return is_github_action()

    @property
    def ref_protected(self) -> bool:
        """Whether GITHUB_REF_PROTECTED is exactly 'true'."""
        return os.environ.get("GITHUB_REF_PROTECTED") == "true"


class RunnerVariables:
    """Read-only RUNNER_* values for the current process."""

    __slots__ = ()

    @property
    def arch(self) -> str | None:
        """Runner CPU architecture."""
        return os.environ.get("RUNNER_ARCH")

    @property
    def environment(self) -> str | None:
        """Runner hosting kind, such as github-hosted or self-hosted."""
        return os.environ.get("RUNNER_ENVIRONMENT")

    @property
    def name(self) -> str | None:
        """Runner name."""
        return os.environ.get("RUNNER_NAME")

    @property
    def os(self) -> str | None:
        """Runner operating system."""
        return os.environ.get("RUNNER_OS")

    @property
    def temp(self) -> str | None:
        """Temporary directory for this job."""
        return os.environ.get("RUNNER_TEMP")

    @property
    def tool_cache(self) -> str | None:
        """Directory containing preinstalled tools."""
        return os.environ.get("RUNNER_TOOL_CACHE")

    @property
    def debug(self) -> bool:
        """Whether RUNNER_DEBUG is exactly '1'."""
        return os.environ.get("RUNNER_DEBUG") == "1"


_GITHUB_VARIABLES = GitHubVariables()
_RUNNER_VARIABLES = RunnerVariables()


class WorkflowVariables:
    """Group live os.environ values by GitHub and runner prefixes.

    Pending GITHUB_ENV writes are read through get_env(), not this view.
    """

    __slots__ = ()

    @property
    def ci(self) -> bool:
        """Whether CI is exactly 'true'."""
        return os.environ.get("CI") == "true"

    @property
    def github(self) -> GitHubVariables:
        """Live GITHUB_* environment values."""
        return _GITHUB_VARIABLES

    @property
    def runner(self) -> RunnerVariables:
        """Live RUNNER_* environment values."""
        return _RUNNER_VARIABLES


vars = WorkflowVariables()
"""Shared read-only view; values are read on property access, not import."""
