import { describe, expect, it } from "vitest";
import { autonomousControl, nextWaypointIndex, robotControl } from "./simulation";

describe("web simulation helpers", () => {
  it("maps keyboard input to robot control", () => {
    expect(robotControl(new Set(["w"]))).toMatchObject({ v: 90, omega: 0 });
    expect(robotControl(new Set(["arrowleft"])).omega).toBeLessThan(0);
    expect(robotControl(new Set([" "]))).toEqual({ v: 0, omega: 0 });
  });

  it("advances reached waypoints safely", () => {
    const index = nextWaypointIndex({ x: 10, y: 10 }, [{ x: 10, y: 10 }, { x: 100, y: 100 }], 0);
    expect(index).toBe(1);
  });

  it("creates bounded autonomous commands", () => {
    const command = autonomousControl({ x: 0, y: 0, theta: 0 }, { x: 100, y: 0 });
    expect(command.v).toBeGreaterThan(0);
    expect(Math.abs(command.omega)).toBeLessThanOrEqual(2.8);
  });
});