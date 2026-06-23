"""Verifier protocol. A verifier maps (step, output) -> Verdict; `failed` is the
only escalation trigger (verification spec)."""

from __future__ import annotations

from typing import Protocol

from ..types import Step, Verdict


class Verifier(Protocol):
    async def verify(self, step: Step, output: str) -> Verdict: ...
