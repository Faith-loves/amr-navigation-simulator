from __future__ import annotations

from dataclasses import dataclass, field

from experiments.experiment_config import ExperimentConfig
from experiments.experiment_result import PlannerSummary, ExperimentResult
from experiments.experiment_runner import ExperimentRunner


@dataclass
class ExperimentManager:
    runner: ExperimentRunner = field(default_factory=ExperimentRunner)
    config: ExperimentConfig | None = None
    results: list[ExperimentResult] = field(default_factory=list)
    cancelled: bool = False

    def run_experiment(self, config: ExperimentConfig, progress_callback=None) -> list[ExperimentResult]:
        self.config = config
        self.cancelled = False
        self.results = self.runner.run(config, progress_callback)
        self.cancelled = self.runner.cancel_requested
        return self.results

    def cancel(self) -> None:
        self.cancelled = True
        self.runner.cancel()

    def grouped_summaries(self) -> list[PlannerSummary]:
        planners = sorted({result.planner for result in self.results})
        return [self._summary_for(planner) for planner in planners]

    def _summary_for(self, planner: str) -> PlannerSummary:
        results = [result for result in self.results if result.planner == planner]
        successes = [result for result in results if result.success]
        return PlannerSummary(
            planner=planner,
            total_runs=len(results),
            successful_runs=len(successes),
            success_rate=0.0 if not results else len(successes) / len(results),
            average_completion_time=_average([result.completion_time for result in successes if result.completion_time is not None]),
            average_path_length=_average([result.path_length for result in successes]),
            average_actual_distance=_average([result.actual_distance for result in successes]),
            average_replans=_average([result.replans for result in results]),
            average_collisions=_average([result.collisions for result in results]),
            average_planning_time=_average([result.average_planning_time for result in results]),
            average_nodes_expanded=_average([result.nodes_expanded for result in results]),
            average_ekf_error=_average([result.average_ekf_error for result in results]),
        )


def _average(values) -> float | None:
    values = list(values)
    if not values:
        return None
    return sum(values) / len(values)
