"""
Inventory & Equipment Screen
Allows the player to see their inventory and equip/unequip items.
"""
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

# --- Monolith Imports ---
try:
    from monolith.modules import character as character_api
    from monolith.modules import rules as rules_api
    from monolith.modules.character_pkg.schemas import CharacterContextResponse
except ImportError as e:
    logging.error(f"INVENTORY_SCREEN: Failed to import monolith modules: {e}")
    character_api = None
    rules_api = None
    CharacterContextResponse = None

# --- Kivy Language (KV) String ---
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

# Load the KV string
Builder.load_string(INVENTORY_SCREEN_KV)

class InventoryScreen(Screen):
    # Kivy properties to hold widget references
    char_name_label = ObjectProperty(None)
    equipment_list = ObjectProperty(None)
    inventory_list = ObjectProperty(None)

    def on_enter(self, *args):
        """Called when this screen is shown. Fetches data and populates UI."""
        app = App.get_running_app()
        main_screen = app.root.get_screen('main_interface')
        char_context = main_screen.active_character_context

        if not char_context:
            logging.error("INVENTORY_SCREEN: No active character context found!")
            if self.ids.char_name_label:
                self.ids.char_name_label.text = "Error: No Character Loaded"
            return

        if self.ids.char_name_label:
            self.ids.char_name_label.text = f"{char_context.name}'s Inventory"

        self.populate_lists(char_context)

    def populate_lists(self, context: CharacterContextResponse):
        """Fills the equipment and inventory lists."""
        if not self.ids:
            return

        equipment_container = self.ids.equipment_list
        inventory_container = self.ids.inventory_list

        equipment_container.clear_widgets()
        inventory_container.clear_widgets()

        if not rules_api or not character_api:
            logging.error("INVENTORY_SCREEN: Missing rules_api or character_api.")
            return

        # --- Populate Equipment ---
        for slot, item_id in context.equipment.items():
            if not item_id:
                continue

            item_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='44dp')

            try:
                template = rules_api.get_item_template_params(item_id)
                item_name = template.get("name", item_id)
            except Exception:
                item_name = item_id

            item_label = Label(text=f"{slot.title()}: {item_name}")
            unequip_btn = Button(text='Unequip', size_hint_x=0.3)

            # TODO: Add unequip logic (more complex, involves finding empty inv slot or stacking)
            # unequip_btn.bind(on_release=partial(self.on_unequip_item, context.id, slot))

            item_box.add_widget(item_label)
            item_box.add_widget(unequip_btn)
            equipment_container.add_widget(item_box)

        # --- Populate Inventory ---
        for item_id, quantity in context.inventory.items():
            if quantity <= 0:
                continue

            item_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='44dp')

            try:
                template = rules_api.get_item_template_params(item_id)
                item_name = template.get("name", item_id)
                item_type = template.get("type", "misc")
            except Exception:
                item_name = item_id
                item_type = "misc"

            item_label = Label(text=f"{item_name} (x{quantity})")
            equip_btn = Button(text='Equip', size_hint_x=0.3)

            if item_type in ("melee", "ranged", "armor"):
                equip_btn.bind(on_release=partial(self.on_equip_item, context.id, item_id, item_type))
            else:
                equip_btn.disabled = True

            item_box.add_widget(item_label)
            item_box.add_widget(equip_btn)
            inventory_container.add_widget(item_box)

    def on_equip_item(self, char_id: str, item_id: str, item_type: str, *args):
        """Handles the 'Equip' button press."""
        logging.info(f"Attempting to equip {item_id} (type: {item_type}) for {char_id}")

        slot = None
        if item_type in ("melee", "ranged"):
            slot = "weapon"
        elif item_type == "armor":
            slot = "armor"

        if not slot:
            logging.warning(f"Item {item_id} has no valid equipment slot.")
            return

        try:
            # Call the backend API
            new_context_dict = character_api.equip_item(char_id, item_id, slot)

            # CRITICAL: Update the main interface's context
            app = App.get_running_app()
            main_screen = app.root.get_screen('main_interface')

            # Re-create the Pydantic model from the new dict
            if CharacterContextResponse:
                main_screen.active_character_context = CharacterContextResponse(**new_context_dict)

            # Refresh this screen
            self.on_enter()

        except Exception as e:
            logging.exception(f"Failed to equip item: {e}")
