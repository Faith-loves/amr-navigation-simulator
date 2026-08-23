"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchScenarios } from "../lib/api";
import type { LidarMode, ModeName, PlannerName, ScenarioSummary } from "../lib/types";

export default function HomePage() {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [selected, setSelected] = useState("open-space");
  const [planner, setPlanner] = useState<PlannerName>("astar");
  const [mode, setMode] = useState<ModeName>("autonomous");
  const [lidar, setLidar] = useState<LidarMode>("minimal");
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("amr-web-settings");
    if (stored) {
      try {
        const value = JSON.parse(stored);
        setSelected(value.scenario ?? "open-space");
        setPlanner(value.planner ?? "astar");
        setMode(value.mode ?? "autonomous");
        setLidar(value.lidar ?? "minimal");
      } catch {}
    }
    fetchScenarios().then(setScenarios).catch((reason) => setError(reason.message));
  }, []);

  useEffect(() => {
    localStorage.setItem("amr-web-settings", JSON.stringify({ scenario: selected, planner, mode, lidar }));
  }, [selected, planner, mode, lidar]);

  return <main className="page"><div className="home-grid"><section className="hero"><h1>AMR Navigation Simulator</h1><p>Plan, localize, map, and control a browser-rendered autonomous mobile robot powered by the Python robotics engine.</p><div className="scenario-grid">{scenarios.map((scenario) => <button key={scenario.slug} className={selected === scenario.slug ? "scenario-card active" : "scenario-card"} onClick={() => setSelected(scenario.slug)}><h3>{scenario.name}</h3><p>{scenario.description}</p><span className="badge">{scenario.difficulty}</span></button>)}</div>{error && <p className="error-line">API unavailable: {error}</p>}</section><aside className="launch card"><h2>Launch</h2><label className="field-label">Planner</label><div className="segmented"><Option label="A*" active={planner === "astar"} onClick={() => setPlanner("astar")} /><Option label="Dijkstra" active={planner === "dijkstra"} onClick={() => setPlanner("dijkstra")} /><Option label="RRT*" active={planner === "rrtstar"} onClick={() => setPlanner("rrtstar")} /></div><label className="field-label">Mode</label><div className="segmented"><Option label="Manual" active={mode === "manual"} onClick={() => setMode("manual")} /><Option label="Auto" active={mode === "autonomous"} onClick={() => setMode("autonomous")} /><Option label="Explore" active={mode === "exploration"} onClick={() => setMode("exploration")} /></div><label className="field-label">LiDAR</label><div className="segmented"><Option label="Off" active={lidar === "off"} onClick={() => setLidar("off")} /><Option label="Minimal" active={lidar === "minimal"} onClick={() => setLidar("minimal")} /><Option label="Full" active={lidar === "full"} onClick={() => setLidar("full")} /></div><div className="actions"><Link className="primary-button" style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", padding: "0 18px" }} href={`/simulator?scenario=${selected}&planner=${planner}&mode=${mode}&lidar=${lidar}`}>Start Simulation</Link><Link className="ghost-button" style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", padding: "0 14px" }} href="/experiments">Experiments</Link></div><div className="actions"><Link className="ghost-button" style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", padding: "0 14px" }} href="/editor">Custom Environment</Link></div></aside></div></main>;
}

function Option({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return <button className={active ? "option active" : "option"} onClick={onClick}>{label}</button>;
}