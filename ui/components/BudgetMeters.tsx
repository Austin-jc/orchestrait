"use client";

import { Totals, Budget } from "@/lib/types";

export default function BudgetMeters({
  totals,
  budget,
  hit,
}: {
  totals: Totals | null;
  budget: Budget;
  hit: string | null;
}) {
  const meters = [
    { key: "max_spend_usd", label: "Spend", used: totals?.usd ?? 0, max: budget.max_spend_usd, fmt: (n: number) => `$${n.toFixed(4)}` },
    { key: "max_wall_seconds", label: "Wall-clock", used: totals?.wall_seconds ?? 0, max: budget.max_wall_seconds, fmt: (n: number) => `${n.toFixed(1)}s` },
    { key: "max_subscription_prompts", label: "Subscription prompts", used: totals?.subscription_prompts ?? 0, max: budget.max_subscription_prompts, fmt: (n: number) => `${n}` },
  ];
  return (
    <div className="panel">
      <h2>Budget</h2>
      {meters.map((m) => {
        const pct = m.max > 0 ? Math.min(100, (m.used / m.max) * 100) : 0;
        const isHit = hit === m.key;
        return (
          <div key={m.key} className={isHit ? "meter hit" : "meter"}>
            <div className="label">
              <span>{m.label}{isHit ? " · halted" : ""}</span>
              <span>{m.fmt(m.used)} / {m.fmt(m.max)}</span>
            </div>
            <div className="bar"><div className="fill" style={{ width: `${pct}%` }} /></div>
          </div>
        );
      })}
    </div>
  );
}
