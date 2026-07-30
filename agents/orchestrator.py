from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class MultiAgentOrchestrator:
    """Orchestrateur initial.

    Cette version ne fabrique aucune donnée financière. Elle prépare seulement
    la structure de sortie qui sera enrichie lors de la connexion des agents.
    """

    def run(self, ticker: str, selected_agents: list[str]) -> dict[str, Any]:
        clean_ticker = ticker.strip().upper()

        if not clean_ticker:
            return {
                "status": "error",
                "message": "Le code de la valeur est obligatoire.",
            }

        agent_results = [
            {
                "agent": agent_name,
                "status": "not_connected",
                "signal": None,
                "score": None,
                "confidence": None,
                "reason": "Source ou modèle non encore connecté.",
            }
            for agent_name in selected_agents
        ]

        return {
            "ticker": clean_ticker,
            "status": "waiting_for_data",
            "recommendation": "ANALYSE EN ATTENTE",
            "global_score": None,
            "confidence": None,
            "paper_trading_only": True,
            "agents": agent_results,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
