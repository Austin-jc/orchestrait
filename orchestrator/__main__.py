"""CLI: `python -m orchestrator "your prompt"`. Loads config.yaml, runs the
orchestrator, prints the answer and the run trace."""

from __future__ import annotations

import asyncio
import sys

from .config import load_config
from .factory import build_orchestrator


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or "Say hello to the orchestrator."
    orchestrator = build_orchestrator(load_config())
    answer = asyncio.run(orchestrator.run(prompt))
    print(answer.text)
    print("\n--- trace ---")
    print(answer.trace.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
