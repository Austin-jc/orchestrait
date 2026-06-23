"use client";

import { useState } from "react";
import RunView from "@/components/RunView";
import WorkersView from "@/components/WorkersView";
import TuningView from "@/components/TuningView";
import ProofView from "@/components/ProofView";

const TABS = ["Run", "Workers", "Tuning", "Proof"] as const;
type Tab = (typeof TABS)[number];

export default function Page() {
  const [tab, setTab] = useState<Tab>("Run");
  return (
    <main>
      <header className="topbar">
        <h1>Orchestrait</h1>
        <nav>
          {TABS.map((t) => (
            <button key={t} className={tab === t ? "tab active" : "tab"} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>
        <span className="muted" style={{ marginLeft: "auto", fontSize: 12 }}>
          local-first · orchestrating your models beats using one alone
        </span>
      </header>
      <section className="content">
        {tab === "Run" && <RunView />}
        {tab === "Workers" && <WorkersView />}
        {tab === "Tuning" && <TuningView />}
        {tab === "Proof" && <ProofView />}
      </section>
    </main>
  );
}
