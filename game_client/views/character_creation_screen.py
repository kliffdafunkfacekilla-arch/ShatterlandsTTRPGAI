# game_client/views/character_creation_screen.py
import logging
import uuid
from functools import partial
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.factory import Factory
from kivy.clock import Clock

from game_client.utils import AsyncHelper
from game_client.views.wizard_steps import IdentityStep, FeatureStep, CapstoneStep, BackgroundStep, FinalStep

# Import Monolith Modules (Local Architecture)
try:
    from monolith.modules import rules as rules_api
    from monolith.modules.save_manager import save_character_to_json
    from monolith.modules.save_schemas import CharacterSave
except ImportError as e:
    logging.error(f"Monolith modules not found: {e}")
    rules_api = None
    save_character_to_json = None
    CharacterSave = None

class CharacterCreationScreen(Screen, AsyncHelper):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rules_data = {}
        self.collected_data = {}
        self.steps = []
        self.current_step_index = 0
        self.build_ui()

    def on_enter(self):
        """Called when screen is displayed."""
        self.reset_wizard()
        self.load_rules_data()

    def build_ui(self):
        self.clear_widgets()
        
        # Root Layout - Dungeon Background
        root = Factory.DungeonBackground(orientation='vertical', padding='20dp', spacing='10dp')
        
        # Header
        self.header_label = Factory.DungeonLabel(
            text="Character Creation Wizard", 
            font_size='24sp', 
            size_hint_y=None, 
            height='50dp',
            bold=True,
            color=(0.9, 0.8, 0.6, 1)
        )
        root.add_widget(self.header_label)

        # Content Area (Holds the current step)
        self.content_area = Factory.ParchmentPanel(orientation='vertical', padding='10dp')
        root.add_widget(self.content_area)

        # Footer (Navigation)
        footer = BoxLayout(size_hint_y=None, height='60dp', spacing='20dp')
        
        self.back_btn = Factory.DungeonButton(text="Back")
        self.back_btn.bind(on_release=self.go_back)
        
        self.next_btn = Factory.DungeonButton(text="Next")
        self.next_btn.bind(on_release=self.go_next)
        
        footer.add_widget(self.back_btn)
        footer.add_widget(self.next_btn)
        root.add_widget(footer)

        self.add_widget(root)

    def load_rules_data(self):
        self.set_loading(True)
        self.run_async(self._fetch_rules_task, self._on_rules_loaded, self._on_rules_error)

    def _fetch_rules_task(self):
        if not rules_api: return {}
        
        # Robust Talent Parsing
        talents_data = rules_api.get_all_talents_data()
        all_talents = []
        
        def extract_names(obj):
            if isinstance(obj, dict):
                if 'talent_name' in obj: all_talents.append(obj['talent_name'])
                elif 'name' in obj: all_talents.append(obj['name'])
                for v in obj.values(): extract_names(v)
            elif isinstance(obj, list):
                for item in obj: extract_names(item)
        
        if talents_data:
            extract_names(talents_data)

        return {
            "kingdoms": rules_api.get_all_kingdoms(),
            "schools": rules_api.get_all_ability_schools(),
            "origins": rules_api.get_origin_choices(),
            "childhoods": rules_api.get_childhood_choices(),
            "coming_of_ages": rules_api.get_coming_of_age_choices(),
            "trainings": rules_api.get_training_choices(),
            "devotions": rules_api.get_devotion_choices(),
            "talents": sorted(list(set(all_talents))) if all_talents else ["Basic Strike"],
            # We need raw feature data for descriptions
            "kingdom_features_data": rules_api.get_data("kingdom_features_data"),
            "stats_list": rules_api.get_all_stats(),
            "all_skills": rules_api.get_all_skills()
        }

    def _on_rules_loaded(self, data):
        self.rules_data = data
        self.set_loading(False)
        self.init_steps()

    def _on_rules_error(self, error):
        logging.error(f"Rules load error: {error}")
        self.set_loading(False)
        # Initialize steps anyway so the UI doesn't crash, but show error
        self.init_steps()
        self.init_steps()
        from game_client.ui_utils import show_error
        show_error("Data Load Error", f"Failed to load game data:\n{error}")

    def init_steps(self):
        self.steps = []
        # 1. Identity
        self.steps.append(IdentityStep(self))
        
        # 2-9. Features F1-F8
        for i in range(1, 9):
            self.steps.append(FeatureStep(self, f"F{i}"))
            
        # 10. Capstone
        self.steps.append(CapstoneStep(self))
        
        # 11-15. Backgrounds
        self.steps.append(BackgroundStep(self, 'origins', "Origin"))
        self.steps.append(BackgroundStep(self, 'childhoods', "Childhood"))
        self.steps.append(BackgroundStep(self, 'coming_of_ages', "Coming of Age"))
        self.steps.append(BackgroundStep(self, 'trainings', "Training"))
        self.steps.append(BackgroundStep(self, 'devotions', "Devotion"))
        
        # 16. Final
        self.steps.append(FinalStep(self))
        
        self.current_step_index = 0
        self.show_step(0)

    def show_step(self, index):
        if index < 0 or index >= len(self.steps):
            return
            
        self.content_area.clear_widgets()
        step = self.steps[index]
        self.content_area.add_widget(step)
        step.on_enter()
        
        self.header_label.text = f"Step {index + 1}/{len(self.steps)}: {step.title}"
        
        # Update buttons
        self.back_btn.text = "Back" if index > 0 else "Cancel"
        self.next_btn.text = "Finish" if index == len(self.steps) - 1 else "Next"
        
        self.update_nav_state()
        # Bind validation
        step.bind(is_valid=self.update_nav_state)

    def update_nav_state(self, *args):
        step = self.steps[self.current_step_index]
        # print(f"DEBUG: update_nav_state: Step={step.title}, Valid={step.is_valid}")
        self.next_btn.disabled = not step.is_valid

    def go_next(self, instance):
        # Collect data from current step
        step = self.steps[self.current_step_index]
        data = step.get_data()
        self.collected_data.update(data)
        
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self.show_step(self.current_step_index)
        else:
            self.submit_character()

    def go_back(self, instance):
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self.show_step(self.current_step_index)
        else:
            App.get_running_app().root.current = 'main_menu'

    def calculate_current_stats(self):
        # Base 8
        stats = {s: 8 for s in ["Might", "Endurance", "Finesse", "Reflexes", "Vitality", "Fortitude", "Knowledge", "Logic", "Awareness", "Intuition", "Charm", "Willpower"]}
        
        # Apply Feature Mods
        kf_data = self.rules_data.get('kingdom_features_data', {})
        kingdom = self.collected_data.get('kingdom')
        
        for i in range(1, 9):
            f_key = f"F{i}"
            choice_name = self.collected_data.get(f_key)
            if not choice_name or not kingdom: continue
            
            # Find the choice object
            f_data = kf_data.get(f_key, {})
            options = f_data.get(kingdom, [])
            if not options and "All" in f_data: options = f_data["All"]
            
            for opt in options:
                if opt.get('name') == choice_name:
                    mods = opt.get('mods', {})
                    for val_str, stat_list in mods.items():
                        try:
                            val = int(val_str)
                            for s in stat_list:
                                if s in stats: stats[s] += val
                        except: pass
                    break
        return stats

    def submit_character(self):
        self.set_loading(True)
        self.run_async(self._create_character_task, self._on_character_created, self._on_creation_error)

    def _create_character_task(self):
        if not save_character_to_json or not CharacterSave:
            raise ImportError("SaveManager or CharacterSave schema not available.")

        # 1. Calculate Stats
        final_stats = self.calculate_current_stats()
        
        # 2. Generate ID
        char_id = str(uuid.uuid4())
        
        # 3. Construct CharacterSave Object
        # Note: We are simplifying here. In a full implementation, we'd map all the background choices
        # to specific skills, equipment, etc. For now, we just save the choices in 'previous_state' or similar
        # if we want to keep them, or just rely on the stats we calculated.
        
        # We'll store the raw choices in 'previous_state' so we can debug or re-process later if needed.
        raw_choices = self.collected_data.copy()
        
        # Default HP/Composure
        max_hp = final_stats.get("Vitality", 10) * 2 + final_stats.get("Might", 10)
        max_comp = final_stats.get("Willpower", 10) * 2 + final_stats.get("Logic", 10)
        
        new_char = CharacterSave(
            id=char_id,
            name=self.collected_data.get("name", "Unknown Hero"),
            kingdom=self.collected_data.get("kingdom"),
            level=1,
            stats=final_stats,
            stats=final_stats,
            skills=self._map_background_to_skills(),
            max_hp=max_hp,
            max_hp=max_hp,
            current_hp=max_hp,
            max_composure=max_comp,
            current_composure=max_comp,
            talents=[self.collected_data.get("ability_talent")] if self.collected_data.get("ability_talent") else [],
            abilities=[],
            inventory={},
            equipment={},
            previous_state={"creation_choices": raw_choices}, # Store choices for reference
            portrait_id="character_1" # Default for now
        )
        
        # 4. Save to JSON
        result = save_character_to_json(new_char)
        
        if not result["success"]:
            raise Exception(result.get("error", "Unknown save error"))
            
        return new_char

    def _on_character_created(self, res):
        logging.info(f"Character Created: {res.name}")
        app = App.get_running_app()
        if not hasattr(app, 'game_settings') or app.game_settings is None:
            app.game_settings = {}
        
        # We don't automatically add to party list anymore, the Game Setup screen handles selection
        # But we can navigate there.
        
        # We don't automatically add to party list anymore, the Game Setup screen handles selection
        # But we can navigate there.
        
        from game_client.ui_utils import show_success
        show_success(f"Character '{res.name}' created successfully!\nIt is now available in Game Setup.")
        
        # Navigate to Game Setup after a delay
        Clock.schedule_once(lambda dt: setattr(app.root, 'current', 'game_setup'), 2.0)
        
        self.set_loading(False)

    def _on_creation_error(self, error):
        logging.error(f"Creation failed: {error}")
        self.set_loading(False)
        from game_client.ui_utils import show_error
        show_error("Creation Error", str(error))

    def set_loading(self, loading):
        if hasattr(self, 'next_btn'):
            self.next_btn.text = "Loading..." if loading else ("Finish" if self.current_step_index == len(self.steps)-1 else "Next")
            self.next_btn.disabled = loading

    def reset_wizard(self):
        self.collected_data = {}
        self.current_step_index = 0
        if self.steps:
            self.show_step(0)
