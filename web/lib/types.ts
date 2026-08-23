export type Point = { x: number; y: number };
export type RobotState = Point & { theta: number };

export type ScenarioSummary = {
  name: string;
  slug: string;
  difficulty: string;
  description: string;
  recommended_planner: string | null;
  mission_label: string;
  cell_size: number;
  rows: number;
  cols: number;
  width: number;
  height: number;
  start: Point & { cell: [number, number]; theta: number };
  goal: Point & { cell: [number, number] };
  grid: number[][];
  obstacles: { row: number; col: number; height: number; width: number }[];
  dynamic_obstacles: Record<string, number>[];
  semantic_locations: { name: string; cell: [number, number]; position: Point; aliases: string[] }[];
};

export type PlannerName = "astar" | "dijkstra" | "rrtstar";
export type ModeName = "manual" | "autonomous" | "exploration";
export type LidarMode = "off" | "minimal" | "full";

export type PlanResponse = {
  success: boolean;
  error?: string;
  planner: string;
  note: string | null;
  start_cell: [number, number];
  goal_cell: [number, number];
  path_cells: [number, number][];
  path: Point[];
  planning_time_ms: number;
  nodes_expanded: number;
  path_length_pixels: number;
  raw_waypoints_count: number;
};

export type LidarRay = { start: Point; end: Point; distance: number; hit: boolean };

export type StepResponse = {
  robot: RobotState;
  collision: boolean;
  goal_distance: number;
  lidar: LidarRay[];
};

export type MissionParseResponse = {
  intent: string;
  destinations: string[];
  confidence: number;
  normalized_text: string;
  error: string;
  tasks: { target_name: string; target_position: Point }[];
};
