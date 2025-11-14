"""
EDHREC Integration Service - Copied from working old repo
Provides sophisticated EDHREC data extraction with proper error handling.
"""

import json
import re
import time
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from services.edhrec_discovery import (
    find_average_deck_url,
    display_average_deck_bracket,
    normalize_average_deck_bracket,
)
from utils.commander_identity import commander_to_slug
from utils.edhrec_commander import (
    extract_build_id_from_html,
    extract_commander_sections_from_json,
    extract_commander_tags_from_html,
    extract_commander_tags_from_json,
    extract_commander_tags_with_counts_from_html,
    extract_commander_tags_with_counts_from_json,
    normalize_commander_tag_name,
    normalize_commander_tags,
    parse_commander_count,
    split_commander_tag_name_and_count,
)

log = __import__("logging").getLogger(__name__)

__all__ = [
    "EdhrecError",
    "EdhrecNotFoundError",
    "EdhrecParsingError",
    "EdhrecTimeoutError",
    "average_deck_url",
    "deep_find_cards",
    "fetch_average_deck",
    "slugify_commander",
    "fetch_commander_summary",
    "fetch_commander_tag_theme",
    "fetch_tag_theme",
    "fetch_tag_index",
]

USER_AGENT = "Mightstone-GPT/2.0 (+https://github.com/Knack117/Mightstone-GPT)"
REQUEST_TIMEOUT = 12
RETRY_ATTEMPTS = 2
CACHE_TTL_SECONDS = 15 * 60

_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}
_CACHE: Dict[Tuple[str, str], Tuple[float, Dict[str, Any]]] = {}

@dataclass
class CommanderMetadata:
    tags: List[str]
    sections: Dict[str, List[str]]

class EdhrecError(RuntimeError):
    def __init__(self, message: str, url: str, details: Optional[str] = None) -> None:
        super().__init__(message)
        self.url = url
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        payload = {"message": str(self), "url": self.url}
        if self.details:
            payload["details"] = self.details
        return payload

class EdhrecTimeoutError(EdhrecError):
    pass

class EdhrecNotFoundError(EdhrecError):
    pass

class EdhrecParsingError(EdhrecError):
    pass

def slugify_commander(name: str) -> str:
    return commander_to_slug(name or "")

def _cache_key(slug: str, bracket: str) -> Tuple[str, str]:
    return slug, (bracket or "")

def _request_average_deck(url: str, session: Optional[requests.Session] = None) -> str:
    last_exc: Optional[EdhrecError] = None
    for attempt in range(RETRY_ATTEMPTS + 1):
        try:
            if session is not None:
                response = session.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
            else:
                response = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        except requests.Timeout:
            last_exc = EdhrecTimeoutError(
                f"Timeout fetching EDHREC page after {REQUEST_TIMEOUT}s", url
            )
        except requests.RequestException as exc:
            last_exc = EdhrecError(f"Network error talking to EDHREC: {exc}", url)
        else:
            if response.status_code == 404:
                raise EdhrecNotFoundError("Average deck not found for this commander/bracket", url)
            if response.status_code >= 500 and attempt < RETRY_ATTEMPTS:
                time.sleep(0.3 * (attempt + 1))
                continue
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                last_exc = EdhrecError(f"Unexpected response: {exc}", url)
            else:
                return response.text
        time.sleep(0.2 * (attempt + 1))
    assert last_exc is not None
    raise last_exc

def _find_next_data(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        raise EdhrecParsingError("Missing __NEXT_DATA__ payload", url, "script id=__NEXT_DATA__")
    try:
        return json.loads(script.string)
    except json.JSONDecodeError as exc:
        raise EdhrecParsingError("Invalid JSON in __NEXT_DATA__", url, str(exc)) from exc

def deep_find_cards(obj: Any) -> Optional[List[Any]]:
    """Deep search for card data in Next.js payload."""
    seen_lists: List[List[Any]] = []
    seen_ids: set[int] = set()

    def is_card_like(item: Any) -> bool:
        if isinstance(item, str):
            stripped = item.strip()
            if not stripped:
                return False
            if re.match(r'^\d+\s+[A-Za-z]', stripped):
                return False
            return True
        if isinstance(item, dict):
            if isinstance(item.get("card"), dict) and isinstance(item["card"].get("name"), str):
                return True
            for name_key in ("name", "cardName", "label", "sortname"):
                if isinstance(item.get(name_key), str):
                    name_value = str(item.get(name_key, "")).strip()
                    if re.match(r'^\d+\s+[A-Za-z]', name_value):
                        return False
                    return True
            if isinstance(item.get("names"), list) and all(isinstance(v, str) for v in item["names"]):
                return True
        return False

    def walk(node: Any) -> None:
        if isinstance(node, list):
            node_id = id(node)
            if node_id in seen_ids:
                return
            if node and all(is_card_like(entry) for entry in node):
                seen_ids.add(node_id)
                seen_lists.append(node)
                return
            seen_ids.add(node_id)
            for entry in node:
                walk(entry)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)

    walk(obj)

    if not seen_lists:
        return None

    flattened: List[Any] = []
    for entries in seen_lists:
        flattened.extend(entries)
    return flattened

@dataclass
class _NormalizedCard:
    name: str
    qty: int
    is_commander: bool = False

def _coerce_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        value = value.strip()
        if value.isdigit():
            return int(value)
    return None

def _normalize_card_entry(entry: Any) -> Optional[_NormalizedCard]:
    if isinstance(entry, str):
        name = entry.strip()
        if not name:
            return None
        if re.match(r'^\d+\s+[A-Za-z]', name):
            return None
        return _NormalizedCard(name=name, qty=1)

    if not isinstance(entry, dict):
        return None

    source = entry
    if isinstance(entry.get("card"), dict):
        source = {**entry, **entry["card"]}

    name: Optional[str] = None
    for key in ("name", "cardName", "card_name", "label", "title"):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            if re.match(r'^\d+\s+[A-Za-z]', value.strip()):
                return None
            name = value.strip()
            break

    if not name and isinstance(source.get("names"), list):
        names = [v.strip() for v in source["names"] if isinstance(v, str) and v.strip()]
        if names:
            name = " // ".join(names)

    if not name:
        return None

    qty: Optional[int] = None
    for key in ("qty", "quantity", "count", "copies", "amount", "q"):
        qty = _coerce_int(source.get(key))
        if qty is not None:
            break
    if qty is None:
        qty = 1

    is_commander = False
    for flag in ("isCommander", "is_commander", "commander"):
        value = source.get(flag)
        if isinstance(value, bool):
            is_commander = is_commander or value

    return _NormalizedCard(name=name, qty=max(1, qty), is_commander=is_commander)

def fetch_average_deck(
    name: Optional[str] = None,
    bracket: Optional[str] = "upgraded",
    *,
    source_url: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """Fetch average deck data from EDHREC with proper error handling."""
    normalized_name = (name or "").strip() or None
    normalized_bracket = None
    available_brackets: Optional[Set[str]] = None

    own_session = False
    if session is None:
        session = requests.Session()
        own_session = True

    try:
        if source_url:
            # Use the URL as-is for direct requests
            url = source_url
            slug = commander_to_slug(normalized_name) if normalized_name else ""
        else:
            if not normalized_name:
                raise ValueError("Commander name is required")
            if not bracket or not bracket.strip():
                raise ValueError("Bracket must be provided when source_url is omitted")

            # Use the EDHREC discovery service to find the URL
            discovery = find_average_deck_url(
                session,
                normalized_name,
                normalize_average_deck_bracket(bracket),
            )
            url = discovery.get("source_url")
            slug = commander_to_slug(normalized_name)

            available_data = discovery.get("available_brackets")
            if isinstance(available_data, (set, list, tuple)):
                available_brackets = {str(item) for item in available_data}

        # Fetch the page HTML
        html = _request_average_deck(url, session=session)
        
        # Extract Next.js data
        payload = _find_next_data(html, url)
        
        # Find cards in the payload
        cards = deep_find_cards(payload.get("props", {}).get("pageProps", {}))
        if not cards:
            cards = deep_find_cards(payload)
        
        if not cards:
            raise EdhrecParsingError("Could not find Next.js data in deck page", url)
        
        # Normalize cards
        normalized = []
        for card in cards:
            normalized_card = _normalize_card_entry(card)
            if normalized_card:
                normalized.append(normalized_card)
        
        # Deduplicate cards
        combined = OrderedDict()
        for card in normalized:
            key = card.name.lower()
            if key in combined:
                combined[key].qty += card.qty
                combined[key].is_commander = combined[key].is_commander or card.is_commander
            else:
                combined[key] = card
        
        # Separate commander from deck
        commander_cards = [card for card in combined.values() if card.is_commander]
        deck_cards = [card for card in combined.values() if not card.is_commander]
        
        # Build response
        result = {
            "commander": normalized_name or (commander_cards[0].name if commander_cards else None),
            "bracket": bracket,
            "source_url": url,
            "deck": {
                "cards": [
                    {"name": card.name, "count": card.qty} 
                    for card in deck_cards
                ]
            },
            "commander_card": {
                "name": commander_cards[0].name,
                "count": commander_cards[0].qty
            } if commander_cards else None,
        }
        
        if available_brackets:
            result["available_brackets"] = sorted(str(item) for item in available_brackets)
        
        return result
        
    except Exception as e:
        log.error(f"Error fetching average deck for '{normalized_name}': {e}")
        raise
    finally:
        if own_session:
            session.close()

def fetch_commander_summary(
    name: str,
    *,
    budget: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """Fetch commander summary including tags and themes."""
    if not name or not name.strip():
        raise ValueError("Commander name is required")

    slug = commander_to_slug(name.strip())

    own_session = False
    if session is None:
        session = requests.Session()
        own_session = True

    try:
        url = f"https://scryfall.com/commanders/{slug}"
        if budget:
            url = f"{url}/{budget}"

        response = session.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        html = response.text

        # Extract Next.js data
        payload = _find_next_data(html, url) if "__NEXT_DATA__" in html else None

        # Extract tags from both HTML and JSON
        tags_from_payload = (
            extract_commander_tags_with_counts_from_json(payload) if payload else []
        )
        tags_from_html = extract_commander_tags_with_counts_from_html(html)
        json_tag_names = extract_commander_tags_from_json(payload) if payload else []
        html_tag_names = extract_commander_tags_from_html(html)

        # Combine all tag sources
        all_tags = []
        for tag_entry in tags_from_payload + tags_from_html:
            if isinstance(tag_entry, dict):
                all_tags.append(tag_entry.get("tag", ""))
            elif isinstance(tag_entry, str):
                all_tags.append(tag_entry)
        
        # Add tag names without counts
        all_tags.extend(json_tag_names + html_tag_names)

        # Normalize and deduplicate tags
        normalized_tags = normalize_commander_tags(all_tags)
        unique_tags = list(dict.fromkeys(normalized_tags))[:20]  # Limit to top 20

        # Extract sections (High Synergy, Top Cards, etc.)
        sections = {}
        if payload:
            sections = extract_commander_sections_from_json(payload)

        return {
            "commander": name.strip(),
            "slug": slug,
            "source_url": url,
            "budget": budget,
            "tags": [{"tag": tag} for tag in unique_tags],
            "themes": unique_tags,
            "sections": sections,
        }
    finally:
        if own_session:
            session.close()

def fetch_tag_theme(
    tag: str,
    *,
    identity: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """Fetch theme/tag data from EDHREC."""
    if not tag or not tag.strip():
        raise ValueError("Tag name is required")

    tag_slug = tag.strip().lower().replace(" ", "-").replace("_", "-")
    
    own_session = False
    if session is None:
        session = requests.Session()
        own_session = True

    try:
        # Try EDHREC theme URLs
        url = f"https://scryfall.com/tags/{tag_slug}"
        if identity:
            url = f"{url}/{identity.lower()}"

        response = session.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        if response.status_code == 404:
            # Try EDHREC tags URL as fallback
            url = f"https://scryfall.com/search?q=name%3A%22enchantress%22"
            response = session.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
            
        response.raise_for_status()
        html = response.text

        # Extract Next.js data if available
        payload = _find_next_data(html, url) if "__NEXT_DATA__" in html else None

        # Parse card lists from the payload
        cards = []
        if payload:
            try:
                # Try to extract cards from the new EDHREC structure
                page_props = payload.get("props", {}).get("pageProps", {})
                data = page_props.get("data", {})
                container = data.get("container", {})
                json_dict = container.get("json_dict", {})
                cardlists = json_dict.get("cardlists", [])
                
                for section in cardlists:
                    header = section.get("header", "")
                    if "cards" in header.lower() or "card" in header.lower():
                        for card_entry in section.get("cards", []):
                            if isinstance(card_entry, dict) and card_entry.get("name"):
                                cards.append({
                                    "name": card_entry["name"],
                                    "percent": card_entry.get("percent", 0),
                                    "synergy": card_entry.get("synergy", 0)
                                })
            except Exception as e:
                log.warning(f"Failed to extract cards from EDHREC data: {e}")

        return {
            "theme": tag_slug,
            "cards": cards,
            "source_url": url,
            "header": f"{tag_slug.title()} | EDHREC",
            "description": f"Popular {tag_slug} cards for Commander",
        }
        
    finally:
        if own_session:
            session.close()
