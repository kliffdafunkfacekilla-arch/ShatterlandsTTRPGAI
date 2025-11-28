# game_client/views/inventory_screen.py
import logging
import asyncio
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
from kivy.clock import Clock

# Import UI utilities
from game_client.ui_utils import show_error, show_success

# Use RuleSetContainer for item data
from monolith.modules.rules_pkg.data_loader_enhanced import RuleSetContainer

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
        char_context = app.active_character_context
        if not char_context:
            logging.error("INVENTORY: No character context found!")
            return

        self.ids.char_name_label.text = f"{char_context.name}'s Inventory"
        self.populate_lists(char_context)

    def populate_lists(self, context):
        self.ids.equipment_list.clear_widgets()
        self.ids.inventory_list.clear_widgets()

        # Populate Equipment
        equipment = context.equipment or {}
        for slot, item_id in equipment.items():
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height='44dp')
            box.add_widget(Label(text=f"{slot.title()}: {item_id}"))
            unequip_btn = Button(text="Unequip", size_hint_x=0.3)
            unequip_btn.bind(on_release=partial(self.on_unequip_item, context.id, slot))
            box.add_widget(unequip_btn)
            self.ids.equipment_list.add_widget(box)

        # Populate Inventory
        inventory = context.inventory or {}
        for item_id, quantity in inventory.items():
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height='44dp')
            box.add_widget(Label(text=f"{item_id} (x{quantity})"))
            equip_btn = Button(text="Equip", size_hint_x=0.3)
            equip_btn.bind(on_release=partial(self.on_equip_item, context.id, item_id))
            box.add_widget(equip_btn)
            self.ids.inventory_list.add_widget(box)

    def on_equip_item(self, char_id, item_id, *args):
        logging.info(f"Equipping {item_id} for {char_id}")
        
        # Use RuleSetContainer to get item details
        rules = RuleSetContainer()
        # Note: In a real implementation, we'd have a proper item database.
        # For now, we'll infer slot from item name or use a default if not found
        # Or check if rules has item templates
        
        # Simple heuristic for now if rules doesn't have it
        slot = "hand" # Default
        if "sword" in item_id.lower() or "axe" in item_id.lower():
            slot = "weapon"
        elif "armor" in item_id.lower() or "mail" in item_id.lower():
            slot = "armor"
        elif "shield" in item_id.lower():
            slot = "offhand"
            
        # Try to get from rules if possible (assuming get_item exists or similar)
        # template = rules.get_item(item_id)
        # if template: slot = template.get("slot", slot)

        app = App.get_running_app()
        
        try:
            # Use Orchestrator
            result = asyncio.run(
                app.orchestrator.handle_player_action(
                    player_id=char_id,
                    action_type="EQUIP",
                    item_id=item_id,
                    slot=slot
                )
            )
            
            if result.get("success"):
                # Update local context
                updated_char = result.get("character")
                if updated_char:
                    app.active_character_context = updated_char
                    self.on_enter() # Refresh UI
                    show_success(f"Equipped {item_id}")
            else:
                show_error("Equip Failed", result.get("error", "Unknown error"))
                
        except Exception as e:
            logging.exception(f"Equip error: {e}")
            show_error("Equip Error", str(e))

    def on_unequip_item(self, char_id: str, slot: str, *args):
        logging.info(f"Unequipping item from {slot} for {char_id}")
        
        app = App.get_running_app()
        
        try:
            # Use Orchestrator
            result = asyncio.run(
                app.orchestrator.handle_player_action(
                    player_id=char_id,
                    action_type="UNEQUIP",
                    slot=slot
                )
            )
            
            if result.get("success"):
                # Update local context
                updated_char = result.get("character")
                if updated_char:
                    app.active_character_context = updated_char
                    self.on_enter() # Refresh UI
                    show_success(f"Unequipped {slot}")
            else:
                show_error("Unequip Failed", result.get("error", "Unknown error"))
                
        except Exception as e:
            logging.exception(f"Unequip error: {e}")
            show_error("Unequip Error", str(e))
