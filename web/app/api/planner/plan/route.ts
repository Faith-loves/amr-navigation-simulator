import { cellFromPoint, cellIsFree, planPath, scenarioFor } from "../../../../lib/server/simulator";
import type { Point } from "../../../../lib/types";

export async function POST(request: Request) {
  const body = await request.json();
  const scenario = scenarioFor(body.scenario ?? "open-space");
  if (!scenario) return Response.json({ detail: "Unknown scenario" }, { status: 404 });
  const start = cellFromPoint(body.start as Point);
  const goal = cellFromPoint(body.goal as Point);
  if (!cellIsFree(scenario.grid, start)) return Response.json({ detail: { error: "INVALID_START", start_cell: start } }, { status: 400 });
  if (!cellIsFree(scenario.grid, goal)) return Response.json({ detail: { error: "INVALID_GOAL", goal_cell: goal } }, { status: 400 });
  return Response.json(planPath(scenario.grid, start, goal, body.planner ?? "astar"));
}
