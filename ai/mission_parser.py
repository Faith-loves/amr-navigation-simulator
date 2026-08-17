import difflib
import re
from dataclasses import dataclass

from ai.semantic_locations import SemanticLocation, locations_for_scenario


TASK_PENDING = "PENDING"
TASK_ACTIVE = "ACTIVE"
TASK_COMPLETED = "COMPLETED"
TASK_FAILED = "FAILED"

MISSION_IDLE = "IDLE"
MISSION_RUNNING = "RUNNING"
MISSION_COMPLETED = "COMPLETED"
MISSION_FAILED = "FAILED"

INTENT_NAVIGATE = "NAVIGATE"
INTENT_MULTI_STOP = "MULTI_STOP"
INTENT_RETURN = "RETURN"
INTENT_STOP = "STOP"
INTENT_PAUSE = "PAUSE"
INTENT_RESUME = "RESUME"
INTENT_CANCEL = "CANCEL"
INTENT_STATUS = "STATUS"
INTENT_CHARGE = "CHARGE"
INTENT_UNKNOWN = "UNKNOWN"

FUZZY_THRESHOLD = 0.72


@dataclass
class ParsedIntent:
    intent: str
    destinations: list[str]
    confidence: float
    raw_text: str
    normalized_text: str
    error_message: str = ""


@dataclass
class MissionTask:
    target_name: str
    target_position: tuple[float, float]
    status: str = TASK_PENDING


@dataclass
class Mission:
    raw_command: str
    tasks: list[MissionTask]
    current_task_index: int = 0
    mission_status: str = MISSION_IDLE
    intent: str = INTENT_NAVIGATE
    confidence: float = 1.0

    @property
    def current_task(self) -> MissionTask | None:
        if self.current_task_index < 0 or self.current_task_index >= len(self.tasks):
            return None
        return self.tasks[self.current_task_index]


class MissionParseError(ValueError):
    pass


class MissionParser:
    def parse_intent(self, raw_command: str, scenario_name: str) -> ParsedIntent:
        normalized = self._normalize(raw_command)
        if not normalized:
            return ParsedIntent(INTENT_UNKNOWN, [], 0.0, raw_command, normalized, "No valid destination found.")

        command_intent = self._command_intent(normalized)
        if command_intent != INTENT_UNKNOWN:
            return ParsedIntent(command_intent, [], 1.0, raw_command, normalized)

        locations = locations_for_scenario(scenario_name)
        segments = self._segments(normalized)
        destinations = []
        confidences = []

        for segment in segments:
            target_phrase = self._target_phrase(segment)
            match, confidence = self._match_location_with_confidence(target_phrase, locations)
            if match is None:
                if self._is_vague_destination(target_phrase):
                    return ParsedIntent(INTENT_UNKNOWN, [], 0.0, raw_command, normalized, "No valid destination found.")
                display = self._display_unknown(target_phrase)
                message = f"Unknown location: {display}" if display else "No valid destination found."
                return ParsedIntent(INTENT_UNKNOWN, [], 0.0, raw_command, normalized, message)
            destinations.append(match.name)
            confidences.append(confidence)

        if not destinations:
            return ParsedIntent(INTENT_UNKNOWN, [], 0.0, raw_command, normalized, "No valid destination found.")

        intent = INTENT_MULTI_STOP if len(destinations) > 1 else INTENT_NAVIGATE
        if normalized.startswith("return") or normalized.startswith("go back") or normalized.startswith("come back"):
            intent = INTENT_RETURN if len(destinations) == 1 else INTENT_MULTI_STOP

        return ParsedIntent(
            intent=intent,
            destinations=destinations,
            confidence=min(confidences),
            raw_text=raw_command,
            normalized_text=normalized,
        )

    def parse(self, raw_command: str, scenario_name: str) -> Mission:
        parsed = self.parse_intent(raw_command, scenario_name)
        if parsed.error_message:
            raise MissionParseError(parsed.error_message)
        if parsed.intent == INTENT_CHARGE:
            parsed.destinations = ["charging station"]
        if parsed.intent not in {INTENT_NAVIGATE, INTENT_MULTI_STOP, INTENT_RETURN, INTENT_CHARGE}:
            raise MissionParseError(f"Command is not a navigation mission: {parsed.intent}")

        locations = locations_for_scenario(scenario_name)
        tasks = []
        for destination in parsed.destinations:
            location = locations[destination]
            tasks.append(MissionTask(target_name=location.name.title(), target_position=location.position))

        if not tasks:
            raise MissionParseError("No valid destination found.")

        return Mission(
            raw_command=raw_command.strip(),
            tasks=tasks,
            intent=parsed.intent,
            confidence=parsed.confidence,
        )

    def _normalize(self, command: str) -> str:
        command = command.lower()
        command = re.sub(r"[^a-z0-9\s]", " ", command)
        command = re.sub(r"\s+", " ", command)
        command = command.strip()

        filler_patterns = [
            r"\bcan you\b",
            r"\bcould you\b",
            r"\bwould you\b",
            r"\bi need you to\b",
            r"\bplease take me to\b",
            r"\bplease\b",
            r"\bthe robot\b",
            r"\brobot\b",
            r"\bamr\b",
            r"\bover\b",
            r"\bfirst\b",
            r"\bfinally\b",
        ]
        for pattern in filler_patterns:
            command = re.sub(pattern, " ", command)

        command = re.sub(r"\s+", " ", command)
        return command.strip()

    def _command_intent(self, normalized: str) -> str:
        if re.fullmatch(r"(stop|stop navigation|stop mission|stop the mission|stop the amr)", normalized):
            return INTENT_STOP
        if re.fullmatch(r"(pause|pause navigation|pause mission|pause the mission)", normalized):
            return INTENT_PAUSE
        if re.fullmatch(r"(resume|continue|continue navigation|resume mission|resume navigation)", normalized):
            return INTENT_RESUME
        if re.fullmatch(r"(cancel|cancel mission|cancel this mission|clear mission)", normalized):
            return INTENT_CANCEL
        if re.search(r"\b(where are you going|where are you heading|status|mission status)\b", normalized):
            return INTENT_STATUS
        if re.fullmatch(r"(charge|charge robot|charge the robot|return to charger|go to charger|go to charging station)", normalized):
            return INTENT_CHARGE
        return INTENT_UNKNOWN

    def _segments(self, command: str) -> list[str]:
        command = re.sub(r"\b(after that|and then|then|next|before going to|before|finally)\b", "|", command)
        return [part.strip() for part in command.split("|") if part.strip()]

    def _target_phrase(self, segment: str) -> str:
        phrase = segment.strip()
        prefixes = [
            "take me to",
            "take to",
            "take",
            "go back to",
            "come back to",
            "return to",
            "navigate to",
            "move to",
            "travel to",
            "head to",
            "go to",
            "visit",
            "head",
            "go",
        ]
        for prefix in prefixes:
            if phrase == prefix:
                return ""
            if phrase.startswith(prefix + " "):
                phrase = phrase[len(prefix) :].strip()
                break
        phrase = re.sub(r"\b(the|a|an|to)\b", " ", phrase)
        return re.sub(r"\s+", " ", phrase).strip()

    def _match_location_with_confidence(
        self,
        target_phrase: str,
        locations: dict[str, SemanticLocation],
    ) -> tuple[SemanticLocation | None, float]:
        if not target_phrase:
            return None, 0.0

        normalized_target = self._compact(target_phrase)
        for name in sorted(locations, key=len, reverse=True):
            if target_phrase == name or normalized_target == self._compact(name):
                return locations[name], 1.0

        for name in sorted(locations, key=len, reverse=True):
            if re.search(rf"\b{re.escape(name)}\b", target_phrase):
                return locations[name], 0.98

        best_name = ""
        best_score = 0.0
        for name in locations:
            score = max(
                difflib.SequenceMatcher(None, target_phrase, name).ratio(),
                difflib.SequenceMatcher(None, normalized_target, self._compact(name)).ratio(),
                difflib.SequenceMatcher(None, self._token_sort(target_phrase), self._token_sort(name)).ratio(),
            )
            if score > best_score:
                best_name = name
                best_score = score

        if best_name and best_score >= FUZZY_THRESHOLD:
            return locations[best_name], best_score

        return None, best_score

    def _match_location(
        self,
        target_phrase: str,
        locations: dict[str, SemanticLocation],
    ) -> SemanticLocation | None:
        location, _confidence = self._match_location_with_confidence(target_phrase, locations)
        return location

    def _compact(self, text: str) -> str:
        return re.sub(r"\s+", "", text)

    def _token_sort(self, text: str) -> str:
        return " ".join(sorted(text.split()))

    def _is_vague_destination(self, target_phrase: str) -> bool:
        return target_phrase in {"somewhere", "anywhere", "there"}

    def _display_unknown(self, target_phrase: str) -> str:
        return target_phrase.title().strip()
