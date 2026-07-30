from __future__ import annotations

from agents.base import AgentContext, AgentResult, BaseAgent, clamp, safe_float


class TechnicalAgent(BaseAgent):
    name = "technical_agent"

    def analyze(self, context: AgentContext) -> AgentResult:
        snapshot = context.market_snapshot
        price = safe_float(snapshot.get("price"))
        opening = safe_float(snapshot.get("opening"))
        previous_close = safe_float(snapshot.get("previous_close"))
        low = safe_float(snapshot.get("low"))
        high = safe_float(snapshot.get("high"))

        if price is None:
            return AgentResult(
                agent=self.name,
                status="insufficient_data",
                signal="ATTENTE",
                score=None,
                confidence=0.0,
                reasons=["Le cours actuel est absent."],
                risks=["Aucune analyse technique ne peut être calculée."],
            )

        score_components: list[float] = []
        reasons: list[str] = []
        risks: list[str] = [
            "L'analyse est limitée à la séance courante, sans historique de prix."
        ]
        data_used = ["price"]

        if previous_close is not None and previous_close > 0:
            momentum = (price / previous_close - 1.0) * 100.0
            score_components.append(clamp(50.0 + momentum * 6.0))
            reasons.append(
                f"Momentum par rapport à la clôture précédente : {momentum:.2f} %."
            )
            data_used.append("previous_close")

        if opening is not None and opening > 0:
            intraday_return = (price / opening - 1.0) * 100.0
            score_components.append(clamp(50.0 + intraday_return * 5.0))
            reasons.append(
                f"Écart par rapport à l'ouverture : {intraday_return:.2f} %."
            )
            data_used.append("opening")

        if low is not None and high is not None and high > low:
            location = (price - low) / (high - low)
            score_components.append(clamp(location * 100.0))
            reasons.append(
                f"Le cours se situe à {location:.0%} de l'intervalle bas-haut de la séance."
            )
            data_used.extend(["low", "high"])

        if not score_components:
            return AgentResult(
                agent=self.name,
                status="insufficient_data",
                signal="ATTENTE",
                score=None,
                confidence=0.1,
                reasons=["Les données intrajournalières sont insuffisantes."],
                risks=risks,
                data_used=data_used,
            )

        score = sum(score_components) / len(score_components)
        confidence = min(0.72, 0.25 + 0.16 * len(score_components))

        if score >= 62:
            signal = "HAUSSIER"
        elif score <= 38:
            signal = "BAISSIER"
        else:
            signal = "NEUTRE"

        return AgentResult(
            agent=self.name,
            status="completed" if len(score_components) >= 2 else "partial",
            signal=signal,
            score=score,
            confidence=confidence,
            reasons=reasons,
            risks=risks,
            data_used=list(dict.fromkeys(data_used)),
        )
