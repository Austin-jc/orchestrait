"""Name -> Verifier registry, resolved by `step.verifier` on the execution
path."""

from __future__ import annotations

from .base import Verifier


class VerifierRegistry:
    def __init__(self, verifiers: dict[str, Verifier] | None = None) -> None:
        self._by_name: dict[str, Verifier] = dict(verifiers or {})

    def register(self, name: str, verifier: Verifier) -> None:
        self._by_name[name] = verifier

    def get(self, name: str) -> Verifier:
        if name not in self._by_name:
            raise KeyError(f"No verifier named '{name}'")
        return self._by_name[name]

    def names(self) -> list[str]:
        return sorted(self._by_name)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name
