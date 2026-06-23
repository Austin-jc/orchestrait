"""Math equivalence: numeric tolerance first, optional symbolic (sympy) fallback
(verification spec). Deterministic, runs inline."""

from __future__ import annotations

import re

from ..types import Step, Verdict

_NUM = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def _last_number(s: str | None) -> float | None:
    matches = _NUM.findall(s or "")
    return float(matches[-1]) if matches else None


class MathEquiv:
    def __init__(self, tol: float = 1e-6) -> None:
        self.tol = tol

    async def verify(self, step: Step, output: str) -> Verdict:
        expected_raw = (step.expected or "").strip()
        got = _last_number(output)
        expected_num = _last_number(expected_raw)
        if got is not None and expected_num is not None:
            if abs(got - expected_num) <= self.tol * max(1.0, abs(expected_num)):
                return Verdict(kind="pass", score=1.0, detail=f"{got} ~= {expected_num}")
        try:  # optional symbolic equivalence
            import sympy

            diff = sympy.simplify(sympy.sympify(output) - sympy.sympify(expected_raw))
            if diff == 0:
                return Verdict(kind="pass", score=1.0, detail="symbolic match")
        except Exception:
            pass
        return Verdict(kind="fail", score=0.0, detail=f"expected {expected_raw!r}, got number {got}")
