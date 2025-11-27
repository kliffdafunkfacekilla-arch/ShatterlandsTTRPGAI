import sys
import os
import logging
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from kivy.clock import Clock
from kivy.base import EventLoop

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'AI-TTRPG')))

# Mock Monolith Modules
class MockRules:
    def get_talent_details(self, name):
        return {"effect": "Test Effect", "modifiers": []}

class MockContext:
    def __init__(self):
        self.name = "Test Char"
        self.level = 1
        self.kingdom = "Test Kingdom"
        self.stats = {"Strength": 10}
        self.skills = {"Athletics": {"rank": 1}}
        self.talents = ["Test Talent"]
        self.abilities = ["Test Ability"]
        self.resource_pools = {"Health": {"current": 10, "max": 10}}

# Mock App
class TestApp(App):
    def build(self):
        self.active_character_context = MockContext()
        sm = ScreenManager()
        
        # Import View
        from game_client.views.character_sheet_screen import CharacterSheetScreen
        # Inject mock rules
        import game_client.views.character_sheet_screen as css
        css.rules_api = MockRules()
        
        screen = CharacterSheetScreen(name='character_sheet')
        sm.add_widget(screen)
        return sm

    def on_start(self):
        Clock.schedule_once(self.test_crash, 1)

    def test_crash(self, dt):
        print("Testing Character Sheet Load...")
        try:
            screen = self.root.get_screen('character_sheet')
            screen.on_enter()
            print("SUCCESS: Character Sheet loaded without crash.")
        except Exception as e:
            print(f"CRASH DETECTED: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()

if __name__ == '__main__':
    TestApp().run()
