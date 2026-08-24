import { cellFromPoint, cellIsFree, collides, lidar, scenarioFor, stepRobot } from "../../../../lib/server/simulator";
import type { Point, RobotState } from "../../../../lib/types";

export async function POST(request: Request) {
  const body = await request.json();
  const scenario = scenarioFor(body.scenario ?? "open-space");
  if (!scenario) return Response.json({ detail: "Unknown scenario" }, { status: 404 });
  const robot = body.robot as RobotState;
  const proposed = stepRobot(robot, body.control ?? { v: 0, omega: 0 }, body.dt ?? 0.08);
  const collision = collides(scenario.grid, proposed);
  const nextRobot = collision ? robot : proposed;
  const goal = (body.goal as Point | undefined) ?? scenario.goal;
  return Response.json({
    robot: nextRobot,
    collision,
    goal_distance: Math.hypot(goal.x - nextRobot.x, goal.y - nextRobot.y),
    lidar: body.lidar ? lidar(nextRobot, scenario.grid) : [],
    robot_cell: cellFromPoint(nextRobot),
    robot_free: cellIsFree(scenario.grid, cellFromPoint(nextRobot))
  });
}
