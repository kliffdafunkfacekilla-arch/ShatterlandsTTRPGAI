# game_client/views/inventory_screen.py
import logging
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import ObjectProperty
from functools import partial

# --- Direct Monolith Imports ---
try:
    from monolith.modules import character as character_api
    from monolith.modules import rules as rules_api
except ImportError as e:
    logging.error(f"INVENTORY: Failed to import monolith modules: {e}")
    character_api = None
    rules_api = None

INVENTORY_SCREEN_KV = """
<InventoryScreen>:
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
                text: 'Inventory'
                font_size: '24sp'
            Button:
                text: 'Back to Game'
                size_hint_x: 0.3
                on_release: app.root.current = 'main_interface'

        # --- Main Content Area ---
        BoxLayout:
            orientation: 'horizontal'
            padding: '10dp'
            spacing: '10dp'

            # --- Equipped Items Panel ---
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.4
                Label:
                    text: 'Equipped'
                    font_size: '20sp'
                    size_hint_y: None
                    height: '30dp'
                GridLayout:
                    id: equipment_list
                    cols: 1
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: '5dp'
                Label: # Spacer
                    text: ''

            # --- Inventory Panel ---
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.6
                Label:
                    text: 'Inventory'
                    font_size: '20sp'
                    size_hint_y: None
                    height: '30dp'
                ScrollView:
                    GridLayout:
                        id: inventory_list
                        cols: 1
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: '5dp'
"""

Builder.load_string(INVENTORY_SCREEN_KV)

class InventoryScreen(Screen):
    char_name_label = ObjectProperty(None)
    equipment_list = ObjectProperty(None)
    inventory_list = ObjectProperty(None)

    def on_enter(self, *args):
        app = App.get_running_app()
        main_screen = app.root.get_screen('main_interface')
        char_context = main_screen.active_character_context
        if not char_context:
            logging.error("INVENTORY: No character context found!")
            return

        self.ids.char_name_label.text = f"{char_context.name}'s Inventory"
        self.populate_lists(char_context)

    def populate_lists(self, context):
        self.ids.equipment_list.clear_widgets()
        self.ids.inventory_list.clear_widgets()

        # Populate Equipment
        for slot, item_id in context.equipment.items():
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height='44dp')
            box.add_widget(Label(text=f"{slot.title()}: {item_id}"))
            unequip_btn = Button(text="Unequip", size_hint_x=0.3)
            # unequip_btn.bind(on_release=partial(self.on_unequip_item, context.id, slot))
            box.add_widget(unequip_btn)
            self.ids.equipment_list.add_widget(box)

        # Populate Inventory
        for item_id, quantity in context.inventory.items():
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height='44dp')
            box.add_widget(Label(text=f"{item_id} (x{quantity})"))
            equip_btn = Button(text="Equip", size_hint_x=0.3)
            equip_btn.bind(on_release=partial(self.on_equip_item, context.id, item_id))
            box.add_widget(equip_btn)
            self.ids.inventory_list.add_widget(box)

    def on_equip_item(self, char_id, item_id, *args):
        logging.info(f"Equipping {item_id} for {char_id}")
        if not rules_api:
            logging.error("Rules API not available.")
            return

        template = rules_api.get_item_template_params(item_id)
        item_type = template.get("type")

        if item_type == "weapon":
            slot = "weapon"
        elif item_type == "armor":
            slot = "armor"
        else:
            logging.error(f"Item {item_id} is not equippable.")
            return

        new_context_dict = character_api.equip_item(char_id, item_id, slot)

        main_screen = App.get_running_app().root.get_screen('main_interface')
        context_schema = main_screen.active_character_context.__class__
        main_screen.active_character_context = context_schema(**new_context_dict)

        self.on_enter()
