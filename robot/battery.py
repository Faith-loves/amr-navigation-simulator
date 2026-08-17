from __future__ import annotations

from dataclasses import dataclass


BATTERY_NORMAL = "NORMAL"
BATTERY_LOW = "LOW"
BATTERY_CRITICAL = "CRITICAL"
BATTERY_CHARGING = "CHARGING"
BATTERY_CHARGED = "CHARGED"
BATTERY_DEPLETED = "BATTERY DEPLETED"

CHARGE_IDLE = "IDLE"
CHARGE_NAVIGATING = "NAVIGATING_TO_CHARGER"
CHARGE_DOCKING = "DOCKING"
CHARGE_CHARGING = "CHARGING"
CHARGE_CHARGED = "CHARGED"
CHARGE_RESUMING = "RESUMING_MISSION"
CHARGE_NO_STATION = "NO_CHARGING_STATION"


@dataclass
class BatteryModel:
    capacity: float = 100.0
    current_charge: float = 100.0
    movement_drain_rate: float = 0.00035
    rotation_drain_rate: float = 0.012
    idle_drain_rate: float = 0.002
    charge_rate: float = 8.0
    low_threshold: float = 30.0
    critical_threshold: float = 20.0
    charging: bool = False
    energy_consumed: float = 0.0

    @property
    def percentage(self) -> float:
        if self.capacity <= 0:
            return 0.0
        return max(0.0, min(100.0, (self.current_charge / self.capacity) * 100.0))

    @property
    def state(self) -> str:
        if self.charging:
            return BATTERY_CHARGING
        if self.percentage <= 0.0:
            return BATTERY_DEPLETED
        if self.percentage <= self.critical_threshold:
            return BATTERY_CRITICAL
        if self.percentage <= self.low_threshold:
            return BATTERY_LOW
        return BATTERY_NORMAL

    def consume(self, linear_velocity: float, angular_velocity: float, dt: float) -> None:
        if self.charging or dt <= 0.0:
            return
        amount = (
            abs(linear_velocity) * self.movement_drain_rate
            + abs(angular_velocity) * self.rotation_drain_rate
            + self.idle_drain_rate
        ) * dt
        self.current_charge = max(0.0, self.current_charge - amount)
        self.energy_consumed += amount

    def charge(self, dt: float) -> None:
        if dt <= 0.0:
            return
        self.charging = True
        self.current_charge = min(self.capacity, self.current_charge + self.charge_rate * dt)
        if self.current_charge >= self.capacity:
            self.current_charge = self.capacity
            self.charging = False

    def set_percentage(self, percentage: float) -> None:
        clamped = max(0.0, min(100.0, percentage))
        self.current_charge = self.capacity * (clamped / 100.0)

    def is_low(self) -> bool:
        return self.percentage <= self.low_threshold

    def is_critical(self) -> bool:
        return self.percentage <= self.critical_threshold

    def is_depleted(self) -> bool:
        return self.percentage <= 0.0


@dataclass
class BatteryManager:
    battery: BatteryModel
    enabled: bool = True
    auto_return_enabled: bool = True
    docking_radius: float = 48.0
    docking_tolerance: float = 14.0
    charging_stops: int = 0
    charge_state: str = CHARGE_IDLE
    interrupted_goal_cell: tuple[int, int] | None = None
    charger_cell: tuple[int, int] | None = None
    returning_to_charger: bool = False
    resume_requested: bool = False
    no_station_reported: bool = False

    def update_consumption(self, linear_velocity: float, angular_velocity: float, dt: float) -> None:
        if self.enabled:
            self.battery.consume(linear_velocity, angular_velocity, dt)

    def should_request_charger(self, autonomous_mode: bool, manual_mode: bool) -> bool:
        if not self.enabled or self.returning_to_charger or self.no_station_reported:
            return False
        if not self.auto_return_enabled or manual_mode:
            return False
        return autonomous_mode and self.battery.is_critical()

    def start_return_to_charger(
        self,
        current_goal_cell: tuple[int, int] | None,
        charger_cell: tuple[int, int] | None,
    ) -> bool:
        if charger_cell is None:
            self.charge_state = CHARGE_NO_STATION
            self.no_station_reported = True
            return False
        self.interrupted_goal_cell = current_goal_cell
        self.charger_cell = charger_cell
        self.returning_to_charger = True
        self.resume_requested = False
        self.charge_state = CHARGE_NAVIGATING
        return True

    def update_docking(self, distance_to_charger: float | None) -> None:
        if not self.returning_to_charger or distance_to_charger is None:
            return
        if self.charge_state == CHARGE_NAVIGATING and distance_to_charger <= self.docking_radius:
            self.charge_state = CHARGE_DOCKING
        if distance_to_charger <= self.docking_tolerance and self.charge_state in {CHARGE_NAVIGATING, CHARGE_DOCKING}:
            self.charge_state = CHARGE_CHARGING
            self.battery.charging = True
            self.charging_stops += 1

    def update_charging(self, dt: float) -> bool:
        if self.charge_state != CHARGE_CHARGING:
            return False
        self.battery.charge(dt)
        if self.battery.percentage >= 100.0:
            self.charge_state = CHARGE_CHARGED
            return True
        return False

    def begin_resume(self) -> tuple[int, int] | None:
        self.charge_state = CHARGE_RESUMING
        self.returning_to_charger = False
        self.resume_requested = True
        return self.interrupted_goal_cell

    def finish_resume(self) -> None:
        self.charge_state = CHARGE_IDLE
        self.interrupted_goal_cell = None
        self.charger_cell = None
        self.resume_requested = False

    def snapshot(self) -> dict[str, object]:
        state = self.battery.state
        if self.charge_state in {CHARGE_NAVIGATING, CHARGE_DOCKING, CHARGE_RESUMING, CHARGE_NO_STATION}:
            state = self.charge_state
        return {
            "percentage": self.battery.percentage,
            "battery_state": state,
            "charge_state": self.charge_state,
            "charging": self.battery.charging,
            "energy_consumed": self.battery.energy_consumed,
            "charging_stops": self.charging_stops,
            "charger_cell": self.charger_cell,
        }
