from __future__ import annotations

from agents.base import AgentContext, AgentResult, BaseAgent


class CompanyAgent(BaseAgent):
    name = "company_agent"

    def analyze(self, context: AgentContext) -> AgentResult:
        company_data = context.extra_data.get("company", {})
        publications = company_data.get("publications", [])
        profile = company_data.get("profile", {})

        if not publications and not profile:
            return AgentResult(
                agent=self.name,
                status="insufficient_data",
                signal="ATTENTE",
                score=None,
                confidence=0.0,
                reasons=[
                    "Aucune publication ni fiche structurée de l'entreprise n'est disponible."
                ],
                risks=[
                    "Les événements propres à l'émetteur ne sont pas encore intégrés."
                ],
            )

        score = 50.0
        reasons = [
            "Des informations d'entreprise sont disponibles pour une analyse ultérieure."
        ]
        data_used = []
        if publications:
            data_used.append("publications")
            reasons.append(f"{len(publications)} publication(s) ont été détectée(s).")
        if profile:
            data_used.append("profile")

        return AgentResult(
            agent=self.name,
            status="partial",
            signal="NEUTRE",
            score=score,
            confidence=0.3,
            reasons=reasons,
            risks=[
                "Une classification sémantique des publications reste à ajouter."
            ],
            data_used=data_used,
        )
