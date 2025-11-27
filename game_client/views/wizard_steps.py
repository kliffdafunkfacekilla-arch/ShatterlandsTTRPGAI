from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.factory import Factory
from kivy.properties import ObjectProperty, StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock
import logging

class WizardStep(BoxLayout):
    """Base class for a wizard step."""
    title = StringProperty("Step Title")
    is_valid = BooleanProperty(False)

    def __init__(self, wizard, **kwargs):
        super().__init__(**kwargs)
        self.wizard = wizard
        self.orientation = 'vertical'
        self.padding = '20dp'
        self.spacing = '10dp'

    def on_enter(self):
        """Called when the step is shown."""
        pass

    def get_data(self):
        """Return data collected in this step."""
        return {}

class IdentityStep(WizardStep):
    """Step 1: Name and Kingdom."""
    title = StringProperty("Identity")

    def __init__(self, wizard, **kwargs):
        super().__init__(wizard, **kwargs)
        
        # Name
        self.add_widget(Factory.DarkTextLabel(text="Character Name:", size_hint_y=None, height='30dp'))
        self.name_input = Factory.TextInput(multiline=False, size_hint_y=None, height='40dp')
        self.name_input.bind(text=self.validate)
        self.add_widget(self.name_input)

        # Kingdom
        self.add_widget(Factory.DarkTextLabel(text="Select Kingdom:", size_hint_y=None, height='30dp'))
        
        # Kingdom Description & Image Area
        self.info_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='150dp', spacing='10dp')
        
        # Placeholder Image - Use a solid color or transparent for now if no asset
        self.kingdom_image = Image(source='', size_hint_x=0.3, allow_stretch=True, keep_ratio=True)
        self.kingdom_image.color = (0.5, 0.5, 0.5, 1) # Grey placeholder
        self.info_layout.add_widget(self.kingdom_image)
        
        # Description
        self.desc_label = Label(text="Select a kingdom to see details.", text_size=(None, None), halign='left', valign='top', color=(0,0,0,1))
        self.info_layout.add_widget(self.desc_label)
        
        self.add_widget(self.info_layout)

        # Kingdom Spinner
        self.kingdom_spinner = Spinner(text='Select Kingdom...', values=('Loading...',), size_hint_y=None, height='44dp')
        self.kingdom_spinner.bind(text=self.on_kingdom_select)
        self.add_widget(self.kingdom_spinner)
        
        # Debug Button
        debug_btn = Button(text="Test Click", size_hint_y=None, height='30dp')
        debug_btn.bind(on_release=lambda x: print("DEBUG: Test Button Clicked"))
        self.add_widget(debug_btn)
        
        self.add_widget(BoxLayout(size_hint_y=1)) # Spacer

    def on_enter(self):
        # Populate kingdoms if available
        print(f"DEBUG: IdentityStep.on_enter called. Rules Data Keys: {self.wizard.rules_data.keys()}")
        if self.wizard.rules_data:
            kingdoms = self.wizard.rules_data.get('kingdoms', [])
            print(f"DEBUG: Kingdoms found: {kingdoms}")
            
            if not kingdoms:
                print("DEBUG: Kingdoms list is empty! Using fallback.")
                kingdoms = ['Fallback Mammal', 'Fallback Reptile']
            
            self.kingdom_spinner.values = tuple(kingdoms)
            if kingdoms and self.kingdom_spinner.text == 'Select Kingdom...':
                 self.kingdom_spinner.text = kingdoms[0]

    def on_kingdom_select(self, spinner, text):
        # Update description and image
        desc_map = {
            "Mammal": "Evolved from warm-blooded beasts. Known for fur or hair and adaptability. Found in diverse habitats from forests to plains.",
            "Reptile": "Evolved from cold-blooded scaled creatures. Features tough scales and patience. Thrives in deserts, swamps, and warm climates.",
            "Avian": "Evolved from birds of prey and songbirds. Features feathers and lightweight bones. Inhabits high altitudes, cliffs, and arboreal cities.",
            "Aquatic": "Evolved from water-dwelling creatures. Features smooth skin or gills. Inhabits coastal regions, islands, and underwater enclaves.",
            "Insect": "Evolved from arthropods. Features protective exoskeletons and compound eyes. Builds complex hives in forests and underground.",
            "Plant": "Evolved from sentient flora. Features bark-like skin and leafy appendages. Rooted in deep forests, jungles, and verdant groves."
        }
        self.desc_label.text = desc_map.get(text, "A unique kingdom of the Shatterlands.")
        # self.kingdom_image.source = f"game_client/assets/graphics/kingdoms/{text.lower()}.png" # Future
        self.validate()

    def validate(self, *args):
        self.is_valid = bool(self.name_input.text and self.kingdom_spinner.text != 'Select Kingdom...')

    def get_data(self):
        return {
            "name": self.name_input.text,
            "kingdom": self.kingdom_spinner.text
        }

class FeatureStep(WizardStep):
    """Generic Step for Features F1-F8."""
    
    def __init__(self, wizard, feature_key, **kwargs):
        super().__init__(wizard, **kwargs)
        self.feature_key = feature_key
        self.title = f"Feature {feature_key[1:]}" # e.g. "Feature 1"
        self.selected_choice = None
        
        self.scroll = ScrollView(size_hint=(1, 1))
        self.options_layout = GridLayout(cols=1, spacing='10dp', size_hint_y=None, padding='10dp')
        self.options_layout.bind(minimum_height=self.options_layout.setter('height'))
        self.scroll.add_widget(self.options_layout)
        self.add_widget(self.scroll)

    def on_enter(self):
        self.options_layout.clear_widgets()
        kingdom = self.wizard.collected_data.get('kingdom')
        if not kingdom:
            return

        # Fetch features for this kingdom and key
        # We need to access the raw data structure because rules_api.get_features_for_kingdom returns names only
        # We want modifiers too.
        # So we'll access wizard.rules_data['kingdom_features_data'] directly if possible
        # Or use the loaded features from the previous screen?
        # The wizard should have access to the full data.
        
        kf_data = self.wizard.rules_data.get('kingdom_features_data', {})
        f_data = kf_data.get(self.feature_key, {})
        options = f_data.get(kingdom, [])
        if not options and "All" in f_data:
            options = f_data["All"]

        for opt in options:
            name = opt.get('name', 'Unknown')
            mods = opt.get('mods', {})
            
            # Format description from mods
            mod_strs = []
            for val, stats in mods.items():
                mod_strs.append(f"{val} to {', '.join(stats)}")
            desc = "; ".join(mod_strs)
            
            # Create a selectable card
            btn = Factory.DungeonButton(text=f"{name}\n[size=14sp]{desc}[/size]", size_hint_y=None, height='80dp', halign='center')
            btn.bind(on_release=lambda inst, n=name: self.select_option(inst, n))
            self.options_layout.add_widget(btn)

    def select_option(self, btn, name):
        # Visual feedback (reset others, highlight this one)
        for child in self.options_layout.children:
            child.background_color = (0.2, 0.15, 0.1, 1) # Default
        btn.background_color = (0.4, 0.3, 0.2, 1) # Highlight
        
        self.selected_choice = name
        self.is_valid = True

    def get_data(self):
        return {self.feature_key: self.selected_choice}

class CapstoneStep(WizardStep):
    """Step 10: Capstone Point Allocation."""
    title = StringProperty("Capstone: Shore Up Weaknesses")
    
    def __init__(self, wizard, **kwargs):
        super().__init__(wizard, **kwargs)
        self.points_remaining = 4
        self.temp_stats = {}
        
        self.header = Label(text=f"Points Remaining: {self.points_remaining}\n(Can only boost stats under 10)", size_hint_y=None, height='50dp')
        self.add_widget(self.header)
        
        self.stats_grid = GridLayout(cols=2, spacing='10dp', size_hint_y=1)
        self.add_widget(self.stats_grid)

    def on_enter(self):
        self.points_remaining = 4
        self.temp_stats = self.wizard.calculate_current_stats() # Calculate stats based on previous choices
        self.base_stats = self.temp_stats.copy() # Snapshot for limits
        self.update_grid()
        self.validate()

    def update_grid(self):
        self.stats_grid.clear_widgets()
        self.header.text = f"Points Remaining: {self.points_remaining}\n(Can only boost stats under 10)"
        
        for stat, value in self.temp_stats.items():
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp')
            name_lbl = Label(text=f"{stat}: {value}", color=(1, 0.5, 0.5, 1) if value < 10 else (1, 1, 1, 1))
            
            btn_add = Button(text="+", size_hint_x=None, width='40dp')
            # Enable only if points > 0 AND current value < 10
            if self.points_remaining > 0 and value < 10:
                btn_add.disabled = False
                btn_add.bind(on_release=lambda inst, s=stat: self.add_point(s))
            else:
                btn_add.disabled = True
                
            box.add_widget(name_lbl)
            box.add_widget(btn_add)
            self.stats_grid.add_widget(box)

    def add_point(self, stat):
        if self.points_remaining > 0 and self.temp_stats[stat] < 10:
            self.temp_stats[stat] += 1
            self.points_remaining -= 1
            self.update_grid()
            self.validate()

    def validate(self, *args):
        # Valid if all points spent? Or optional? User said "add 4 points". I'll enforce spending all 4 if possible.
        # But what if no stats are < 10? Then we can't spend points.
        # So valid if points == 0 OR (points > 0 but no eligible stats)
        has_eligible = any(v < 10 for v in self.temp_stats.values())
        self.is_valid = (self.points_remaining == 0) or (not has_eligible)

    def get_data(self):
        # Return the final stats or the modifications?
        # The wizard will likely just use the final stats or we store the capstone choices.
        # For now, we'll store the final stats in the wizard context if needed, or just the fact we are done.
        return {"capstone_stats": self.temp_stats}

class BackgroundStep(WizardStep):
    """Generic Step for Backgrounds (Origin, Childhood, etc.)."""
    
    def __init__(self, wizard, key, title, **kwargs):
        super().__init__(wizard, **kwargs)
        self.data_key = key # e.g. 'origins'
        self.title = title
        self.selected_choice = None
        
        self.scroll = ScrollView(size_hint=(1, 1))
        self.options_layout = GridLayout(cols=1, spacing='10dp', size_hint_y=None, padding='10dp')
        self.options_layout.bind(minimum_height=self.options_layout.setter('height'))
        self.scroll.add_widget(self.options_layout)
        self.add_widget(self.scroll)

    def on_enter(self):
        self.options_layout.clear_widgets()
        options = self.wizard.rules_data.get(self.data_key, [])
        
        for opt in options:
            name = opt.get('name', 'Unknown')
            desc = opt.get('description', 'No description available.')
            
            # Card with Name and Description
            btn = Factory.DungeonButton(text=f"{name}\n[size=14sp]{desc}[/size]", size_hint_y=None, height='100dp', halign='center')
            btn.bind(on_release=lambda inst, n=name: self.select_option(inst, n))
            self.options_layout.add_widget(btn)

    def select_option(self, btn, name):
        for child in self.options_layout.children:
            child.background_color = (0.2, 0.15, 0.1, 1)
        btn.background_color = (0.4, 0.3, 0.2, 1)
        self.selected_choice = name
        self.is_valid = True

    def get_data(self):
        # Map data_key to submission key
        # origins -> origin
        # childhoods -> childhood
        # coming_of_ages -> coming_of_age
        # trainings -> training
        # devotions -> devotion
        key_map = {
            'origins': 'origin',
            'childhoods': 'childhood',
            'coming_of_ages': 'coming_of_age',
            'trainings': 'training',
            'devotions': 'devotion'
        }
        return {key_map.get(self.data_key, self.data_key): self.selected_choice}

class FinalStep(WizardStep):
    """Talent, School, and Finish."""
    title = StringProperty("Final Touches")
    
    def __init__(self, wizard, **kwargs):
        super().__init__(wizard, **kwargs)
        
        self.add_widget(Label(text="Select Starting Talent:", size_hint_y=None, height='30dp'))
        self.talent_spinner = Spinner(text='Select Talent...', values=(), size_hint_y=None, height='44dp')
        self.talent_spinner.bind(text=self.check_valid)
        self.add_widget(self.talent_spinner)

        self.add_widget(Label(text="Select Ability School:", size_hint_y=None, height='30dp'))
        self.school_spinner = Spinner(text='Select School...', values=(), size_hint_y=None, height='44dp')
        self.school_spinner.bind(text=self.check_valid)
        self.add_widget(self.school_spinner)
        
        self.add_widget(BoxLayout(size_hint_y=1))

    def on_enter(self):
        # Populate based on rules
        # For now, just load all available
        if self.wizard.rules_data:
            self.talent_spinner.values = tuple(self.wizard.rules_data.get('talents', [])) or ('No Talents',)
            self.school_spinner.values = tuple(self.wizard.rules_data.get('schools', [])) or ('No Schools',)
            
            if self.talent_spinner.values: self.talent_spinner.text = self.talent_spinner.values[0]
            if self.school_spinner.values: self.school_spinner.text = self.school_spinner.values[0]
            self.check_valid()

    def check_valid(self, *args):
        self.is_valid = (self.talent_spinner.text != 'Select Talent...' and self.school_spinner.text != 'Select School...')

    def get_data(self):
        return {
            "ability_talent": self.talent_spinner.text,
            "ability_school": self.school_spinner.text
        }
