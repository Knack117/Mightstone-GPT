"""
Handler for EDHREC average deck functionality.
"""

import logging
from typing import Dict, Any, Optional

from models.schemas import DeckData, DeckCard
from services.edhrec_service import EDHRECService

log = logging.getLogger(__name__)


class AverageDeckHandler:
    """Handler for EDHREC average deck operations."""
    
    def __init__(self, edhrec_service: EDHRECService):
        self.edhrec_service = edhrec_service
    
    async def get_average_deck(
        self, 
        commander_name: str, 
        bracket: str = "optimized"
    ) -> DeckData:
        """Get average deck for a commander."""
        try:
            deck_data = await self.edhrec_service.get_average_deck(commander_name, bracket)
            return deck_data
            
        except Exception as e:
            log.error(f"Error in average deck handler for '{commander_name}': {e}")
            raise
    
    async def get_multiple_brackets(
        self, 
        commander_name: str, 
        brackets: list[str]
    ) -> Dict[str, Optional[DeckData]]:
        """Get decks for multiple brackets."""
        results = {}
        
        for bracket in brackets:
            try:
                deck_data = await self.edhrec_service.get_average_deck(commander_name, bracket)
                results[bracket] = deck_data
            except Exception as e:
                log.warning(f"Could not get {bracket} deck for '{commander_name}': {e}")
                results[bracket] = None
        
        return results
    
    async def compare_brackets(
        self, 
        commander_name: str, 
        bracket1: str, 
        bracket2: str
    ) -> Dict[str, Any]:
        """Compare two different brackets."""
        try:
            deck1_data = await self.edhrec_service.get_average_deck(commander_name, bracket1)
            deck2_data = await self.edhrec_service.get_average_deck(commander_name, bracket2)
            
            # Calculate differences
            comparison = {
                "commander": commander_name,
                "bracket1": {
                    "name": bracket1,
                    "total_cards": deck1_data.total_cards if deck1_data else 0,
                    "cards": deck1_data.cards if deck1_data else []
                },
                "bracket2": {
                    "name": bracket2,
                    "total_cards": deck2_data.total_cards if deck2_data else 0,
                    "cards": deck2_data.cards if deck2_data else []
                },
                "analysis": await self._analyze_deck_difference(deck1_data, deck2_data)
            }
            
            return comparison
            
        except Exception as e:
            log.error(f"Error comparing brackets for '{commander_name}': {e}")
            raise
    
    async def _analyze_deck_difference(
        self, 
        deck1: Optional[DeckData], 
        deck2: Optional[DeckData]
    ) -> Dict[str, Any]:
        """Analyze the difference between two decks."""
        if not deck1 or not deck2:
            return {"error": "One or both decks not available for comparison"}
        
        # Get card names
        cards1 = {card.name: card.quantity for card in deck1.cards}
        cards2 = {card.name: card.quantity for card in deck2.cards}
        
        # Find unique cards
        unique_to_deck1 = set(cards1.keys()) - set(cards2.keys())
        unique_to_deck2 = set(cards2.keys()) - set(cards1.keys())
        common_cards = set(cards1.keys()) & set(cards2.keys())
        
        # Calculate quantity differences for common cards
        quantity_diffs = {}
        for card_name in common_cards:
            diff = cards2[card_name] - cards1[card_name]
            if diff != 0:
                quantity_diffs[card_name] = diff
        
        return {
            "total_cards_deck1": deck1.total_cards,
            "total_cards_deck2": deck2.total_cards,
            "unique_to_deck1": list(unique_to_deck1),
            "unique_to_deck2": list(unique_to_deck2),
            "common_cards_count": len(common_cards),
            "quantity_changes": quantity_diffs
        }