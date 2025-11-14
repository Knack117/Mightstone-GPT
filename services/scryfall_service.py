"""
Scryfall service - Handles Scryfall card data via Mightstone integration.
"""

import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from models.schemas import CardInfo

log = logging.getLogger(__name__)


class ScryfallService:
    """Service for interacting with Scryfall data via Mightstone."""
    
    def __init__(self):
        self.base_url = "https://api.scryfall.com"
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
            log.info("✅ Scryfall service initialized")
        except Exception as e:
            log.error(f"Failed to initialize Scryfall service: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.client:
            await self.client.aclose()
            self._initialized = False
            log.info("✅ Scryfall service cleaned up")
    
    async def search_cards(
        self, 
        query: str, 
        limit: int = 50, 
        order: str = "name"
    ) -> List[CardInfo]:
        """Search for cards using Scryfall syntax."""
        if not self._initialized:
            raise RuntimeError("Scryfall service not initialized")
        
        try:
            # Prepare search parameters
            params = {
                "q": query,
                "order": order,
                "unique": "cards"
            }
            
            if limit:
                params["page_size"] = min(limit, 100)
            
            # Make request to Scryfall
            response = await self.client.get(
                f"{self.base_url}/cards/search",
                params=params
            )
            
            if response.status_code == 429:
                # Rate limited
                raise ValueError("Scryfall rate limit exceeded. Please wait before making more requests.")
            
            response.raise_for_status()
            data = response.json()
            
            # Extract cards from response
            cards_data = data.get("data", [])
            
            return [self._convert_scryfall_card(card_data) for card_data in cards_data]
            
        except Exception as e:
            log.error(f"Error searching cards with query '{query}': {e}")
            raise
    
    async def get_card_by_name(self, card_name: str, exact: bool = True) -> CardInfo:
        """Get a specific card by name."""
        if not self._initialized:
            raise RuntimeError("Scryfall service not initialized")
        
        try:
            if exact:
                url = f"{self.base_url}/cards/named"
                params = {"exact": card_name}
            else:
                url = f"{self.base_url}/cards/search"
                params = {
                    "q": f"name:{card_name}",
                    "order": "name",
                    "unique": "cards",
                    "page_size": 1
                }
            
            response = await self.client.get(url, params=params)
            
            if response.status_code == 404:
                raise ValueError(f"Card '{card_name}' not found")
            
            if response.status_code == 429:
                raise ValueError("Scryfall rate limit exceeded. Please wait before making more requests.")
            
            response.raise_for_status()
            data = response.json()
            
            # Handle both single card and search result responses
            if "object" in data and data["object"] == "list":
                cards = data.get("data", [])
                if not cards:
                    raise ValueError(f"Card '{card_name}' not found")
                card_data = cards[0]
            else:
                card_data = data
            
            return self._convert_scryfall_card(card_data)
            
        except Exception as e:
            log.error(f"Error getting card by name '{card_name}': {e}")
            raise
    
    async def get_card_by_id(self, scryfall_id: str) -> CardInfo:
        """Get a specific card by Scryfall ID."""
        if not self._initialized:
            raise RuntimeError("Scryfall service not initialized")
        
        try:
            response = await self.client.get(f"{self.base_url}/cards/{scryfall_id}")
            
            if response.status_code == 404:
                raise ValueError(f"Card with ID '{scryfall_id}' not found")
            
            if response.status_code == 429:
                raise ValueError("Scryfall rate limit exceeded. Please wait before making more requests.")
            
            response.raise_for_status()
            data = response.json()
            
            return self._convert_scryfall_card(data)
            
        except Exception as e:
            log.error(f"Error getting card by ID '{scryfall_id}': {e}")
            raise
    
    async def get_random_card(self, query: Optional[str] = None) -> CardInfo:
        """Get a random card, optionally filtered by query."""
        if not self._initialized:
            raise RuntimeError("Scryfall service not initialized")
        
        try:
            params = {}
            if query:
                params["q"] = query
            
            response = await self.client.get(
                f"{self.base_url}/cards/random",
                params=params
            )
            
            if response.status_code == 429:
                raise ValueError("Scryfall rate limit exceeded. Please wait before making more requests.")
            
            response.raise_for_status()
            data = response.json()
            
            return self._convert_scryfall_card(data)
            
        except Exception as e:
            log.error(f"Error getting random card: {e}")
            raise
    
    async def get_card_suggestions(self, partial_name: str, limit: int = 20) -> List[Dict[str, str]]:
        """Get auto-complete suggestions for card names."""
        if not self._initialized:
            raise RuntimeError("Scryfall service not initialized")
        
        try:
            params = {
                "q": partial_name,
                "limit": min(limit, 20)
            }
            
            response = await self.client.get(
                f"{self.base_url}/cards/autocomplete",
                params=params
            )
            
            if response.status_code == 429:
                raise ValueError("Scryfall rate limit exceeded. Please wait before making more requests.")
            
            response.raise_for_status()
            data = response.json()
            
            suggestions = data.get("data", [])
            
            return [{"name": name} for name in suggestions]
            
        except Exception as e:
            log.error(f"Error getting suggestions for '{partial_name}': {e}")
            raise
    
    # Utility methods for common searches
    
    async def search_by_commander_colors(self, colors: str) -> List[CardInfo]:
        """Search for cards matching specific commander colors."""
        if not self._initialized:
            raise RuntimeError("Scryfall service not initialized")
        
        # Convert color codes to Scryfall syntax
        color_codes = "".join(sorted(colors.upper()))
        if len(color_codes) == 1:
            query = f"color:{color_codes}"
        else:
            query = f"color>=c{color_codes} and color<=c{color_codes}"
        
        return await self.search_cards(query, limit=50)
    
    async def search_by_mana_value(self, cmc: int, operator: str = "=") -> List[CardInfo]:
        """Search for cards by converted mana cost."""
        if not self._initialized:
            raise RuntimeError("Scryfall service not initialized")
        
        query = f"cmc{operator}{cmc}"
        return await self.search_cards(query, limit=50)
    
    async def search_creatures(self, query: Optional[str] = None) -> List[CardInfo]:
        """Search for creature cards."""
        if not self._initialized:
            raise RuntimeError("Scryfall service not initialized")
        
        base_query = "type:creature"
        if query:
            full_query = f"{base_query} {query}"
        else:
            full_query = base_query
        
        return await self.search_cards(full_query, limit=50)
    
    async def search_spells(self, query: Optional[str] = None) -> List[CardInfo]:
        """Search for spell cards (non-creature)."""
        if not self._initialized:
            raise RuntimeError("Scryfall service not initialized")
        
        base_query = "-type:creature"
        if query:
            full_query = f"{base_query} {query}"
        else:
            full_query = base_query
        
        return await self.search_cards(full_query, limit=50)
    
    async def search_lands(self, query: Optional[str] = None) -> List[CardInfo]:
        """Search for land cards."""
        if not self._initialized:
            raise RuntimeError("Scryfall service not initialized")
        
        base_query = "type:land"
        if query:
            full_query = f"{base_query} {query}"
        else:
            full_query = base_query
        
        return await self.search_cards(full_query, limit=50)
    
    # Private helper methods
    
    def _convert_scryfall_card(self, card_data: Dict[str, Any]) -> CardInfo:
        """Convert Scryfall card data to our CardInfo schema."""
        return CardInfo(
            id=card_data.get("id", ""),
            name=card_data.get("name", ""),
            mana_cost=card_data.get("mana_cost"),
            cmc=card_data.get("cmc"),
            type_line=card_data.get("type_line"),
            oracle_text=card_data.get("oracle_text"),
            power=card_data.get("power"),
            toughness=card_data.get("toughness"),
            loyalty=card_data.get("loyalty"),
            colors=card_data.get("colors"),
            color_identity=card_data.get("color_identity"),
            keywords=card_data.get("keywords"),
            legalities=card_data.get("legalities"),
            games=card_data.get("games"),
            reserved=card_data.get("reserved"),
            foil=card_data.get("foil"),
            nonfoil=card_data.get("nonfoil"),
            oversized=card_data.get("oversized"),
            promo=card_data.get("promo"),
            reprint=card_data.get("reprint"),
            variation=card_data.get("variation"),
            set_id=card_data.get("set_id"),
            set=card_data.get("set"),
            set_name=card_data.get("set_name"),
            set_type=card_data.get("set_type"),
            set_uri=card_data.get("set_uri"),
            set_search_uri=card_data.get("set_search_uri"),
            scryfall_set_uri=card_data.get("scryfall_set_uri"),
            rulings_uri=card_data.get("rulings_uri"),
            prints_search_uri=card_data.get("prints_search_uri"),
            collector_number=card_data.get("collector_number"),
            digital=card_data.get("digital"),
            rarity=card_data.get("rarity"),
            flavor_text=card_data.get("flavor_text"),
            artist=card_data.get("artist"),
            artist_ids=card_data.get("artist_ids"),
            illustration_id=card_data.get("illustration_id"),
            border_color=card_data.get("border_color"),
            frame=card_data.get("frame"),
            full_art=card_data.get("full_art"),
            textless=card_data.get("textless"),
            booster=card_data.get("booster"),
            story_spotlight=card_data.get("story_spotlight"),
            edhrec_rank=card_data.get("edhrec_rank"),
            prices=card_data.get("prices"),
            related_uris=card_data.get("related_uris"),
            image_uris=card_data.get("image_uris"),
            mana_cost_html=card_data.get("mana_cost_html")
        )
    
    def _normalize_color_query(self, colors: str) -> str:
        """Normalize color query for Scryfall search."""
        # Remove spaces and convert to uppercase
        normalized = colors.upper().replace(" ", "").replace("-", "")
        
        # Validate color combinations
        valid_colors = set("WUBRG")
        for color in normalized:
            if color not in valid_colors:
                raise ValueError(f"Invalid color: {color}")
        
        return normalized