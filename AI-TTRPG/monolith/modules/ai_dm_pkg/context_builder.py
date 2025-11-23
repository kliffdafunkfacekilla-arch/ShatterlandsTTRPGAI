"""
Context builder for minimal, efficient LLM prompts.
Generates diff-based context snapshots to reduce token usage.
"""
import logging
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger("monolith.ai_dm.context")

@dataclass
class ContextSnapshot:
    """Minimal context payload for LLM prompts."""
    # Player essentials (current state only)
    player_name: str
    player_hp_percent: float  # Current HP as percentage of max
    player_composure_percent: float  # Current composure as percentage
    
    # Location essentials
    location_name: str
    location_description: str
    nearby_npcs: List[str]  # Just names/template IDs
    nearby_items: List[str]  # Just template IDs
    
    # Recent history (the "diff")
    recent_events: List[str]  # Last 3-5 narrative events
    recent_changes: Dict[str, Any]  # {hp_change: -5, item_added: "dagger"}
    
    def to_prompt_text(self) -> str:
        """Convert to a concise prompt string for the LLM."""
        npc_str = ", ".join(self.nearby_npcs) if self.nearby_npcs else "none"
        item_str = ", ".join(self.nearby_items) if self.nearby_items else "none"
        
        events_str = "\\n- ".join(self.recent_events) if self.recent_events else "None"
        if self.recent_events:
            events_str = "- " + events_str
        
        changes_parts = []
        for key, value in self.recent_changes.items():
            changes_parts.append(f"{key}: {value}")
        changes_str = ", ".join(changes_parts) if changes_parts else "None"
        
        return f"""[CONTEXT START]
Player: {self.player_name} (HP: {self.player_hp_percent:.0%}, Composure: {self.player_composure_percent:.0%})
Location: {self.location_name}
Description: {self.location_description}
NPCs Nearby: {npc_str}
Items Nearby: {item_str}

Recent Events:
{events_str}

Recent Changes: {changes_str}
[CONTEXT END]
"""

def build_minimal_context(
    char_context: Dict[str, Any],
    loc_context: Dict[str, Any],
    recent_log: List[str] = None
) -> ContextSnapshot:
    """Build a minimal context snapshot from full game state.
    
    This is the core of the diff-based prompting strategy. Instead of sending
    the entire world state to the LLM, we extract only the essentials:
    - Player's current vital stats (as percentages)
    - Immediate location context
    - Recent narrative events (last 3-5)
    - Delta changes from the last turn
    
    Args:
        char_context: Full character context dict
        loc_context: Full location context dict
        recent_log: Optional list of recent story log entries
    
    Returns:
        ContextSnapshot ready for LLM prompt injection
    """
    # Extract player vitals
    current_hp = char_context.get("current_hp", 0)
    max_hp = char_context.get("max_hp", 1)
    hp_percent = current_hp / max(max_hp, 1)
    
    current_composure = char_context.get("current_composure", 0)
    max_composure = char_context.get("max_composure", 1)
    composure_percent = current_composure / max(max_composure, 1)
    
    # Extract location essentials
    npcs = loc_context.get("npcs", [])
    npc_names = [npc.get("template_id", "Unknown NPC") for npc in npcs[:5]]  # Limit to 5
    
    items = loc_context.get("items", [])
    item_names = [item.get("template_id", "Unknown Item") for item in items[:5]]  # Limit to 5
    
    # Recent events (last 3-5 from story log)
    events = recent_log[-5:] if recent_log else []
    
    # Recent changes - calculate actual diffs from context data
    recent_changes = _calculate_state_diff(char_context)
    
    return ContextSnapshot(
        player_name=char_context.get("name", "Unknown"),
        player_hp_percent=hp_percent,
        player_composure_percent=composure_percent,
        location_name=loc_context.get("name", "Unknown Location"),
        location_description=loc_context.get("description", "A mysterious place."),
        nearby_npcs=npc_names,
        nearby_items=item_names,
        recent_events=events,
        recent_changes=recent_changes,
    )

def _calculate_state_diff(char_context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate state changes from cached previous state.
    
    Compares current character state to cached 'previous_state' field to detect:
    - HP changes
    - Items gained/lost
    - Status effects applied/removed
    - Resource changes (composure, action points, etc.)
    
    Args:
        char_context: Current character context with optional 'previous_state' cache
    
    Returns:
        Dictionary of recent changes for LLM context
    """
    changes = {}
    prev_state = char_context.get("previous_state", {})
    
    # HP change
    current_hp = char_context.get("current_hp", 0)
    prev_hp = prev_state.get("current_hp", current_hp)  # Default to current if no cache
    if current_hp != prev_hp:
        hp_change = current_hp - prev_hp
        changes["hp_change"] = hp_change
    
    # Composure change
    current_comp = char_context.get("current_composure", 0)
    prev_comp = prev_state.get("current_composure", current_comp)
    if current_comp != prev_comp:
        comp_change = current_comp - prev_comp
        changes["composure_change"] = comp_change
    
    # Inventory changes (simplified - detect additions)
    current_inv = set(char_context.get("inventory", []))
    prev_inv = set(prev_state.get("inventory", []))
    items_gained = current_inv - prev_inv
    items_lost = prev_inv - current_inv
    
    if items_gained:
        changes["items_gained"] = list(items_gained)
    if items_lost:
        changes["items_lost"] = list(items_lost)
    
    # Status effects changes
    current_status = set(char_context.get("status_effects", []))
    prev_status = set(prev_state.get("status_effects", []))
    effects_gained = current_status - prev_status
    effects_removed = prev_status - current_status
    
    if effects_gained:
        changes["status_gained"] = list(effects_gained)
    if effects_removed:
        changes["status_removed"] = list(effects_removed)
    
    return changes
