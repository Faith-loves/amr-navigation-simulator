"use client";

import { useEffect, useRef } from "react";
import type { LidarMode, LidarRay, Point, RobotState, ScenarioSummary } from "../lib/types";

type Props = {
  scenario: ScenarioSummary | null;
  robot: RobotState | null;
  goal: Point | null;
  path: Point[];
  trajectory: Point[];
  lidar: LidarRay[];
  lidarMode: LidarMode;
  onCanvasGoal?: (point: Point) => void;
};

export default function SimulationCanvas({ scenario, robot, goal, path, trajectory, lidar, lidarMode, onCanvasGoal }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#07101d";
    ctx.fillRect(0, 0, width, height);

    if (!scenario) {
      ctx.fillStyle = "#8ea0ba";
      ctx.font = "16px Arial";
      ctx.fillText("Loading map...", 24, 36);
      return;
    }

    const scale = Math.min((width - 32) / scenario.width, (height - 32) / scenario.height);
    const offsetX = (width - scenario.width * scale) / 2;
    const offsetY = (height - scenario.height * scale) / 2;
    const cell = scenario.cell_size * scale;

    ctx.fillStyle = "#0d1726";
    ctx.fillRect(offsetX, offsetY, scenario.width * scale, scenario.height * scale);

    ctx.strokeStyle = "rgba(76, 105, 143, 0.28)";
    ctx.lineWidth = 1;
    for (let row = 0; row <= scenario.rows; row += 1) {
      const y = offsetY + row * cell;
      ctx.beginPath();
      ctx.moveTo(offsetX, y);
      ctx.lineTo(offsetX + scenario.width * scale, y);
      ctx.stroke();
    }
    for (let col = 0; col <= scenario.cols; col += 1) {
      const x = offsetX + col * cell;
      ctx.beginPath();
      ctx.moveTo(x, offsetY);
      ctx.lineTo(x, offsetY + scenario.height * scale);
      ctx.stroke();
    }

    ctx.fillStyle = "#d8e0ea";
    scenario.grid.forEach((line, row) => {
      line.forEach((value, col) => {
        if (value === 1) ctx.fillRect(offsetX + col * cell, offsetY + row * cell, cell, cell);
      });
    });

    if (trajectory.length > 1) drawPolyline(ctx, trajectory, offsetX, offsetY, scale, "rgba(86, 139, 255, 0.42)", 2);
    if (path.length > 1) drawPolyline(ctx, path, offsetX, offsetY, scale, "#3ee0c2", 3);

    if (lidarMode !== "off" && lidar.length && robot) {
      const rays = lidarMode === "minimal" ? lidar.filter((_, index) => index % 3 === 0) : lidar;
      ctx.lineWidth = 1;
      rays.forEach((ray) => {
        ctx.strokeStyle = ray.hit ? "rgba(255, 201, 102, 0.42)" : "rgba(62, 224, 194, 0.24)";
        ctx.beginPath();
        ctx.moveTo(offsetX + ray.start.x * scale, offsetY + ray.start.y * scale);
        ctx.lineTo(offsetX + ray.end.x * scale, offsetY + ray.end.y * scale);
        ctx.stroke();
      });
    }

    if (goal) drawGoal(ctx, goal, offsetX, offsetY, scale);
    if (robot) drawRobot(ctx, robot, offsetX, offsetY, scale);
  }, [scenario, robot, goal, path, trajectory, lidar, lidarMode]);

  return (
    <canvas
      ref={canvasRef}
      width={760}
      height={600}
      className="simulation-canvas"
      onClick={(event) => {
        if (!scenario || !onCanvasGoal) return;
        const canvas = event.currentTarget;
        const rect = canvas.getBoundingClientRect();
        const displayScaleX = canvas.width / rect.width;
        const displayScaleY = canvas.height / rect.height;
        const canvasX = (event.clientX - rect.left) * displayScaleX;
        const canvasY = (event.clientY - rect.top) * displayScaleY;
        const scale = Math.min((canvas.width - 32) / scenario.width, (canvas.height - 32) / scenario.height);
        const offsetX = (canvas.width - scenario.width * scale) / 2;
        const offsetY = (canvas.height - scenario.height * scale) / 2;
        const x = (canvasX - offsetX) / scale;
        const y = (canvasY - offsetY) / scale;
        if (x < 0 || y < 0 || x > scenario.width || y > scenario.height) return;
        onCanvasGoal({ x, y });
      }}
    />
  );
}

function drawPolyline(ctx: CanvasRenderingContext2D, points: Point[], offsetX: number, offsetY: number, scale: number, color: string, width: number) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = offsetX + point.x * scale;
    const y = offsetY + point.y * scale;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function drawGoal(ctx: CanvasRenderingContext2D, goal: Point, offsetX: number, offsetY: number, scale: number) {
  const x = offsetX + goal.x * scale;
  const y = offsetY + goal.y * scale;
  ctx.strokeStyle = "#ff6b6b";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(x, y, 10, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = "#ff6b6b";
  ctx.beginPath();
  ctx.arc(x, y, 4, 0, Math.PI * 2);
  ctx.fill();
}

function drawRobot(ctx: CanvasRenderingContext2D, robot: RobotState, offsetX: number, offsetY: number, scale: number) {
  const x = offsetX + robot.x * scale;
  const y = offsetY + robot.y * scale;
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(robot.theta);
  ctx.fillStyle = "#172438";
  roundRect(ctx, -18, -13, 36, 26, 7);
  ctx.fill();
  ctx.strokeStyle = "#60a5fa";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = "#3ee0c2";
  ctx.fillRect(5, -8, 10, 16);
  ctx.fillStyle = "#9fb0c8";
  ctx.beginPath();
  ctx.arc(-6, 0, 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#3ee0c2";
  ctx.beginPath();
  ctx.moveTo(17, 0);
  ctx.lineTo(28, 0);
  ctx.stroke();
  ctx.restore();
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}