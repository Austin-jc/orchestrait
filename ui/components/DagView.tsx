"use client";

import { useMemo } from "react";
import type { ReactNode } from "react";
import ReactFlow, { Background, Controls, MiniMap, MarkerType } from "reactflow";
import type { Node, Edge } from "reactflow";
import { RunEvent, Plan, StepResult } from "@/lib/types";

type Status = "pending" | "running" | "pass" | "fail" | "escalating";

const FILL: Record<Status, string> = {
  pending: "#1b232e",
  running: "#1f2d44",
  pass: "#16331f",
  fail: "#3a1d1c",
  escalating: "#3a2f12",
};
const STROKE: Record<Status, string> = {
  pending: "#263141",
  running: "#4f86f7",
  pass: "#2ea043",
  fail: "#e5534b",
  escalating: "#d29922",
};

function planFrom(events: RunEvent[]): Plan | null {
  return events.find((e) => e.type === "plan_ready")?.plan ?? null;
}

function nodeBox(id: string, label: ReactNode, status: Status, x: number, y: number): Node {
  return {
    id,
    position: { x, y },
    data: { label },
    style: {
      background: FILL[status],
      border: `1px solid ${STROKE[status]}`,
      borderRadius: 10,
      color: "#e6edf3",
      width: 250,
      padding: 0,
    },
  };
}

function stepLabel(i: number, subtask: string, primitive: string, verifier: string | null | undefined, st: Status): ReactNode {
  return (
    <div className="node">
      <div className="title">#{i} · {st}</div>
      <div className="meta">{(subtask || "").slice(0, 64)}</div>
      <div style={{ marginTop: 4 }}>
        <span className="badge">{primitive}</span>
        {verifier ? <span className="badge">✓ {verifier}</span> : null}
      </div>
    </div>
  );
}

function childLabel(c: StepResult): ReactNode {
  return (
    <div className="node">
      <div className="title">↳ sub · w{c.worker_id} · {c.verdict ?? "done"}</div>
      <div className="meta">{(c.output || "").slice(0, 64)}</div>
    </div>
  );
}

function appendChildren(nodes: Node[], edges: Edge[], parentId: string, children: StepResult[], depth: number, baseY: number) {
  children.forEach((c, k) => {
    const id = `${parentId}.${k}`;
    const st: Status = c.verdict === "pass" ? "pass" : c.verdict === "fail" ? "fail" : "pass";
    nodes.push(nodeBox(id, childLabel(c), st, depth * 320, baseY + (k + 1) * 120));
    edges.push({
      id: `ce-${id}`,
      source: parentId,
      target: id,
      animated: true,
      style: { stroke: "#d29922", strokeDasharray: "4 3" },
      markerEnd: { type: MarkerType.ArrowClosed },
    });
    if (c.children?.length) appendChildren(nodes, edges, id, c.children, depth + 1, baseY + (k + 1) * 120);
  });
}

function buildGraph(events: RunEvent[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const plan = planFrom(events);
  if (!plan) return { nodes, edges };

  const status: Record<number, Status> = {};
  plan.steps.forEach((_, i) => (status[i] = "pending"));
  const doneByIndex: Record<number, StepResult> = {};

  for (const e of events) {
    if (e.depth && e.depth > 0) continue; // top-level only
    if (e.index === undefined) continue;
    if (e.type === "step_started") status[e.index] = "running";
    else if (e.type === "verdict") status[e.index] = e.kind === "pass" ? "pass" : "fail";
    else if (e.type === "escalation") status[e.index] = "escalating";
    else if (e.type === "step_done") {
      if (e.result) doneByIndex[e.result.index] = e.result;
      const v = e.result?.verdict;
      if (v === "pass") status[e.index] = "pass";
      else if (v === "fail") status[e.index] = "fail";
      else if (status[e.index] === "running") status[e.index] = "pass";
    }
  }

  plan.steps.forEach((step, i) => {
    const st = status[i] ?? "pending";
    nodes.push(nodeBox(`n${i}`, stepLabel(i, step.subtask, step.primitive, step.verifier, st), st, 0, i * 160));
    const acc = step.access === "all" ? plan.steps.map((_, j) => j).filter((j) => j < i) : (step.access as number[]);
    (acc || []).forEach((j) => {
      edges.push({ id: `e${j}-${i}`, source: `n${j}`, target: `n${i}`, markerEnd: { type: MarkerType.ArrowClosed } });
    });
    const res = doneByIndex[i];
    if (res?.children?.length) appendChildren(nodes, edges, `n${i}`, res.children, 1, i * 160);
  });

  return { nodes, edges };
}

export default function DagView({ events }: { events: RunEvent[] }) {
  const { nodes, edges } = useMemo(() => buildGraph(events), [events]);
  return (
    <div className="dag">
      <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
        <Background />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  );
}
