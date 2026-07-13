import shutil
import sys
from typing import Iterable, List


class EnvironmentDependencyError(RuntimeError):
    """Raised when required system-level dependencies are missing."""


def verify_system_dependencies(dependencies: Iterable[str]) -> None:
    """Ensure required system binaries are present in PATH."""
    missing = [dep for dep in dependencies if not shutil.which(dep)]

    if missing:
        dependency_list = ", ".join(missing)
        raise EnvironmentDependencyError(
            f"Missing system dependencies: {dependency_list}. "
            f"Install them before running the pipeline."
        )
