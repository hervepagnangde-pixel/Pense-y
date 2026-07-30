from __future__ import annotations

from datetime import datetime


def build_alert_preview(
    recipient: str,
    ticker: str,
    alert_type: str,
    message: str,
) -> str:
    """Construit une prévisualisation sans envoyer de message."""

    clean_recipient = recipient.strip() or "[destinataire non renseigné]"
    clean_ticker = ticker.strip().upper() or "[valeur non renseignée]"
    clean_message = message.strip() or "[message vide]"

    return (
        f"Destinataire : {clean_recipient}\n"
        f"Valeur : {clean_ticker}\n"
        f"Type : {alert_type}\n"
        f"Date : {datetime.now():%d/%m/%Y %H:%M}\n\n"
        f"{clean_message}"
    )
