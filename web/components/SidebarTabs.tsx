"use client";

import { useState } from "react";
import type { LidarMode, MissionParseResponse, PlanResponse, RobotState, ScenarioSummary } from "../lib/types";

type Props = {
  scenario: ScenarioSummary | null;
  robot: RobotState | null;
  planner: string;
  mode: string;
  lidarMode: LidarMode;
  plan: PlanResponse | null;
  mission: MissionParseResponse | null;
  status: string;
  collision: boolean;
  apiError: string;
  goalDistance: number | null;
  missionCommand: string;
  onMissionCommand: (value: string) => void;
  onMissionSubmit: () => void;
};

const tabs = ["Status", "Metrics", "Controls", "Mission"] as const;

export default function SidebarTabs(props: Props) {
  const [active, setActive] = useState<(typeof tabs)[number]>("Status");
  return (
    <aside className="sidebar-card">
      <div className="tabs" role="tablist" aria-label="Dashboard tabs">
        {tabs.map((tab) => (
          <button key={tab} className={active === tab ? "tab active" : "tab"} onClick={() => setActive(tab)}>{tab}</button>
        ))}
      </div>
      <div className="tab-panel">
        {active === "Status" && <StatusTab {...props} />}
        {active === "Metrics" && <MetricsTab {...props} />}
        {active === "Controls" && <ControlsTab />}
        {active === "Mission" && <MissionTab {...props} />}
      </div>
      <div className="sidebar-footer">F Auto &nbsp; V LiDAR &nbsp; 1/2/3 Planner</div>
    </aside>
  );
}

function StatusTab({ scenario, robot, planner, mode, lidarMode, status, collision, apiError, goalDistance, mission }: Props) {
  return <div className="stack">
    <Info label="Control Mode" value={mode.toUpperCase()} />
    <Info label="Scenario" value={scenario?.name ?? "Loading"} />
    <Info label="Planner" value={planner.toUpperCase()} />
    <Info label="Target" value={scenario?.mission_label ?? "Scenario goal"} />
    <Info label="Battery" value="Web demo: nominal" />
    <Info label="Mission" value={mission?.intent ?? "IDLE"} />
    <Info label="LiDAR" value={lidarMode.toUpperCase()} />
    <Info label="Goal Distance" value={goalDistance === null ? "--" : `${goalDistance.toFixed(0)} px`} />
    <Info label="Collision" value={collision ? "BLOCKED" : "CLEAR"} danger={collision} />
    <Info label="Robot" value={robot ? `${robot.x.toFixed(0)}, ${robot.y.toFixed(0)}` : "--"} />
    {status && <p className="status-line">{status}</p>}
    {apiError && <p className="error-line">{apiError}</p>}
  </div>;
}

function MetricsTab({ plan, robot, goalDistance }: Props) {
  return <div className="stack compact">
    <Info label="Planning Time" value={plan ? `${plan.planning_time_ms.toFixed(2)} ms` : "N/A"} />
    <Info label="Nodes Expanded" value={plan ? String(plan.nodes_expanded) : "N/A"} />
    <Info label="Path Length" value={plan ? `${plan.path_length_pixels.toFixed(0)} px` : "N/A"} />
    <Info label="Waypoints" value={plan ? String(plan.raw_waypoints_count) : "N/A"} />
    <Info label="Plan Status" value={plan ? (plan.success ? "SUCCESS" : "FAILED") : "N/A"} />
    <Info label="Goal Distance" value={goalDistance === null ? "--" : `${goalDistance.toFixed(1)} px`} />
    <Info label="Robot X" value={robot ? robot.x.toFixed(1) : "--"} />
    <Info label="Robot Y" value={robot ? robot.y.toFixed(1) : "--"} />
    <Info label="Heading" value={robot ? robot.theta.toFixed(2) : "--"} />
    {plan?.note && <p className="status-line">{plan.note}</p>}
  </div>;
}

function ControlsTab() {
  const controls = [
    ["W / Up", "Forward"], ["S / Down", "Reverse"], ["A / Left", "Rotate left"], ["D / Right", "Rotate right"], ["Space", "Emergency stop"],
    ["F", "Auto mode"], ["E", "Explore"], ["V", "LiDAR view"], ["1", "A*"], ["2", "Dijkstra"], ["3", "RRT*"], ["Esc", "Home"]
  ];
  return <div className="control-grid">{controls.map(([key, label]) => <div key={key} className="control-row"><span>{key}</span><b>{label}</b></div>)}</div>;
}

function MissionTab({ mission, missionCommand, onMissionCommand, onMissionSubmit }: Props) {
  return <div className="stack">
    <label className="field-label" htmlFor="mission-command">Mission command</label>
    <input id="mission-command" className="text-input" value={missionCommand} onChange={(event) => onMissionCommand(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") onMissionSubmit(); }} placeholder="Go to the kitchen" />
    <button className="primary-button" onClick={onMissionSubmit}>Parse Mission</button>
    <Info label="Intent" value={mission?.intent ?? "IDLE"} />
    <Info label="Confidence" value={mission ? `${Math.round(mission.confidence * 100)}%` : "N/A"} />
    <Info label="Destinations" value={mission?.destinations.join(", ") || "N/A"} />
    <Info label="Current Task" value={mission?.tasks[0]?.target_name ?? "N/A"} />
    {mission?.error && <p className="error-line">{mission.error}</p>}
  </div>;
}

function Info({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return <div className="info-row"><span>{label}</span><b className={danger ? "danger" : ""}>{value}</b></div>;
}