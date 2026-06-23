"""Claude subscription adapter — drives `claude -p` headless so a Pro/Max
subscription (not API credits) backs the call (D3). Cost is one
`subscription_prompt` per call; the budget axis caps it across all roles (D4).

The subprocess runner is injectable so the parsing/usage logic is unit-testable
without a live `claude` CLI.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Awaitable, Callable

from ..types import Usage, WorkerSpec

Runner = Callable[[list[str], str, dict], Awaitable[str]]


class ClaudeSubscriptionAdapter:
    def __init__(
        self,
        spec: WorkerSpec,
        *,
        oauth_token: str | None = None,
        binary: str = "claude",
        extra_args: list[str] | None = None,
        runner: Runner | None = None,
    ) -> None:
        self.spec = spec
        self.oauth_token = oauth_token
        self.binary = binary
        self.extra_args = extra_args or []
        self._runner = runner

    @staticmethod
    def _serialize(messages: list[dict]) -> str:
        parts = []
        for m in messages:
            role = m.get("role", "user")
            if role == "system":
                continue
            prefix = "Assistant" if role == "assistant" else "User"
            parts.append(f"{prefix}: {m['content']}")
        return "\n\n".join(parts)

    @staticmethod
    def _parse(stdout: str) -> str:
        stdout = stdout.strip()
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout  # tolerate plain text
        if isinstance(data, dict):
            return data.get("result") or data.get("text") or data.get("content") or ""
        return str(data)

    async def call(
        self, messages: list[dict], *, max_tokens: int, temperature: float
    ) -> tuple[str, Usage]:
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        prompt = self._serialize(messages)
        args = [self.binary, "-p", "--output-format", "json"]
        if system:
            args += ["--append-system-prompt", system]
        args += self.extra_args
        env = dict(os.environ)
        if self.oauth_token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = self.oauth_token

        t0 = time.monotonic()
        stdout = await self._invoke(args, prompt, env)
        wall = time.monotonic() - t0
        return self._parse(stdout), Usage(wall_seconds=wall, subscription_prompts=1)

    async def _invoke(self, args: list[str], prompt: str, env: dict) -> str:
        if self._runner is not None:
            return await self._runner(args, prompt, env)
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        out, err = await proc.communicate(prompt.encode())
        if proc.returncode != 0:
            raise RuntimeError(f"`claude -p` failed (exit {proc.returncode}): {err.decode()[:500]}")
        return out.decode()

    async def test_connection(self) -> tuple[bool, str]:
        try:
            text, _ = await self.call([{"role": "user", "content": "reply with: ok"}], max_tokens=16, temperature=0.0)
            return bool(text), text[:120] or "empty response"
        except Exception as e:  # pragma: no cover - depends on local claude CLI
            return False, str(e)
