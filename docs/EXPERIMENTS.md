# Experiments

Experiment mode evaluates planner behavior through repeated, deterministic simulation runs.

## Repeatable Runs

An `ExperimentConfig` stores the scenario, selected planners, runs per planner, LiDAR noise level, dynamic obstacle option, battery option, timeout, and random seed. Each run derives a deterministic seed from the base seed, planner name, and run number.

This makes repeated comparisons easier to reproduce and explain in a portfolio or interview.

## Planner Comparison

The experiment runner resets the scenario for each run, executes the selected planner, and records an `ExperimentResult`. The manager groups those results into one summary per planner.

Useful comparisons include:

- success rate
- completion time
- planned path length
- actual distance travelled
- average planning time
- nodes expanded
- replans
- collisions
- odometry error
- EKF error
- battery and energy metrics

Failed runs are represented explicitly. Completion time and path length averages exclude failed runs so a timeout is not treated as a zero-second success.

## Exported Data

Click `EXPORT DATA` on the experiment results screen to create:

- `config.json`
- `runs.csv`
- `summary.csv`
- `metadata.json`
- `raw_results.json`

CSV files are UTF-8 and compatible with Excel, Google Sheets, LibreOffice, and pandas. JSON files are intended for reproducibility and programmatic analysis.

## Interpreting Metrics

- `success_rate`: successful runs divided by total runs
- `mean_completion_time`: mean of successful completion times only
- `std_completion_time`: sample standard deviation when multiple successful runs exist
- `mean_planning_time`: average planner compute time across all runs
- `mean_nodes_expanded`: search effort for graph-based planners
- `mean_ekf_error`: localization error in pixels

## Limitations

Simulation-based comparisons are only valid inside the simulator assumptions: simplified robot dynamics, simplified position measurements, grid-world maps, scripted dynamic obstacles, and local deterministic planners. Treat the results as engineering evidence for this software system, not physical robot benchmarks.
