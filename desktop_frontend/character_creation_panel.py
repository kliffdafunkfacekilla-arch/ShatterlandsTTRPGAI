from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner

class CharacterCreationPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_widget(Label(text='Create New Character'))
        self.name_input = TextInput(hint_text='Name')
        self.add_widget(self.name_input)
        self.kingdom_input = TextInput(hint_text='Kingdom')
        self.add_widget(self.kingdom_input)
        # Feature choices (9 spinners for F1-F9, using talents)
        from kivy.uix.spinner import Spinner
        import json
        # Load real choices from JSON files
        with open('../../AI-TTRPG/rules_engine/data/talents.json', 'r') as f:
            talents_data = json.load(f)
        talent_names = [t['talent_name'] for t in talents_data['single_stat_mastery']]
        self.feature_spinners = []
        for i in range(1, 10):
            spinner = Spinner(
                text=f'Feature {i}',
                values=talent_names,
                size_hint_y=None,
                height=40
            )
            self.feature_spinners.append(spinner)
            self.add_widget(spinner)
        # Origin, childhood, coming of age, training, devotion
        with open('../../AI-TTRPG/rules_engine/data/origin_choices.json', 'r') as f:
            origin_choices = json.load(f)
        self.origin_spinner = Spinner(
            text='Origin Choice',
            values=[o['name'] for o in origin_choices],
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.origin_spinner)
        with open('../../AI-TTRPG/rules_engine/data/childhood_choices.json', 'r') as f:
            childhood_choices = json.load(f)
        self.childhood_spinner = Spinner(
            text='Childhood Choice',
            values=[c['name'] for c in childhood_choices],
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.childhood_spinner)
        with open('../../AI-TTRPG/rules_engine/data/coming_of_age_choices.json', 'r') as f:
            coming_of_age_choices = json.load(f)
        self.coming_of_age_spinner = Spinner(
            text='Coming of Age Choice',
            values=[c['name'] for c in coming_of_age_choices],
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.coming_of_age_spinner)
        with open('../../AI-TTRPG/rules_engine/data/training_choices.json', 'r') as f:
            training_choices = json.load(f)
        self.training_spinner = Spinner(
            text='Training Choice',
            values=[t['name'] for t in training_choices],
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.training_spinner)
        with open('../../AI-TTRPG/rules_engine/data/devotion_choices.json', 'r') as f:
            devotion_choices = json.load(f)
        self.devotion_spinner = Spinner(
            text='Devotion Choice',
            values=[d['name'] for d in devotion_choices],
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.devotion_spinner)
        # Ability school and talent
        self.ability_school_input = TextInput(hint_text='Ability School')
        self.add_widget(self.ability_school_input)
        self.ability_talent_spinner = Spinner(
            text='Ability Talent',
            values=talent_names,
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.ability_talent_spinner)
        self.submit_btn = Button(text='Create Character')
        self.submit_btn.bind(on_release=self.create_character)
        self.add_widget(self.submit_btn)

    def create_character(self, instance):
        import requests
        # Collect all input data
        name = self.name_input.text
        kingdom = self.kingdom_input.text
        feature_choices = []
        for i, spinner in enumerate(self.feature_spinners):
            feature_choices.append({
                "feature_id": f"F{i+1}",
                "choice_name": spinner.text
            })
        origin_choice = self.origin_spinner.text
        childhood_choice = self.childhood_spinner.text
        coming_of_age_choice = self.coming_of_age_spinner.text
        training_choice = self.training_spinner.text
        devotion_choice = self.devotion_spinner.text
        ability_school = self.ability_school_input.text
        ability_talent = self.ability_talent_spinner.text
        # Build payload
        payload = {
            "name": name,
            "kingdom": kingdom,
            "feature_choices": feature_choices,
            "origin_choice": origin_choice,
            "childhood_choice": childhood_choice,
            "coming_of_age_choice": coming_of_age_choice,
            "training_choice": training_choice,
            "devotion_choice": devotion_choice,
            "ability_school": ability_school,
            "ability_talent": ability_talent
        }
        # Send to backend (update URL as needed)
        url = "http://localhost:8000/api/character/create"
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print("Character created successfully!")
            else:
                print(f"Error: {response.status_code}", response.text)
        except Exception as e:
            print(f"Request failed: {e}")
