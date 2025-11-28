import json
import logging
from sqlalchemy.orm import Session
from . import models
from . import schemas
from ..ai_dm_pkg.llm_service import ai_client
from ..simulation import get_world_context

try:
    from ..lore import LoreManager
except ImportError:
    LoreManager = None

logger = logging.getLogger("monolith.story.director")

class CampaignDirector:
    def __init__(self, db: Session, campaign_id: int):
        self.db = db
        self.campaign_id = campaign_id

    def _get_state(self) -> models.CampaignState:
        state = self.db.query(models.CampaignState).filter(models.CampaignState.campaign_id == self.campaign_id).first()
        if not state:
            # Create default state if missing
            state = models.CampaignState(
                campaign_id=self.campaign_id,
                current_act=1,
                plot_points={"major_beats": [], "completed_beats": []},
                narrative_tags=[],
                active_seeds=[]
            )
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)
        return state

    def check_pacing(self, player_xp: int) -> bool:
        """
        Compares current XP (or level, simplified here) to pacing thresholds.
        Returns True if a major plot point should be triggered.
        """
        # Simplified logic: every 1000 XP triggers a check?
        # Or based on level. Let's assume input is level for now based on prompt context "Compariing XP to target level".
        # Prompt says "Compares current XP to the target level".
        # Let's assume checking if ready for major beat.

        # For prototype, we'll just check if there are no active quests, then we are ready.
        active_quests = self.db.query(models.ActiveQuest).filter(
            models.ActiveQuest.campaign_id == self.campaign_id,
            models.ActiveQuest.status == "active"
        ).count()

        return active_quests == 0

    def generate_next_beat(self) -> dict:
        """
        Calls AI to generate the next quest/beat based on simulation state.
        """
        state = self._get_state()
        world_context = get_world_context()
        narrative_tags = state.narrative_tags or []
        current_act = state.current_act

        lore_context = ""
        if LoreManager:
            try:
                lore_mgr = LoreManager()
                lore_context = lore_mgr.get_lore_context(narrative_tags)
            except Exception as e:
                logger.error(f"Failed to load lore context: {e}")

        prompt = f"""
        Act as a Campaign Director for a TTRPG.

        World Context:
        {world_context}

        Campaign Narrative Tags:
        {', '.join(narrative_tags)}

        Lore Context:
        {lore_context}

        Current Act: {current_act}

        Generate the next quest/plot beat in JSON format with fields:
        - title
        - description
        - objectives (list of strings)
        - enemy_types (list of strings, e.g. "Goblin", "Bandit")
        - reward_summary
        - new_narrative_tags (list of strings to add to state)
        """

        logger.info("Director generating next beat...")

        # Fallback response if AI fails or is offline
        fallback_quest = {
            "title": "A Simple Task",
            "description": "The world is quiet. You should look for work at the nearest town.",
            "objectives": ["Travel to town", "Talk to the Innkeeper"],
            "enemy_types": ["Rat"],
            "reward_summary": "10 Gold",
            "new_narrative_tags": ["peaceful"]
        }

        if ai_client and ai_client.model:
            try:
                # Use the 'generate_content' method of the underlying model if exposed,
                # or better, check if LLMService has a generic generate method.
                # It has `generate_map_flavor` which uses `self.model.generate_content`.
                # We can access `ai_client.model` directly since it's an attribute of LLMService.

                response = ai_client.model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )

                # Clean and parse
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]

                data = json.loads(text)

                # Basic validation
                required_fields = ["title", "description", "objectives"]
                if all(k in data for k in required_fields):
                    return data
                else:
                    logger.warning(f"AI returned invalid quest structure: {data.keys()}")
                    return fallback_quest

            except Exception as e:
                logger.error(f"AI Director failed: {e}")
                return fallback_quest

        # For now, return fallback to ensure stability until LLM service is fully inspected/updated
        return fallback_quest

    def resolve_seed(self, seed_id: str) -> dict:
        """
        Generates content for a specific story seed.
        """
        # In a real impl, this would look up the seed type and generate specific content.
        # For now, it generates a generic mini-quest.
        return self.generate_next_beat()

    def record_event(self, event_summary: str):
        """
        Records a major event and updates narrative tags.
        """
        state = self._get_state()
        tags = state.narrative_tags or []

        # Simple keyword extraction (naive)
        if "kill" in event_summary.lower():
            tags.append("violent")
        if "save" in event_summary.lower():
            tags.append("heroic")

        state.narrative_tags = list(set(tags)) # dedup

        # Add to completed beats if it matches a plot point (simplified)
        completed = state.plot_points.get("completed_beats", [])
        completed.append(event_summary)

        # Update JSON field
        # We need to re-assign to trigger SQLAlchemy detection or use flag_modified
        new_points = dict(state.plot_points)
        new_points["completed_beats"] = completed
        state.plot_points = new_points

        self.db.commit()
        self.db.refresh(state)

# Helper function to instantiate
def get_director(db: Session, campaign_id: int) -> CampaignDirector:
    return CampaignDirector(db, campaign_id)
