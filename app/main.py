"""
Mightstone GPT Webservice - Modern MTG Commander Deckbuilding API
Built using Mightstone as the backbone for comprehensive MTG data access.
"""

import json
import logging
import os
from datetime import date
from typing import Dict, List, Optional, Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from models.schemas import (
    CommanderDeck, 
    CardInfo, 
    ThemeData, 
    HealthResponse,
    BudgetComparison,
    SearchResponse
)
from services.edhrec_service import EDHRECService  
from services.scryfall_service import ScryfallService
from services.mightstone_service import MightstoneService

# -----------------------------------------------------------------------------
# Config & Logging
# -----------------------------------------------------------------------------
PORT = int(os.environ.get("PORT", "8080"))
USER_AGENT = os.environ.get(
    "MIGHTSTONE_UA",
    "Mightstone-GPT/2.0 (+https://github.com/Knack117/Mightstone-GPT)"
)
LOG_LEVEL = os.environ.get("LOGLEVEL", "INFO")

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("mightstone-gpt")

# -----------------------------------------------------------------------------
# FastAPI App Setup
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Mightstone GPT Webservice",
    description="Modern MTG Commander deckbuilding API powered by Mightstone",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Service Initialization
# -----------------------------------------------------------------------------
mightstone_service = MightstoneService()
edhrec_service = EDHRECService()
scryfall_service = ScryfallService()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    log.info("🚀 Starting Mightstone GPT Webservice v2.0")
    await mightstone_service.initialize()
    await edhrec_service.initialize()
    await scryfall_service.initialize()
    log.info("✅ All services initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown."""
    log.info("🛑 Shutting down Mightstone GPT Webservice")
    await mightstone_service.cleanup()
    await edhrec_service.cleanup()
    await scryfall_service.cleanup()

# -----------------------------------------------------------------------------
# Health & Info Endpoints
# -----------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="mightstone-gpt",
        version="2.0.0",
        timestamp=date.today().isoformat()
    )

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Mightstone GPT Webservice",
        "version": "2.0.0",
        "description": "Modern MTG Commander deckbuilding API",
        "docs": "/docs",
        "features": [
            "Commander deck analysis",
            "EDHREC theme integration", 
            "Scryfall card search",
            "Budget deck comparisons",
            "Modern Mightstone backend"
        ]
    }

# -----------------------------------------------------------------------------
# Commander & Deck Endpoints
# -----------------------------------------------------------------------------
@app.get("/commander/{commander_name}", response_model=CommanderDeck)
async def get_commander_data(
    commander_name: str,
    bracket: Optional[str] = Query(None, description="Deck bracket: precon, core, upgraded, optimized, cedh")
):
    """
    Get comprehensive commander data including average deck and themes.
    
    Args:
        commander_name: Name of the commander
        bracket: Optional deck bracket preference
    """
    try:
        # Use Mightstone to get commander data
        commander_data = await mightstone_service.get_commander_data(commander_name)
        
        # Get average deck if bracket specified
        if bracket:
            deck_data = await edhrec_service.get_average_deck(commander_name, bracket)
            commander_data.deck = deck_data
        
        return commander_data
        
    except Exception as e:
        log.error(f"Error getting commander data for {commander_name}: {e}")
        raise HTTPException(status_code=404, detail=f"Commander '{commander_name}' not found")

@app.get("/commander/{commander_name}/deck", response_model=Dict[str, Any])
async def get_commander_deck(
    commander_name: str,
    bracket: str = Query("optimized", description="Deck bracket preference")
):
    """Get average deck for a commander with specific bracket."""
    try:
        deck_data = await edhrec_service.get_average_deck(commander_name, bracket)
        return deck_data
        
    except Exception as e:
        log.error(f"Error getting deck for {commander_name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/commander/{commander_name}/budget-comparison", response_model=BudgetComparison)
async def get_budget_comparison(commander_name: str):
    """Get budget vs expensive deck comparison for a commander."""
    try:
        comparison = await edhrec_service.get_budget_comparison(commander_name)
        return comparison
        
    except Exception as e:
        log.error(f"Error getting budget comparison for {commander_name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# -----------------------------------------------------------------------------
# Card Search & Information
# -----------------------------------------------------------------------------
@app.get("/cards/search", response_model=SearchResponse)
async def search_cards(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results to return"),
    order: str = Query("name", description="Sort order")
):
    """
    Search for MTG cards using Scryfall via Mightstone.
    
    Args:
        q: Search query (supports Scryfall syntax)
        limit: Number of results to return
        order: Sort order
    """
    try:
        results = await scryfall_service.search_cards(q, limit, order)
        return SearchResponse(
            query=q,
            total_cards=len(results),
            cards=results
        )
        
    except Exception as e:
        log.error(f"Error searching cards with query '{q}': {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/cards/{card_name}", response_model=CardInfo)
async def get_card_info(card_name: str):
    """Get detailed information for a specific card."""
    try:
        card_data = await scryfall_service.get_card_by_name(card_name)
        return card_data
        
    except Exception as e:
        log.error(f"Error getting card info for '{card_name}': {e}")
        raise HTTPException(status_code=404, detail=f"Card '{card_name}' not found")

# -----------------------------------------------------------------------------
# EDHREC Theme & Tag Endpoints
# -----------------------------------------------------------------------------
@app.get("/themes/{theme_name}", response_model=ThemeData)
async def get_theme_data(
    theme_name: str,
    colors: Optional[str] = Query(None, description="Color identity (e.g., 'UR', 'WBG')")
):
    """
    Get theme/tag data from EDHREC.
    
    Args:
        theme_name: Name of the theme or tag
        colors: Optional color identity filter
    """
    try:
        theme_data = await edhrec_service.get_theme_data(theme_name, colors)
        return theme_data
        
    except Exception as e:
        log.error(f"Error getting theme data for '{theme_name}': {e}")
        raise HTTPException(status_code=404, detail=f"Theme '{theme_name}' not found")

@app.get("/themes/suggestions")
async def get_theme_suggestions(commander_name: str):
    """Get theme suggestions for a commander based on EDHREC data."""
    try:
        suggestions = await edhrec_service.get_theme_suggestions(commander_name)
        return {"commander": commander_name, "themes": suggestions}
        
    except Exception as e:
        log.error(f"Error getting theme suggestions for '{commander_name}': {e}")
        raise HTTPException(status_code=404, detail=f"No themes found for '{commander_name}'")

# -----------------------------------------------------------------------------
# Deck Analysis & Recommendations
# -----------------------------------------------------------------------------
@app.post("/deck/analyze")
async def analyze_deck(deck_list: List[str]):
    """
    Analyze a deck list and provide recommendations.
    
    Args:
        deck_list: List of card names in the deck
    """
    try:
        analysis = await mightstone_service.analyze_deck(deck_list)
        return analysis
        
    except Exception as e:
        log.error(f"Error analyzing deck: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/recommendations/{commander_name}")
async def get_recommendations(
    commander_name: str,
    exclude_cards: Optional[str] = Query(None, description="Comma-separated list of cards to exclude"),
    include_themes: Optional[str] = Query(None, description="Comma-separated list of themes to include")
):
    """Get card recommendations for a commander based on EDHREC data."""
    try:
        exclude_list = exclude_cards.split(",") if exclude_cards else []
        theme_list = include_themes.split(",") if include_themes else []
        
        recommendations = await mightstone_service.get_recommendations(
            commander_name, exclude_list, theme_list
        )
        return recommendations
        
    except Exception as e:
        log.error(f"Error getting recommendations for '{commander_name}': {e}")
        raise HTTPException(status_code=400, detail=str(e))

# -----------------------------------------------------------------------------
# Privacy Policy
# -----------------------------------------------------------------------------
@app.get("/privacy")
async def privacy_policy():
    """Privacy policy endpoint for GPT publishing."""
    return {
        "title": "Privacy Policy - Mightstone GPT Webservice",
        "last_updated": date.today().isoformat(),
        "contact": "pommnetwork@gmail.com",
        "policy": """
        This API service stores no personal data. All requests are processed
        anonymously and no user information is logged or stored.
        
        The service fetches publicly available MTG card data from:
        - Scryfall (public API)
        - EDHREC (public website data)
        
        No personal information, game data, or user behavior is collected.
        """
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level=LOG_LEVEL.lower()
    )