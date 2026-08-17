# Architecture

The simulator separates robotics logic from UI rendering so each subsystem can be inspected, tested, and discussed independently.

## High-Level Stack

```mermaid
flowchart TD
    UI["UI / Pygame Screens"] --> Scenario["Scenario / Mission Layer"]
    Scenario --> Nav["Navigation Manager / Simulation Loop"]
    Nav --> Planner["Planner: A* / Dijkstra / RRT* target"]
    Planner --> Controller["Waypoint Controller"]
    Controller --> Robot["Robot Model / Kinematics"]
    Robot --> Environment["Ground-Truth Environment"]

    Environment --> Lidar["LiDAR"]
    Lidar --> Mapping["Occupancy Grid Mapping"]
    Robot --> Odometry["Odometry"]
    Robot --> EKF["EKF Localization"]
    Nav --> Logging["Logging / Replay"]
    Nav --> Experiments["Experiment Runner / Export"]
```

## Runtime Data Flow

```mermaid
flowchart LR
    Env["Environment"] --> Lidar["LiDAR"]
    Lidar --> Belief["Belief Map"]
    Belief --> Planner["Planner"]
    Planner --> Path["Path"]
    Path --> Controller["Controller"]
    Controller --> Robot["Robot"]
    Robot --> Env

    Robot --> Odom["Odometry"]
    Lidar --> Measure["Noisy Measurements"]
    Odom --> EKF["EKF"]
    Measure --> EKF
    EKF --> Pose["Estimated Pose"]
```

## Major Modules

- `app.py`: application state routing between home, simulation, editor, replay, results, and experiments
- `simulator/simulation_loop.py`: frame integration, controls, planning, sensing, mapping, logging, replay, and dashboard updates
- `environment/`: scenarios, grid geometry, dynamic obstacles, and collision checks
- `planning/`: graph search, path smoothing, replanning, and frontier selection
- `robot/`: state, kinematics, odometry, and EKF localization
- `sensors/`: LiDAR ray casting
- `ai/`: local mission parser and mission manager
- `experiments/`: repeated trials, statistics, dashboard data, and export files
- `ui/` and `visualization/`: screens, theme, reusable UI components, robot rendering, and maps

## Frame Sequence

1. Poll keyboard and mouse input.
2. Update dynamic obstacles.
3. Resolve mission/autonomous/exploration targets.
4. Replan when the path is missing, blocked, or stale.
5. Convert waypoints into velocity commands.
6. Apply collision-checked robot motion.
7. Update odometry and EKF estimates.
8. Cast LiDAR rays and update the belief map.
9. Log frame data if logging is enabled.
10. Draw the dashboard.

Replay mode skips physics and planner updates and displays logged states through the same dashboard renderer.
