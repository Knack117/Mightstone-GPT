"""
EDHREC Integration Service - Updated to use the working implementation from old repo.
Provides sophisticated EDHREC data extraction with proper error handling.
"""

import logging
from typing import Any, Dict, List, Optional

from models.schemas import (
    ThemeData,
    BudgetComparison,
    DeckData,
    DeckCard,
    ThemeSuggestion
)

# Import the complete EDHREC service
from services.edhrec_complete import (
    EdhrecError,
    EdhrecNotFoundError,
    EdhrecParsingError,
    fetch_average_deck,
    fetch_commander_summary,
    fetch_tag_theme,
)

log = logging.getLogger(__name__)

class EDHRECService:
    """Service for interacting with EDHREC data using the complete implementation."""
    
    def __init__(self):
        self._initialized = False
    
    async def initialize(self):
        """Initialize the service."""
        try:
            self._initialized = True
            log.info("✅ EDHREC service initialized")
        except Exception as e:
            log.error(f"Failed to initialize EDHREC service: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        self._initialized = False
        log.info("✅ EDHREC service cleaned up")
    
    async def get_average_deck(self, commander_name: str, bracket: str = "optimized") -> DeckData:
        """Get average deck for a commander using proper EDHREC discovery."""
        if not self._initialized:
            raise RuntimeError("EDHREC service not initialized")
        
        try:
            # Use the complete EDHREC service
            deck_data = fetch_average_deck(
                name=commander_name,
                bracket=bracket
            )
            
            # Convert to our API format
            cards = []
            if deck_data.get("deck", {}).get("cards"):
                for card in deck_data["deck"]["cards"]:
                    cards.append(DeckCard(
                        name=card["name"],
                        count=card["count"],
                        percent=None
                    ))
            
            return DeckData(
                commander=deck_data.get("commander"),
                bracket=deck_data.get("bracket"),
                cards=cards,
                source_url=deck_data.get("source_url"),
                commander_card=deck_data.get("commander_card")
            )
            
        except EdhrecNotFoundError as e:
            log.error(f"Commander or deck not found: {e}")
            raise Exception(f"Average deck not found for '{commander_name}' with bracket '{bracket}'") from e
        except Exception as e:
            log.error(f"Error getting average deck for '{commander_name}': {e}")
            raise
    
    async def get_budget_comparison(self, commander_name: str) -> BudgetComparison:
        """Get budget vs expensive deck comparison."""
        if not self._initialized:
            raise RuntimeError("EDHREC service not initialized")
        
        try:
            # Get budget and expensive decks
            budget_deck = fetch_average_deck(name=commander_name, bracket="exhibition/budget")
            expensive_deck = fetch_average_deck(name=commander_name, bracket="exhibition/expensive")
            
            return BudgetComparison(
                commander=commander_name,
                budget_bracket="exhibition/budget",
                expensive_bracket="exhibition/expensive",
                budget_cards=budget_deck.get("deck", {}).get("cards", []),
                expensive_cards=expensive_deck.get("deck", {}).get("cards", []),
                budget_source_url=budget_deck.get("source_url"),
                expensive_source_url=expensive_deck.get("source_url")
            )
            
        except Exception as e:
            log.error(f"Error getting budget comparison for '{commander_name}': {e}")
            raise
    
    async def get_theme_data(self, theme_name: str, colors: Optional[str] = None) -> ThemeData:
        """Get theme/tag data from EDHREC."""
        if not self._initialized:
            raise RuntimeError("EDHREC service not initialized")
        
        try:
            # Use the complete EDHREC service
            theme_data = fetch_tag_theme(
                tag=theme_name,
                identity=colors
            )
            
            # Convert to our API format
            cards = []
            for card in theme_data.get("cards", []):
                cards.append({
                    "name": card["name"],
                    "percent": card.get("percent", 0),
                    "edhrec_rank": card.get("synergy", 0)
                })
            
            return ThemeData(
                theme=theme_data.get("theme"),
                header=theme_data.get("header"),
                description=theme_data.get("description"),
                cards=cards,
                source_url=theme_data.get("source_url")
            )
            
        except EdhrecNotFoundError as e:
            log.error(f"Theme '{theme_name}' not found: {e}")
            raise Exception(f"Theme '{theme_name}' not found") from e
        except Exception as e:
            log.error(f"Error getting theme data for '{theme_name}': {e}")
            raise
    
    async def get_theme_suggestions(self, commander_name: str) -> List[ThemeSuggestion]:
        """Get theme suggestions for a commander."""
        if not self._initialized:
            raise RuntimeError("EDHREC service not initialized")
        
        try:
            # Get commander summary which includes tags
            summary = fetch_commander_summary(commander_name)
            
            suggestions = []
            for tag_data in summary.get("tags", [])[:10]:  # Top 10 tags
                suggestions.append(ThemeSuggestion(
                    theme_name=tag_data["tag"],
                    popularity_score=None,
                    category=None,
                    color_alignment=None
                ))
            
            return suggestions
            
        except Exception as e:
            log.error(f"Error getting theme suggestions for '{commander_name}': {e}")
            return []
    
    async def get_commander_data(self, commander_name: str) -> Dict[str, Any]:
        """Get comprehensive commander data including tags and themes."""
        if not self._initialized:
            raise RuntimeError("EDHREC service not initialized")
        
        try:
            # Get commander summary with tags
            summary = fetch_commander_summary(commander_name)
            
            # Get average deck for different brackets
            decks = {}
            for bracket in ["exhibition", "upgraded", "optimized"]:
                try:
                    deck_data = fetch_average_deck(name=commander_name, bracket=bracket)
                    decks[bracket] = deck_data.get("deck", {}).get("cards", [])
                except Exception:
                    decks[bracket] = []
            
            return {
                "commander": summary.get("commander"),
                "themes": summary.get("themes", []),
                "tags": summary.get("tags", []),
                "sections": summary.get("sections", {}),
                "available_decks": decks
            }
            
        except Exception as e:
            log.error(f"Error getting commander data for '{commander_name}': {e}")
            raise
