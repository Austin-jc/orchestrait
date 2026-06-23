"""Normalized string / MCQ-letter equality (verification spec)."""

from __future__ import annotations

import re

from ..types import Step, Verdict


def _normalize(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower()).strip(" .!?\"'")


def _mcq_letter(s: str | None) -> str | None:
    letters = re.findall(r"\b([a-dA-D])\b", s or "")
    return letters[-1].lower() if letters else None


class ExactMatch:
    async def verify(self, step: Step, output: str) -> Verdict:
        expected = _normalize(step.expected or "")
        got = _normalize(output)
        ok = bool(expected) and (got == expected or _mcq_letter(output) == expected)
        return Verdict(
            kind="pass" if ok else "fail",
            score=1.0 if ok else 0.0,
            detail=f"expected={expected!r} got={got!r}",
        )
