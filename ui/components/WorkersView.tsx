"use client";

import { useEffect, useState } from "react";
import { getConfig, saveWorkers, testWorker, getSecrets, setSecret, deleteSecret } from "@/lib/api";
import { Worker } from "@/lib/types";

export default function WorkersView() {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [json, setJson] = useState("");
  const [tests, setTests] = useState<Record<number, string>>({});
  const [secrets, setSecrets] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [msg, setMsg] = useState("");

  async function refresh() {
    try {
      const cfg = await getConfig();
      setWorkers(cfg.workers);
      setJson(JSON.stringify(cfg.workers, null, 2));
      const s = await getSecrets();
      setSecrets(s.names);
    } catch (e) {
      setMsg(String(e));
    }
  }
  useEffect(() => {
    refresh();
  }, []);

  async function onTest(id: number) {
    try {
      const r = await testWorker(id);
      setTests((t) => ({ ...t, [id]: r.ok ? "✓ ok" : `✗ ${r.reason}` }));
    } catch (e) {
      setTests((t) => ({ ...t, [id]: String(e) }));
    }
  }
  async function onSave() {
    try {
      await saveWorkers(JSON.parse(json));
      setMsg("Saved. Restart the API server to apply.");
    } catch (e) {
      setMsg(`Invalid JSON or save failed: ${e}`);
    }
  }
  async function onAddSecret() {
    if (!name) return;
    try {
      const r = await setSecret(name, value);
      setSecrets(r.names);
      setName("");
      setValue("");
    } catch (e) {
      setMsg(String(e));
    }
  }
  async function onDeleteSecret(n: string) {
    const r = await deleteSecret(n);
    setSecrets(r.names);
  }

  return (
    <div className="row">
      <div className="grow col">
        <div className="panel">
          <h2>Workers</h2>
          {workers.length === 0 ? <div className="muted">No workers — is the API running?</div> : null}
          {workers.map((w) => (
            <div key={w.id} className="list-item">
              <span>
                <b>Model {w.id}</b> · <span className="mono">{w.name}</span> <span className="tag">{w.kind}</span>
                {w.conductor_eligible ? <span className="tag"> conductor</span> : null}
              </span>
              <span>
                <span className="muted" style={{ marginRight: 8 }}>{tests[w.id] ?? ""}</span>
                <button className="ghost" onClick={() => onTest(w.id)}>Test</button>
              </span>
            </div>
          ))}
        </div>
        <div className="panel">
          <h2>Edit workers (JSON)</h2>
          <textarea rows={14} value={json} onChange={(e) => setJson(e.target.value)} />
          <div style={{ marginTop: 8 }}>
            <button className="primary" onClick={onSave}>Save workers</button> <span className="muted">{msg}</span>
          </div>
        </div>
      </div>
      <div className="col" style={{ width: 360 }}>
        <div className="panel">
          <h2>Secrets (encrypted)</h2>
          {secrets.length === 0 ? (
            <div className="muted">No secrets stored.</div>
          ) : (
            secrets.map((n) => (
              <div key={n} className="list-item">
                <span className="mono">{n}</span>
                <button className="ghost" onClick={() => onDeleteSecret(n)}>Delete</button>
              </div>
            ))
          )}
          <div className="col" style={{ marginTop: 10 }}>
            <input placeholder="name (e.g. OPENAI_API_KEY)" value={name} onChange={(e) => setName(e.target.value)} />
            <input placeholder="value" type="password" value={value} onChange={(e) => setValue(e.target.value)} />
            <button className="primary" onClick={onAddSecret}>Store secret</button>
          </div>
          <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
            Encrypted at rest, never logged. Reference by name from a worker&apos;s <span className="mono">secret_ref</span>.
          </div>
        </div>
      </div>
    </div>
  );
}
