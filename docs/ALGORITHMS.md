# Algorithms

This document summarizes the robotics algorithms used by the simulator. It is intentionally concise; source modules contain the implementation details.

## Unicycle Kinematics

Robot pose is represented as:

```text
x = [px, py, theta]
```

Velocity commands integrate as:

```text
px' = px + v * cos(theta) * dt
py' = py + v * sin(theta) * dt
theta' = theta + omega * dt
```

The heading is normalized to `[-pi, pi]`.

## LiDAR Ray Casting

The LiDAR casts rays across a field of view centered on the robot heading. Each ray steps through the grid until it reaches maximum range or intersects an occupied cell. The ray records start point, endpoint, true distance, noisy distance, and hit status.

## Gaussian Noise

Sensor and odometry noise use:

```text
z_noisy = z_true + N(0, sigma)
```

LiDAR noise affects measured distance. Odometry noise perturbs linear and angular velocity before pose integration.

## Occupancy Mapping

The belief map stores:

```text
-1 unknown
 0 free
 1 occupied
```

Cells along a ray before the endpoint are marked free. A hit endpoint is marked occupied.

## A*

A* searches the grid with 8-connected motion. Straight moves cost `1`; diagonal moves cost approximately `1.414`. Priority is:

```text
f(n) = g(n) + h(n)
```

where `h(n)` is Euclidean distance to the goal.

## Dijkstra

Dijkstra uses the same grid and costs as A* but no heuristic:

```text
f(n) = g(n)
```

It is useful as an optimal baseline and often expands more nodes than A*.

## RRT*

RRT* is documented as a sampling-based comparison target. A complete implementation would include sampling, nearest-neighbor search, steering, collision checks, parent selection, rewiring, and goal connection. This checkout does not include `planning/rrt_star.py`, so do not claim RRT* runtime results unless that module is added and tested.

## EKF Localization

The EKF estimates:

```text
x = [px, py, theta]
```

Prediction uses noisy odometry controls. Correction uses a simplified noisy position measurement:

```text
h(x) = [px, py]
```

The dashboard reports EKF position error and covariance trace.

## Path Smoothing

Line-of-sight smoothing removes unnecessary grid waypoints. The smoother keeps the farthest reachable waypoint that can be connected without crossing an occupied cell.

## Replanning

Replanning runs when autonomous mode needs a path, timed replanning expires, or dynamic obstacles invalidate the current path. If the original goal is unreachable, the replanner can select the nearest reachable free cell to avoid impossible objectives.

## Frontier Exploration

A frontier is a known free cell adjacent to unknown space. Frontier clusters are scored by size and distance:

```text
score = cluster_size - 0.05 * distance_to_robot
```

The highest-scoring frontier becomes the next exploration target.
