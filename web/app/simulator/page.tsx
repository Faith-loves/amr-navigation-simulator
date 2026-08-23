"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import SimulationCanvas from "../../components/SimulationCanvas";
import SidebarTabs from "../../components/SidebarTabs";
import { fetchScenarios, parseMission, planPath, resetSimulation, stepSimulation } from "../../lib/api";
import { autonomousControl, nextWaypointIndex, robotControl } from "../../lib/simulation";
import type { LidarMode, MissionParseResponse, PlanResponse, PlannerName, Point, RobotState, ScenarioSummary, StepResponse } from "../../lib/types";

export default function SimulatorPage() {
  return <Suspense fallback={<main className="page"><section className="panel"><h1>Simulator</h1><p className="status-line">Loading simulator...</p></section></main>}><SimulatorContent /></Suspense>;
}

function SimulatorContent() {
  const params = useSearchParams();
  const router = useRouter();
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [scenario, setScenario] = useState<ScenarioSummary | null>(null);
  const [robot, setRobot] = useState<RobotState | null>(null);
  const [goal, setGoal] = useState<Point | null>(null);
  const [planner, setPlanner] = useState<PlannerName>((params.get("planner") as PlannerName) || "astar");
  const [mode, setMode] = useState(params.get("mode") || "autonomous");
  const [lidarMode, setLidarMode] = useState<LidarMode>((params.get("lidar") as LidarMode) || "minimal");
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [trajectory, setTrajectory] = useState<Point[]>([]);
  const [lidar, setLidar] = useState<StepResponse["lidar"]>([]);
  const [collision, setCollision] = useState(false);
  const [goalDistance, setGoalDistance] = useState<number | null>(null);
  const [status, setStatus] = useState("Loading scenario...");
  const [apiError, setApiError] = useState("");
  const [missionCommand, setMissionCommand] = useState("");
  const [mission, setMission] = useState<MissionParseResponse | null>(null);
  const keys = useRef(new Set<string>());
  const waypointIndex = useRef(0);
  const robotRef = useRef<RobotState | null>(null);
  const planRef = useRef<PlanResponse | null>(null);
  const modeRef = useRef(mode);

  useEffect(() => { robotRef.current = robot; }, [robot]);
  useEffect(() => { planRef.current = plan; }, [plan]);
  useEffect(() => { modeRef.current = mode; }, [mode]);

  const loadScenario = useCallback(async (slug: string) => {
    setStatus("Loading Scenario...");
    setApiError("");
    try {
      const data = await fetchScenarios();
      setScenarios(data);
      const selected = data.find((item) => item.slug === slug) ?? data[0];
      const reset = await resetSimulation(selected.slug);
      setScenario(reset.scenario);
      setRobot(reset.robot);
      setGoal({ x: reset.scenario.goal.x, y: reset.scenario.goal.y });
      setTrajectory([{ x: reset.robot.x, y: reset.robot.y }]);
      setStatus("Ready");
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "API unavailable");
      setStatus("API unavailable");
    }
  }, []);

  const requestPlan = useCallback(async (target?: Point) => {
    const activeScenario = scenario;
    const activeRobot = robotRef.current;
    const activeGoal = target ?? goal;
    if (!activeScenario || !activeRobot || !activeGoal) return;
    setStatus("Planning...");
    setApiError("");
    try {
      const result = await planPath({ planner, scenario: activeScenario.slug, start: activeRobot, goal: activeGoal });
      setPlan(result);
      planRef.current = result;
      waypointIndex.current = 0;
      setStatus(result.success ? "Path ready" : "No path found");
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Planner failed");
      setStatus("Planner failed");
    }
  }, [goal, planner, scenario]);

  useEffect(() => { void loadScenario(params.get("scenario") || "open-space"); }, [loadScenario, params]);
  useEffect(() => { if (scenario && robot && goal) void requestPlan(); }, [scenario?.slug, planner]);

  useEffect(() => {
    const onDown = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      if (["arrowup", "arrowdown", "arrowleft", "arrowright", " "].includes(key)) event.preventDefault();
      keys.current.add(key);
      if (key === "f") setMode((value) => value === "autonomous" ? "manual" : "autonomous");
      if (key === "e") setMode("exploration");
      if (key === "v") setLidarMode((value) => value === "off" ? "minimal" : value === "minimal" ? "full" : "off");
      if (key === "1") setPlanner("astar");
      if (key === "2") setPlanner("dijkstra");
      if (key === "3") setPlanner("rrtstar");
      if (key === "escape") router.push("/");
    };
    const onUp = (event: KeyboardEvent) => keys.current.delete(event.key.toLowerCase());
    window.addEventListener("keydown", onDown, { passive: false });
    window.addEventListener("keyup", onUp);
    return () => { window.removeEventListener("keydown", onDown); window.removeEventListener("keyup", onUp); };
  }, [router]);

  useEffect(() => {
    const interval = window.setInterval(async () => {
      const activeScenario = scenario;
      const activeRobot = robotRef.current;
      if (!activeScenario || !activeRobot) return;
      let control = robotControl(keys.current);
      if (modeRef.current === "autonomous") {
        const currentPlan = planRef.current;
        if (currentPlan?.success) {
          waypointIndex.current = nextWaypointIndex(activeRobot, currentPlan.path, waypointIndex.current);
          control = autonomousControl(activeRobot, currentPlan.path[waypointIndex.current]);
        }
      }
      try {
        const response = await stepSimulation({ scenario: activeScenario.slug, robot: activeRobot, control, dt: 0.08, lidar: lidarMode !== "off" });
        setRobot(response.robot);
        setCollision(response.collision);
        setGoalDistance(response.goal_distance);
        setLidar(response.lidar);
        setTrajectory((points) => [...points.slice(-420), { x: response.robot.x, y: response.robot.y }]);
      } catch (error) {
        setApiError(error instanceof Error ? error.message : "Simulation API unavailable");
      }
    }, 80);
    return () => window.clearInterval(interval);
  }, [scenario, lidarMode]);

  async function submitMission() {
    if (!scenario || !missionCommand.trim()) return;
    setStatus("Parsing Mission...");
    try {
      const parsed = await parseMission({ scenario: scenario.slug, command: missionCommand });
      setMission(parsed);
      const target = parsed.tasks[0]?.target_position;
      if (target) {
        setGoal(target);
        await requestPlan(target);
        setMode("autonomous");
      }
      setStatus(parsed.error || "Mission parsed");
      const history = JSON.parse(localStorage.getItem("amr-recent-missions") || "[]") as string[];
      localStorage.setItem("amr-recent-missions", JSON.stringify([missionCommand, ...history.filter((item) => item !== missionCommand)].slice(0, 5)));
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Mission parse failed");
    }
  }

  return <><div className="mobile-warning"><h1>AMR Simulator</h1><p>AMR Simulator works best on a desktop or tablet.</p></div><main className="sim-page"><section className="sim-main"><div className="sim-header"><div><h1>{scenario?.name ?? "Simulator"}</h1><p>{status}</p></div><div className="toolbar"><select value={scenario?.slug ?? ""} onChange={(event) => void loadScenario(event.target.value)}>{scenarios.map((item) => <option key={item.slug} value={item.slug}>{item.name}</option>)}</select><button onClick={() => setMode(mode === "autonomous" ? "manual" : "autonomous")}>{mode === "autonomous" ? "Manual" : "Auto"}</button><button onClick={() => void requestPlan()}>Plan</button><button onClick={() => router.push("/")}>Home</button></div></div><SimulationCanvas scenario={scenario} robot={robot} goal={goal} path={plan?.path ?? []} trajectory={trajectory} lidar={lidar} lidarMode={lidarMode} onCanvasGoal={(point) => { setGoal(point); void requestPlan(point); }} /></section><SidebarTabs scenario={scenario} robot={robot} planner={planner} mode={mode} lidarMode={lidarMode} plan={plan} mission={mission} status={status} collision={collision} apiError={apiError} goalDistance={goalDistance} missionCommand={missionCommand} onMissionCommand={setMissionCommand} onMissionSubmit={() => void submitMission()} /></main></>;
}