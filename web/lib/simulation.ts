export function robotControl(keys: Set<string>, speed = 90, turnRate = 2.4): { v: number; omega: number } {
  let v = 0;
  let omega = 0;
  if (keys.has("w") || keys.has("arrowup")) v += speed;
  if (keys.has("s") || keys.has("arrowdown")) v -= speed;
  if (keys.has("a") || keys.has("arrowleft")) omega -= turnRate;
  if (keys.has("d") || keys.has("arrowright")) omega += turnRate;
  if (keys.has(" ")) return { v: 0, omega: 0 };
  return { v, omega };
}

export function nextWaypointIndex(robot: { x: number; y: number }, path: { x: number; y: number }[], current: number, tolerance = 14): number {
  let index = current;
  while (index < path.length) {
    const point = path[index];
    const dx = point.x - robot.x;
    const dy = point.y - robot.y;
    if (Math.sqrt(dx * dx + dy * dy) > tolerance) break;
    index += 1;
  }
  return index;
}

export function autonomousControl(robot: { x: number; y: number; theta: number }, target: { x: number; y: number } | undefined) {
  if (!target) return { v: 0, omega: 0 };
  const dx = target.x - robot.x;
  const dy = target.y - robot.y;
  const desired = Math.atan2(dy, dx);
  const error = Math.atan2(Math.sin(desired - robot.theta), Math.cos(desired - robot.theta));
  const distance = Math.sqrt(dx * dx + dy * dy);
  return {
    v: Math.min(95, distance * 1.8) * Math.max(0, 1 - Math.abs(error) / Math.PI),
    omega: Math.max(-2.8, Math.min(2.8, error * 4.0))
  };
}