"""
Mightstone service - Core MTG data service using Mightstone as backbone.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from mightstone.client import MightstoneClient
from mightstone.models import Card, Commander, Deck

from models.schemas import (
    CommanderDeck, 
    CardInfo, 
    DeckAnalysis,
    RecommendationData
)

log = logging.getLogger(__name__)


class MightstoneService:
    """Main service class using Mightstone for MTG data access."""
    
    def __init__(self):
        self.client: Optional[MightstoneClient] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the Mightstone client."""
        try:
            self.client = MightstoneClient()
            await self.client.initialize()
            self._initialized = True
            log.info("✅ Mightstone client initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize Mightstone client: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.client:
            await self.client.cleanup()
            self._initialized = False
            log.info("✅ Mightstone client cleaned up")
    
    async def get_commander_data(self, commander_name: str) -> CommanderDeck:
        """Get comprehensive commander data using Mightstone."""
        if not self._initialized:
            raise RuntimeError("Mightstone client not initialized")
        
        try:
            # Use Mightstone to search for the commander
            search_results = await self.client.search_commanders(commander_name)
            
            if not search_results:
                raise ValueError(f"Commander '{commander_name}' not found")
            
            # Get the best match (first result)
            commander_card = search_results[0]
            
            # Convert to our schema
            commander_info = self._convert_card_to_schema(commander_card)
            
            # Get additional commander-specific data
            commander_data = await self._enrich_commander_data(commander_card)
            
            return CommanderDeck(
                commander=commander_info,
                deck=commander_data.get("deck"),
                themes=commander_data.get("themes"),
                tags=commander_data.get("tags"),
                colors=commander_data.get("colors"),
                edhrec_url=commander_data.get("edhrec_url"),
                average_deck_url=commander_data.get("average_deck_url"),
                budget_brackets=commander_data.get("budget_brackets")
            )
            
        except Exception as e:
            log.error(f"Error getting commander data for '{commander_name}': {e}")
            raise
    
    async def search_commanders(self, query: str, limit: int = 20) -> List[Commander]:
        """Search for commanders using Mightstone."""
        if not self._initialized:
            raise RuntimeError("Mightstone client not initialized")
        
        try:
            # Use Mightstone's search capabilities
            search_params = {
                "q": f"type:legendary type:creature {query}",
                "order": "name",
                "unique": "cards"
            }
            
            results = await self.client.search_cards(**search_params)
            
            # Filter to only legendary creatures
            commanders = [
                card for card in results 
                if card.type_line and "Legendary" in card.type_line and "Creature" in card.type_line
            ]
            
            return commanders[:limit]
            
        except Exception as e:
            log.error(f"Error searching commanders with query '{query}': {e}")
            raise
    
    async def get_card_by_name(self, card_name: str) -> CardInfo:
        """Get card information by name using Mightstone."""
        if not self._initialized:
            raise RuntimeError("Mightstone client not initialized")
        
        try:
            cards = await self.client.search_cards(
                q=f"name:\"{card_name}\"",
                unique="cards"
            )
            
            if not cards:
                raise ValueError(f"Card '{card_name}' not found")
            
            # Return the first exact match
            card = cards[0]
            return self._convert_card_to_schema(card)
            
        except Exception as e:
            log.error(f"Error getting card by name '{card_name}': {e}")
            raise
    
    async def search_cards(self, query: str, limit: int = 50, order: str = "name") -> List[CardInfo]:
        """Search for cards using Mightstone and Scryfall syntax."""
        if not self._initialized:
            raise RuntimeError("Mightstone client not initialized")
        
        try:
            search_params = {
                "q": query,
                "order": order,
                "unique": "cards"
            }
            
            if limit:
                search_params["page_size"] = min(limit, 100)
            
            results = await self.client.search_cards(**search_params)
            
            return [self._convert_card_to_schema(card) for card in results[:limit]]
            
        except Exception as e:
            log.error(f"Error searching cards with query '{query}': {e}")
            raise
    
    async def analyze_deck(self, deck_list: List[str]) -> DeckAnalysis:
        """Analyze a deck list and provide recommendations."""
        if not self._initialized:
            raise RuntimeError("Mightstone client not initialized")
        
        try:
            # Get card data for all cards in the deck
            cards_data = []
            for card_name in deck_list:
                try:
                    card = await self.get_card_by_name(card_name)
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
            raise RuntimeError("Mightstone client not initialized")
        
        try:
            # Get commander data first
            commander = await self.get_commander_data(commander_name)
            
            # Get recommendations based on commander themes and colors
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
    def _convert_card_to_schema(self, card: Card) -> CardInfo:
        """Convert Mightstone Card model to our CardInfo schema."""
        return CardInfo(
            id=card.id,
            name=card.name,
            mana_cost=card.mana_cost,
            cmc=card.cmc,
            type_line=card.type_line,
            oracle_text=card.oracle_text,
            power=card.power,
            toughness=card.toughness,
            loyalty=card.loyalty,
            colors=card.colors,
            color_identity=card.color_identity,
            keywords=card.keywords,
            legalities=card.legalities,
            games=card.games,
            reserved=card.reserved,
            foil=card.foil,
            nonfoil=card.nonfoil,
            oversized=card.oversized,
            promo=card.promo,
            reprint=card.reprint,
            variation=card.variation,
            set_id=card.set_id,
            set=card.set,
            set_name=card.set_name,
            set_type=card.set_type,
            set_uri=card.set_uri,
            set_search_uri=card.set_search_uri,
            scryfall_set_uri=card.scryfall_set_uri,
            rulings_uri=card.rulings_uri,
            prints_search_uri=card.prints_search_uri,
            collector_number=card.collector_number,
            digital=card.digital,
            rarity=card.rarity,
            flavor_text=card.flavor_text,
            artist=card.artist,
            artist_ids=card.artist_ids,
            illustration_id=card.illustration_id,
            border_color=card.border_color,
            frame=card.frame,
            full_art=card.full_art,
            textless=card.textless,
            booster=card.booster,
            story_spotlight=card.story_spotlight,
            edhrec_rank=card.edhrec_rank,
            prices=card.prices,
            related_uris=card.related_uris,
            image_uris=card.image_uris,
            mana_cost_html=card.mana_cost_html
        )
    
    async def _enrich_commander_data(self, commander_card: Card) -> Dict[str, Any]:
        """Enrich commander data with additional information."""
        # This would integrate with EDHREC and other sources
        # For now, return basic structure
        return {
            "themes": [],
            "tags": [],
            "colors": commander_card.color_identity or [],
            "edhrec_url": None,
            "average_deck_url": None,
            "budget_brackets": ["exhibition", "core", "upgraded", "optimized", "cedh"]
        }
    
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
        # This would use Mightstone + EDHREC integration
        # For now, return basic structure
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