"use client";

import { useEffect, useState } from "react";
import { getPresets, savePreset } from "@/lib/api";
import { Budget } from "@/lib/types";

const DEFAULT: Budget = {
  max_depth: 2,
  max_react_steps: 4,
  max_spend_usd: 0.5,
  max_wall_seconds: 120,
  max_subscription_prompts: 50,
};

const FIELDS: { key: keyof Budget; label: string; step: number }[] = [
  { key: "max_depth", label: "Max replan depth", step: 1 },
  { key: "max_spend_usd", label: "Max spend ($)", step: 0.05 },
  { key: "max_wall_seconds", label: "Max wall-clock (s)", step: 5 },
  { key: "max_subscription_prompts", label: "Max subscription prompts", step: 1 },
];

export default function TuningView() {
  const [budget, setBudget] = useState<Budget>(DEFAULT);
  const [presets, setPresets] = useState<Record<string, { budget?: Budget }>>({});
  const [presetName, setPresetName] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    try {
      const s = localStorage.getItem("orchestrait.budget");
      if (s) setBudget({ ...DEFAULT, ...JSON.parse(s) });
    } catch {
      /* ignore */
    }
    getPresets()
      .then((r) => setPresets(r.presets || {}))
      .catch(() => {});
  }, []);

  function update(key: keyof Budget, v: number) {
    const next = { ...budget, [key]: v };
    setBudget(next);
    localStorage.setItem("orchestrait.budget", JSON.stringify(next));
  }
  async function onSavePreset() {
    if (!presetName) return;
    const r = await savePreset(presetName, { budget });
    setPresets(r.presets);
    setMsg(`Saved preset "${presetName}".`);
  }
  function applyPreset(n: string) {
    const p = presets[n];
    if (p?.budget) {
      const next = { ...DEFAULT, ...p.budget };
      setBudget(next);
      localStorage.setItem("orchestrait.budget", JSON.stringify(next));
      setMsg(`Applied "${n}".`);
    }
  }

  return (
    <div className="row">
      <div className="panel grow">
        <h2>Run parameters</h2>
        {FIELDS.map((f) => (
          <div key={f.key} className="kv" style={{ marginBottom: 8 }}>
            <label>{f.label}</label>
            <input type="number" step={f.step} value={budget[f.key]} onChange={(e) => update(f.key, Number(e.target.value))} />
          </div>
        ))}
        <div className="muted" style={{ fontSize: 12 }}>
          Applied to runs on the Run tab (stored in your browser).
        </div>
      </div>
      <div className="panel" style={{ width: 360 }}>
        <h2>Presets</h2>
        {Object.keys(presets).length === 0 ? (
          <div className="muted">No presets yet.</div>
        ) : (
          Object.keys(presets).map((n) => (
            <div key={n} className="list-item">
              <span>{n}</span>
              <button className="ghost" onClick={() => applyPreset(n)}>Apply</button>
            </div>
          ))
        )}
        <div className="col" style={{ marginTop: 10 }}>
          <input placeholder="preset name" value={presetName} onChange={(e) => setPresetName(e.target.value)} />
          <button className="primary" onClick={onSavePreset}>Save current as preset</button>
          <span className="muted">{msg}</span>
        </div>
      </div>
    </div>
  );
}
