"""Commander tag extraction utilities - Copied from working old repo."""

from __future__ import annotations

import re
from collections import OrderedDict
from html import unescape
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from bs4 import BeautifulSoup

__all__ = [
    "extract_build_id_from_html",
    "extract_commander_tags_from_html",
    "extract_commander_sections_from_json",
    "extract_commander_tags_from_json",
    "extract_commander_tags_with_counts_from_html",
    "extract_commander_tags_with_counts_from_json",
    "normalize_commander_tag_name",
    "parse_commander_count",
    "split_commander_tag_name_and_count",
    "normalize_commander_tags",
]

_BUILD_ID_RE = re.compile(r'"buildId"\s*:\s*"([^"]+)"')
_TAG_HREF_RE = re.compile(r"/(?:tags|themes)/[a-z0-9\-]+", re.IGNORECASE)
_TAG_LINK_RE = re.compile(r"/(?:tags|themes)/[a-z0-9\-]+(?:/[a-z0-9\-]+)?", re.IGNORECASE)
_TAG_SECTION_HEADING_RE = re.compile(r"^tags$", re.IGNORECASE)
_SECTION_KEY_MAP: Dict[str, str] = {
    "highsynergy": "High Synergy Cards",
    "highsynergycards": "High Synergy Cards",
    "synergycards": "High Synergy Cards",
    "topcards": "Top Cards",
    "popularcards": "Top Cards",
    "gamechangers": "Game Changers",
    "gamechanger": "Game Changers",
}
_MAX_TAG_LENGTH = 64
_STRUCTURAL_TAG_NAMES = {
    "themes",
    "kindred",
    "new cards",
    "high synergy",
    "high synergy cards",
    "top cards",
    "game changers",
    "card types",
    "creatures",
    "spells",
    "enchantments",
    "artifacts",
    "instants",
    "sorceries",
    "planeswalkers",
    "battles",
    "lands",
    "utility lands",
    "mana artifacts",
    "utility artifacts",
}

def extract_build_id_from_html(html: str) -> Optional[str]:
    """Extract the Next.js build ID from HTML."""
    match = _BUILD_ID_RE.search(html)
    return match.group(1) if match else None

def extract_commander_tags_from_html(html: str) -> List[str]:
    """Extract commander tags from HTML (legacy format)."""
    soup = BeautifulSoup(html, "html.parser")
    tags = []
    
    # Look for tag cloud
    tag_cloud = soup.find("div", class_="tag-cloud")
    if tag_cloud:
        for tag_link in tag_cloud.find_all("a", href=True):
            if _TAG_LINK_RE.search(tag_link.get("href", "")):
                tag_text = tag_link.get_text(strip=True)
                if tag_text and len(tag_text) <= _MAX_TAG_LENGTH:
                    tags.append(tag_text)
    
    return normalize_commander_tags(tags)

def extract_commander_tags_with_counts_from_html(html: str) -> List[Dict[str, Any]]:
    """Extract commander tags with counts from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    tags = []
    
    # Look for tag cloud with counts
    tag_cloud = soup.find("div", class_="tag-cloud")
    if tag_cloud:
        for tag_link in tag_cloud.find_all("a", href=True):
            if _TAG_LINK_RE.search(tag_link.get("href", "")):
                tag_text = tag_link.get_text(strip=True)
                if tag_text and len(tag_text) <= _MAX_TAG_LENGTH:
                    # Try to parse count from the tag text
                    name, count = split_commander_tag_name_and_count(tag_text)
                    if name:
                        tags.append({"tag": name, "deck_count": count})
    
    return tags

def extract_commander_sections_from_json(payload: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extract sections (High Synergy, Top Cards, etc.) from JSON data."""
    sections = {}
    
    try:
        page_props = payload.get("props", {}).get("pageProps", {})
        
        # Try new structure
        data = page_props.get("data", {})
        container = data.get("container", {})
        json_dict = container.get("json_dict", {})
        cardlists = json_dict.get("cardlists", [])
        
        for section in cardlists:
            header = section.get("header", "")
            if header in _SECTION_KEY_MAP.values():
                section_name = header
                cards = []
                
                for key in ("cardviews", "cards", "items"):
                    card_entries = section.get(key, [])
                    for entry in card_entries:
                        if isinstance(entry, dict) and entry.get("name"):
                            cards.append(entry["name"])
                        elif isinstance(entry, str):
                            cards.append(entry)
                
                sections[section_name] = cards
                
    except Exception:
        # Fallback to empty sections
        sections = {
            "High Synergy Cards": [],
            "Top Cards": [],
            "Game Changers": [],
        }
    
    return sections

def extract_commander_tags_from_json(payload: Dict[str, Any]) -> List[str]:
    """Extract commander tags from the new EDHREC JSON structure."""
    try:
        page_props = payload.get("props", {}).get("pageProps", {})
        
        # Try the new structure first
        data = page_props.get("data", {})
        if "panels" in data and "links" in data["panels"]:
            for section in data["panels"]["links"]:
                header = section.get("header", "")
                if _TAG_SECTION_HEADING_RE.search(header):
                    # Found tags section, extract links
                    tags = []
                    for item in section.get("items", []):
                        if isinstance(item, dict) and item.get("name"):
                            name = item["name"]
                            if len(name) <= _MAX_TAG_LENGTH:
                                tags.append(name)
                    return normalize_commander_tags(tags)
        
        # Fallback to old structure
        commander = page_props.get("commander", {})
        if "metadata" in commander and "tagCloud" in commander["metadata"]:
            tag_cloud = commander["metadata"]["tagCloud"]
            if isinstance(tag_cloud, list):
                tags = [item.get("name", "") for item in tag_cloud if item.get("name")]
                return normalize_commander_tags(tags)
    
    except Exception:
        pass
    
    return []

def extract_commander_tags_with_counts_from_json(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract commander tags with counts from the new EDHREC JSON structure."""
    try:
        page_props = payload.get("props", {}).get("pageProps", {})
        
        # Try the new structure first
        data = page_props.get("data", {})
        if "panels" in data and "links" in data["panels"]:
            for section in data["panels"]["links"]:
                header = section.get("header", "")
                if _TAG_SECTION_HEADING_RE.search(header):
                    # Found tags section, extract links with counts
                    tags = []
                    for item in section.get("items", []):
                        if isinstance(item, dict) and item.get("name"):
                            name = item["name"]
                            if len(name) <= _MAX_TAG_LENGTH:
                                # Try to get count from various possible fields
                                count = None
                                for count_key in ("deckCount", "deck_count", "numDecks", "count"):
                                    if count_key in item:
                                        count = parse_commander_count(item[count_key])
                                        break
                                tags.append({"tag": name, "deck_count": count})
                    return tags
        
        # Fallback to old structure
        commander = page_props.get("commander", {})
        if "metadata" in commander and "tagCloud" in commander["metadata"]:
            tag_cloud = commander["metadata"]["tagCloud"]
            if isinstance(tag_cloud, list):
                return [
                    {"tag": item.get("name", ""), "deck_count": item.get("deckCount")}
                    for item in tag_cloud if item.get("name")
                ]
    
    except Exception:
        pass
    
    return []

def normalize_commander_tag_name(name: str) -> Optional[str]:
    """Normalize a commander tag name."""
    if not name:
        return None
    
    normalized = name.strip()
    if len(normalized) > _MAX_TAG_LENGTH:
        normalized = normalized[:_MAX_TAG_LENGTH]
    
    # Remove common prefixes/suffixes that aren't part of the tag
    normalized = re.sub(r'^\d+\.\s*', '', normalized)  # Remove "1. ", "2. ", etc.
    normalized = re.sub(r'\s+\(\d+\)$', '', normalized)  # Remove " (123)" suffixes
    normalized = normalized.strip()
    
    if not normalized:
        return None
    
    return normalized

def parse_commander_count(value: Any) -> Optional[int]:
    """Parse commander count from various formats."""
    if value is None:
        return None
    
    if isinstance(value, bool):
        return None
    
    if isinstance(value, (int, float)):
        if value >= 0:
            return int(value)
        return None
    
    if isinstance(value, str):
        # Extract numbers from strings like "1,234", "123", etc.
        import re
        match = re.search(r'\d+', value.replace(',', ''))
        if match:
            try:
                return int(match.group())
            except ValueError:
                return None
    
    return None

def split_commander_tag_name_and_count(text: str) -> Tuple[Optional[str], Optional[int]]:
    """Split commander tag name and count from text."""
    if not text:
        return None, None
    
    text = text.strip()
    
    # Try to find count patterns like "(123)" or "123"
    import re
    
    # Pattern 1: "Tag Name (123)"
    match = re.match(r'^(.+)\s+\((\d+)\)$', text)
    if match:
        name = match.group(1).strip()
        count = int(match.group(2))
        return normalize_commander_tag_name(name), count
    
    # Pattern 2: "Tag Name 123"
    match = re.match(r'^(.+)\s+(\d+)$', text)
    if match:
        name = match.group(1).strip()
        count = int(match.group(2))
        return normalize_commander_tag_name(name), count
    
    # No count found
    return normalize_commander_tag_name(text), None

def normalize_commander_tags(tags: Iterable[str]) -> List[str]:
    """Normalize and deduplicate a list of commander tags."""
    if not tags:
        return []
    
    normalized = []
    seen = set()
    
    for tag in tags:
        name = normalize_commander_tag_name(tag)
        if name and name.lower() not in seen and name.lower() not in _STRUCTURAL_TAG_NAMES:
            seen.add(name.lower())
            normalized.append(name)
    
    return normalized
