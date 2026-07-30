from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.base import AgentContext, AgentResult, object_to_dict
from agents.company_agent import CompanyAgent
from agents.decision_agent import DecisionAgent
from agents.fundamental_agent import FundamentalAgent
from agents.macro_agent import MacroAgent
from agents.market_agent import MarketAgent
from agents.llm_agent import LLMDecisionAgent
from agents.risk_agent import RiskAgent
from agents.technical_agent import TechnicalAgent


class MultiAgentOrchestrator:
    """Orchestre les agents sans laisser l'échec d'un agent bloquer l'application."""

    def __init__(self) -> None:
        self.registry = {
            "market_agent": MarketAgent(),
            "company_agent": CompanyAgent(),
            "macro_agent": MacroAgent(),
            "technical_agent": TechnicalAgent(),
            "fundamental_agent": FundamentalAgent(),
            "risk_agent": RiskAgent(),
        }
        self.decision_agent = DecisionAgent()
        self.llm_agent = LLMDecisionAgent()

    @staticmethod
    def _load_market_snapshot(ticker: str) -> tuple[dict[str, Any], list[str]]:
        warnings: list[str] = []
        try:
            from modules import market_data

            getter = getattr(market_data, "get_market_snapshot", None)
            if not callable(getter):
                warnings.append(
                    "modules.market_data.get_market_snapshot est introuvable."
                )
                return {}, warnings

            snapshot = getter(ticker)
            snapshot_dict = object_to_dict(snapshot)
            if not snapshot_dict:
                warnings.append("La source marché a retourné un objet vide.")
            warning = snapshot_dict.get("warning")
            if warning:
                warnings.append(str(warning))
            return snapshot_dict, warnings
        except Exception as exc:
            warnings.append(
                f"Le connecteur de marché n'a pas pu être interrogé : {type(exc).__name__}: {exc}"
            )
            return {}, warnings

    @staticmethod
    def _error_result(agent_name: str, exc: Exception) -> AgentResult:
        return AgentResult(
            agent=agent_name,
            status="error",
            signal="ERREUR",
            score=None,
            confidence=0.0,
            reasons=[
                f"L'agent a échoué sans interrompre l'orchestration : {type(exc).__name__}."
            ],
            risks=[str(exc)],
        )

    def run(
        self,
        ticker: str,
        selected_agents: list[str],
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_ticker = "".join(
            character for character in ticker.strip().upper()
            if character.isalnum() or character in {"-", "_"}
        )

        if not clean_ticker:
            return {
                "ticker": "",
                "status": "error",
                "recommendation": "CODE VALEUR MANQUANT",
                "global_score": None,
                "confidence": 0.0,
                "data_coverage": 0.0,
                "paper_trading_only": True,
                "agents": [],
                "warnings": ["Le code de la valeur est obligatoire."],
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }

        selected = list(dict.fromkeys(selected_agents))
        market_snapshot, warnings = self._load_market_snapshot(clean_ticker)
        context = AgentContext(
            ticker=clean_ticker,
            market_snapshot=market_snapshot,
            extra_data=extra_data or {},
        )

        results: list[AgentResult] = []
        for agent_name in selected:
            if agent_name in {"decision_agent", "llm_agent"}:
                continue

            agent = self.registry.get(agent_name)
            if agent is None:
                warnings.append(f"Agent inconnu ignoré : {agent_name}.")
                continue

            try:
                results.append(agent.analyze(context))
            except Exception as exc:
                results.append(self._error_result(agent_name, exc))

        decision_result: AgentResult | None = None
        if "decision_agent" in selected:
            try:
                decision_result = self.decision_agent.synthesize(results, selected)
            except Exception as exc:
                decision_result = self._error_result("decision_agent", exc)
            results.append(decision_result)

        valid_non_decision = [
            result
            for result in results
            if result.agent != "decision_agent"
            and result.score is not None
            and result.status in {"completed", "partial"}
        ]
        requested_non_decision = [
            name
            for name in selected
            if name not in {"decision_agent", "llm_agent"}
        ]
        data_coverage = (
            len(valid_non_decision) / len(requested_non_decision)
            if requested_non_decision else 0.0
        )

        if decision_result is not None:
            recommendation = decision_result.signal
            global_score = decision_result.score
            confidence = decision_result.confidence
            status = decision_result.status
        elif valid_non_decision:
            recommendation = "ANALYSES DISPONIBLES — SYNTHÈSE NON DEMANDÉE"
            global_score = round(
                sum(result.score for result in valid_non_decision)
                / len(valid_non_decision),
                2,
            )
            confidence = round(
                sum(result.confidence for result in valid_non_decision)
                / len(valid_non_decision),
                2,
            )
            status = "partial"
        else:
            recommendation = "DONNÉES INSUFFISANTES"
            global_score = None
            confidence = 0.0
            status = "insufficient_data"

        structured_results = [result.to_dict() for result in results]
        deterministic_decision = (
            decision_result.to_dict()
            if decision_result is not None
            else None
        )

        llm_analysis: dict[str, Any] | None = None
        if "llm_agent" in selected:
            llm_analysis = self.llm_agent.analyze(
                ticker=clean_ticker,
                market_snapshot=market_snapshot,
                agent_results=structured_results,
                deterministic_decision=deterministic_decision,
            )
            structured_results.append(llm_analysis)

        return {
            "ticker": clean_ticker,
            "status": status,
            "recommendation": recommendation,
            "global_score": global_score,
            "confidence": round(float(confidence), 2),
            "data_coverage": round(float(data_coverage), 2),
            "paper_trading_only": True,
            "market_source_status": market_snapshot.get(
                "source_status", "unavailable"
            ),
            "agents": structured_results,
            "llm_analysis": llm_analysis,
            "warnings": warnings,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
