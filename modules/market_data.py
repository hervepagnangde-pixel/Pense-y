from __future__ import annotations

import re
import unicodedata
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry


BOURSE_BASE_URL = "https://www.casablanca-bourse.com"
TLS_FALLBACK_HOSTS = {"www.casablanca-bourse.com", "casablanca-bourse.com"}
DEFAULT_TIMEOUT = 18
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 Pense-y/0.2"
)


@dataclass(frozen=True)
class MarketSnapshot:
    ticker: str
    source_status: str
    source_name: str
    source_url: str
    price: float | None
    change_percent: float | None
    opening: float | None
    low: float | None
    high: float | None
    previous_close: float | None
    capitalization: float | None
    volume: float | None
    quantity_traded: float | None
    transactions: int | None
    currency: str
    market_delay_minutes: int
    observed_at: str | None
    collected_at_utc: str
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MarketOverview:
    source_status: str
    source_name: str
    source_url: str
    session_status: str | None
    session_date: str | None
    masi: float | None
    masi_change_percent: float | None
    masi_20: float | None
    masi_20_change_percent: float | None
    total_volume_mad: float | None
    capitalization_mad: float | None
    market_delay_minutes: int
    collected_at_utc: str
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _session() -> requests.Session:
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return session



def _get_official_page(url: str) -> tuple[requests.Response, str | None]:
    """Télécharge une page officielle avec un repli TLS strictement limité.

    La vérification SSL reste activée par défaut. Le repli sans vérification
    n'est utilisé qu'après une SSLError et uniquement pour les domaines publics
    explicitement autorisés de la Bourse de Casablanca.
    """

    session = _session()

    try:
        response = session.get(
            url,
            timeout=DEFAULT_TIMEOUT,
            verify=True,
            allow_redirects=True,
        )
        response.raise_for_status()
        return response, None

    except requests.exceptions.SSLError as ssl_error:
        requested_host = (urlparse(url).hostname or "").lower()

        if requested_host not in TLS_FALLBACK_HOSTS:
            raise

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", InsecureRequestWarning)
                response = session.get(
                    url,
                    timeout=DEFAULT_TIMEOUT,
                    verify=False,
                    allow_redirects=True,
                )
            response.raise_for_status()
        except requests.RequestException as fallback_error:
            raise requests.ConnectionError(
                "La connexion a échoué avec vérification SSL puis avec le "
                f"repli TLS contrôlé. Erreur initiale : {ssl_error}. "
                f"Erreur du repli : {fallback_error}"
            ) from fallback_error

        final_host = (urlparse(response.url).hostname or "").lower()
        if final_host not in TLS_FALLBACK_HOSTS:
            raise requests.ConnectionError(
                "La redirection TLS a quitté le domaine autorisé de la "
                "Bourse de Casablanca."
            )

        return (
            response,
            "La page officielle a été chargée avec un repli TLS contrôlé, "
            "car la chaîne de certificats du site n'a pas été validée par "
            "Streamlit Cloud. Ce repli est limité au domaine public de la "
            "Bourse de Casablanca et ne doit jamais être utilisé pour une "
            "API contenant des clés ou des données privées.",
        )


def _combine_warnings(*messages: str | None) -> str | None:
    clean_messages = [
        message.strip()
        for message in messages
        if message and message.strip()
    ]
    return " ".join(clean_messages) if clean_messages else None

def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _normalize_label(value: str) -> str:
    value = _normalize_space(value).lower()
    value = "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )
    return value.rstrip(":")


def _page_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return [_normalize_space(text) for text in soup.stripped_strings if _normalize_space(text)]


def _extract_after_label(
    lines: list[str],
    labels: tuple[str, ...],
    *,
    max_distance: int = 4,
) -> str | None:
    normalized_labels = tuple(_normalize_label(label) for label in labels)
    normalized_lines = [_normalize_label(line) for line in lines]

    for index, normalized_line in enumerate(normalized_lines):
        for label in normalized_labels:
            if normalized_line == label:
                for candidate in lines[index + 1 : index + 1 + max_distance]:
                    candidate_normalized = _normalize_label(candidate)
                    if candidate_normalized and candidate_normalized not in normalized_labels:
                        return candidate
            elif normalized_line.startswith(label + " "):
                suffix = lines[index][len(label) :].strip(" :-")
                if suffix:
                    return suffix
    return None


def _parse_number(value: str | None) -> float | None:
    if not value:
        return None
    cleaned = _normalize_space(value)
    if cleaned in {"-", "—", "–", "n/a", "N/A"}:
        return None

    cleaned = re.sub(r"[^0-9,\.\-+]", "", cleaned)
    if not cleaned or cleaned in {"-", "+"}:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) in {1, 2, 3}:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        else:
            cleaned = "".join(parts)
    elif cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = "".join(parts[:-1]) + "." + parts[-1]

    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_integer(value: str | None) -> int | None:
    number = _parse_number(value)
    return None if number is None else int(round(number))


def _first_matching_line(lines: list[str], patterns: tuple[str, ...]) -> str | None:
    for line in lines:
        normalized = _normalize_label(line)
        if any(pattern in normalized for pattern in patterns):
            return line
    return None


def _empty_snapshot(ticker: str, url: str, warning: str) -> MarketSnapshot:
    return MarketSnapshot(
        ticker=ticker,
        source_status="unavailable",
        source_name="Bourse de Casablanca",
        source_url=url,
        price=None,
        change_percent=None,
        opening=None,
        low=None,
        high=None,
        previous_close=None,
        capitalization=None,
        volume=None,
        quantity_traded=None,
        transactions=None,
        currency="MAD",
        market_delay_minutes=15,
        observed_at=None,
        collected_at_utc=datetime.now(timezone.utc).isoformat(),
        warning=warning,
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_market_snapshot(ticker: str) -> MarketSnapshot:
    """Collecte la fiche d'une valeur depuis la Bourse de Casablanca.

    Le connecteur ne remplit jamais une valeur absente. En cas de blocage ou de
    changement du site, les champs restent à ``None`` et le statut l'indique.
    """

    clean_ticker = re.sub(r"[^A-Z0-9]", "", ticker.strip().upper())
    url = f"{BOURSE_BASE_URL}/en/live-market/instruments/{quote(clean_ticker)}"

    if not clean_ticker:
        return _empty_snapshot(clean_ticker, url, "Le code de la valeur est vide.")

    try:
        response, tls_warning = _get_official_page(url)
    except requests.RequestException as exc:
        return _empty_snapshot(clean_ticker, url, f"Connexion impossible : {exc}")

    lines = _page_lines(response.text)
    if not lines:
        return _empty_snapshot(clean_ticker, url, "La page officielle ne contient aucune donnée lisible.")

    price = _parse_number(_extract_after_label(lines, ("Price", "Cours")))
    extraction_warning = None
    status = "connected" if price is not None else "partial"
    if price is None:
        extraction_warning = (
            "La page officielle a répondu, mais le cours n'a pas pu être extrait. "
            "La structure du site a peut-être changé ou la valeur est introuvable."
        )
    warning = _combine_warnings(tls_warning, extraction_warning)

    observed_at = _first_matching_line(
        lines,
        (
            "session open",
            "session closed",
            "seance ouverte",
            "seance cloturee",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
        ),
    )

    return MarketSnapshot(
        ticker=clean_ticker,
        source_status=status,
        source_name="Bourse de Casablanca",
        source_url=url,
        price=price,
        change_percent=_parse_number(
            _extract_after_label(lines, ("Change", "Variation", "Var."))
        ),
        opening=_parse_number(_extract_after_label(lines, ("Opening", "Ouverture"))),
        low=_parse_number(_extract_after_label(lines, ("Low", "Plus bas"))),
        high=_parse_number(_extract_after_label(lines, ("High", "Plus haut"))),
        previous_close=_parse_number(
            _extract_after_label(lines, ("Previous closing price", "Cours de clôture précédent"))
        ),
        capitalization=_parse_number(
            _extract_after_label(lines, ("Capitalization", "Capitalisation"))
        ),
        volume=_parse_number(_extract_after_label(lines, ("Volume", "Volume global"))),
        quantity_traded=_parse_number(
            _extract_after_label(lines, ("Quantity traded", "Quantité échangée"))
        ),
        transactions=_parse_integer(
            _extract_after_label(lines, ("Number of transactions", "Nombre de transactions"))
        ),
        currency="MAD",
        market_delay_minutes=15,
        observed_at=observed_at,
        collected_at_utc=datetime.now(timezone.utc).isoformat(),
        warning=warning,
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_market_overview() -> MarketOverview:
    """Collecte les principaux indicateurs de séance sur le portail officiel."""

    url = f"{BOURSE_BASE_URL}/en/live-market/overview"
    try:
        response, tls_warning = _get_official_page(url)
    except requests.RequestException as exc:
        return MarketOverview(
            source_status="unavailable",
            source_name="Bourse de Casablanca",
            source_url=url,
            session_status=None,
            session_date=None,
            masi=None,
            masi_change_percent=None,
            masi_20=None,
            masi_20_change_percent=None,
            total_volume_mad=None,
            capitalization_mad=None,
            market_delay_minutes=15,
            collected_at_utc=datetime.now(timezone.utc).isoformat(),
            warning=f"Connexion impossible : {exc}",
        )

    lines = _page_lines(response.text)
    masi = _parse_number(_extract_after_label(lines, ("MASI",), max_distance=3))
    masi_20 = _parse_number(_extract_after_label(lines, ("MASI 20",), max_distance=3))

    session_status = _first_matching_line(
        lines,
        ("session open", "session closed", "seance ouverte", "seance cloturee"),
    )
    session_date = _first_matching_line(
        lines,
        ("monday", "tuesday", "wednesday", "thursday", "friday", "samedi", "dimanche"),
    )

    status = "connected" if any(
        value is not None for value in (masi, masi_20)
    ) else "partial"
    extraction_warning = None if status == "connected" else (
        "La page officielle a répondu, mais les indices n'ont pas pu être entièrement extraits."
    )
    warning = _combine_warnings(tls_warning, extraction_warning)

    return MarketOverview(
        source_status=status,
        source_name="Bourse de Casablanca",
        source_url=url,
        session_status=session_status,
        session_date=session_date,
        masi=masi,
        masi_change_percent=None,
        masi_20=masi_20,
        masi_20_change_percent=None,
        total_volume_mad=_parse_number(
            _extract_after_label(
                lines,
                ("Total Value traded (in MAD)", "Volume", "Volume global"),
                max_distance=3,
            )
        ),
        capitalization_mad=_parse_number(
            _extract_after_label(
                lines,
                ("Capitalisation (in MAD)", "Capitalization", "Capitalisation"),
                max_distance=3,
            )
        ),
        market_delay_minutes=15,
        collected_at_utc=datetime.now(timezone.utc).isoformat(),
        warning=warning,
    )
