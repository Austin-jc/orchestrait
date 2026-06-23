"""Security pass (task 8.2): secrets are not world/group readable and the
code-exec sandbox runs isolated from the repo."""

import os
import stat

from orchestrator.secrets import SecretsStore
from orchestrator.types import Step
from orchestrator.verify import CodeExec
from orchestrator.verify.sandbox import Limits


def test_secret_files_are_not_group_or_world_readable(tmp_path):
    s = SecretsStore(path=tmp_path / "secrets.enc", key_path=tmp_path / "key")
    s.set("OPENAI_API_KEY", "sk-x")
    for p in (tmp_path / "secrets.enc", tmp_path / "key"):
        mode = stat.S_IMODE(os.stat(p).st_mode)
        assert mode & 0o077 == 0  # owner-only


async def test_code_exec_sandbox_cannot_see_repo(tmp_path):
    # The spec asserts the repo's pyproject.toml is NOT visible from the sandbox
    # cwd; if isolation holds, the spec exits 0 and the verdict passes.
    spec = tmp_path / "spec_test.py"
    spec.write_text(
        "import os, solution\n"
        "assert not os.path.exists('pyproject.toml'), 'sandbox should not see the repo'\n"
        "print('isolated')\n"
    )
    verdict = await CodeExec(limits=Limits(wall_seconds=15)).verify(
        Step(worker_id=0, subtask="x", expected=str(spec)), "value = 1\n"
    )
    assert verdict.kind == "pass"
