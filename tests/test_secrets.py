from orchestrator.secrets import SecretsStore


def test_secrets_roundtrip_and_encrypted_at_rest(tmp_path):
    store = SecretsStore(path=tmp_path / "secrets.enc", key_path=tmp_path / "key")
    store.set("OPENAI_API_KEY", "sk-supersecret-123")

    assert store.get("OPENAI_API_KEY") == "sk-supersecret-123"
    assert "OPENAI_API_KEY" in store.names()
    # names() never leaks values
    assert "sk-supersecret-123" not in "".join(store.names())
    # the on-disk blob is ciphertext, not plaintext
    raw = (tmp_path / "secrets.enc").read_bytes()
    assert b"sk-supersecret-123" not in raw
    # repr never leaks values
    assert "sk-supersecret-123" not in repr(store)

    store.delete("OPENAI_API_KEY")
    assert store.get("OPENAI_API_KEY") is None
