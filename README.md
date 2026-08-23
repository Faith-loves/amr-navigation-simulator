# AMR Navigation Simulator

AMR Navigation Simulator is a fully local 2D autonomous robotics simulation platform built in Python for evaluating perception, localization, planning, control, and navigation across configurable indoor environments. It is designed for MSc AI and Robotics portfolios, technical interviews, and reproducible algorithm experiments without ROS, cloud services, or robot hardware.

## Demo Preview

Demo video: coming soon

Screenshots should be captured from real runs and saved in `docs/screenshots/`:

- `home.png`
- `house_navigation.png`
- `warehouse_navigation.png`
- `lidar_mapping.png`
- `ekf_localization.png`
- `ai_mission.png`
- `custom_map_editor.png`
- `experiment_results.png`
- `planner_comparison.png`

## Core Capabilities

- Manual, autonomous, and frontier-exploration navigation modes
- Scenario selection for open space, corridor, house, warehouse, and office maps
- Custom map editor with start, goal, walls, obstacles, and semantic locations
- Simulated 2D LiDAR with configurable noise and occupancy-grid mapping
- Odometry and Extended Kalman Filter localization visualization
- A* and Dijkstra grid planners, path smoothing, and dynamic replanning
- Local AI mission command parsing for semantic navigation tasks
- Battery simulation with optional autonomous return-to-charger behavior
- Logging, replay, profiling, results summaries, and experiment exports

## Architecture

The application is organized into focused Python modules:

- `environment/`: scenarios, grid maps, collision checks, dynamic obstacles
- `sensors/`: LiDAR ray casting and measurement noise
- `mapping/`: occupancy-grid belief map
- `planning/`: A*, Dijkstra, smoothing, replanning, frontier exploration
- `robot/`: kinematics, odometry, EKF state estimation
- `ai/`: local mission parsing and mission queue logic
- `simulator/`: live simulation loop, logging, replay
- `experiments/`: repeated planner comparisons, statistics, export
- `ui/` and `visualization/`: Pygame screens, dashboard, theme, components

See `docs/ARCHITECTURE.md` for diagrams and data flow.

## Algorithms

Implemented robotics concepts include unicycle kinematics, LiDAR ray casting, Gaussian sensor and odometry noise, occupancy-grid updates, A* search, Dijkstra search, line-of-sight path smoothing, timed/dynamic replanning, frontier exploration, and EKF localization.

RRT* is treated as a comparison target in the portfolio documentation. Add a real `planning/rrt_star.py` implementation before presenting RRT* as a fully implemented runtime planner in this checkout.

See `docs/ALGORITHMS.md` for formulas and implementation notes.

## Scenarios

The built-in environments cover progressively richer navigation problems:

- Open Space: basic planning and sensing
- Tight Corridor: narrow passages and turning clearance
- House Layout: rooms, hallway structure, and door openings
- Warehouse: shelving aisles and moving obstacles
- Office: multiple rooms, clutter, and tighter routes

## AI Mission System

The local mission system parses commands such as `Go to kitchen then bedroom then charging station`, maps known semantic locations to navigation targets, and tracks current, pending, completed, or failed tasks. It is deterministic and local; it does not use an external LLM or cloud API.

## Experiment Mode

Experiment mode runs repeated planner comparisons under a fixed scenario, seed, noise setting, timeout, and selected planner list. The results dashboard reports success rate, completion time, path length, planning time, nodes expanded, replans, odometry error, and EKF error.

Click `EXPORT DATA` to write:

- `config.json`
- `runs.csv`
- `summary.csv`
- `metadata.json`
- `raw_results.json`

Exports are saved under `experiment_results/` using UTF-8 CSV/JSON.

## Installation

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Controls

```text
W / Up      Forward
S / Down    Reverse
A / Left    Rotate left
D / Right   Rotate right
Space       Emergency stop
F           Toggle autonomous mode
E           Toggle exploration mode
V           LiDAR view mode
1 / 2 / 3   Planner selection
L           Start or stop logging
O           Load latest replay
P           Play or pause replay
N / B       Step replay forward or backward
R           Restart scenario
ESC         Return home
```

Use `DEMO MODE` on the home screen for a strong default portfolio demo: Warehouse, A*, autonomous mode, minimal LiDAR, dynamic obstacles, localization, and battery enabled.

## Running Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Example Experiment Results

`experiment_results/example/` is reserved for one curated real export. If it only contains a README, generate a real experiment from the app and copy one clean exported folder there. Do not fabricate measurements.

## Limitations

- This is a software simulation, not physical robot deployment.
- The map is a simplified 2D grid world, not full SLAM.
- EKF measurements use simplified noisy position updates rather than landmarks.
- Dynamic obstacles are scripted rectangles.
- Results are useful for comparing behavior inside this simulator, not for making direct real-world performance claims.

## Future Work

- Add a tested RRT* runtime planner module.
- Add landmark-based localization and richer SLAM-style map correction.
- Add curated screenshots and a short demo video.
- Add CI for the full pytest suite.
- Expand experiment presets across more scenarios and noise levels.

## Web Version (Step 41)

This repository now includes a browser-based foundation alongside the desktop simulator:

- web/ contains the Next.js + React + TypeScript frontend.
- pi/index.py exposes stateless Python REST endpoints for scenarios, planning, simulation stepping, and mission parsing.
- The original Python/Pygame desktop version remains available with python main.py.

Local frontend commands:

`powershell
cd web
npm install
npm run dev
npm run build
` 

See docs/WEB.md for the web architecture and API endpoint summary.


## Web Demo

Deployed URL: _pending Vercel deployment_

The web version runs as a Next.js frontend with same-origin Python API routes. It does not require paid API keys or cloud AI services.

## Deployment

The repository is prepared for Vercel as a monorepo-style deployment:

- Frontend: `web/` Next.js + React + TypeScript
- Backend: `api/index.py` FastAPI serverless API
- Shared robotics engine: existing Python packages such as `planning/`, `robot/`, `sensors/`, `environment/`, and `ai/`

Use the repository root as the Vercel project root so both `web/` and `api/` are available. The frontend calls relative routes such as `/api/scenarios`, so it works locally and in production without hardcoded domains.

For frontend-only local development:

```powershell
cd web
npm install
npm run dev
```

For full-stack local web development, run Vercel dev from the repository root so `/api/...` routes are available. If you run only `npm run dev` inside `web/`, the UI will load but API calls will return 404.

For desktop usage:

```powershell
python main.py
```