from __future__ import annotations

import math
from dataclasses import dataclass

from experiments.experiment_result import ExperimentResult, PlannerSummary


@dataclass(frozen=True)
class MetricStats:
    mean: float | None
    stddev: float | None
    count: int


@dataclass(frozen=True)
class PlannerAnalysis:
    summary: PlannerSummary
    completion_time: MetricStats
    path_length: MetricStats
    planning_time: MetricStats
    ekf_error: MetricStats
    odometry_error: MetricStats


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def standard_deviation(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    average = mean(values)
    assert average is not None
    variance = sum((value - average) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def metric_stats(values: list[float]) -> MetricStats:
    return MetricStats(mean(values), standard_deviation(values), len(values))


def planner_analyses(results: list[ExperimentResult], summaries: list[PlannerSummary]) -> list[PlannerAnalysis]:
    analyses = []
    for summary in summaries:
        planner_results = [result for result in results if result.planner == summary.planner]
        successes = [result for result in planner_results if result.success]
        analyses.append(
            PlannerAnalysis(
                summary=summary,
                completion_time=metric_stats([result.completion_time for result in successes if result.completion_time is not None]),
                path_length=metric_stats([result.path_length for result in successes]),
                planning_time=metric_stats([result.average_planning_time for result in planner_results]),
                ekf_error=metric_stats([result.average_ekf_error for result in planner_results]),
                odometry_error=metric_stats([result.average_odometry_error for result in planner_results]),
            )
        )
    return analyses


def best_unique(
    analyses: list[PlannerAnalysis],
    value_getter,
    higher_is_better: bool = False,
) -> str:
    values: list[tuple[str, float]] = []
    for analysis in analyses:
        value = value_getter(analysis)
        if value is not None:
            values.append((analysis.summary.planner, float(value)))
    if len(values) < 2:
        return "Insufficient data"
    key = (lambda item: item[1]) if higher_is_better else (lambda item: -item[1])
    sorted_values = sorted(values, key=key, reverse=True)
    best_value = sorted_values[0][1]
    tied = [planner for planner, value in values if math.isclose(value, best_value, rel_tol=1e-9, abs_tol=1e-9)]
    if len(tied) > 1:
        return "Tie"
    return sorted_values[0][0]


def summary_cards(analyses: list[PlannerAnalysis]) -> dict[str, str]:
    return {
        "BEST SUCCESS RATE": best_unique(analyses, lambda analysis: analysis.summary.success_rate, higher_is_better=True),
        "FASTEST PLANNER": best_unique(analyses, lambda analysis: analysis.completion_time.mean),
        "SHORTEST PATH": best_unique(analyses, lambda analysis: analysis.path_length.mean),
        "LOWEST EKF ERROR": best_unique(analyses, lambda analysis: analysis.ekf_error.mean),
    }


def format_mean_std(stats: MetricStats, unit: str = "") -> str:
    if stats.mean is None:
        return "N/A"
    suffix = unit
    if stats.stddev is None:
        return f"{stats.mean:.1f}{suffix}"
    return f"{stats.mean:.1f} +/- {stats.stddev:.1f}{suffix}"


def generate_observations(analyses: list[PlannerAnalysis]) -> list[str]:
    observations: list[str] = []
    if not analyses:
        return ["No experiment results are available yet."]

    cards = summary_cards(analyses)
    fastest = cards["FASTEST PLANNER"]
    if fastest not in {"Tie", "Insufficient data"}:
        observations.append(f"{fastest} achieved the lowest average completion time.")

    lowest_planning = best_unique(analyses, lambda analysis: analysis.planning_time.mean)
    if lowest_planning not in {"Tie", "Insufficient data"}:
        observations.append(f"{lowest_planning} achieved the lowest average planning time.")

    if len(analyses) >= 2:
        sorted_nodes = sorted(analyses, key=lambda analysis: analysis.summary.average_nodes_expanded or 0.0)
        baseline = sorted_nodes[0]
        highest = sorted_nodes[-1]
        if baseline.summary.average_nodes_expanded and highest.summary.average_nodes_expanded:
            ratio = highest.summary.average_nodes_expanded / baseline.summary.average_nodes_expanded
            if ratio >= 1.5:
                observations.append(
                    f"{highest.summary.planner} expanded {ratio:.1f}x more nodes than {baseline.summary.planner}."
                )

    variable = [
        analysis
        for analysis in analyses
        if analysis.completion_time.stddev is not None
    ]
    if variable:
        most_variable = max(variable, key=lambda analysis: analysis.completion_time.stddev or 0.0)
        observations.append(f"{most_variable.summary.planner} showed the highest completion-time variability.")

    if not observations:
        observations.append("The available results are too similar or limited for a strong comparison.")
    return observations[:4]
