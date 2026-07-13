from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Mapping, Optional

from dotenv import dotenv_values


class BaseTokenProvider(ABC):
    """Abstract interface for supplying provider tokens to backend engines."""

    @abstractmethod
    def get_token(self) -> Optional[str]:
        """Return a token value, if one is available."""
        raise NotImplementedError


class EnvTokenProvider(BaseTokenProvider):
    """Read tokens from the process environment and a local .env file."""

    def __init__(
        self,
        env_name: str = "GOOGLE_API_KEY",
        env_file: Optional[os.PathLike[str] | str] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.env_name = env_name
        self.env_file = Path(env_file) if env_file is not None else None
        self._env = env

    def get_token(self) -> Optional[str]:
        values = self._load_values()
        token = values.get(self.env_name)
        if not token:
            raise ValueError(f"Missing required token: {self.env_name}")
        return token

    def _load_values(self) -> dict[str, str]:
        values: dict[str, str] = {}

        if self._env is not None:
            values.update({key: str(value) for key, value in self._env.items() if value is not None})

        if self.env_file is not None:
            values.update({key: str(value) for key, value in dotenv_values(self.env_file).items() if value is not None})

        values.update({key: str(value) for key, value in os.environ.items() if value is not None})
        return values
