from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class MarketSnapshot:
    ticker: str
    source_status: str
    price: float | None
    volume: float | None
    currency: str | None
    timestamp_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_market_snapshot(ticker: str) -> MarketSnapshot:
    """Retourne un objet vide tant qu'aucune source réelle n'est connectée."""

    clean_ticker = ticker.strip().upper()

    return MarketSnapshot(
        ticker=clean_ticker,
        source_status="not_connected",
        price=None,
        volume=None,
        currency="MAD",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )
