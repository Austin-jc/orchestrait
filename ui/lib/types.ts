export type Totals = { usd: number; wall_seconds: number; subscription_prompts: number };

export type PlanStep = {
  worker_id: number;
  subtask: string;
  access: number[] | "all";
  primitive: string;
  verifier?: string | null;
};

export type Plan = { reasoning?: string; steps: PlanStep[]; budget?: Record<string, number> };

export type StepResult = {
  index: number;
  worker_id: number;
  output: string;
  verdict?: string | null;
  score?: number | null;
  children?: StepResult[];
};

export type RunEvent = {
  type: string;
  seq: number;
  index?: number;
  depth?: number;
  worker_id?: number;
  subtask?: string;
  primitive?: string;
  access?: number[] | "all";
  verifier?: string | null;
  kind?: string;
  score?: number;
  result?: StepResult;
  totals?: Totals;
  budget_hit?: string | null;
  answer?: string;
  plan?: Plan;
  prompt?: string;
  requalified?: boolean;
};

export type Worker = {
  id: number;
  name: string;
  kind: string;
  conductor_eligible?: boolean;
  capabilities?: Record<string, number>;
  api_base?: string | null;
  secret_ref?: string | null;
};

export type EvalReport = {
  n: number;
  orchestrator: number;
  workers: Record<string, number>;
  best_single_id: number | null;
  best_single: number;
  delta_vs_best: number;
  baseline_worker_id: number | null;
  delta_vs_baseline: number;
  by_type: { task_type: string; n: number; orchestrator: number; workers: Record<string, number> }[];
};

export type CalEntry = {
  worker_id: number;
  task_type: string;
  win_rate: number;
  avg_cost: number;
  n: number;
  measured_at: number;
  worker_version: string;
};

export type Calibration = { entries: Record<string, CalEntry>; ttl_seconds: number };

export type Budget = {
  max_depth: number;
  max_react_steps: number;
  max_spend_usd: number;
  max_wall_seconds: number;
  max_subscription_prompts: number;
};
