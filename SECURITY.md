# Security notes

Orchestrait is **local-first**: it runs on your machine with your own
credentials. The two security-sensitive surfaces and how they're handled:

## 1. Model-produced code execution (`code_exec` verifier)

- Untrusted code only ever runs inside the sandbox boundary
  (`orchestrator/verify/sandbox.py`), never in the host process.
- `SubprocessSandbox` runs code in a fresh temp directory (`cwd` isolated from
  the repo), with POSIX `RLIMIT_CPU` / `RLIMIT_AS` limits and a hard
  wall-clock kill. A runaway loop is terminated, not allowed to hang the host
  (`tests/test_code_exec.py`, `tests/test_security.py`).
- The boundary is a swappable interface (D12): a container/microVM backend can
  replace `SubprocessSandbox` without touching callers. For untrusted inputs at
  scale, use a stronger backend — subprocess+rlimits is the v1 default.

## 2. BYO secrets

- API keys / tokens live in an encrypted local store (`orchestrator/secrets.py`,
  Fernet). The on-disk blob is ciphertext; the key file and secrets file are
  `chmod 600` (`tests/test_security.py`).
- `SecretsStore.names()` and `repr()` never return secret values; secrets are
  never written to logs.
- Secrets resolve from environment variables first, then the encrypted store.
  Config files (`config.yaml`) never contain secrets — only `secret_ref` names.

## Subscription / ToS

- The Claude subscription path uses the official `claude -p` headless interface
  with your own token. Do not expose this as a multi-tenant hosted service —
  Anthropic disallows third-party subscription bridging (a hosted tier must use
  metered API keys instead).
