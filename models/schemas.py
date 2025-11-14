"""
Pydantic models for Mightstone GPT API data validation.
"""

from datetime import date
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# Response Models
class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str
    timestamp: str


class CardInfo(BaseModel):
    """Card information model."""
    id: str
    name: str
    mana_cost: Optional[str] = None
    cmc: Optional[float] = None
    type_line: Optional[str] = None
    oracle_text: Optional[str] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    loyalty: Optional[str] = None
    colors: Optional[List[str]] = None
    color_identity: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    legalities: Optional[Dict[str, str]] = None
    games: Optional[List[str]] = None
    reserved: Optional[bool] = None
    foil: Optional[bool] = None
    nonfoil: Optional[bool] = None
    oversized: Optional[bool] = None
    promo: Optional[bool] = None
    reprint: Optional[bool] = None
    variation: Optional[bool] = None
    set_id: Optional[str] = None
    set: Optional[str] = None
    set_name: Optional[str] = None
    set_type: Optional[str] = None
    set_uri: Optional[str] = None
    set_search_uri: Optional[str] = None
    scryfall_set_uri: Optional[str] = None
    rulings_uri: Optional[str] = None
    prints_search_uri: Optional[str] = None
    collector_number: Optional[str] = None
    digital: Optional[bool] = None
    rarity: Optional[str] = None
    flavor_text: Optional[str] = None
    artist: Optional[str] = None
    artist_ids: Optional[List[str]] = None
    illustration_id: Optional[str] = None
    border_color: Optional[str] = None
    frame: Optional[str] = None
    full_art: Optional[bool] = None
    textless: Optional[bool] = None
    booster: Optional[bool] = None
    story_spotlight: Optional[bool] = None
    edhrec_rank: Optional[int] = None
    prices: Optional[Dict[str, Optional[float]]] = None
    related_uris: Optional[Dict[str, str]] = None
    image_uris: Optional[Dict[str, str]] = None
    mana_cost_html: Optional[str] = None


class DeckCard(BaseModel):
    """Individual card in a deck."""
    name: str
    quantity: int
    scryfall_id: Optional[str] = None
    image_url: Optional[str] = None
    scryfall_uri: Optional[str] = None


class CommanderDeck(BaseModel):
    """Complete commander and deck information."""
    commander: CardInfo
    deck: Optional[Dict[str, Any]] = None
    themes: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    edhrec_url: Optional[str] = None
    average_deck_url: Optional[str] = None
    budget_brackets: Optional[List[str]] = None


class ThemeItem(BaseModel):
    """Individual item in a theme."""
    name: str
    count: Optional[int] = None
    scryfall_id: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None


class ThemeCollection(BaseModel):
    """Collection of theme items."""
    items: List[ThemeItem]
    total_count: int


class ThemeData(BaseModel):
    """Theme/tag data from EDHREC."""
    theme_name: str
    description: Optional[str] = None
    colors: Optional[List[str]] = None
    category: str
    items: ThemeCollection
    edhrec_url: Optional[str] = None
    source: str = "edhrec"


class DeckData(BaseModel):
    """Average deck data."""
    commander: str
    bracket: str
    source_url: str
    cards: List[DeckCard]
    total_cards: int
    last_updated: Optional[str] = None


class BudgetComparison(BaseModel):
    """Budget vs expensive deck comparison."""
    commander: str
    budget_deck: Optional[DeckData] = None
    expensive_deck: Optional[DeckData] = None
    comparison_summary: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Card search response."""
    query: str
    total_cards: int
    cards: List[CardInfo]


class RecommendationData(BaseModel):
    """Card recommendation data."""
    category: str
    cards: List[CardInfo]
    reasoning: Optional[str] = None


class DeckAnalysis(BaseModel):
    """Deck analysis results."""
    total_cards: int
    mana_curve: Optional[Dict[str, int]] = None
    color_distribution: Optional[Dict[str, int]] = None
    card_types: Optional[Dict[str, int]] = None
    recommendations: List[RecommendationData]
    synergies: Optional[List[str]] = None
    improvements: Optional[List[str]] = None


# Error Models
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str
    status_code: int


# Utility Models
class APIInfo(BaseModel):
    """API information model."""
    service: str
    version: str
    features: List[str]
    docs_url: str
    contact: str


class ThemeSuggestion(BaseModel):
    """Theme suggestion model."""
    theme_name: str
    popularity_score: Optional[float] = None
    category: Optional[str] = None
    color_alignment: Optional[List[str]] = None