from __future__ import annotations

from agents.base import AgentContext, AgentResult, BaseAgent, clamp, safe_float


class FundamentalAgent(BaseAgent):
    name = "fundamental_agent"

    def analyze(self, context: AgentContext) -> AgentResult:
        data = context.extra_data.get("fundamentals", {})
        pe = safe_float(data.get("pe"))
        roe = safe_float(data.get("roe"))
        debt_ratio = safe_float(data.get("debt_ratio"))
        dividend_yield = safe_float(data.get("dividend_yield"))

        available = {
            "pe": pe,
            "roe": roe,
            "debt_ratio": debt_ratio,
            "dividend_yield": dividend_yield,
        }
        data_used = [key for key, value in available.items() if value is not None]

        if len(data_used) < 2:
            return AgentResult(
                agent=self.name,
                status="insufficient_data",
                signal="ATTENTE",
                score=None,
                confidence=0.0,
                reasons=[
                    "Les états financiers structurés de l'entreprise ne sont pas encore connectés."
                ],
                risks=[
                    "Une recommandation sans rentabilité, endettement et valorisation serait fragile."
                ],
                data_used=data_used,
            )

        components: list[float] = []
        reasons: list[str] = []

        if pe is not None and pe > 0:
            components.append(clamp(80.0 - pe * 2.0))
            reasons.append(f"PER observé : {pe:.2f}.")
        if roe is not None:
            components.append(clamp(50.0 + roe * 2.0))
            reasons.append(f"ROE observé : {roe:.2f} %.")
        if debt_ratio is not None:
            components.append(clamp(100.0 - debt_ratio))
            reasons.append(f"Ratio d'endettement observé : {debt_ratio:.2f} %.")
        if dividend_yield is not None:
            components.append(clamp(50.0 + dividend_yield * 5.0))
            reasons.append(f"Rendement du dividende : {dividend_yield:.2f} %.")

        score = sum(components) / len(components)
        signal = "ATTRACTIF" if score >= 62 else "FAIBLE" if score <= 38 else "NEUTRE"

        return AgentResult(
            agent=self.name,
            status="completed" if len(data_used) >= 3 else "partial",
            signal=signal,
            score=score,
            confidence=min(0.85, 0.25 + 0.15 * len(data_used)),
            reasons=reasons,
            risks=[],
            data_used=data_used,
        )
