"""Check artifact identities when the runner supplies populated metadata."""

import hashlib
import os
from pathlib import Path

import github_action_utils as gha

CONTENT = b"github-action-utils artifact integration\n"
FILE_NAME = "github-action-utils-artifact-fixture.txt"
OCI_NAME = "ghcr.io/github-action-utils/integration:fixture"
OCI_DIGEST = "sha256:" + "a" * 64


def probe() -> bool:
    """Check for populated, valid artifact metadata."""
    metadata = os.environ.get("GITHUB_ARTIFACTS_LIST")
    if (
        not os.environ.get("GITHUB_ARTIFACTS")
        or not metadata
        or not Path(metadata).read_bytes().strip()
    ):
        return False
    gha.get_workflow_artifacts()
    return True


def write() -> None:
    """Create a fixture and declare its file and OCI identities."""
    path = Path(os.environ["GITHUB_WORKSPACE"]) / FILE_NAME
    path.write_bytes(CONTENT)
    gha.declare_file_artifact(FILE_NAME)
    gha.declare_oci_artifact(OCI_NAME + "@" + OCI_DIGEST)


def verify() -> None:
    """Check the identities returned in a later step's runner metadata."""
    subjects = {subject.name: subject for subject in gha.get_workflow_artifacts()}
    assert subjects[FILE_NAME] == gha.ArtifactSubject(
        FILE_NAME, "sha256:" + hashlib.sha256(CONTENT).hexdigest(), "file"
    )
    assert subjects[OCI_NAME] == gha.ArtifactSubject(OCI_NAME, OCI_DIGEST, "oci")
