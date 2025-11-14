"""
Handler for EDHREC budget comparison functionality.
"""

import logging
from typing import Dict, Any, Optional, List

from models.schemas import BudgetComparison, DeckData
from services.edhrec_service import EDHRECService

log = logging.getLogger(__name__)


class BudgetComparisonHandler:
    """Handler for budget vs expensive deck comparisons."""
    
    def __init__(self, edhrec_service: EDHRECService):
        self.edhrec_service = edhrec_service
    
    async def get_budget_comparison(
        self, 
        commander_name: str
    ) -> BudgetComparison:
        """Get budget vs expensive comparison for a commander."""
        try:
            comparison = await self.edhrec_service.get_budget_comparison(commander_name)
            return comparison
            
        except Exception as e:
            log.error(f"Error in budget comparison handler for '{commander_name}': {e}")
            raise
    
    async def get_detailed_comparison(
        self, 
        commander_name: str,
        include_similar: bool = True
    ) -> Dict[str, Any]:
        """Get detailed comparison with analysis."""
        try:
            basic_comparison = await self.edhrec_service.get_budget_comparison(commander_name)
            
            detailed_comparison = {
                "commander": commander_name,
                "budget_deck": basic_comparison.budget_deck,
                "expensive_deck": basic_comparison.expensive_deck,
                "analysis": await self._analyze_budget_difference(
                    basic_comparison.budget_deck, 
                    basic_comparison.expensive_deck
                ),
                "recommendations": await self._generate_budget_recommendations(
                    basic_comparison.budget_deck,
                    basic_comparison.expensive_deck
                )
            }
            
            if include_similar:
                # Find similar commanders
                detailed_comparison["similar_commanders"] = await self._find_similar_commanders(
                    commander_name
                )
            
            return detailed_comparison
            
        except Exception as e:
            log.error(f"Error getting detailed comparison for '{commander_name}': {e}")
            raise
    
    async def _analyze_budget_difference(
        self, 
        budget_deck: Optional[DeckData], 
        expensive_deck: Optional[DeckData]
    ) -> Dict[str, Any]:
        """Analyze differences between budget and expensive decks."""
        if not budget_deck or not expensive_deck:
            return {"error": "Insufficient deck data for comparison"}
        
        # Extract card data
        budget_cards = {card.name: card.quantity for card in budget_deck.cards}
        expensive_cards = {card.name: card.quantity for card in expensive_deck.cards}
        
        # Calculate differences
        all_cards = set(budget_cards.keys()) | set(expensive_cards.keys())
        
        card_analysis = {
            "only_in_budget": [],
            "only_in_expensive": [],
            "upgraded_cards": [],
            "downgraded_cards": []
        }
        
        for card_name in all_cards:
            budget_qty = budget_cards.get(card_name, 0)
            expensive_qty = expensive_cards.get(card_name, 0)
            
            if budget_qty > 0 and expensive_qty == 0:
                card_analysis["only_in_budget"].append({
                    "name": card_name,
                    "budget_quantity": budget_qty
                })
            elif budget_qty == 0 and expensive_qty > 0:
                card_analysis["only_in_expensive"].append({
                    "name": card_name,
                    "expensive_quantity": expensive_qty
                })
            elif budget_qty > 0 and expensive_qty > 0 and budget_qty != expensive_qty:
                if expensive_qty > budget_qty:
                    card_analysis["upgraded_cards"].append({
                        "name": card_name,
                        "budget_quantity": budget_qty,
                        "expensive_quantity": expensive_qty
                    })
                else:
                    card_analysis["downgraded_cards"].append({
                        "name": card_name,
                        "budget_quantity": budget_qty,
                        "expensive_quantity": expensive_qty
                    })
        
        return {
            "budget_total_cards": budget_deck.total_cards,
            "expensive_total_cards": expensive_deck.total_cards,
            "budget_unique_cards": len(budget_cards),
            "expensive_unique_cards": len(expensive_cards),
            "common_cards": len(set(budget_cards.keys()) & set(expensive_cards.keys())),
            "card_analysis": card_analysis,
            "upgrade_suggestions": self._identify_upgrade_patterns(card_analysis)
        }
    
    async def _generate_budget_recommendations(
        self,
        budget_deck: Optional[DeckData],
        expensive_deck: Optional[DeckData]
    ) -> List[Dict[str, Any]]:
        """Generate budget-focused recommendations."""
        recommendations = []
        
        if not budget_deck or not expensive_deck:
            return recommendations
        
        # Extract card differences
        budget_cards = {card.name: card.quantity for card in budget_deck.cards}
        expensive_cards = {card.name: card.quantity for card in expensive_deck.cards}
        
        # High-value upgrades (expensive deck cards not in budget)
        high_value_additions = []
        for card_name in expensive_cards.keys():
            if card_name not in budget_cards:
                high_value_additions.append({
                    "card": card_name,
                    "priority": "high",
                    "reason": "Common upgrade choice in expensive builds"
                })
        
        if high_value_additions:
            recommendations.append({
                "category": "High-Value Additions",
                "description": "Cards that frequently appear in expensive builds",
                "cards": high_value_additions[:10],  # Top 10
                "budget_impact": "These additions typically increase deck power significantly"
            })
        
        # Synergy improvements
        synergy_cards = self._identify_synergy_improvements(budget_cards, expensive_cards)
        if synergy_cards:
            recommendations.append({
                "category": "Synergy Improvements",
                "description": "Cards that improve existing synergies",
                "cards": synergy_cards,
                "budget_impact": "Moderate cost with good synergy benefits"
            })
        
        # Mana base improvements
        mana_recommendations = self._analyze_mana_base(budget_cards, expensive_cards)
        if mana_recommendations:
            recommendations.append({
                "category": "Mana Base",
                "description": "Land and mana production improvements",
                "cards": mana_recommendations,
                "budget_impact": "Significant impact on mana consistency"
            })
        
        return recommendations
    
    def _identify_upgrade_patterns(self, card_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Identify common upgrade patterns."""
        patterns = []
        
        # Look for common categories of upgrades
        if card_analysis["only_in_expensive"]:
            # Group by common card types/themes
            expensive_names = [item["name"] for item in card_analysis["only_in_expensive"]]
            
            # Simple pattern identification (could be more sophisticated)
            lands = [name for name in expensive_names if "land" in name.lower()]
            if lands:
                patterns.append({
                    "pattern": "Land upgrades",
                    "description": f"{len(lands)} land cards are exclusive to expensive builds",
                    "cards": lands[:5]
                })
            
            artifacts = [name for name in expensive_names if "artifact" in name.lower()]
            if artifacts:
                patterns.append({
                    "pattern": "Artifact additions", 
                    "description": f"{len(artifacts)} artifact cards appear in expensive builds",
                    "cards": artifacts[:5]
                })
        
        return patterns
    
    def _identify_synergy_improvements(
        self, 
        budget_cards: Dict[str, int], 
        expensive_cards: Dict[str, int]
    ) -> List[Dict[str, str]]:
        """Identify cards that improve synergies."""
        # This would need more sophisticated analysis
        # For now, return empty list as placeholder
        return []
    
    def _analyze_mana_base(
        self, 
        budget_cards: Dict[str, int], 
        expensive_cards: Dict[str, int]
    ) -> List[Dict[str, str]]:
        """Analyze mana base improvements."""
        # This would analyze land differences
        # For now, return empty list as placeholder
        return []
    
    async def _find_similar_commanders(self, commander_name: str) -> List[Dict[str, str]]:
        """Find commanders with similar budget patterns."""
        # This would use EDHREC data to find similar commanders
        # For now, return empty list as placeholder
        return []