from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)


ALLOWED_SIGNALS = {
    "ACHAT À ÉTUDIER",
    "CONSERVER / SURVEILLER",
    "ÉVITER / VENTE À ÉTUDIER",
    "DONNÉES INSUFFISANTES",
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_json(text: str) -> dict[str, Any]:
    clean = text.strip()
    clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean)

    try:
        value = json.loads(clean)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
        if not match:
            return {}
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}


@dataclass
class LLMDecisionAgent:
    """Agent OpenAI chargé d'interpréter les sorties structurées des autres agents."""

    model: str | None = None

    def __post_init__(self) -> None:
        self.model = self.model or os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

    @staticmethod
    def _compact_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        allowed_fields = {
            "ticker",
            "source_status",
            "price",
            "change_percent",
            "opening",
            "previous_close",
            "low",
            "high",
            "volume",
            "transactions",
            "currency",
            "market_delay_minutes",
            "warning",
            "timestamp_utc",
        }
        return {
            key: value
            for key, value in snapshot.items()
            if key in allowed_fields
        }

    @staticmethod
    def _compact_agents(agent_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compact: list[dict[str, Any]] = []
        for result in agent_results:
            compact.append(
                {
                    "agent": result.get("agent"),
                    "status": result.get("status"),
                    "signal": result.get("signal"),
                    "score": result.get("score"),
                    "confidence": result.get("confidence"),
                    "reasons": result.get("reasons", []),
                    "risks": result.get("risks", []),
                    "data_used": result.get("data_used", []),
                }
            )
        return compact

    def analyze(
        self,
        ticker: str,
        market_snapshot: dict[str, Any],
        agent_results: list[dict[str, Any]],
        deterministic_decision: dict[str, Any] | None,
    ) -> dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            return {
                "agent": "llm_agent",
                "status": "not_configured",
                "signal": "DONNÉES INSUFFISANTES",
                "score": None,
                "confidence": 0.0,
                "reason": "La clé OPENAI_API_KEY n'est pas configurée.",
                "reasons": ["Ajoute la clé dans les Secrets de Streamlit Cloud."],
                "risks": ["L'agent OpenAI n'a pas été exécuté."],
                "data_used": [],
                "model": self.model,
                "analysis": "",
            }

        payload = {
            "ticker": ticker,
            "market_snapshot": self._compact_snapshot(market_snapshot),
            "deterministic_agents": self._compact_agents(agent_results),
            "deterministic_decision": deterministic_decision or {},
        }

        prompt = f"""
Tu es l'agent de synthèse qualitative de Pense-y, une application de paper trading
consacrée au marché financier marocain.

RÈGLES IMPÉRATIVES
1. Utilise uniquement le JSON fourni ci-dessous.
2. N'invente aucun cours, ratio financier, actualité, indicateur macroéconomique ou source.
3. Les résultats des agents déterministes sont prioritaires sur ton interprétation.
4. Si les données fondamentales ou la couverture sont insuffisantes, ne conclus pas à un achat.
5. Ne prétends jamais avoir exécuté un ordre.
6. La sortie doit être un objet JSON valide, sans texte avant ou après.
7. Le champ signal doit être exactement l'une des valeurs suivantes :
   - ACHAT À ÉTUDIER
   - CONSERVER / SURVEILLER
   - ÉVITER / VENTE À ÉTUDIER
   - DONNÉES INSUFFISANTES
8. confidence doit être compris entre 0 et 1.
9. score doit être compris entre 0 et 100, ou être null si les données sont insuffisantes.
10. Explique clairement les données manquantes.

FORMAT ATTENDU
{{
  "signal": "...",
  "score": 0,
  "confidence": 0.0,
  "summary": "Synthèse brève en français.",
  "reasons": ["raison 1", "raison 2"],
  "risks": ["risque 1"],
  "missing_data": ["donnée manquante"]
}}

DONNÉES STRUCTURÉES
{json.dumps(payload, ensure_ascii=False, default=str)}
""".strip()

        try:
            client = OpenAI(
                api_key=api_key,
                timeout=45.0,
                max_retries=2,
            )
            response = client.responses.create(
                model=self.model,
                input=prompt,
            )
            raw_text = (response.output_text or "").strip()
            parsed = _extract_json(raw_text)

            if not parsed:
                return {
                    "agent": "llm_agent",
                    "status": "partial",
                    "signal": "DONNÉES INSUFFISANTES",
                    "score": None,
                    "confidence": 0.0,
                    "reason": "La réponse OpenAI n'était pas un JSON exploitable.",
                    "reasons": [raw_text[:600]] if raw_text else [],
                    "risks": ["La synthèse automatique n'a pas pu être structurée."],
                    "data_used": ["deterministic_agents"],
                    "model": self.model,
                    "analysis": raw_text,
                }

            signal = str(parsed.get("signal", "DONNÉES INSUFFISANTES")).strip().upper()
            if signal not in ALLOWED_SIGNALS:
                signal = "DONNÉES INSUFFISANTES"

            score = _safe_float(parsed.get("score"))
            if score is not None:
                score = round(_clamp(score, 0.0, 100.0), 2)

            confidence = _safe_float(parsed.get("confidence"))
            confidence = round(_clamp(confidence or 0.0, 0.0, 1.0), 2)

            summary = str(parsed.get("summary", "")).strip()
            reasons = [
                str(item).strip()
                for item in parsed.get("reasons", [])
                if str(item).strip()
            ]
            risks = [
                str(item).strip()
                for item in parsed.get("risks", [])
                if str(item).strip()
            ]
            missing_data = [
                str(item).strip()
                for item in parsed.get("missing_data", [])
                if str(item).strip()
            ]

            if missing_data:
                risks.extend(
                    f"Donnée manquante : {item}"
                    for item in missing_data
                )

            return {
                "agent": "llm_agent",
                "status": "completed",
                "signal": signal,
                "score": score,
                "confidence": confidence,
                "reason": summary,
                "reasons": reasons or ([summary] if summary else []),
                "risks": risks,
                "data_used": ["market_snapshot", "deterministic_agents"],
                "model": self.model,
                "analysis": summary,
            }

        except AuthenticationError:
            message = "La clé OpenAI est invalide ou n'a pas les autorisations nécessaires."
        except RateLimitError:
            message = (
                "La limite de débit, le crédit disponible ou la limite de dépenses "
                "du projet OpenAI a été atteinte."
            )
        except APIConnectionError:
            message = "La connexion à l'API OpenAI a échoué."
        except APIStatusError as exc:
            message = f"L'API OpenAI a retourné le statut {exc.status_code}."
        except Exception as exc:
            message = f"Erreur OpenAI non prévue : {type(exc).__name__}."

        return {
            "agent": "llm_agent",
            "status": "error",
            "signal": "DONNÉES INSUFFISANTES",
            "score": None,
            "confidence": 0.0,
            "reason": message,
            "reasons": [message],
            "risks": ["La décision déterministe reste disponible sans l'agent OpenAI."],
            "data_used": [],
            "model": self.model,
            "analysis": "",
        }
