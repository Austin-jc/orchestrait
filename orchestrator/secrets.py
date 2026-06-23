"""Local encrypted secrets store for BYO API keys / tokens (task 3.6).

Keys are encrypted at rest with Fernet. The encryption key comes from
`ORCHESTRAIT_SECRET_KEY` (env) or a local key file (chmod 600). Values are
never logged and never returned by `names()`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from cryptography.fernet import Fernet


class SecretsStore:
    def __init__(
        self,
        path: str | Path = "data/secrets.enc",
        key_path: str | Path = "data/secret.key",
        env_key_var: str = "ORCHESTRAIT_SECRET_KEY",
    ) -> None:
        self.path = Path(path)
        self.key_path = Path(key_path)
        self.env_key_var = env_key_var
        self._fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        env = os.environ.get(self.env_key_var)
        if env:
            return env.encode()
        if self.key_path.exists():
            return self.key_path.read_bytes()
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        _chmod_600(self.key_path)
        return key

    def _read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self._fernet.decrypt(self.path.read_bytes()).decode())
        except Exception:
            return {}

    def _write(self, data: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(self._fernet.encrypt(json.dumps(data).encode()))
        _chmod_600(self.path)

    def set(self, name: str, value: str) -> None:
        data = self._read()
        data[name] = value
        self._write(data)

    def get(self, name: str) -> str | None:
        return self._read().get(name)

    def delete(self, name: str) -> None:
        data = self._read()
        data.pop(name, None)
        self._write(data)

    def names(self) -> list[str]:
        """Secret names only — never values."""
        return sorted(self._read().keys())

    def __repr__(self) -> str:  # never leak values
        return f"SecretsStore(path={self.path!s}, names={self.names()})"


def _chmod_600(p: Path) -> None:
    try:
        os.chmod(p, 0o600)
    except OSError:  # pragma: no cover - platform dependent
        pass
