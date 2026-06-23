import { RunEvent } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function j(path: string, opts?: RequestInit) {
  const r = await fetch(API_BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

export const getWorkers = () => j("/workers");
export const getConfig = () => j("/config");
export const saveWorkers = (workers: unknown[]) =>
  j("/config/workers", { method: "POST", body: JSON.stringify({ workers }) });
export const testWorker = (id: number) => j(`/workers/${id}/test`, { method: "POST" });

export const getSecrets = () => j("/secrets");
export const setSecret = (name: string, value: string) =>
  j("/secrets", { method: "POST", body: JSON.stringify({ name, value }) });
export const deleteSecret = (name: string) =>
  j(`/secrets/${encodeURIComponent(name)}`, { method: "DELETE" });

export const getCalibration = () => j("/calibration");
export const runEval = () => j("/eval", { method: "POST" });
export const runMeasure = () => j("/measure", { method: "POST" });

export const getPresets = () => j("/presets");
export const savePreset = (name: string, params: unknown) =>
  j("/presets", { method: "POST", body: JSON.stringify({ name, params }) });

export async function streamRun(
  prompt: string,
  budget: unknown,
  onEvent: (e: RunEvent) => void,
): Promise<void> {
  const r = await fetch(API_BASE + "/run/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, budget }),
  });
  if (!r.body) throw new Error("no stream body");
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (line) onEvent(JSON.parse(line.slice(6)) as RunEvent);
    }
  }
}
