"""
Utility functions for commander name normalization and identity handling.
"""

import re
from typing import List, Tuple


def normalize_commander_name(name: str) -> str:
    """
    Normalize commander name for consistent searching.
    
    Args:
        name: Raw commander name
        
    Returns:
        Normalized name
    """
    # Remove special characters and normalize whitespace
    normalized = re.sub(r'[^\w\s\-]', '', name)
    normalized = re.sub(r'\s+', ' ', normalized.strip())
    
    return normalized


def commander_slug_candidates(name: str) -> Tuple[str, ...]:
    """
    Generate potential slug candidates for a commander name.
    
    Args:
        name: Commander name
        
    Returns:
        Tuple of potential slug strings
    """
    if not name or not name.strip():
        return ("",)
    
    normalized = normalize_commander_name(name)
    candidates = []
    
    # Clean version
    clean = re.sub(r'[^\w\s]', '', normalized).lower()
    candidates.append(clean.replace(' ', '-'))
    
    # Remove common prefixes
    for prefix in ['the ', 'lord ', 'lady ', 'sir ']:
        if clean.startswith(prefix):
            candidates.append(clean.replace(prefix, '').replace(' ', '-'))
    
    # Remove common suffixes
    for suffix in [' the ', ' of ']:
        if suffix in clean:
            base = clean.split(suffix)[0]
            candidates.append(base.replace(' ', '-'))
    
    return tuple(candidates)


def canonicalize_color_identity(colors: List[str]) -> str:
    """
    Convert color list to standardized color identity string.
    
    Args:
        colors: List of color codes (e.g., ['W', 'U', 'R'])
        
    Returns:
        Canonicalized color identity string
    """
    if not colors:
        return "C"  # Colorless
    
    # Standard order: W, U, B, R, G
    color_order = ['W', 'U', 'B', 'R', 'G']
    present_colors = [color for color in color_order if color in colors]
    
    if len(present_colors) == 0:
        return "C"  # Colorless
    elif len(present_colors) == 5:
        return "WUBRG"  # Five color
    else:
        return ''.join(present_colors)


def parse_mana_cost(mana_cost: str) -> dict:
    """
    Parse mana cost string into components.
    
    Args:
        mana_cost: Mana cost string (e.g., "{2}{U}{R}")
        
    Returns:
        Dictionary with parsed mana components
    """
    if not mana_cost:
        return {"total": 0, "colored": {}, "colorless": 0, "generic": 0}
    
    # Extract numeric values
    numbers = re.findall(r'\{(\d+)\}', mana_cost)
    generic = sum(int(n) for n in numbers) if numbers else 0
    
    # Count colored mana
    colored_mana = re.findall(r'\{([WUBRG])\}', mana_cost)
    colored_counts = {}
    for color in colored_mana:
        colored_counts[color] = colored_counts.get(color, 0) + 1
    
    total_cmc = generic + sum(colored_counts.values())
    
    return {
        "total": total_cmc,
        "colored": colored_counts,
        "colorless": generic,
        "generic": generic,
        "original": mana_cost
    }


def extract_card_type(type_line: str) -> dict:
    """
    Extract card type information from type line.
    
    Args:
        type_line: Card type line (e.g., "Legendary Creature — Human Wizard")
        
    Returns:
        Dictionary with parsed type information
    """
    if not type_line:
        return {"supertype": "", "types": [], "subtypes": []}
    
    # Split by em dash
    parts = type_line.split('—')
    main_types = parts[0].strip()
    subtypes = parts[1].strip() if len(parts) > 1 else ""
    
    # Split supertypes and types
    type_words = main_types.split()
    supertypes = []
    card_types = []
    
    supertype_words = ['Legendary', 'Basic', 'Snow', 'World']
    for word in type_words:
        if word in supertype_words:
            supertypes.append(word)
        else:
            card_types.append(word)
    
    subtype_list = subtypes.split() if subtypes else []
    
    return {
        "supertype": ' '.join(supertypes),
        "types": card_types,
        "subtypes": subtype_list,
        "is_legendary": "Legendary" in supertypes,
        "is_basic": "Basic" in supertypes
    }