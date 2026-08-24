import type { PlanResponse, Point, RobotState, ScenarioSummary } from "../types";

const CELL_SIZE = 20;
const ROWS = 30;
const COLS = 20;

type Rectangle = [number, number, number, number];
type Cell = [number, number];

type ScenarioSpec = {
  name: string;
  description: string;
  difficulty: string;
  obstacles: Rectangle[];
  clearCells?: Cell[];
  start: Cell;
  goal: Cell;
  theta?: number;
  recommended_planner?: string;
  mission_label?: string;
  dynamic_obstacles?: Record<string, number>[];
};

function cellCenter(row: number, col: number): Point {
  return { x: col * CELL_SIZE + CELL_SIZE / 2, y: row * CELL_SIZE + CELL_SIZE / 2 };
}

function slug(name: string): string {
  return name.toLowerCase().replaceAll(" ", "-");
}

function buildGrid(obstacles: Rectangle[], clearCells: Cell[] = []): number[][] {
  const grid = Array.from({ length: ROWS }, () => Array.from({ length: COLS }, () => 0));
  for (let row = 0; row < ROWS; row += 1) {
    grid[row][0] = 1;
    grid[row][COLS - 1] = 1;
  }
  for (let col = 0; col < COLS; col += 1) {
    grid[0][col] = 1;
    grid[ROWS - 1][col] = 1;
  }
  for (const [startRow, startCol, height, width] of obstacles) {
    for (let row = startRow; row < startRow + height; row += 1) {
      for (let col = startCol; col < startCol + width; col += 1) {
        if (grid[row]?.[col] !== undefined) grid[row][col] = 1;
      }
    }
  }
  for (const [row, col] of clearCells) {
    if (grid[row]?.[col] !== undefined) grid[row][col] = 0;
  }
  return grid;
}

const specs: ScenarioSpec[] = [
  {
    name: "Open Space",
    description: "Mostly open map with several rectangular obstacles and wide navigation paths.",
    difficulty: "Beginner",
    obstacles: [[5, 5, 4, 3], [8, 13, 3, 3], [15, 4, 5, 2], [18, 11, 4, 4], [24, 6, 2, 7]],
    start: [3, 2],
    goal: [26, 17],
    recommended_planner: "A*"
  },
  {
    name: "Tight Corridor",
    description: "Narrow corridor network with turns sized for the robot and obstacle inflation.",
    difficulty: "Easy",
    obstacles: [[3, 4, 20, 2], [7, 8, 20, 2], [3, 12, 20, 2], [11, 16, 15, 2]],
    clearCells: [[23, 4], [23, 5], [6, 8], [6, 9], [23, 12], [23, 13], [10, 16], [10, 17]],
    start: [3, 2],
    goal: [26, 17],
    recommended_planner: "A*"
  },
  {
    name: "House Layout",
    description: "Simplified house floor plan with rooms, a hallway, and door openings.",
    difficulty: "Intermediate",
    obstacles: [[6, 1, 1, 7], [6, 10, 1, 9], [14, 1, 1, 9], [14, 12, 1, 7], [22, 1, 1, 6], [22, 9, 1, 10], [1, 7, 5, 1], [8, 7, 6, 1], [15, 7, 7, 1], [1, 12, 6, 1], [9, 12, 5, 1], [15, 12, 7, 1], [17, 3, 2, 2], [3, 15, 2, 2]],
    clearCells: [[6, 5], [6, 6], [6, 7], [6, 8], [6, 9], [14, 7], [14, 8], [14, 9], [14, 10], [14, 11], [14, 12], [14, 13], [14, 14], [22, 7], [22, 8], [22, 9], [22, 10], [22, 11], [22, 12], [22, 13], [22, 14], [22, 15], [22, 16], [22, 17]],
    start: [3, 3],
    goal: [10, 11],
    recommended_planner: "A*"
  },
  {
    name: "Warehouse",
    description: "Warehouse aisles with shelving rows, intersections, and a loading area.",
    difficulty: "Intermediate / Advanced",
    obstacles: [[4, 3, 9, 2], [16, 3, 9, 2], [4, 7, 9, 2], [16, 7, 9, 2], [4, 11, 9, 2], [16, 11, 9, 2], [4, 15, 9, 2], [16, 15, 9, 2], [26, 2, 1, 7], [26, 12, 1, 6]],
    start: [27, 2],
    goal: [2, 17],
    theta: -1.57,
    recommended_planner: "A*",
    dynamic_obstacles: [{ x: 110, y: 275 }, { x: 250, y: 55 }, { x: 335, y: 300 }]
  },
  {
    name: "Office",
    description: "Office rooms, hallways, desks, multiple routes, and tighter turns.",
    difficulty: "Advanced",
    obstacles: [[5, 1, 1, 6], [5, 9, 1, 10], [12, 1, 1, 8], [12, 11, 1, 8], [20, 1, 1, 7], [20, 10, 1, 9], [1, 6, 4, 1], [7, 6, 5, 1], [13, 6, 7, 1], [1, 13, 4, 1], [7, 13, 5, 1], [14, 13, 6, 1], [7, 2, 2, 2], [8, 15, 2, 2], [15, 3, 2, 2], [16, 9, 2, 2], [23, 14, 2, 3], [25, 4, 2, 3]],
    clearCells: [[5, 6], [5, 7], [12, 6], [12, 7], [20, 6], [20, 7], [5, 13], [5, 14], [12, 13], [12, 14], [20, 13], [20, 14]],
    start: [26, 2],
    goal: [2, 17],
    theta: -1.57,
    recommended_planner: "A*",
    dynamic_obstacles: [{ x: 150, y: 155 }, { x: 300, y: 430 }]
  }
];

export const scenarios: ScenarioSummary[] = specs.map((spec) => {
  const grid = buildGrid(spec.obstacles, spec.clearCells);
  const startPoint = cellCenter(spec.start[0], spec.start[1]);
  const goalPoint = cellCenter(spec.goal[0], spec.goal[1]);
  return {
    name: spec.name,
    slug: slug(spec.name),
    difficulty: spec.difficulty,
    description: spec.description,
    recommended_planner: spec.recommended_planner ?? null,
    mission_label: spec.mission_label ?? "START -> TARGET",
    cell_size: CELL_SIZE,
    rows: ROWS,
    cols: COLS,
    width: COLS * CELL_SIZE,
    height: ROWS * CELL_SIZE,
    start: { ...startPoint, cell: spec.start, theta: spec.theta ?? 0 },
    goal: { ...goalPoint, cell: spec.goal },
    grid,
    obstacles: spec.obstacles.map(([row, col, height, width]) => ({ row, col, height, width })),
    dynamic_obstacles: spec.dynamic_obstacles ?? [],
    semantic_locations: []
  };
});

export function scenarioFor(value: string): ScenarioSummary | undefined {
  const key = value.trim().toLowerCase().replaceAll("_", "-").replaceAll(" ", "-");
  return scenarios.find((scenario) => scenario.slug === key || scenario.name.toLowerCase() === value.trim().toLowerCase());
}

export function cellFromPoint(point: Point): Cell {
  return [Math.floor(point.y / CELL_SIZE), Math.floor(point.x / CELL_SIZE)];
}

export function pointFromCell([row, col]: Cell): Point {
  return cellCenter(row, col);
}

export function cellIsFree(grid: number[][], [row, col]: Cell): boolean {
  return row >= 0 && row < grid.length && col >= 0 && col < grid[0].length && grid[row][col] === 0;
}

export function planPath(grid: number[][], start: Cell, goal: Cell, planner: string): PlanResponse {
  const started = performance.now();
  if (!cellIsFree(grid, start) || !cellIsFree(grid, goal)) {
    return emptyPlan(planner, start, goal, performance.now() - started, 0, "INVALID_GOAL");
  }
  const useDijkstra = planner.toLowerCase() === "dijkstra";
  const open: Array<{ cell: Cell; f: number }> = [{ cell: start, f: 0 }];
  const key = ([row, col]: Cell) => `${row},${col}`;
  const cameFrom = new Map<string, Cell>();
  const gScore = new Map<string, number>([[key(start), 0]]);
  let nodes = 0;

  while (open.length) {
    open.sort((a, b) => a.f - b.f);
    const current = open.shift()!.cell;
    nodes += 1;
    if (current[0] === goal[0] && current[1] === goal[1]) {
      const cells = reconstruct(cameFrom, current);
      return makePlan(planner, start, goal, cells, performance.now() - started, nodes);
    }
    for (const [neighbor, cost] of neighbors(grid, current)) {
      const score = (gScore.get(key(current)) ?? Infinity) + cost;
      const neighborKey = key(neighbor);
      if (score < (gScore.get(neighborKey) ?? Infinity)) {
        cameFrom.set(neighborKey, current);
        gScore.set(neighborKey, score);
        const h = useDijkstra ? 0 : heuristic(neighbor, goal);
        open.push({ cell: neighbor, f: score + h });
      }
    }
  }
  return emptyPlan(planner, start, goal, performance.now() - started, nodes, "NO_PATH");
}

function neighbors(grid: number[][], [row, col]: Cell): Array<[Cell, number]> {
  const moves: Array<[number, number, number]> = [[-1, 0, 1], [1, 0, 1], [0, -1, 1], [0, 1, 1], [-1, -1, 1.414], [-1, 1, 1.414], [1, -1, 1.414], [1, 1, 1.414]];
  return moves.map(([dr, dc, cost]) => [[row + dr, col + dc] as Cell, cost] as [Cell, number]).filter(([cell]) => cellIsFree(grid, cell));
}

function heuristic([row, col]: Cell, [goalRow, goalCol]: Cell): number {
  return Math.hypot(goalRow - row, goalCol - col);
}

function reconstruct(cameFrom: Map<string, Cell>, current: Cell): Cell[] {
  const path = [current];
  while (cameFrom.has(`${current[0]},${current[1]}`)) {
    current = cameFrom.get(`${current[0]},${current[1]}`)!;
    path.push(current);
  }
  return path.reverse();
}

function pathLength(cells: Cell[]): number {
  let total = 0;
  for (let i = 1; i < cells.length; i += 1) total += Math.hypot(cells[i][0] - cells[i - 1][0], cells[i][1] - cells[i - 1][1]);
  return total * CELL_SIZE;
}

function makePlan(planner: string, start: Cell, goal: Cell, cells: Cell[], ms: number, nodes: number): PlanResponse {
  const note = planner.toLowerCase() === "rrtstar" ? "RRT* runtime planner is not implemented in the web build; using A* fallback." : null;
  return { success: cells.length > 0, error: "", planner, note, start_cell: start, goal_cell: goal, path_cells: cells, path: cells.map(pointFromCell), planning_time_ms: ms, nodes_expanded: nodes, path_length_pixels: pathLength(cells), raw_waypoints_count: cells.length };
}

function emptyPlan(planner: string, start: Cell, goal: Cell, ms: number, nodes: number, error: string): PlanResponse {
  return { success: false, error, planner, note: null, start_cell: start, goal_cell: goal, path_cells: [], path: [], planning_time_ms: ms, nodes_expanded: nodes, path_length_pixels: 0, raw_waypoints_count: 0 };
}

export function stepRobot(robot: RobotState, control: { v: number; omega: number }, dt: number): RobotState {
  const theta = robot.theta + control.omega * dt;
  return { x: robot.x + control.v * Math.cos(theta) * dt, y: robot.y + control.v * Math.sin(theta) * dt, theta };
}

export function collides(grid: number[][], robot: RobotState): boolean {
  const [row, col] = cellFromPoint(robot);
  return !cellIsFree(grid, [row, col]);
}

export function lidar(robot: RobotState, grid: number[][]) {
  const rays = [];
  const fov = Math.PI * 1.5;
  for (let i = 0; i < 41; i += 1) {
    const angle = robot.theta - fov / 2 + (fov * i) / 40;
    let distance = 0;
    let hit = false;
    while (distance < 250) {
      distance += 4;
      const point = { x: robot.x + Math.cos(angle) * distance, y: robot.y + Math.sin(angle) * distance };
      if (!cellIsFree(grid, cellFromPoint(point))) { hit = true; break; }
    }
    const end = { x: robot.x + Math.cos(angle) * distance, y: robot.y + Math.sin(angle) * distance };
    rays.push({ start: { x: robot.x, y: robot.y }, end, distance, hit });
  }
  return rays;
}
