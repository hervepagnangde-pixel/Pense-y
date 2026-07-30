from __future__ import annotations

import hmac

import streamlit as st


MAX_ATTEMPTS = 5


def _read_secret(name: str) -> str | None:
    try:
        value = st.secrets[name]
    except (KeyError, FileNotFoundError):
        return None

    if value is None:
        return None

    clean_value = str(value).strip()
    return clean_value or None


def require_password() -> None:
    """Bloque toute l'application tant que le mot de passe est incorrect."""

    if st.session_state.get("authenticated", False):
        return

    expected_password = _read_secret("APP_PASSWORD")

    st.markdown(
        """
        <div style="
            max-width:520px;
            margin:8vh auto 1.5rem auto;
            padding:1.5rem 1.6rem;
            border:1px solid #E5E7EB;
            border-radius:18px;
            background:linear-gradient(135deg,#FFFFFF 0%,#F1F8F3 100%);
        ">
            <div style="font-size:.78rem;font-weight:800;letter-spacing:.12em;color:#176B3A;">
                PENSE-Y
            </div>
            <div style="font-size:1.65rem;font-weight:800;color:#111827;margin-top:.25rem;">
                Accès sécurisé
            </div>
            <div style="color:#6B7280;margin-top:.45rem;line-height:1.5;">
                Saisis le mot de passe de l'application pour accéder aux analyses.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if expected_password is None:
        st.error(
            "Le secret APP_PASSWORD n'est pas configuré dans Streamlit Cloud. "
            "Ajoute-le dans Manage app → Settings → Secrets."
        )
        st.stop()

    attempts = int(st.session_state.get("login_attempts", 0))

    if attempts >= MAX_ATTEMPTS:
        st.error(
            "Trop de tentatives incorrectes pour cette session. "
            "Ferme l'onglet puis ouvre une nouvelle session."
        )
        st.stop()

    with st.form("login_form", clear_on_submit=True):
        password = st.text_input(
            "Mot de passe",
            type="password",
            autocomplete="current-password",
        )
        submitted = st.form_submit_button(
            "Se connecter",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if hmac.compare_digest(password, expected_password):
            st.session_state.authenticated = True
            st.session_state.login_attempts = 0
            st.rerun()

        st.session_state.login_attempts = attempts + 1
        remaining = MAX_ATTEMPTS - st.session_state.login_attempts
        st.error(
            f"Mot de passe incorrect. "
            f"{max(remaining, 0)} tentative(s) restante(s) pour cette session."
        )

    st.stop()


def render_logout_button() -> None:
    """Ajoute un bouton de déconnexion dans la barre latérale."""

    if st.sidebar.button("Se déconnecter", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.login_attempts = 0
        st.rerun()
