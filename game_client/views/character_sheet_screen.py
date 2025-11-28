"""
Character Sheet Screen
Displays all stats, skills, abilities, and talents for the
active character.
"""
import logging
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.properties import ObjectProperty
from kivy.clock import Clock

# --- Kivy Language (KV) String for the Layout ---
CHARACTER_SHEET_KV = """
<CharacterSheetScreen>:
    # Main layout with a back button
    BoxLayout:
        orientation: 'vertical'

        # --- Top Bar ---
        BoxLayout:
            size_hint_y: None
            height: '48dp'
            canvas.before:
                Color:
                    rgba: 0.1, 0.1, 0.1, 0.9
                Rectangle:
                    pos: self.pos
                    size: self.size

            Label:
                id: char_name_label
                text: 'Character Sheet'
                font_size: '24sp'

            Button:
                text: 'Back to Game'
                size_hint_x: 0.3
                on_release: app.root.current = 'main_interface'

        # --- Main Content Area ---
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: '10dp'
                spacing: '15dp'

                # --- STATS ---
                Label:
                    text: 'Core Stats'
                    font_size: '20sp'
                    size_hint_y: None
                    height: '30dp'

                # We will populate this grid from the .py file
                GridLayout:
                    id: stats_grid
                    cols: 4
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: '5dp'

                # --- RESOURCE POOLS ---
                Label:
                    text: 'Resource Pools'
                    font_size: '20sp'
                    size_hint_y: None
                    height: '30dp'

                GridLayout:
                    id: resource_pools_grid
                    cols: 3
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: '5dp'

                # --- SKILLS ---
                Label:
                    text: 'Skills'
                    font_size: '20sp'
                    size_hint_y: None
                    height: '30dp'

                # We will populate this grid
                GridLayout:
                    id: skills_grid
                    cols: 3
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: '5dp'

                # --- TALENTS & ABILITIES ---
                BoxLayout:
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: '10dp'

                    BoxLayout:
                        orientation: 'vertical'
                        Label:
                            text: 'Talents'
                            font_size: '20sp'
                        # We will populate this list
                        BoxLayout:
                            id: talents_list
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height

                    BoxLayout:
                        orientation: 'vertical'
                        Label:
                            text: 'Abilities'
                            font_size: '20sp'
                        # We will populate this list
                        BoxLayout:
                            id: abilities_list
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
"""

# Load the KV string
Builder.load_string(CHARACTER_SHEET_KV)

class CharacterSheetScreen(Screen):
    # --- UI References ---
    char_name_label = ObjectProperty(None)
    stats_grid = ObjectProperty(None)
    skills_grid = ObjectProperty(None)
    resource_pools_grid = ObjectProperty(None)
    talents_list = ObjectProperty(None)
    abilities_list = ObjectProperty(None)

    def on_enter(self, *args):
        """Called when this screen is shown. Fetches data and populates UI."""
        try:
            app = App.get_running_app()

            # Get the active character directly from the App
            char_context = app.active_character_context

            if not char_context:
                logging.error("CHAR_SHEET: No active character context found!")
                if 'char_name_label' in self.ids:
                    self.ids.char_name_label.text = "Error: No Character Loaded"
                return

            self.populate_sheet(char_context)
        except Exception as e:
            logging.exception("CRASH PREVENTED IN CHARACTER SHEET")
            if 'char_name_label' in self.ids:
                self.ids.char_name_label.text = f"CRASH ERROR: {str(e)}"
            import traceback
            traceback.print_exc()

    def populate_sheet(self, context):
        """Fills all UI elements with character data."""

        if 'char_name_label' in self.ids:
            self.ids.char_name_label.text = f"{context.name} (Lvl {context.level} {context.kingdom})"

        # --- Populate Stats ---
        if 'stats_grid' in self.ids:
            self.ids.stats_grid.clear_widgets()
            stats = context.stats or {}
            if stats:
                for stat_name, value in stats.items():
                    self.ids.stats_grid.add_widget(
                        Label(text=f"{stat_name}:", font_size='16sp', size_hint_x=0.6, size_hint_y=None, height='30dp')
                    )
                    self.ids.stats_grid.add_widget(
                        Label(text=f"{value}", font_size='16sp', size_hint_x=0.4, size_hint_y=None, height='30dp')
                    )

        # --- Populate Skills ---
        if 'skills_grid' in self.ids:
            self.ids.skills_grid.clear_widgets()
            skills = context.skills or {}
            if skills:
                # We only want to show skills the character actually has
                for skill_name, data in skills.items():
                    rank = data.get('rank', 0)
                    if rank > 0:
                        self.ids.skills_grid.add_widget(
                            Label(text=f"{skill_name}:", font_size='14sp', size_hint_x=0.7, size_hint_y=None, height='30dp')
                        )
                        self.ids.skills_grid.add_widget(
                            Label(text=f"Rank {rank}", font_size='14sp', size_hint_x=0.3, size_hint_y=None, height='30dp')
                        )

        # --- Populate Talents ---
        if 'talents_list' in self.ids:
            self.ids.talents_list.clear_widgets()
            talents = context.talents or []
            if talents:
                from monolith.modules import rules as rules_api # Import here to avoid circular imports if any
                
                for talent_name in talents:
                    talent_data = rules_api.get_talent_details(talent_name)
                    
                    # Create a box for each talent
                    talent_box = BoxLayout(orientation='vertical', size_hint_y=None, height='60dp', spacing='2dp')
                    
                    # Name (Bold)
                    name_label = Label(text=f"[b]{talent_name}[/b]", markup=True, font_size='16sp', size_hint_y=None, height='20dp', halign='left', valign='middle')
                    name_label.bind(size=name_label.setter('text_size'))
                    talent_box.add_widget(name_label)
                    
                    # Effect Description
                    effect_text = talent_data.get("effect", "No description available.")
                    desc_label = Label(text=effect_text, font_size='12sp', color=(0.8, 0.8, 0.8, 1), size_hint_y=None, height='20dp', halign='left', valign='middle')
                    desc_label.bind(size=desc_label.setter('text_size'))
                    talent_box.add_widget(desc_label)

                    # Modifiers (if any)
                    modifiers = talent_data.get("modifiers", [])
                    if modifiers:
                        mod_text = ", ".join([f"{m.get('type')}: +{m.get('bonus', 0)}" for m in modifiers if 'bonus' in m])
                        if mod_text:
                            mod_label = Label(text=f"[i]Bonus: {mod_text}[/i]", markup=True, font_size='12sp', color=(0.5, 1, 0.5, 1), size_hint_y=None, height='15dp', halign='left', valign='middle')
                            mod_label.bind(size=mod_label.setter('text_size'))
                            talent_box.add_widget(mod_label)
                            talent_box.height = '75dp' # Increase height if modifiers exist

                    self.ids.talents_list.add_widget(talent_box)

        # --- Populate Abilities ---
        if 'abilities_list' in self.ids:
            self.ids.abilities_list.clear_widgets()
            abilities = context.abilities or []
            if abilities:
                for ability_desc in abilities:
                    self.ids.abilities_list.add_widget(
                        Label(text=ability_desc, font_size='14sp', text_size=(self.ids.abilities_list.width, None), size_hint_y=None, height='60dp')
                    )

        # --- Populate Resource Pools ---
        if 'resource_pools_grid' in self.ids:
            self.ids.resource_pools_grid.clear_widgets()
            pools = context.resource_pools or {}
            if pools:
                for pool_name, data in pools.items():
                    # Handle both dict and Pydantic object
                    if isinstance(data, dict):
                        current = data.get('current', 0)
                        max_val = data.get('max', 0)
                    else:
                        current = getattr(data, 'current', 0)
                        max_val = getattr(data, 'max', 0)

                    self.ids.resource_pools_grid.add_widget(
                        Label(text=f"{pool_name}:", font_size='16sp', size_hint_x=0.4, size_hint_y=None, height='30dp')
                    )
                    self.ids.resource_pools_grid.add_widget(
                        Label(text=f"{current}", font_size='16sp', size_hint_x=0.3, size_hint_y=None, height='30dp')
                    )
                    self.ids.resource_pools_grid.add_widget(
                        Label(text=f"Max {max_val}", font_size='16sp', size_hint_x=0.3, size_hint_y=None, height='30dp')
                    )
