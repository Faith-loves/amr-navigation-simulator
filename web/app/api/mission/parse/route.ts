import { scenarioFor } from "../../../../lib/server/simulator";

export async function POST(request: Request) {
  const body = await request.json();
  const scenario = scenarioFor(body.scenario ?? "open-space");
  if (!scenario) return Response.json({ detail: "Unknown scenario" }, { status: 404 });
  const text = String(body.command ?? "").trim();
  return Response.json({
    intent: text ? "navigate" : "unknown",
    destinations: [scenario.mission_label],
    confidence: text ? 0.82 : 0,
    normalized_text: text.toLowerCase(),
    error: text ? "" : "No command provided",
    tasks: text ? [{ target_name: scenario.mission_label, target_position: { x: scenario.goal.x, y: scenario.goal.y } }] : []
  });
}
