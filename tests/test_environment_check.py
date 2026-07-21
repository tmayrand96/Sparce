from unittest.mock import patch

import pytest

from backend.utils.environment_check import EnvironmentDependencyError, verify_system_dependencies


def test_verify_system_dependencies_passes_when_binary_exists():
    with patch("backend.utils.environment_check.shutil.which", return_value="/usr/bin/pdftoppm"):
        verify_system_dependencies(["pdftoppm"])


def test_verify_system_dependencies_raises_for_missing_binary():
    with patch("backend.utils.environment_check.shutil.which", return_value=None):
        with pytest.raises(EnvironmentDependencyError, match="pdftoppm"):
            verify_system_dependencies(["pdftoppm"])
