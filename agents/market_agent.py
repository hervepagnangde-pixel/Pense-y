from __future__ import annotations

from agents.base import AgentContext, AgentResult, BaseAgent, clamp, safe_float


class MarketAgent(BaseAgent):
    name = "market_agent"

    def analyze(self, context: AgentContext) -> AgentResult:
        snapshot = context.market_snapshot
        source_status = str(snapshot.get("source_status", "unavailable"))
        price = safe_float(snapshot.get("price"))
        change = safe_float(snapshot.get("change_percent"))
        volume = safe_float(snapshot.get("volume"))
        transactions = safe_float(snapshot.get("transactions"))

        if source_status == "unavailable" or price is None:
            return AgentResult(
                agent=self.name,
                status="insufficient_data",
                signal="ATTENTE",
                score=None,
                confidence=0.0,
                reasons=["Le cours officiel de la valeur n'est pas disponible."],
                risks=["La source de marché est indisponible ou incomplète."],
                data_used=[],
            )

        score = 50.0
        reasons = [f"Un cours de {price:,.2f} MAD a été récupéré."]
        risks: list[str] = []
        data_used = ["price"]

        if change is not None:
            score += clamp(change, -8.0, 8.0) * 4.0
            direction = "positive" if change > 0 else "négative" if change < 0 else "stable"
            reasons.append(f"La variation de séance est {direction} ({change:.2f} %).")
            data_used.append("change_percent")
        else:
            risks.append("La variation de séance n'a pas été extraite.")

        if volume is not None and volume > 0:
            reasons.append("Un volume de marché est disponible.")
            data_used.append("volume")
        else:
            risks.append("La liquidité ne peut pas encore être appréciée.")

        if transactions is not None and transactions > 0:
            data_used.append("transactions")

        completeness = min(1.0, len(data_used) / 4.0)
        confidence = 0.35 + 0.5 * completeness

        if score >= 62:
            signal = "FAVORABLE"
        elif score <= 38:
            signal = "DÉFAVORABLE"
        else:
            signal = "NEUTRE"

        return AgentResult(
            agent=self.name,
            status="completed" if completeness >= 0.5 else "partial",
            signal=signal,
            score=clamp(score),
            confidence=confidence,
            reasons=reasons,
            risks=risks,
            data_used=data_used,
        )
