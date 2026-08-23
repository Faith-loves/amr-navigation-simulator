"use client";

import { useMemo, useState } from "react";

type Tool = "wall" | "start" | "goal" | "erase";

export default function EditorPage() {
  const rows = 30;
  const cols = 20;
  const [tool, setTool] = useState<Tool>("wall");
  const [walls, setWalls] = useState(() => new Set<string>());
  const [start, setStart] = useState("3,2");
  const [goal, setGoal] = useState("26,17");
  const valid = useMemo(() => start !== goal && !walls.has(start) && !walls.has(goal), [start, goal, walls]);

  function paint(row: number, col: number) {
    const key = `${row},${col}`;
    if (tool === "start") { if (!walls.has(key)) setStart(key); return; }
    if (tool === "goal") { if (!walls.has(key)) setGoal(key); return; }
    setWalls((previous) => {
      const next = new Set(previous);
      if (tool === "erase") next.delete(key);
      else if (key !== start && key !== goal) next.add(key);
      return next;
    });
  }

  return <main className="page"><section className="panel"><h1>Custom Environment Builder</h1><p className="status-line">Basic web editor foundation: paint walls, place start, place goal, and validate the map locally. Advanced import/export remains available in desktop mode.</p><div className="toolbar" style={{ margin: "16px 0" }}>{(["wall", "erase", "start", "goal"] as Tool[]).map((item) => <button key={item} className={tool === item ? "option active" : "option"} onClick={() => setTool(item)}>{item.toUpperCase()}</button>)}<span className={valid ? "badge" : "error-line"}>{valid ? "VALID MAP" : "INVALID MAP"}</span></div><div className="editor-grid">{Array.from({ length: rows * cols }, (_, index) => { const row = Math.floor(index / cols); const col = index % cols; const key = `${row},${col}`; const className = key === start ? "editor-cell start" : key === goal ? "editor-cell goal" : walls.has(key) ? "editor-cell wall" : "editor-cell"; return <button aria-label={`Cell ${row}, ${col}`} key={key} className={className} onClick={() => paint(row, col)} />; })}</div></section></main>;
}