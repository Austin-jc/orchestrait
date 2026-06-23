"""Run produced code against a spec/test file inside the sandbox; pass iff the
spec exits 0 (verification spec). `step.expected` is the path to the spec file;
the produced code is written as `solution.py` for it to import."""

from __future__ import annotations

import re
from pathlib import Path

from ..types import Step, Verdict
from .sandbox import Limits, Sandbox, SubprocessSandbox

_FENCE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)


def _extract_code(output: str) -> str:
    fenced = _FENCE.findall(output or "")
    return fenced[0].strip() if fenced else (output or "")


class CodeExec:
    def __init__(self, sandbox: Sandbox | None = None, limits: Limits | None = None) -> None:
        self.sandbox = sandbox or SubprocessSandbox()
        self.limits = limits or Limits()

    async def verify(self, step: Step, output: str) -> Verdict:
        spec = step.expected
        if not spec or not Path(spec).exists():
            return Verdict(kind="fail", score=0.0, detail=f"spec file not found: {spec}")
        files = {"solution.py": _extract_code(output), "spec_test.py": Path(spec).read_text()}
        result = await self.sandbox.run_python(files, "spec_test.py", self.limits)
        return Verdict(
            kind="pass" if result.ok else "fail",
            score=1.0 if result.ok else 0.0,
            detail=result.detail[:1000],
        )
