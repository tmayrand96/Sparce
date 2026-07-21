import os
from unittest.mock import patch

import pytest

from backend.token_provider import EnvTokenProvider


class TestEnvTokenProvider:
    def test_returns_expected_value_when_key_is_present(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-token"}, clear=True):
            provider = EnvTokenProvider()

            assert provider.get_token() == "test-token"

    def test_raises_value_error_when_key_is_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = EnvTokenProvider()

            with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
                provider.get_token()
