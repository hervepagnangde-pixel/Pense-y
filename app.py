from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import pandas as pd
import streamlit as st

from agents.orchestrator import MultiAgentOrchestrator
from config.settings import get_settings
from modules.financial_models import calculate_simple_return
from modules.market_data import get_market_snapshot
from modules.notifications import build_alert_preview


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
        :root {--green:#176B3A;--soft:#EEF7F1;--dark:#111827;--muted:#6B7280;--line:#E5E7EB;}
        .block-container{padding-top:1.2rem;padding-bottom:2.5rem;max-width:1500px;}
        [data-testid="stSidebar"]{border-right:1px solid var(--line);}
        h1,h2,h3{color:var(--dark);letter-spacing:-.02em;}
        .eyebrow{color:var(--green);font-size:.78rem;font-weight:800;letter-spacing:.12em;}
        .subtitle{color:var(--muted);font-size:1rem;margin-top:-.45rem;margin-bottom:1.2rem;}
        .hero{border:1px solid var(--line);border-radius:18px;padding:1.25rem 1.35rem;
              background:linear-gradient(135deg,#fff 0%,#f2f8f4 100%);margin-bottom:1rem;}
        .hero-title{font-size:1.35rem;font-weight:800;color:var(--dark);margin-bottom:.35rem;}
        .hero-text{color:var(--muted);margin:0;line-height:1.55;}
        .card{border:1px solid var(--line);border-radius:16px;padding:1rem 1.1rem;background:#fff;}
        .card-label{font-size:.82rem;color:var(--muted);margin-bottom:.4rem;}
        .card-value{font-size:1.35rem;font-weight:800;color:var(--dark);margin-bottom:.25rem;}
        .card-note{font-size:.82rem;color:var(--muted);line-height:1.4;}
        .pill{display:inline-block;border-radius:999px;padding:.2rem .6rem;background:var(--soft);
              color:var(--green);font-size:.74rem;font-weight:800;}
        div[data-testid="stMetric"]{border:1px solid var(--line);border-radius:16px;padding:.85rem 1rem;background:#fff;}
        .stButton>button{border-radius:10px;font-weight:700;}
        .footer{color:var(--muted);font-size:.78rem;border-top:1px solid var(--line);
                padding-top:.8rem;margin-top:2rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    defaults: dict[str, Any] = {
        "selected_ticker": "ATW",
        "watchlist": [],
        "market_snapshot": None,
        "last_agent_run": None,
        "alert_history": [],
        "portfolio_df": pd.DataFrame(
            columns=["Ticker", "Quantité", "Prix d'achat", "Prix actuel"]
        ),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def page_header(title: str, subtitle: str) -> None:
    st.markdown('<div class="eyebrow">PENSE-Y</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="subtitle">{subtitle}</div>', unsafe_allow_html=True)


def footer() -> None:
    st.markdown(
        """
        <div class="footer">
        Pense-y est actuellement un outil d'analyse et de simulation.
        Aucun ordre réel n'est exécuté et aucune donnée de marché n'est inventée.
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar() -> str:
    st.sidebar.markdown("## Pense-y")
    st.sidebar.caption("Intelligence multi-agents pour le marché financier marocain")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Tableau de bord",
            "Analyse d'une valeur",
            "Portefeuille simulé",
            "Multi-agents",
            "Alertes",
            "Configuration",
        ],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    ticker = st.sidebar.text_input(
        "Valeur suivie",
        value=st.session_state.selected_ticker,
        max_chars=20,
        help="Exemple : ATW",
    ).strip().upper()
    if ticker:
        st.session_state.selected_ticker = ticker

    st.sidebar.markdown('<span class="pill">PAPER TRADING UNIQUEMENT</span>', unsafe_allow_html=True)
    st.sidebar.caption(
        f"Environnement : {settings.environment}\n\n"
        f"Session : {datetime.now():%d/%m/%Y %H:%M}"
    )
    return page


def dashboard() -> None:
    page_header(
        "Tableau de bord",
        "Vue centrale des sources, des agents, des analyses et du portefeuille simulé.",
    )

    st.markdown(
        """
        <div class="hero">
          <div class="hero-title">Construire une décision, pas seulement un signal</div>
          <p class="hero-text">Pense-y réunira les données de marché, l'analyse des entreprises,
          les politiques économiques, les modèles financiers et les avis des agents dans une
          même chaîne de décision traçable.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sources connectées", "0")
    c2.metric("Agents opérationnels", "0")
    c3.metric("Valeurs surveillées", len(st.session_state.watchlist))
    c4.metric("Exécution réelle", "Désactivée")

    st.subheader("Vue opérationnelle")
    left, right = st.columns([1.45, 1])

    with left:
        system_df = pd.DataFrame(
            [
                ["Marché", "Cours, volumes et indices", "À connecter"],
                ["Entreprises", "Publications et fondamentaux", "À connecter"],
                ["Actualités", "Maroc, Afrique et monde", "À connecter"],
                ["Multi-agents", "Analyse et synthèse", "Socle prêt"],
                ["Finance", "Risque, stratégies et ML", "Socle prêt"],
            ],
            columns=["Bloc", "Mission", "État"],
        )
        st.dataframe(system_df, use_container_width=True, hide_index=True)

    with right:
        st.markdown("#### Liste de surveillance")
        a, b = st.columns([2.2, 1])
        ticker = a.text_input(
            "Ajouter une valeur",
            placeholder="Code de la valeur",
            label_visibility="collapsed",
            key="watchlist_input",
        ).strip().upper()
        if b.button("Ajouter", use_container_width=True):
            if ticker and ticker not in st.session_state.watchlist:
                st.session_state.watchlist.append(ticker)

        if st.session_state.watchlist:
            to_remove = st.multiselect("Retirer", st.session_state.watchlist)
            if st.button(
                "Retirer la sélection",
                use_container_width=True,
                disabled=not to_remove,
            ):
                st.session_state.watchlist = [
                    value for value in st.session_state.watchlist if value not in to_remove
                ]
            st.dataframe(
                pd.DataFrame(
                    {
                        "Valeur": st.session_state.watchlist,
                        "Données": ["Non connectées"] * len(st.session_state.watchlist),
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("La liste de surveillance est vide.")

    st.subheader("Dernière décision multi-agents")
    result = st.session_state.last_agent_run
    if result is None:
        st.info("Aucune analyse multi-agents n'a encore été lancée.")
    else:
        d1, d2, d3 = st.columns(3)
        d1.metric("Valeur", result.get("ticker", "—"))
        d2.metric("Décision", result.get("recommendation", "ANALYSE EN ATTENTE"))
        confidence = result.get("confidence")
        d3.metric("Confiance", "Non calculée" if confidence is None else f"{confidence:.0%}")
    footer()


def company_analysis() -> None:
    page_header(
        "Analyse d'une valeur",
        "Point d'entrée unique pour les données, les modèles et les agents.",
    )

    ticker = st.text_input(
        "Code de la valeur",
        value=st.session_state.selected_ticker,
        key="analysis_ticker",
        max_chars=20,
    ).strip().upper()
    if ticker:
        st.session_state.selected_ticker = ticker

    a1, a2, a3 = st.columns([1, 1, 2])
    if a1.button("Préparer les données", type="primary", use_container_width=True):
        st.session_state.market_snapshot = get_market_snapshot(ticker)
    if a2.button("Lancer les agents", use_container_width=True):
        st.session_state.last_agent_run = MultiAgentOrchestrator().run(
            ticker=ticker,
            selected_agents=[
                "market_agent",
                "company_agent",
                "macro_agent",
                "technical_agent",
                "fundamental_agent",
                "risk_agent",
                "decision_agent",
            ],
        )
    a3.caption("Aucun prix ni signal n'est fabriqué pendant cette phase.")

    tab1, tab2, tab3, tab4 = st.tabs(["Synthèse", "Données", "Agents", "Journal"])

    with tab1:
        snapshot = st.session_state.market_snapshot
        result = st.session_state.last_agent_run
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Valeur", ticker or "—")
        c2.metric(
            "Cours",
            "Non disponible"
            if snapshot is None or snapshot.price is None
            else f"{snapshot.price:,.2f}",
        )
        c3.metric(
            "Signal",
            "En attente" if result is None else result.get("recommendation", "En attente"),
        )
        c4.metric("Risque", "Non évalué")
        st.markdown(
            """
            <div class="card">
              <div class="card-label">Synthèse actuelle</div>
              <div class="card-value">Analyse non encore alimentée</div>
              <div class="card-note">Cette zone sera renseignée lorsque les connecteurs,
              les publications financières et les modèles seront intégrés.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with tab2:
        snapshot = st.session_state.market_snapshot
        if snapshot is None:
            st.info("Clique sur « Préparer les données ».")
        else:
            st.json(snapshot.to_dict())
            st.warning("Le connecteur réel n'est pas encore branché.")

    with tab3:
        result = st.session_state.last_agent_run
        if result is None:
            st.info("Clique sur « Lancer les agents ».")
        else:
            agents_df = pd.DataFrame(result.get("agents", []))
            if agents_df.empty:
                st.info("Aucun résultat d'agent disponible.")
            else:
                st.dataframe(agents_df, use_container_width=True, hide_index=True)
            with st.expander("Sortie complète"):
                st.json(result)

    with tab4:
        notes = st.text_area(
            "Notes d'analyse",
            placeholder="Hypothèses, événements importants, points à vérifier...",
            height=220,
        )
        st.caption(
            f"{len(notes)} caractère(s). La sauvegarde persistante sera ajoutée plus tard."
        )
    footer()


def portfolio() -> None:
    page_header(
        "Portefeuille simulé",
        "Saisis manuellement les positions pour mesurer leur valeur et leur performance.",
    )
    st.info("Les prix sont saisis manuellement tant qu'aucune source de marché n'est connectée.")

    edited = st.data_editor(
        st.session_state.portfolio_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="portfolio_editor",
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker"),
            "Quantité": st.column_config.NumberColumn("Quantité", min_value=0.0, format="%.2f"),
            "Prix d'achat": st.column_config.NumberColumn(
                "Prix d'achat", min_value=0.0, format="%.2f MAD"
            ),
            "Prix actuel": st.column_config.NumberColumn(
                "Prix actuel", min_value=0.0, format="%.2f MAD"
            ),
        },
    )
    st.session_state.portfolio_df = edited.copy()

    data = edited.copy()
    for col in ["Quantité", "Prix d'achat", "Prix actuel"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data["Ticker"] = data["Ticker"].fillna("").astype(str).str.upper()
    data = data[
        (data["Ticker"] != "")
        & data["Quantité"].notna()
        & data["Prix d'achat"].notna()
        & data["Prix actuel"].notna()
    ].copy()

    if data.empty:
        st.warning("Ajoute au moins une position complète pour obtenir les calculs.")
        footer()
        return

    data["Coût initial"] = data["Quantité"] * data["Prix d'achat"]
    data["Valeur actuelle"] = data["Quantité"] * data["Prix actuel"]
    data["Gain / Perte"] = data["Valeur actuelle"] - data["Coût initial"]
    data["Rendement"] = data.apply(
        lambda row: calculate_simple_return(row["Prix d'achat"], row["Prix actuel"])
        if row["Prix d'achat"] > 0
        else 0.0,
        axis=1,
    )

    cost = float(data["Coût initial"].sum())
    value = float(data["Valeur actuelle"].sum())
    pnl = value - cost
    performance = pnl / cost if cost > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Capital investi", f"{cost:,.2f} MAD")
    c2.metric("Valeur actuelle", f"{value:,.2f} MAD")
    c3.metric("Gain / Perte", f"{pnl:,.2f} MAD")
    c4.metric("Rendement", f"{performance:.2%}")

    display = data.copy()
    display["Rendement"] = display["Rendement"].map(lambda x: f"{x:.2%}")
    st.dataframe(display, use_container_width=True, hide_index=True)

    allocation = data.groupby("Ticker")["Valeur actuelle"].sum()
    if not allocation.empty:
        st.subheader("Allocation actuelle")
        st.bar_chart(allocation, height=320)
    footer()


def agents() -> None:
    page_header(
        "Centre multi-agents",
        "Sélection, lancement et contrôle des agents spécialisés.",
    )

    ticker = st.text_input(
        "Valeur analysée",
        value=st.session_state.selected_ticker,
        key="agents_ticker",
    ).strip().upper()
    selected = st.multiselect(
        "Agents à mobiliser",
        [
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

    if st.button(
        "Lancer l'orchestration",
        type="primary",
        disabled=not ticker or not selected,
    ):
        st.session_state.last_agent_run = MultiAgentOrchestrator().run(
            ticker=ticker,
            selected_agents=selected,
        )

    result = st.session_state.last_agent_run
    if result is None:
        st.info("Aucune orchestration n'a encore été exécutée.")
        footer()
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Valeur", result.get("ticker", "—"))
    c2.metric("Statut", result.get("status", "—"))
    c3.metric("Décision", result.get("recommendation", "—"))

    agents_df = pd.DataFrame(result.get("agents", []))
    if not agents_df.empty:
        st.dataframe(agents_df, use_container_width=True, hide_index=True)
    with st.expander("Réponse structurée complète"):
        st.json(result)
    st.warning("Les agents sont encore en mode structurel.")
    footer()


def alerts() -> None:
    page_header(
        "Alertes",
        "Prépare des notifications sans envoyer de message dans cette version.",
    )

    left, right = st.columns(2)
    with left:
        recipient = st.text_input("Destinataire", placeholder="nom@exemple.com")
        ticker = st.text_input(
            "Valeur",
            value=st.session_state.selected_ticker,
            key="alert_ticker",
        ).strip().upper()
        alert_type = st.selectbox(
            "Type d'alerte",
            [
                "Variation de prix",
                "Publication financière",
                "Actualité importante",
                "Signal multi-agents",
                "Risque exceptionnel",
            ],
        )
        message = st.text_area("Message", placeholder="Contenu de l'alerte...", height=150)
        if st.button("Créer la prévisualisation", type="primary"):
            preview = build_alert_preview(recipient, ticker, alert_type, message)
            st.session_state.alert_history.insert(
                0,
                {
                    "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Destinataire": recipient or "Non renseigné",
                    "Valeur": ticker or "Non renseignée",
                    "Type": alert_type,
                    "Prévisualisation": preview,
                },
            )

    with right:
        st.markdown("#### Prévisualisation")
        if st.session_state.alert_history:
            st.code(st.session_state.alert_history[0]["Prévisualisation"], language="text")
        else:
            st.info("Aucune alerte préparée.")

    st.subheader("Historique de la session")
    if st.session_state.alert_history:
        history = pd.DataFrame(st.session_state.alert_history)[
            ["Date", "Destinataire", "Valeur", "Type"]
        ]
        st.dataframe(history, use_container_width=True, hide_index=True)
    else:
        st.caption("L'historique est vide.")
    st.warning("Aucun e-mail ou message n'est envoyé à ce stade.")
    footer()


def configuration() -> None:
    page_header(
        "Configuration",
        "État des modules et règles de fonctionnement de l'application.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="card"><div class="card-label">Environnement</div>'
            f'<div class="card-value">{settings.environment}</div>'
            '<div class="card-note">Version de construction et de test.</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="card"><div class="card-label">Mode d\'exécution</div>'
            '<div class="card-value">Paper trading</div>'
            '<div class="card-note">Aucun ordre réel n\'est autorisé.</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="card"><div class="card-label">Données sensibles</div>'
            '<div class="card-value">Secrets externes</div>'
            '<div class="card-note">Les clés resteront hors du dépôt public.</div></div>',
            unsafe_allow_html=True,
        )

    st.subheader("État des cinq modules")
    modules = pd.DataFrame(
        [
            ["1 — Interface", "Version intégrée", "Affinage visuel"],
            ["2 — Informations", "À connecter", "Première source marché"],
            ["3 — Raisonnement", "Orchestrateur initial", "Règles et mémoire"],
            ["4 — Finance", "Calculs initiaux", "Indicateurs et risque"],
            ["5 — Actions", "Prévisualisation", "E-mail sécurisé"],
        ],
        columns=["Module", "État", "Prochaine étape"],
    )
    st.dataframe(modules, use_container_width=True, hide_index=True)
    st.success("Étape suivante : connecter les premières données du marché marocain.")
    footer()


def main() -> None:
    inject_css()
    initialize_state()
    pages: dict[str, Callable[[], None]] = {
        "Tableau de bord": dashboard,
        "Analyse d'une valeur": company_analysis,
        "Portefeuille simulé": portfolio,
        "Multi-agents": agents,
        "Alertes": alerts,
        "Configuration": configuration,
    }
    pages[sidebar()]()


if __name__ == "__main__":
    main()
