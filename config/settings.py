from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    allow_live_trading: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Pense-y"),
        environment=os.getenv("APP_ENV", "development"),
        allow_live_trading=False,
    )
