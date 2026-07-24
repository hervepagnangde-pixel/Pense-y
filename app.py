from __future__ import annotations

from datetime import datetime
from typing import Callable

import pandas as pd
import streamlit as st

from agents.orchestrator import MultiAgentOrchestrator
from config.settings import get_settings
from modules.financial_models import calculate_simple_return
from modules.market_data import get_market_snapshot
from modules.notifications import build_alert_preview


def configure_page() -> None:
    settings = get_settings()
    st.set_page_config(
        page_title=settings.app_name,
        page_icon="P",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --primary: #176B3A;
                --dark: #111827;
                --muted: #6B7280;
                --soft: #F3F4F6;
            }

            .block-container {
                padding-top: 1.4rem;
                padding-bottom: 2rem;
            }

            h1, h2, h3 {
                color: var(--dark);
            }

            [data-testid="stSidebar"] {
                border-right: 1px solid #E5E7EB;
            }

            .app-badge {
                display: inline-block;
                padding: 0.25rem 0.65rem;
                border-radius: 999px;
                background: #E8F5EC;
                color: var(--primary);
                font-weight: 700;
                font-size: 0.82rem;
                margin-bottom: 0.5rem;
            }

            .status-box {
                border: 1px solid #E5E7EB;
                background: #FAFAFA;
                border-radius: 0.75rem;
                padding: 1rem;
            }

            .small-muted {
                color: var(--muted);
                font-size: 0.88rem;
            }

            div[data-testid="stMetric"] {
                border: 1px solid #E5E7EB;
                border-radius: 0.75rem;
                padding: 0.8rem;
                background: white;
            }

            .stButton > button {
                border-radius: 0.6rem;
                font-weight: 700;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    defaults = {
        "selected_ticker": "ATW",
        "last_agent_run": None,
        "paper_trading_only": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar() -> str:
    settings = get_settings()

    st.sidebar.markdown(f"## {settings.app_name}")
    st.sidebar.caption("Plateforme multi-agents — marché financier marocain")

    page = st.sidebar.radio(
        "Navigation",
        options=[
            "Accueil",
            "Module 2 — Informations",
            "Module 3 — Agents",
            "Module 4 — Finance",
            "Module 5 — Alertes",
        ],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    st.sidebar.toggle(
        "Mode paper trading",
        key="paper_trading_only",
        help="Aucun ordre réel ne peut être exécuté.",
        disabled=True,
    )
    st.sidebar.caption(
        f"Environnement : {settings.environment}\n\n"
        f"Dernière ouverture : {datetime.now():%d/%m/%Y %H:%M}"
    )

    return page


def page_header(title: str, subtitle: str) -> None:
    st.markdown('<span class="app-badge">PENSE-Y</span>', unsafe_allow_html=True)
    st.title(title)
    st.caption(subtitle)


def render_home() -> None:
    page_header(
        "Tableau de bord",
        "Socle initial de l'application multi-agents pour la Bourse de Casablanca.",
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sources connectées", "0")
    col2.metric("Agents actifs", "0")
    col3.metric("Modèles financiers", "1")
    col4.metric("Ordres réels", "Désactivés")

    st.subheader("Architecture")
    left, right = st.columns([1.25, 1])

    with left:
        modules = pd.DataFrame(
            [
                {
                    "Module": "1",
                    "Composant": "Interface Streamlit",
                    "État": "Initialisé",
                },
                {
                    "Module": "2",
                    "Composant": "Informations de marché",
                    "État": "À connecter",
                },
                {
                    "Module": "3",
                    "Composant": "Raisonnement multi-agents",
                    "État": "Socle créé",
                },
                {
                    "Module": "4",
                    "Composant": "Mathématiques financières",
                    "État": "Socle créé",
                },
                {
                    "Module": "5",
                    "Composant": "Alertes et notifications",
                    "État": "Socle créé",
                },
            ]
        )
        st.dataframe(modules, use_container_width=True, hide_index=True)

    with right:
        st.markdown(
            """
            <div class="status-box">
                <strong>Règle de sécurité initiale</strong>
                <p class="small-muted">
                    Cette version produit uniquement des analyses et des simulations.
                    Elle n'envoie aucun ordre réel et ne constitue pas une recommandation
                    financière personnalisée.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("Prochaine intégration")
    st.info(
        "Connecter une première source fiable pour les cours, volumes et données "
        "fondamentales des sociétés cotées à Casablanca."
    )


def render_information_module() -> None:
    page_header(
        "Module 2 — Informations actualisées",
        "Préparation des connecteurs marché, entreprises, actualités et macroéconomie.",
    )

    col1, col2 = st.columns([1, 1.4])

    with col1:
        ticker = st.text_input(
            "Code de la valeur",
            value=st.session_state.selected_ticker,
            max_chars=20,
        ).strip().upper()

        source_types = st.multiselect(
            "Flux à consulter",
            options=[
                "Cours et volumes",
                "Publications de l'entreprise",
                "Actualités financières",
                "Réglementation marocaine",
                "Macroéconomie",
            ],
            default=["Cours et volumes"],
        )

        if st.button("Préparer la collecte", type="primary", use_container_width=True):
            st.session_state.selected_ticker = ticker
            snapshot = get_market_snapshot(ticker)
            st.session_state["market_snapshot"] = snapshot

    with col2:
        snapshot = st.session_state.get("market_snapshot")

        if snapshot is None:
            st.info("Saisis une valeur puis lance la préparation de la collecte.")
        else:
            st.write("### État du connecteur")
            st.json(snapshot.to_dict())
            st.warning(
                "Le connecteur de données réelles n'est pas encore branché. "
                "Aucune donnée de marché n'a été inventée."
            )

    if source_types:
        st.caption("Flux sélectionnés : " + ", ".join(source_types))


def render_agents_module() -> None:
    page_header(
        "Module 3 — Raisonnement multi-agents",
        "Orchestration des analyses technique, fondamentale, macroéconomique et risque.",
    )

    ticker = st.text_input(
        "Valeur à analyser",
        value=st.session_state.selected_ticker,
        key="agent_ticker",
    ).strip().upper()

    selected_agents = st.multiselect(
        "Agents à solliciter",
        options=[
            "market_agent",
            "company_agent",
            "macro_agent",
            "technical_agent",
            "fundamental_agent",
            "risk_agent",
            "decision_agent",
        ],
        default=[
            "market_agent",
            "technical_agent",
            "fundamental_agent",
            "risk_agent",
            "decision_agent",
        ],
    )

    if st.button("Lancer l'orchestration", type="primary"):
        orchestrator = MultiAgentOrchestrator()
        result = orchestrator.run(ticker=ticker, selected_agents=selected_agents)
        st.session_state.last_agent_run = result

    result = st.session_state.last_agent_run

    if result is None:
        st.info("Aucune orchestration n'a encore été lancée.")
        return

    st.write("### Résultat")
    st.json(result)
    st.warning(
        "Résultat provisoire : les agents sont créés mais les sources réelles "
        "et modèles de décision ne sont pas encore connectés."
    )


def render_finance_module() -> None:
    page_header(
        "Module 4 — Mathématiques financières",
        "Premier calcul intégré : rendement simple entre deux prix.",
    )

    col1, col2 = st.columns(2)

    with col1:
        initial_price = st.number_input(
            "Prix initial",
            min_value=0.0,
            value=100.0,
            step=1.0,
        )
        final_price = st.number_input(
            "Prix final",
            min_value=0.0,
            value=105.0,
            step=1.0,
        )

        if st.button("Calculer le rendement", type="primary"):
            try:
                result = calculate_simple_return(initial_price, final_price)
                st.metric("Rendement simple", f"{result:.2%}")
            except ValueError as exc:
                st.error(str(exc))

    with col2:
        st.write("### Modèles prévus")
        st.markdown(
            """
            - Indicateurs techniques
            - Mesures de risque
            - Valorisation fondamentale
            - Optimisation de portefeuille
            - Backtesting
            - Modèles économétriques
            - Machine learning
            """
        )


def render_alerts_module() -> None:
    page_header(
        "Module 5 — Alertes et notifications",
        "Préparation des e-mails et messages sans envoi réel dans cette version.",
    )

    recipient = st.text_input("Destinataire", placeholder="nom@exemple.com")
    ticker = st.text_input(
        "Valeur concernée",
        value=st.session_state.selected_ticker,
        key="alert_ticker",
    ).strip().upper()
    alert_type = st.selectbox(
        "Type d'alerte",
        options=[
            "Variation de prix",
            "Publication financière",
            "Actualité importante",
            "Signal multi-agents",
            "Risque exceptionnel",
        ],
    )
    message = st.text_area(
        "Message",
        placeholder="Contenu de l'alerte...",
        height=130,
    )

    if st.button("Prévisualiser l'alerte", type="primary"):
        preview = build_alert_preview(
            recipient=recipient,
            ticker=ticker,
            alert_type=alert_type,
            message=message,
        )
        st.code(preview, language="text")
        st.info("La prévisualisation n'envoie aucun message.")


def main() -> None:
    configure_page()
    inject_css()
    initialize_state()

    pages: dict[str, Callable[[], None]] = {
        "Accueil": render_home,
        "Module 2 — Informations": render_information_module,
        "Module 3 — Agents": render_agents_module,
        "Module 4 — Finance": render_finance_module,
        "Module 5 — Alertes": render_alerts_module,
    }

    selected_page = render_sidebar()
    pages[selected_page]()


if __name__ == "__main__":
    main()
