import type { MissionParseResponse, PlanResponse, PlannerName, Point, RobotState, ScenarioSummary, StepResponse } from "./types";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the generic message if the server did not return JSON.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const data = await requestJson<{ scenarios: ScenarioSummary[] }>("/api/scenarios");
  return data.scenarios;
}

export async function resetSimulation(scenario: string): Promise<{ scenario: ScenarioSummary; robot: RobotState }> {
  return requestJson("/api/simulation/reset", { method: "POST", body: JSON.stringify({ scenario }) });
}

export async function stepSimulation(input: {
  scenario: string;
  robot: RobotState;
  control: { v: number; omega: number };
  dt: number;
  lidar: boolean;
}): Promise<StepResponse> {
  return requestJson("/api/simulation/step", { method: "POST", body: JSON.stringify(input) });
}

export async function planPath(input: {
  planner: PlannerName;
  scenario: string;
  start: Point;
  goal: Point;
}): Promise<PlanResponse> {
  return requestJson("/api/planner/plan", { method: "POST", body: JSON.stringify(input) });
}

export async function parseMission(input: { scenario: string; command: string }): Promise<MissionParseResponse> {
  return requestJson("/api/mission/parse", { method: "POST", body: JSON.stringify(input) });
}