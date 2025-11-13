from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput

class CharacterSheetPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_widget(Label(text='Character Sheet'))
        self.add_widget(Label(text='Name: Demo Adventurer'))
        self.add_widget(Label(text='Class: Warrior'))
        self.add_widget(Label(text='Level: 3'))
        self.add_widget(Label(text='HP: 24/30'))
        self.add_widget(Label(text='Stats:'))
        stats = [
            "Might", "Endurance", "Finesse", "Reflexes", "Vitality", "Fortitude",
            "Knowledge", "Logic", "Awareness", "Intuition", "Charm", "Willpower"
        ]
        for stat in stats:
            self.add_widget(Label(text=f"  {stat}: [value]"))
        self.add_widget(Label(text='Skills:'))
        skill_categories = {
            "Conversational": ["Intimidation", "Resilience", "Slight of Hand", "Evasion", "Comfort", "Discipline", "Debate", "Rhetoric", "Insight", "Empathy", "Persuasion", "Negotiations"],
            "Utility": ["Labor", "Security", "Artifice", "Kinetics", "Provisioning", "Environment", "Scholarship", "Ingenuity", "Investigation", "Thaumaturgy", "Expression", "Coordination"],
        }
        for cat, skills in skill_categories.items():
            self.add_widget(Label(text=f"{cat} Skills:"))
            for skill in skills:
                self.add_widget(Label(text=f"  {skill}: [linked stat]"))

class InventoryPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_widget(Label(text='Inventory'))
        items = [
            {"name": "Iron Sword", "type": "melee", "category": "Double/dual wield"},
            {"name": "Iron Axe", "type": "melee", "category": "Great Weapons"},
            {"name": "Short Bow", "type": "ranged", "category": "Bows and Firearms"},
            {"name": "Leather Jerkin", "type": "armor", "category": "Leather/Hides"},
            {"name": "Iron Plate", "type": "armor", "category": "Plate Armor"},
            {"name": "Brawling Gloves", "type": "melee", "category": "Brawling Weapons"},
            {"name": "Iron Key", "type": "key", "category": "quest"},
        ]
        for item in items:
            self.add_widget(Label(text=f"- {item['name']} ({item['type']}, {item['category']})"))
        self.add_widget(Button(text='Use Item'))
        self.add_widget(Button(text='Drop Item'))

class MapPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_widget(Label(text='Map Display'))
        # Placeholder for Arcade/Pygame integration

class NarrationPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_widget(Label(text='Narration / Dialogue'))
        # Add scrolling text or dialogue options here

class SystemLogPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_widget(Label(text='System Log'))
        # Add dice roll and game info log here

class HUDPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.add_widget(Label(text='Turn:'))
        self.add_widget(Label(text='Health:'))
        self.add_widget(Label(text='Status:'))
        # Add more HUD elements as needed

class ControlPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.add_widget(Label(text='Player Input:'))
        self.input_field = TextInput(hint_text='Enter command or action')
        self.add_widget(self.input_field)
        self.add_widget(Button(text='Send'))

# --- LORE PANEL ---
import requests
class LorePanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_widget(Label(text='Lore'))
        self.lore_entries = []
        self.refresh_lore()

    def refresh_lore(self):
        try:
            resp = requests.get('http://127.0.0.1:8005/v1/lore')
            if resp.status_code == 200:
                self.lore_entries = resp.json()
                for entry in self.lore_entries:
                    self.add_widget(Label(text=f"{entry['title']} ({entry['type']})"))
            else:
                self.add_widget(Label(text='Failed to load lore.'))
        except Exception as e:
            self.add_widget(Label(text=f'Error: {e}'))
