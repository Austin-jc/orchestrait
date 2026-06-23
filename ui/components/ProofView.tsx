"use client";

import { useEffect, useState } from "react";
import { getCalibration, runEval, runMeasure } from "@/lib/api";
import { Calibration, EvalReport } from "@/lib/types";

function heatColor(v: number): string {
  const r = Math.round(229 - v * (229 - 46));
  const g = Math.round(83 + v * (160 - 83));
  const b = Math.round(75 + v * (67 - 75));
  return `rgb(${r},${g},${b})`;
}

export default function ProofView() {
  const [cal, setCal] = useState<Calibration | null>(null);
  const [report, setReport] = useState<EvalReport | null>(null);
  const [busy, setBusy] = useState("");

  async function loadCal() {
    try {
      setCal(await getCalibration());
    } catch {
      /* ignore */
    }
  }
  useEffect(() => {
    loadCal();
  }, []);

  async function onMeasure() {
    setBusy("measuring");
    try {
      await runMeasure();
      await loadCal();
    } finally {
      setBusy("");
    }
  }
  async function onEval() {
    setBusy("evaluating");
    try {
      setReport(await runEval());
    } finally {
      setBusy("");
    }
  }

  const entries = cal ? Object.values(cal.entries) : [];
  const workers = Array.from(new Set(entries.map((e) => e.worker_id))).sort((a, b) => a - b);
  const types = Array.from(new Set(entries.map((e) => e.task_type))).sort();
  const nowSec = Date.now() / 1000;

  return (
    <div className="col">
      <div className="panel">
        <h2>Proof — does orchestrating beat a single model?</h2>
        <div className="row">
          <button className="primary" onClick={onEval} disabled={!!busy}>
            {busy === "evaluating" ? "Evaluating…" : "Run eval"}
          </button>
          <button className="ghost" onClick={onMeasure} disabled={!!busy}>
            {busy === "measuring" ? "Measuring…" : "Re-measure calibration"}
          </button>
        </div>
        {report && (
          <div style={{ marginTop: 12 }}>
            <div className="kv"><span>Orchestrator</span><b>{(report.orchestrator * 100).toFixed(0)}%</b></div>
            <div className="kv"><span>Best single worker</span><span>{(report.best_single * 100).toFixed(0)}% (model {String(report.best_single_id)})</span></div>
            <div className="kv">
              <span>Δ vs best single</span>
              <span className={report.delta_vs_best >= 0 ? "delta-pos" : "delta-neg"}>
                {report.delta_vs_best >= 0 ? "+" : ""}{(report.delta_vs_best * 100).toFixed(0)}%
              </span>
            </div>
            <div className="kv">
              <span>Δ vs same model (Baseline A, model {String(report.baseline_worker_id)})</span>
              <span className={report.delta_vs_baseline >= 0 ? "delta-pos" : "delta-neg"}>
                {report.delta_vs_baseline >= 0 ? "+" : ""}{(report.delta_vs_baseline * 100).toFixed(0)}%
              </span>
            </div>
            <table style={{ marginTop: 10 }}>
              <thead>
                <tr>
                  <th>task type</th>
                  <th>orchestrator</th>
                  {Object.keys(report.workers).map((w) => <th key={w}>model {w}</th>)}
                </tr>
              </thead>
              <tbody>
                {report.by_type.map((t) => (
                  <tr key={t.task_type}>
                    <td>{t.task_type}</td>
                    <td><b>{(t.orchestrator * 100).toFixed(0)}%</b></td>
                    {Object.keys(report.workers).map((w) => (
                      <td key={w}>{((t.workers[Number(w)] ?? 0) * 100).toFixed(0)}%</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Calibration heatmap (win-rate · model × task type)</h2>
        {workers.length === 0 ? (
          <div className="muted">No calibration yet — run “Re-measure calibration”.</div>
        ) : (
          <table>
            <thead>
              <tr><th>model</th>{types.map((t) => <th key={t}>{t}</th>)}</tr>
            </thead>
            <tbody>
              {workers.map((w) => (
                <tr key={w}>
                  <td>model {w}</td>
                  {types.map((t) => {
                    const e = cal?.entries[`${w}:${t}`];
                    const stale = e ? nowSec - e.measured_at > (cal?.ttl_seconds ?? 0) : false;
                    return (
                      <td key={t}>
                        {e ? (
                          <span className="cell" style={{ background: heatColor(e.win_rate), color: "#0c0f14" }}>
                            {(e.win_rate * 100).toFixed(0)}%{stale ? " ⚠" : ""}
                          </span>
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
