"""
Tools registry for GPT integration.
"""

from handlers.edhrec_average_deck import AverageDeckHandler
from handlers.edhrec_budget import BudgetComparisonHandler

# Import the service handlers
from services.edhrec_service import EDHRECService
from services.mightstone_service import MightstoneService

# Initialize services
edhrec_service = EDHRECService()
mightstone_service = MightstoneService()

# Initialize handlers
average_deck_handler = AverageDeckHandler(edhrec_service)
budget_comparison_handler = BudgetComparisonHandler(edhrec_service)

# Register tools for GPT integration
TOOL_REGISTRY = {
    # EDHREC Deck Tools
    "edhrec_average_deck": average_deck_handler.get_average_deck,
    "edhrec_average_deck_multiple": average_deck_handler.get_multiple_brackets,
    "edhrec_compare_brackets": average_deck_handler.compare_brackets,
    
    # Budget Analysis Tools  
    "edhrec_budget_comparison": budget_comparison_handler.get_budget_comparison,
    "edhrec_detailed_comparison": budget_comparison_handler.get_detailed_comparison,
    
    # Mightstone Core Tools
    "mightstone_search_commanders": mightstone_service.search_commanders,
    "mightstone_get_commander_data": mightstone_service.get_commander_data,
    "mightstone_search_cards": mightstone_service.search_cards,
    "mightstone_get_card_by_name": mightstone_service.get_card_by_name,
    "mightstone_analyze_deck": mightstone_service.analyze_deck,
    "mightstone_get_recommendations": mightstone_service.get_recommendations,
}

def get_tool(tool_name: str):
    """Get a tool by name from the registry."""
    return TOOL_REGISTRY.get(tool_name)

def list_available_tools():
    """List all available tools."""
    return list(TOOL_REGISTRY.keys())

def get_tool_description(tool_name: str) -> str:
    """Get description for a specific tool."""
    descriptions = {
        "edhrec_average_deck": "Get EDHREC average deck for a commander with specific bracket",
        "edhrec_average_deck_multiple": "Get average decks for a commander across multiple brackets",
        "edhrec_compare_brackets": "Compare two different deck brackets for analysis",
        "edhrec_budget_comparison": "Get budget vs expensive deck comparison",
        "edhrec_detailed_comparison": "Get detailed budget analysis with recommendations",
        "mightstone_search_commanders": "Search for MTG commanders using Mightstone",
        "mightstone_get_commander_data": "Get comprehensive commander data",
        "mightstone_search_cards": "Search for MTG cards using Scryfall syntax",
        "mightstone_get_card_by_name": "Get detailed card information by name",
        "mightstone_analyze_deck": "Analyze a deck list and provide recommendations",
        "mightstone_get_recommendations": "Get card recommendations for a commander",
    }
    
    return descriptions.get(tool_name, "No description available")