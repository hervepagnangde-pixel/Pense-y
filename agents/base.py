from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def object_to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        return dict(result) if isinstance(result, Mapping) else {}
    try:
        return asdict(value)
    except (TypeError, ValueError):
        return {}


@dataclass(frozen=True)
class AgentContext:
    ticker: str
    market_snapshot: dict[str, Any] = field(default_factory=dict)
    extra_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent: str
    status: str
    signal: str
    score: float | None
    confidence: float
    reasons: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    data_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        score = None if self.score is None else round(float(self.score), 2)
        confidence = round(clamp(float(self.confidence), 0.0, 1.0), 2)
        return {
            "agent": self.agent,
            "status": self.status,
            "signal": self.signal,
            "score": score,
            "confidence": confidence,
            "reason": self.reasons[0] if self.reasons else "",
            "reasons": self.reasons,
            "risks": self.risks,
            "data_used": self.data_used,
        }


class BaseAgent:
    name = "base_agent"

    def analyze(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError
