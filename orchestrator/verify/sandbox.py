"""Swappable sandbox boundary for running model-produced code (verification
spec, D12). v1 = subprocess + POSIX rlimits + a hard wall-clock kill. The
interface is the load-bearing part; a container/microVM backend can replace
`SubprocessSandbox` without touching callers."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class Limits:
    cpu_seconds: int = 5
    mem_bytes: int = 512 * 1024 * 1024
    wall_seconds: float = 5.0


@dataclass
class SandboxResult:
    ok: bool
    detail: str = ""
    returncode: int | None = None
    timed_out: bool = False


class Sandbox(Protocol):
    async def run_python(self, files: dict[str, str], entry: str, limits: Limits) -> SandboxResult: ...


def _rlimit_preexec(limits: Limits):
    import resource

    def preexec():  # pragma: no cover - runs in the child process
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
        except Exception:
            pass
        try:
            if limits.mem_bytes:
                resource.setrlimit(resource.RLIMIT_AS, (limits.mem_bytes, limits.mem_bytes))
        except Exception:
            pass

    return preexec


class SubprocessSandbox:
    async def run_python(self, files: dict[str, str], entry: str, limits: Limits) -> SandboxResult:
        with tempfile.TemporaryDirectory() as d:
            for name, content in files.items():
                (Path(d) / name).write_text(content)
            preexec = _rlimit_preexec(limits) if os.name == "posix" else None
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    entry,
                    cwd=d,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={"PYTHONPATH": d, "PATH": os.environ.get("PATH", "")},
                    preexec_fn=preexec,
                )
            except Exception as e:  # pragma: no cover
                return SandboxResult(ok=False, detail=f"spawn failed: {e}")
            try:
                out, err = await asyncio.wait_for(proc.communicate(), timeout=limits.wall_seconds)
            except asyncio.TimeoutError:
                proc.kill()
                try:
                    await proc.wait()
                except Exception:
                    pass
                return SandboxResult(ok=False, detail="wall-clock timeout", timed_out=True)
            detail = (out + err).decode(errors="replace")[:4000]
            return SandboxResult(ok=proc.returncode == 0, detail=detail, returncode=proc.returncode)
