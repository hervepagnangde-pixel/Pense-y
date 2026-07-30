from __future__ import annotations

from agents.base import AgentResult, clamp


class DecisionAgent:
    name = "decision_agent"

    WEIGHTS = {
        "market_agent": 0.20,
        "company_agent": 0.10,
        "macro_agent": 0.10,
        "technical_agent": 0.25,
        "fundamental_agent": 0.25,
        "risk_agent": 0.10,
    }

    def synthesize(
        self,
        results: list[AgentResult],
        selected_agents: list[str],
    ) -> AgentResult:
        valid = [
            result
            for result in results
            if result.score is not None and result.status in {"completed", "partial"}
        ]

        selected_non_decision = [
            name for name in selected_agents if name != self.name and name in self.WEIGHTS
        ]
        selected_weight = sum(self.WEIGHTS[name] for name in selected_non_decision)
        valid_weight = sum(self.WEIGHTS[result.agent] for result in valid)
        coverage = valid_weight / selected_weight if selected_weight > 0 else 0.0

        if len(valid) < 2 or coverage < 0.40:
            return AgentResult(
                agent=self.name,
                status="insufficient_data",
                signal="DONNÉES INSUFFISANTES",
                score=None,
                confidence=clamp(coverage, 0.0, 1.0),
                reasons=[
                    "Trop peu d'agents disposent de données exploitables pour conclure."
                ],
                risks=[
                    "Aucune recommandation d'achat ou de vente ne doit être produite à ce stade."
                ],
                data_used=[result.agent for result in valid],
            )

        weighted_score = sum(
            result.score * self.WEIGHTS[result.agent] for result in valid
        ) / valid_weight
        average_agent_confidence = sum(result.confidence for result in valid) / len(valid)
        confidence = average_agent_confidence * coverage

        has_fundamental = any(
            result.agent == "fundamental_agent" and result.score is not None
            for result in valid
        )
        has_macro = any(
            result.agent == "macro_agent" and result.score is not None
            for result in valid
        )

        if not has_fundamental:
            signal = "À SURVEILLER"
            reasons = [
                f"Score provisoire : {weighted_score:.1f}/100.",
                "La décision reste limitée faute de données fondamentales.",
            ]
        elif weighted_score >= 65 and confidence >= 0.45:
            signal = "ACHAT À ÉTUDIER"
            reasons = [f"Score agrégé favorable : {weighted_score:.1f}/100."]
        elif weighted_score <= 35 and confidence >= 0.45:
            signal = "ÉVITER / VENTE À ÉTUDIER"
            reasons = [f"Score agrégé défavorable : {weighted_score:.1f}/100."]
        else:
            signal = "CONSERVER / SURVEILLER"
            reasons = [f"Score agrégé intermédiaire : {weighted_score:.1f}/100."]

        risks = []
        if not has_fundamental:
            risks.append("Absence d'analyse fondamentale exploitable.")
        if not has_macro:
            risks.append("Contexte macroéconomique non intégré.")
        if coverage < 0.70:
            risks.append("Couverture partielle des agents sélectionnés.")

        return AgentResult(
            agent=self.name,
            status="completed" if coverage >= 0.70 else "partial",
            signal=signal,
            score=weighted_score,
            confidence=confidence,
            reasons=reasons,
            risks=risks,
            data_used=[result.agent for result in valid],
        )
