"""
Modern MTG data service - Core MTG data service using direct API calls.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from models.schemas import (
    CommanderDeck, 
    CardInfo, 
    DeckAnalysis,
    RecommendationData
)

log = logging.getLogger(__name__)


class MightstoneService:
    """Main service class using direct API calls for MTG data access."""
    
    def __init__(self):
        self._initialized = False
    
    async def initialize(self):
        """Initialize the service."""
        try:
            self._initialized = True
            log.info("✅ MTG data service initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize MTG data service: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        self._initialized = False
        log.info("✅ MTG data service cleaned up")
    
    async def get_commander_data(self, commander_name: str) -> CommanderDeck:
        """Get comprehensive commander data."""
        if not self._initialized:
            raise RuntimeError("MTG data service not initialized")
        
        try:
            # Use Scryfall to search for the commander
            from services.scryfall_service import ScryfallService
            scryfall = ScryfallService()
            await scryfall.initialize()
            
            # Search for commander
            search_query = f'name:"{commander_name}" (type:legendary type:creature or type:planeswalker)'
            results = await scryfall.search_cards(search_query, limit=20)
            
            if not results:
                raise ValueError(f"Commander '{commander_name}' not found")
            
            # Get the best match (first result that's actually a legendary creature)
            commander_card = None
            for card in results:
                if card.type_line and ("Legendary" in card.type_line):
                    commander_card = card
                    break
            
            if not commander_card:
                commander_card = results[0]  # Fallback to first result
            
            # Create commander data
            return CommanderDeck(
                commander=commander_card,
                deck=None,
                themes=[],
                tags=[],
                colors=commander_card.color_identity or [],
                edhrec_url=f"https://scryfall.com/search?q=name%3A%22{commander_name.replace(' ', '%20')}%22",
                average_deck_url=f"https://scryfall.com/search?q=name%3A%22{commander_name.replace(' ', '%20')}%22",
                budget_brackets=["exhibition", "core", "upgraded", "optimized", "cedh"]
            )
            
        except Exception as e:
            log.error(f"Error getting commander data for '{commander_name}': {e}")
            raise
    
    async def search_commanders(self, query: str, limit: int = 20) -> List[CardInfo]:
        """Search for commanders."""
        if not self._initialized:
            raise RuntimeError("MTG data service not initialized")
        
        try:
            from services.scryfall_service import ScryfallService
            scryfall = ScryfallService()
            await scryfall.initialize()
            
            # Search for legendary creatures
            search_query = f'type:legendary type:creature {query}'
            results = await scryfall.search_cards(search_query, limit)
            
            return results
            
        except Exception as e:
            log.error(f"Error searching commanders with query '{query}': {e}")
            raise
    
    async def get_card_by_name(self, card_name: str) -> CardInfo:
        """Get card information by name."""
        if not self._initialized:
            raise RuntimeError("MTG data service not initialized")
        
        try:
            from services.scryfall_service import ScryfallService
            scryfall = ScryfallService()
            await scryfall.initialize()
            
            card = await scryfall.get_card_by_name(card_name)
            return card
            
        except Exception as e:
            log.error(f"Error getting card by name '{card_name}': {e}")
            raise
    
    async def search_cards(self, query: str, limit: int = 50, order: str = "name") -> List[CardInfo]:
        """Search for cards."""
        if not self._initialized:
            raise RuntimeError("MTG data service not initialized")
        
        try:
            from services.scryfall_service import ScryfallService
            scryfall = ScryfallService()
            await scryfall.initialize()
            
            results = await scryfall.search_cards(query, limit, order)
            return results
            
        except Exception as e:
            log.error(f"Error searching cards with query '{query}': {e}")
            raise
    
    async def analyze_deck(self, deck_list: List[str]) -> DeckAnalysis:
        """Analyze a deck list and provide recommendations."""
        if not self._initialized:
            raise RuntimeError("MTG data service not initialized")
        
        try:
            # Get card data for all cards in the deck
            cards_data = []
            from services.scryfall_service import ScryfallService
            scryfall = ScryfallService()
            await scryfall.initialize()
            
            for card_name in deck_list:
                try:
                    card = await scryfall.get_card_by_name(card_name)
                    cards_data.append(card)
                except Exception as e:
                    log.warning(f"Could not find data for card '{card_name}': {e}")
                    continue
            
            # Perform analysis
            analysis = await self._perform_deck_analysis(cards_data)
            
            return analysis
            
        except Exception as e:
            log.error(f"Error analyzing deck: {e}")
            raise
    
    async def get_recommendations(
        self, 
        commander_name: str, 
        exclude_cards: List[str] = None, 
        include_themes: List[str] = None
    ) -> Dict[str, Any]:
        """Get card recommendations for a commander."""
        if not self._initialized:
            raise RuntimeError("MTG data service not initialized")
        
        try:
            # Get commander data first
            commander = await self.get_commander_data(commander_name)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(
                commander, exclude_cards or [], include_themes or []
            )
            
            return {
                "commander": commander_name,
                "recommendations": recommendations,
                "total_recommendations": sum(len(rec.cards) for rec in recommendations)
            }
            
        except Exception as e:
            log.error(f"Error getting recommendations for '{commander_name}': {e}")
            raise
    
    # Private helper methods
    
    async def _perform_deck_analysis(self, cards_data: List[CardInfo]) -> DeckAnalysis:
        """Perform comprehensive deck analysis."""
        # Analyze mana curve
        mana_curve = {}
        for card in cards_data:
            cmc = card.cmc or 0
            curve_key = "0" if cmc == 0 else f"{int(cmc)}"
            mana_curve[curve_key] = mana_curve.get(curve_key, 0) + 1
        
        # Analyze color distribution
        color_distribution = {}
        for card in cards_data:
            if card.color_identity:
                for color in card.color_identity:
                    color_distribution[color] = color_distribution.get(color, 0) + 1
        
        # Analyze card types
        card_types = {}
        for card in cards_data:
            if card.type_line:
                # Extract main type
                main_type = card.type_line.split("—")[0].strip().split()[0] if "—" in card.type_line else card.type_line.split()[0]
                card_types[main_type] = card_types.get(main_type, 0) + 1
        
        # Generate basic recommendations
        recommendations = [
            RecommendationData(
                category="Mana Base",
                cards=[],
                reasoning="Based on color identity and curve analysis"
            ),
            RecommendationData(
                category="Interaction",
                cards=[],
                reasoning="Essential removal and counter magic"
            ),
            RecommendationData(
                category="Ramp",
                cards=[],
                reasoning="Mana acceleration based on curve"
            )
        ]
        
        return DeckAnalysis(
            total_cards=len(cards_data),
            mana_curve=mana_curve,
            color_distribution=color_distribution,
            card_types=card_types,
            recommendations=recommendations,
            synergies=[],
            improvements=[]
        )
    
    async def _generate_recommendations(
        self, 
        commander: CommanderDeck, 
        exclude_cards: List[str], 
        include_themes: List[str]
    ) -> List[RecommendationData]:
        """Generate recommendations based on commander data."""
        return [
            RecommendationData(
                category="Lands",
                cards=[],
                reasoning=f"Optimal land base for {commander.colors or 'colorless'} commander"
            ),
            RecommendationData(
                category="Ramp",
                cards=[],
                reasoning="Mana acceleration cards"
            ),
            RecommendationData(
                category="Interaction",
                cards=[],
                reasoning="Removal and protection"
            )
        ]
