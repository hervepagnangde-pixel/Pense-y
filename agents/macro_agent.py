from __future__ import annotations

from agents.base import AgentContext, AgentResult, BaseAgent, clamp, safe_float


class MacroAgent(BaseAgent):
    name = "macro_agent"

    def analyze(self, context: AgentContext) -> AgentResult:
        data = context.extra_data.get("macro", {})
        policy_rate = safe_float(data.get("policy_rate"))
        inflation = safe_float(data.get("inflation"))
        gdp_growth = safe_float(data.get("gdp_growth"))

        data_used = [
            key
            for key, value in {
                "policy_rate": policy_rate,
                "inflation": inflation,
                "gdp_growth": gdp_growth,
            }.items()
            if value is not None
        ]

        if len(data_used) < 2:
            return AgentResult(
                agent=self.name,
                status="insufficient_data",
                signal="ATTENTE",
                score=None,
                confidence=0.0,
                reasons=[
                    "Les indicateurs macroéconomiques structurés ne sont pas encore connectés."
                ],
                risks=[
                    "Le contexte de taux, d'inflation et de croissance manque à la décision."
                ],
                data_used=data_used,
            )

        components: list[float] = []
        reasons: list[str] = []

        if inflation is not None:
            components.append(clamp(70.0 - inflation * 5.0))
            reasons.append(f"Inflation observée : {inflation:.2f} %.")
        if policy_rate is not None:
            components.append(clamp(70.0 - policy_rate * 5.0))
            reasons.append(f"Taux directeur observé : {policy_rate:.2f} %.")
        if gdp_growth is not None:
            components.append(clamp(50.0 + gdp_growth * 6.0))
            reasons.append(f"Croissance observée : {gdp_growth:.2f} %.")

        score = sum(components) / len(components)
        signal = "PORTEUR" if score >= 62 else "CONTRAIGNANT" if score <= 38 else "NEUTRE"

        return AgentResult(
            agent=self.name,
            status="completed",
            signal=signal,
            score=score,
            confidence=min(0.8, 0.35 + 0.15 * len(data_used)),
            reasons=reasons,
            risks=[],
            data_used=data_used,
        )
