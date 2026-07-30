from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_TIMEOUT = 18
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 Pense-y/0.2"
)
DATE_PATTERN = re.compile(r"\b(?:\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b")


@dataclass(frozen=True)
class OfficialSource:
    key: str
    name: str
    category: str
    url: str
    country_scope: str
    authority_level: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NewsItem:
    source: str
    category: str
    date: str | None
    title: str
    url: str
    collected_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


OFFICIAL_SOURCES: tuple[OfficialSource, ...] = (
    OfficialSource(
        key="bourse",
        name="Bourse de Casablanca",
        category="Marché et émetteurs",
        url="https://www.casablanca-bourse.com/en/insights-institutionnels",
        country_scope="Maroc",
        authority_level="Source de marché officielle",
    ),
    OfficialSource(
        key="ammc",
        name="AMMC",
        category="Réglementation et opérations",
        url="https://www.ammc.ma/actualites/communique-presse",
        country_scope="Maroc",
        authority_level="Autorité de régulation",
    ),
    OfficialSource(
        key="hcp",
        name="Haut-Commissariat au Plan",
        category="Macroéconomie",
        url="https://www.hcp.ma/Economie_r327.html",
        country_scope="Maroc",
        authority_level="Statistique publique",
    ),
    OfficialSource(
        key="bam",
        name="Bank Al-Maghrib",
        category="Monnaie et stabilité financière",
        url="https://www.bkam.ma/en/Press-releases",
        country_scope="Maroc",
        authority_level="Banque centrale",
    ),
)


def get_official_source_registry() -> list[dict[str, Any]]:
    return [source.to_dict() for source in OFFICIAL_SOURCES]


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
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return session


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _nearest_date(anchor: Any) -> str | None:
    current = anchor
    for _ in range(5):
        if current is None:
            break
        text = _clean(current.get_text(" ", strip=True))
        match = DATE_PATTERN.search(text)
        if match:
            return match.group(0)
        current = current.parent
    return None


def _is_relevant_title(title: str, href: str) -> bool:
    if len(title) < 12 or len(title) > 260:
        return False
    lowered = title.casefold()
    rejected = {
        "accueil",
        "home",
        "contact",
        "read more",
        "see more",
        "voir plus",
        "publications",
        "regulation",
        "search",
        "advanced search",
        "download",
        "facebook",
        "linkedin",
        "youtube",
        "instagram",
    }
    if lowered in rejected:
        return False
    if href.startswith("javascript:") or href.startswith("mailto:"):
        return False
    return True


def _deduplicate(items: list[NewsItem]) -> list[NewsItem]:
    output: list[NewsItem] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item.source.casefold(), item.title.casefold())
        if key not in seen:
            seen.add(key)
            output.append(item)
    return output


def _date_sort_key(value: str | None) -> tuple[int, str]:
    if not value:
        return (0, "")
    for pattern in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return (1, datetime.strptime(value, pattern).strftime("%Y%m%d"))
        except ValueError:
            continue
    return (0, value)


@st.cache_data(ttl=900, show_spinner=False)
def get_official_news(
    selected_source_keys: tuple[str, ...] = ("bourse", "ammc", "hcp"),
    limit_per_source: int = 8,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collecte les titres des pages officielles sélectionnées.

    Retourne ``(actualités, état_des_sources)``. Une source bloquée ne fait pas
    échouer l'ensemble de la collecte.
    """

    selected = [source for source in OFFICIAL_SOURCES if source.key in selected_source_keys]
    collected: list[NewsItem] = []
    statuses: list[dict[str, Any]] = []

    for source in selected:
        try:
            response = _session().get(source.url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            source_items: list[NewsItem] = []

            for anchor in soup.find_all("a", href=True):
                title = _clean(anchor.get_text(" ", strip=True))
                href = _clean(anchor.get("href", ""))
                if not _is_relevant_title(title, href):
                    continue

                date = _nearest_date(anchor)
                if date is None:
                    continue

                absolute_url = urljoin(source.url, href)
                parsed = urlparse(absolute_url)
                if parsed.scheme not in {"http", "https"}:
                    continue

                source_items.append(
                    NewsItem(
                        source=source.name,
                        category=source.category,
                        date=date,
                        title=title,
                        url=absolute_url,
                        collected_at_utc=datetime.now(timezone.utc).isoformat(),
                    )
                )

            source_items = _deduplicate(source_items)
            source_items.sort(key=lambda item: _date_sort_key(item.date), reverse=True)
            source_items = source_items[: max(1, limit_per_source)]
            collected.extend(source_items)
            statuses.append(
                {
                    "Source": source.name,
                    "Statut": "Connectée" if source_items else "Réponse sans élément extrait",
                    "Éléments": len(source_items),
                    "URL": source.url,
                    "Erreur": None,
                }
            )
        except requests.RequestException as exc:
            statuses.append(
                {
                    "Source": source.name,
                    "Statut": "Indisponible",
                    "Éléments": 0,
                    "URL": source.url,
                    "Erreur": str(exc),
                }
            )

    collected = _deduplicate(collected)
    collected.sort(key=lambda item: _date_sort_key(item.date), reverse=True)
    return [item.to_dict() for item in collected], statuses
