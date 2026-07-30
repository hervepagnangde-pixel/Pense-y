from __future__ import annotations

from agents.base import AgentContext, AgentResult, BaseAgent, clamp, safe_float


class RiskAgent(BaseAgent):
    name = "risk_agent"

    def analyze(self, context: AgentContext) -> AgentResult:
        snapshot = context.market_snapshot
        price = safe_float(snapshot.get("price"))
        low = safe_float(snapshot.get("low"))
        high = safe_float(snapshot.get("high"))
        volume = safe_float(snapshot.get("volume"))
        transactions = safe_float(snapshot.get("transactions"))

        if price is None:
            return AgentResult(
                agent=self.name,
                status="insufficient_data",
                signal="RISQUE NON MESURABLE",
                score=None,
                confidence=0.0,
                reasons=["Le cours est absent."],
                risks=["Le risque de marché ne peut pas être quantifié."],
            )

        safety_components: list[float] = []
        reasons: list[str] = []
        risks: list[str] = []
        data_used = ["price"]

        if low is not None and high is not None and price > 0 and high >= low:
            intraday_range = (high - low) / price * 100.0
            safety_components.append(clamp(100.0 - intraday_range * 10.0))
            reasons.append(
                f"Amplitude intrajournalière estimée : {intraday_range:.2f} %."
            )
            data_used.extend(["low", "high"])
            if intraday_range >= 5:
                risks.append("Amplitude intrajournalière élevée.")

        if volume is not None and volume > 0:
            safety_components.append(65.0)
            reasons.append("Un volume de négociation est disponible.")
            data_used.append("volume")
        else:
            safety_components.append(35.0)
            risks.append("La liquidité n'est pas suffisamment documentée.")

        if transactions is not None and transactions > 0:
            data_used.append("transactions")

        score = sum(safety_components) / len(safety_components)
        confidence = min(0.75, 0.25 + 0.13 * len(set(data_used)))

        if score >= 65:
            signal = "RISQUE MODÉRÉ"
        elif score <= 40:
            signal = "RISQUE ÉLEVÉ"
        else:
            signal = "RISQUE À SURVEILLER"

        return AgentResult(
            agent=self.name,
            status="completed" if len(safety_components) >= 2 else "partial",
            signal=signal,
            score=score,
            confidence=confidence,
            reasons=reasons,
            risks=risks,
            data_used=list(dict.fromkeys(data_used)),
        )
