"use client";

import { useState } from "react";
import { streamRun, API_BASE } from "@/lib/api";
import { RunEvent, Totals, Budget } from "@/lib/types";
import DagView from "./DagView";
import BudgetMeters from "./BudgetMeters";

const DEFAULT_BUDGET: Budget = {
  max_depth: 2,
  max_react_steps: 4,
  max_spend_usd: 0.5,
  max_wall_seconds: 120,
  max_subscription_prompts: 50,
};

function loadBudget(): Budget {
  if (typeof window === "undefined") return DEFAULT_BUDGET;
  try {
    const s = window.localStorage.getItem("orchestrait.budget");
    if (s) return { ...DEFAULT_BUDGET, ...JSON.parse(s) };
  } catch {
    /* ignore */
  }
  return DEFAULT_BUDGET;
}

export default function RunView() {
  const [prompt, setPrompt] = useState("Compute 17 * 23, then double-check the result.");
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [totals, setTotals] = useState<Totals | null>(null);
  const [hit, setHit] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const budget = loadBudget();

  async function run() {
    setEvents([]);
    setTotals(null);
    setHit(null);
    setAnswer("");
    setRunning(true);
    try {
      await streamRun(prompt, budget, (e) => {
        setEvents((prev) => [...prev, e]);
        if (e.type === "budget_tick" && e.totals) setTotals(e.totals);
        if (e.type === "run_done") {
          if (e.totals) setTotals(e.totals);
          setHit(e.budget_hit ?? null);
          setAnswer(e.answer ?? "");
        }
      });
    } catch (err) {
      setAnswer(`Error: ${String(err)} — is the API running at ${API_BASE}?`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="row">
      <div className="grow col">
        <div className="panel">
          <h2>Prompt</h2>
          <textarea rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          <div style={{ marginTop: 8 }}>
            <button className="primary" onClick={run} disabled={running}>
              {running ? "Running…" : "Run"}
            </button>
          </div>
        </div>
        <DagView events={events} />
      </div>
      <div className="col" style={{ width: 340 }}>
        <BudgetMeters totals={totals} budget={budget} hit={hit} />
        <div className="panel">
          <h2>Answer</h2>
          {answer ? <div className="answer">{answer}</div> : <div className="muted">Run a prompt to watch the plan execute.</div>}
        </div>
      </div>
    </div>
  );
}
