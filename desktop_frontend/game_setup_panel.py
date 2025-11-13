from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

class GameSetupPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_widget(Label(text='Game Setup'))
        # Party selection
        self.add_widget(Label(text='Select Party Members'))
        import requests
        try:
            response = requests.get('http://localhost:8000/api/character/list')
            if response.status_code == 200:
                char_list = response.json()
                char_names = [c['name'] for c in char_list]
            else:
                char_names = ['No characters found']
        except Exception as e:
            char_names = [f'Error: {e}']
        self.party_spinner = Spinner(text='Party Member', values=char_names, size_hint_y=None, height=40)
        self.add_widget(self.party_spinner)
        self.new_char_btn = Button(text='Create New Character')
        self.add_widget(self.new_char_btn)
        self.new_char_btn.bind(on_release=self.open_character_creation)
        # Game settings
        self.add_widget(Label(text='Difficulty'))
        self.difficulty_spinner = Spinner(text='Normal', values=['Easy', 'Normal', 'Hard', 'Nightmare'], size_hint_y=None, height=40)
        self.add_widget(self.difficulty_spinner)
        self.add_widget(Label(text='Combat Amount'))
        self.combat_spinner = Spinner(text='Balanced', values=['None', 'Low', 'Balanced', 'High', 'Constant'], size_hint_y=None, height=40)
        self.add_widget(self.combat_spinner)
        self.add_widget(Label(text='Game Style'))
        self.style_spinner = Spinner(text='Epic', values=['Intrigue', 'Cute', 'Epic', 'Bloody', 'Horrifying'], size_hint_y=None, height=40)
        self.add_widget(self.style_spinner)
        self.add_widget(Label(text='Death Setting'))
        self.death_spinner = Spinner(text='Normal', values=['Undead', 'Normal', 'Perma Death'], size_hint_y=None, height=40)
        self.add_widget(self.death_spinner)

        # Start location selection with scenario blurbs
        self.add_widget(Label(text='Start Location / Scenario'))
        self.start_locations = {
            'Caravan Guard': 'You joined a caravan as a guard to escape your past and have arrived in a town far from your old life.',
            'Letter Delivery': 'Tasked to deliver a letter, you sailed to a port in the north to find its recipient.',
            'Wilderness Refuge': 'You and your companions are hiding out in the deep woods, seeking safety from pursuers.',
            'Festival Arrival': 'You arrive in a bustling town during a festival, blending in with the crowds.',
            'Mercenary Contract': 'Hired as mercenaries, you and your party are stationed at a border outpost.'
        }
        self.start_location_spinner = Spinner(
            text='Choose Scenario',
            values=list(self.start_locations.keys()),
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.start_location_spinner)
        self.scenario_blurb = Label(text='', size_hint_y=None, height=60)
        self.add_widget(self.scenario_blurb)
        self.start_location_spinner.bind(text=self.update_blurb)

        self.start_btn = Button(text='Start Game')
        self.add_widget(self.start_btn)
        self.start_btn.bind(on_release=self.start_game)

    def update_blurb(self, spinner, text):
        self.scenario_blurb.text = self.start_locations.get(text, '')

    def open_character_creation(self, instance):
        # Switch to character creation screen
        self.parent.parent.manager.current = 'character_creation'

    def start_game(self, instance):
        # Save/apply game settings and transition to main interface
        selected_party = self.party_spinner.text
        difficulty = self.difficulty_spinner.text
        combat = self.combat_spinner.text
        style = self.style_spinner.text
        death = self.death_spinner.text
        start_location = self.start_location_spinner.text
        scenario_blurb = self.scenario_blurb.text
        # Save settings (could POST to backend or store locally)
        settings = {
            'party': selected_party,
            'difficulty': difficulty,
            'combat': combat,
            'style': style,
            'death': death,
            'start_location': start_location,
            'scenario_blurb': scenario_blurb
        }
        print('Game settings:', settings)
        # Transition to main game interface
        self.parent.parent.manager.current = 'main_interface'
