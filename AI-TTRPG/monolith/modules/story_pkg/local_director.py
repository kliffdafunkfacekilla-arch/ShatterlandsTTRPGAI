import logging
import json
from typing import List, Dict, Any, Optional
from ..save_schemas import SaveGameData, QuestSave
from ..ai_dm_pkg.llm_service import ai_client

logger = logging.getLogger("monolith.story.director.local")

class LocalCampaignDirector:
    """
    A local version of the Campaign Director that operates on SaveGameData.
    """
    
    def __init__(self):
        self.logger = logger

    def check_pacing(self, state: SaveGameData) -> bool:
        """
        Checks if a new plot beat should be generated.
        """
        if not state:
            return False
            
        # Simple logic: If no active quests, generate one.
        active_quests = [q for q in state.quests if q.status == "active"]
        return len(active_quests) == 0

    def generate_next_beat(self, state: SaveGameData) -> Dict[str, Any]:
        """
        Calls AI to generate the next quest/beat based on simulation state.
        """
        # Gather context
        narrative_tags = [] # state.narrative_tags if exists
        current_act = 1 # state.current_act if exists
        
        # Build prompt
        prompt = f"""
        Act as a Campaign Director for a TTRPG.
        
        Current Act: {current_act}
        
        Generate the next quest/plot beat in JSON format with fields:
        - title
        - description
        - objectives (list of strings)
        - enemy_types (list of strings, e.g. "Goblin", "Bandit")
        - reward_summary
        - new_narrative_tags (list of strings)
        """
        
        logger.info("Director generating next beat...")
        
        # Fallback
        fallback_quest = {
            "title": "A Local Trouble",
            "description": "Villagers are complaining about disturbances nearby.",
            "objectives": ["Investigate the area", "Report back"],
            "enemy_types": ["Bandit"],
            "reward_summary": "50 Gold",
            "new_narrative_tags": ["minor_disturbance"]
        }

        if ai_client and ai_client.model:
            try:
                response = ai_client.model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                text = response.text.strip()
                # Basic cleanup if markdown is included
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                    
                data = json.loads(text)
                return data
                
            except Exception as e:
                logger.error(f"AI Director failed: {e}")
                return fallback_quest
        
        return fallback_quest
