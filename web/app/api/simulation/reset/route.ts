import { scenarioFor } from "../../../../lib/server/simulator";

export async function POST(request: Request) {
  const body = await request.json();
  const scenario = scenarioFor(body.scenario ?? "open-space");
  if (!scenario) return Response.json({ detail: "Unknown scenario" }, { status: 404 });
  return Response.json({ scenario, robot: { x: scenario.start.x, y: scenario.start.y, theta: scenario.start.theta } });
}
