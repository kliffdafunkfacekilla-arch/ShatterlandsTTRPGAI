# game_client/views/shop_screen.py
import logging
import asyncio
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

from game_client.utils import AsyncHelper
from game_client.ui_utils import show_error, show_success

# --- Monolith Imports ---
try:
    from monolith.modules import story as story_api
except ImportError as e:
    logging.error(f"SHOP_SCREEN: Failed to import monolith modules: {e}")
    story_api = None

SHOP_SCREEN_KV = """
<ShopScreen>:
    shop_inventory_container: shop_inventory_container
    player_inventory_container: player_inventory_container
    player_currency_label: player_currency_label

    BoxLayout:
        orientation: 'vertical'
        padding: '20dp'
        spacing: '20dp'

        Label:
            text: 'Shop'
            font_size: '24sp'
            size_hint_y: 0.1

        BoxLayout:
            orientation: 'horizontal'
            spacing: '20dp'

            # Shop Inventory
            BoxLayout:
                orientation: 'vertical'
                Label:
                    text: 'Shop Inventory'
                ScrollView:
                    BoxLayout:
                        id: shop_inventory_container
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height

            # Player Inventory
            BoxLayout:
                orientation: 'vertical'
                Label:
                    text: 'Your Inventory'
                Label:
                    id: player_currency_label
                    text: 'Currency: 0'
                ScrollView:
                    BoxLayout:
                        id: player_inventory_container
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height

        Button:
            text: 'Back to Game'
            size_hint_y: 0.1
            on_release: app.root.current = 'main_interface'
"""
Builder.load_string(SHOP_SCREEN_KV)

class ShopScreen(Screen, AsyncHelper):
    shop_inventory_container = ObjectProperty(None)
    player_inventory_container = ObjectProperty(None)
    player_currency_label = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shop_id = "willows_wares" # Hardcoded for now

    def on_enter(self, *args):
        """Called when the screen is entered."""
        self.update_inventories()

    def update_inventories(self):
        """Updates both the shop and player inventories."""
        if not story_api:
            return

        # Update Shop Inventory
        self.shop_inventory_container.clear_widgets()
        try:
            shop_inventory = story_api.get_shop_inventory(self.shop_id)
            for item_id, item_data in shop_inventory["inventory"].items():
                item_label = f"{item_id} (x{item_data['quantity']}) - {item_data['price']} gold"
                buy_button = Button(text=f"Buy {item_label}")
                buy_button.bind(on_release=lambda x, item=item_id: self.buy_item(item))
                self.shop_inventory_container.add_widget(buy_button)
        except Exception as e:
            logging.error(f"Failed to load shop inventory: {e}")

        # Update Player Inventory
        self.player_inventory_container.clear_widgets()
        app = App.get_running_app()
        char_context = app.active_character_context
        
        if char_context:
            currency = char_context.inventory.get('currency', 0)
            self.player_currency_label.text = f"Currency: {currency}"
            
            # Handle both flat and nested inventory structures
            gear = char_context.inventory.get("carried_gear", {})
            # If carried_gear is empty, maybe items are in root inventory?
            # For now, assume carried_gear as per Orchestrator logic
            
            for item_id, quantity in gear.items():
                item_label = f"{item_id} (x{quantity})"
                sell_button = Button(text=f"Sell {item_label}")
                sell_button.bind(on_release=lambda x, item=item_id: self.sell_item(item))
                self.player_inventory_container.add_widget(sell_button)

    def buy_item(self, item_id):
        """Handles buying an item."""
        app = App.get_running_app()
        char_context = app.active_character_context
        if not char_context:
            return

        def task():
            return asyncio.run(
                app.orchestrator.handle_player_action(
                    player_id=char_context.id,
                    action_type="BUY",
                    shop_id=self.shop_id,
                    item_id=item_id,
                    quantity=1
                )
            )

        def on_success(result):
            if result.get("success"):
                # Update local context
                updated_char = result.get("character")
                if updated_char:
                    app.active_character_context = updated_char
                    self.update_inventories()
                    show_success(f"Bought {item_id}")
            else:
                show_error("Buy Failed", result.get("error", "Unknown error"))

        def on_error(e):
            logging.exception(f"Buy error: {e}")
            show_error("Buy Error", str(e))

        self.run_async(task, on_success, on_error)

    def sell_item(self, item_id):
        """Handles selling an item."""
        app = App.get_running_app()
        char_context = app.active_character_context
        if not char_context:
            return

        def task():
            return asyncio.run(
                app.orchestrator.handle_player_action(
                    player_id=char_context.id,
                    action_type="SELL",
                    shop_id=self.shop_id,
                    item_id=item_id,
                    quantity=1
                )
            )

        def on_success(result):
            if result.get("success"):
                # Update local context
                updated_char = result.get("character")
                if updated_char:
                    app.active_character_context = updated_char
                    self.update_inventories()
                    show_success(f"Sold {item_id}")
            else:
                show_error("Sell Failed", result.get("error", "Unknown error"))

        def on_error(e):
            logging.exception(f"Sell error: {e}")
            show_error("Sell Error", str(e))

        self.run_async(task, on_success, on_error)
