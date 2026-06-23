"""Verifier registry and v1 verifiers (verification spec). Verdicts are the only
escalation trigger."""

from .base import Verifier
from .code_exec import CodeExec
from .exact_match import ExactMatch
from .math_equiv import MathEquiv
from .registry import VerifierRegistry
from .sandbox import Limits, Sandbox, SandboxResult, SubprocessSandbox


def default_registry() -> VerifierRegistry:
    return VerifierRegistry(
        {"exact_match": ExactMatch(), "math_equiv": MathEquiv(), "code_exec": CodeExec()}
    )


__all__ = [
    "Verifier",
    "VerifierRegistry",
    "ExactMatch",
    "MathEquiv",
    "CodeExec",
    "Sandbox",
    "SubprocessSandbox",
    "Limits",
    "SandboxResult",
    "default_registry",
]
