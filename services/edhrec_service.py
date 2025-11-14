"""
EDHREC service - Handles EDHREC data fetching and processing.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote_plus

import httpx

from models.schemas import (
    ThemeData, 
    ThemeItem, 
    ThemeCollection, 
    DeckData, 
    DeckCard,
    BudgetComparison,
    ThemeSuggestion
)

log = logging.getLogger(__name__)


class EDHRECService:
    """Service for interacting with EDHREC data."""
    
    def __init__(self):
        self.base_url = "https://edhrec.com"
        self.client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        self._user_agent = "Mightstone-GPT/2.0 (+https://github.com/Knack117/Mightstone-GPT)"
    
    async def initialize(self):
        """Initialize the HTTP client."""
        try:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(20.0, connect=10.0),
                headers={"User-Agent": self._user_agent}
            )
            self._initialized = True
            log.info("✅ EDHREC service initialized")
        except Exception as e:
            log.error(f"Failed to initialize EDHREC service: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.client:
            await self.client.aclose()
            self._initialized = False
            log.info("✅ EDHREC service cleaned up")
    
    async def get_average_deck(self, commander_name: str, bracket: str = "optimized") -> Dict[str, Any]:
        """Get average deck for a commander with specific bracket."""
        if not self._initialized:
            raise RuntimeError("EDHREC service not initialized")
        
        try:
            # Find the commander page
            commander_url = await self._find_commander_page(commander_name)
            if not commander_url:
                raise ValueError(f"Commander '{commander_name}' not found on EDHREC")
            
            # Get the deck URL
            deck_info = await self._find_average_deck_url(commander_name, bracket)
            if not deck_info.get("url"):
                raise ValueError(f"No {bracket} deck found for '{commander_name}'")
            
            # Fetch the deck data
            deck_html = await self._fetch_html(deck_info["url"])
            deck_data = await self._parse_average_deck(deck_html, commander_name, bracket)
            
            return deck_data
            
        except Exception as e:
            log.error(f"Error getting average deck for '{commander_name}': {e}")
            raise
    
    async def get_budget_comparison(self, commander_name: str) -> BudgetComparison:
        """Get budget vs expensive deck comparison."""
        if not self._initialized:
            raise RuntimeError("EDHREC service not initialized")
        
        try:
            # Get budget deck
            try:
                budget_deck = await self.get_average_deck(commander_name, "budget")
            except Exception:
                budget_deck = None
            
            # Get expensive deck
            try:
                expensive_deck = await self.get_average_deck(commander_name, "expensive")
            except Exception:
                expensive_deck = None
            
            return BudgetComparison(
                commander=commander_name,
                budget_deck=budget_deck,
                expensive_deck=expensive_deck
            )
            
        except Exception as e:
            log.error(f"Error getting budget comparison for '{commander_name}': {e}")
            raise
    
    async def get_theme_data(self, theme_name: str, colors: Optional[str] = None) -> ThemeData:
        """Get theme/tag data from EDHREC."""
        if not self._initialized:
            raise RuntimeError("EDHREC service not initialized")
        
        try:
            # Build theme URL
            if colors:
                url = f"{self.base_url}/tags/{theme_name}/{colors.lower()}"
            else:
                url = f"{self.base_url}/tags/{theme_name}"
            
            # Try to fetch the theme page
            try:
                response = await self.client.get(url, timeout=15.0)
                response.raise_for_status()
                html = response.text
            except httpx.HTTPError:
                # Fallback to search
                url = f"{self.base_url}/search?q={quote_plus(theme_name)}"
                response = await self.client.get(url, timeout=15.0)
                response.raise_for_status()
                html = response.text
            
            # Parse the theme data
            theme_data = await self._parse_theme_page(html, theme_name, colors)
            
            return theme_data
            
        except Exception as e:
            log.error(f"Error getting theme data for '{theme_name}': {e}")
            raise
    
    async def get_theme_suggestions(self, commander_name: str) -> List[ThemeSuggestion]:
        """Get theme suggestions for a commander."""
        if not self._initialized:
            raise RuntimeError("EDHREC service not initialized")
        
        try:
            # Find commander page
            commander_url = await self._find_commander_page(commander_name)
            if not commander_url:
                return []
            
            # Fetch commander page
            html = await self._fetch_html(commander_url)
            
            # Extract themes/tags
            themes = await self._extract_commander_themes(html)
            
            # Convert to suggestions
            suggestions = []
            for theme_name, score in themes.items():
                suggestions.append(ThemeSuggestion(
                    theme_name=theme_name,
                    popularity_score=score,
                    category="theme"
                ))
            
            return suggestions
            
        except Exception as e:
            log.error(f"Error getting theme suggestions for '{commander_name}': {e}")
            raise
    
    # Private helper methods
    
    async def _find_commander_page(self, commander_name: str) -> Optional[str]:
        """Find the EDHREC commander page URL."""
        # Try direct URL first
        slug = self._normalize_commander_name(commander_name)
        direct_url = f"{self.base_url}/commanders/{slug}"
        
        response = await self.client.get(direct_url, timeout=15.0)
        if response.status_code == 200:
            return direct_url
        
        # Try search
        search_url = f"{self.base_url}/search?q={quote_plus(commander_name)}"
        search_html = await self._fetch_html(search_url)
        
        # Look for commander link in search results
        match = re.search(r'href="(/commanders/[a-z0-9\-]+)"', search_html)
        if match:
            return f"{self.base_url}{match.group(1)}"
        
        return None
    
    async def _find_average_deck_url(self, commander_name: str, bracket: str) -> Dict[str, Optional[str]]:
        """Find the URL for a commander's average deck."""
        commander_url = await self._find_commander_page(commander_name)
        if not commander_url:
            return {"url": None, "available": set()}
        
        # Fetch commander page
        html = await self._fetch_html(commander_url)
        
        # Look for deck links
        deck_links = re.findall(r'href="(/average-decks/[a-z0-9\-]+(?:/[a-z0-9\-]+){0,2})"', html)
        deck_links = list(dict.fromkeys(deck_links))  # Remove duplicates
        
        if not deck_links:
            return {"url": None, "available": set()}
        
        # Find the best match for the bracket
        normalized_bracket = self._normalize_bracket(bracket)
        available_brackets = set()
        
        for link in deck_links:
            # Extract bracket from link
            match = re.match(r"/average-decks/[a-z0-9\-]+(?:/([a-z0-9\-]+))?(?:/([a-z0-9\-]+))?", link)
            if match:
                bracket_parts = [part for part in match.groups() if part]
                link_bracket = "/".join(bracket_parts)
                available_brackets.add(link_bracket or "all")
                
                if link_bracket == normalized_bracket:
                    return {
                        "url": f"{self.base_url}{link}",
                        "available": available_brackets
                    }
        
        # Return the default deck if no exact match
        return {
            "url": f"{self.base_url}{deck_links[0]}",
            "available": available_brackets
        }
    
    async def _fetch_html(self, url: str) -> str:
        """Fetch HTML content with error handling."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.get(url, timeout=15.0)
                if response.status_code == 429 and attempt < max_retries - 1:
                    # Rate limited, wait and retry
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response.text
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.5)
        
        raise RuntimeError("Failed to fetch HTML after retries")
    
    async def _parse_average_deck(self, html: str, commander_name: str, bracket: str) -> DeckData:
        """Parse average deck from HTML."""
        try:
            # Look for the Next.js data JSON
            script_match = re.search(r'__NEXT_DATA__\s*=\s*(\{.*?\});', html, re.DOTALL)
            if not script_match:
                raise ValueError("Could not find Next.js data in deck page")
            
            json_data = json.loads(script_match.group(1))
            
            # Extract deck information from the JSON
            deck_info = json_data.get("props", {}).get("pageProps", {})
            cards_data = self._extract_cards_from_json(deck_info)
            
            if not cards_data:
                raise ValueError("No card data found in deck")
            
            # Convert to our schema
            cards = []
            for card_name, count in cards_data.items():
                cards.append(DeckCard(
                    name=card_name,
                    quantity=count,
                    scryfall_uri=None  # Would need additional API call
                ))
            
            return DeckData(
                commander=commander_name,
                bracket=bracket,
                source_url=f"https://edhrec.com/average-decks/{self._normalize_commander_name(commander_name)}/{bracket}",
                cards=cards,
                total_cards=sum(card.quantity for card in cards),
                last_updated=None
            )
            
        except Exception as e:
            log.error(f"Error parsing average deck: {e}")
            raise
    
    async def _parse_theme_page(self, html: str, theme_name: str, colors: Optional[str]) -> ThemeData:
        """Parse theme page from HTML."""
        try:
            # Extract Next.js data
            script_match = re.search(r'__NEXT_DATA__\s*=\s*(\{.*?\});', html, re.DOTALL)
            if not script_match:
                raise ValueError("Could not find Next.js data in theme page")
            
            json_data = json.loads(script_match.group(1))
            page_props = json_data.get("props", {}).get("pageProps", {})
            
            # Extract theme information
            theme_info = page_props.get("theme", {})
            
            # Extract card data
            cards_data = self._extract_cards_from_json(theme_info)
            
            if not cards_data:
                raise ValueError("No card data found in theme")
            
            # Convert to our schema
            items = []
            for card_name, count in cards_data.items():
                items.append(ThemeItem(
                    name=card_name,
                    count=count,
                    category="card"
                ))
            
            return ThemeData(
                theme_name=theme_name,
                description=theme_info.get("description"),
                colors=[colors] if colors else None,
                category=theme_info.get("category", "theme"),
                items=ThemeCollection(
                    items=items,
                    total_count=len(items)
                ),
                edhrec_url=f"https://ryfall.com/tags/{theme_name}" + (f"/{colors}" if colors else ""),
                source="edhrec"
            )
            
        except Exception as e:
            log.error(f"Error parsing theme page: {e}")
            raise
    
    def _extract_cards_from_json(self, data: Dict) -> Dict[str, int]:
        """Extract card data from EDHREC JSON structure."""
        cards = {}
        
        # Look for various card data locations
        card_sources = [
            data.get("cards"),
            data.get("cardData"),
            data.get("items"),
            data.get("synergyList"),
            data.get("popularCards")
        ]
        
        for source in card_sources:
            if source and isinstance(source, (list, dict)):
                if isinstance(source, list):
                    for item in source:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("cardName")
                            count = item.get("count", item.get("quantity", 1))
                            if name:
                                cards[name] = count
                elif isinstance(source, dict):
                    for name, count in source.items():
                        if name and isinstance(count, int):
                            cards[name] = count
        
        return cards
    
    async def _extract_commander_themes(self, html: str) -> Dict[str, float]:
        """Extract themes/tags from commander page HTML."""
        themes = {}
        
        # Look for theme data in the HTML
        patterns = [
            r'data-theme="([^"]+)"',
            r'class="theme[^"]*">([^<]+)',
            r'href="/tags/([^"]+)"'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                theme_name = match.strip()
                if theme_name:
                    themes[theme_name] = themes.get(theme_name, 0.0) + 1.0
        
        return themes
    
    def _normalize_commander_name(self, name: str) -> str:
        """Normalize commander name for URL."""
        # Remove special characters and convert to lowercase
        normalized = re.sub(r'[^a-zA-Z0-9\s\-]', '', name)
        normalized = re.sub(r'\s+', '-', normalized.strip().lower())
        return normalized
    
    def _normalize_bracket(self, bracket: str) -> str:
        """Normalize bracket name."""
        bracket_map = {
            "precon": "exhibition",
            "average": "",
            "all": "",
            "default": "",
            "1": "exhibition",
            "2": "core", 
            "3": "upgraded",
            "4": "optimized",
            "5": "cedh"
        }
        
        normalized = bracket.lower().replace("-", "/")
        return bracket_map.get(normalized, normalized)