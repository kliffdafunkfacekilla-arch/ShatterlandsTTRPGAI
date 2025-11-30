import logging
from kivy.app import App
from monolith.modules.world_pkg import crud as world_crud
from monolith.modules.world_pkg import schemas as world_schemas
from monolith.modules.world_pkg.database import SessionLocal as WorldSession
from monolith.modules.character_pkg import services as char_services
from monolith.modules.character_pkg.database import SessionLocal as CharSession

def teleport_to_construct(app):
    """Teleports the active character (and party) to the Construct (Loc 999)."""
    logging.info("Debug: Teleporting to Construct...")
    db = WorldSession()
    try:
        # 1. Ensure Location 999 exists
        loc = world_crud.get_location(db, 999)
        if not loc:
            logging.info("Construct not found. Creating...")
            construct_data = world_schemas.LocationCreate(
                name="The Construct",
                region_id=1, # Assuming Region 1 exists
                tags=["test_chamber", "flat", "bright"],
                exits={}
            )
            # We need to manually set ID to 999, but create_location doesn't support it directly via schema
            # So we create it and then hack the ID or just let it be auto-assigned?
            # Better to just find it by name or create a new one.
            # For now, let's just create it and assume we can use whatever ID it gets, 
            # OR we use a SQL hack. But let's try to be clean.
            # Actually, for a test environment, we can just search for "The Construct"
            
            # Check by name first
            existing = db.query(world_crud.models.Location).filter(world_crud.models.Location.name == "The Construct").first()
            if existing:
                loc = existing
            else:
                loc = world_crud.create_location(db, construct_data)
                # Force a simple map
                map_update = world_schemas.LocationMapUpdate(
                    generated_map_data=[[1]*20 for _ in range(20)], # 20x20 floor
                    map_seed="construct",
                    spawn_points={"default": [10, 10]}
                )
                world_crud.update_location_map(db, loc.id, map_update)
        
        target_loc_id = loc.id
        
        # 2. Move Party (Update Orchestrator State)
        if app.orchestrator and app.orchestrator.state_manager.current_state:
            state = app.orchestrator.state_manager.current_state
            
            # Update all characters to new location
            for char in state.characters:
                char.current_location_id = target_loc_id
                char.position_x = 10
                char.position_y = 10
                
            # Save and Refresh
            app.orchestrator.state_manager.save_current_game()
            
            # Also sync to DB for consistency (optional but good)
            from monolith.modules import character as character_api
            for char in state.characters:
                character_api.update_character_location(char.id, target_loc_id, [10, 10])
                
            # Trigger UI Refresh
            app.event_bus.publish("state_updated", {})
            
            main_screen = app.root.get_screen('main_interface')
            main_screen.update_log("Teleported to The Construct.")
            
    except Exception as e:
        logging.error(f"Teleport failed: {e}")
    finally:
        db.close()

def spawn_npc(app, template_id):
    """Spawns an NPC near the player."""
    logging.info(f"Debug: Spawning {template_id}...")
    main_screen = app.root.get_screen('main_interface')
    if not main_screen.active_character_context: return
    
    loc_id = main_screen.active_character_context.current_location_id
    # Get player pos
    # We don't have easy access to player pos in context unless we refresh.
    # Let's assume (10, 11) for now or random near center.
    
    db = WorldSession()
    try:
        spawn_req = world_schemas.NpcSpawnRequest(
            template_id=template_id,
            location_id=loc_id,
            coordinates=[10, 12] # Offset from center
        )
        
        # 1. DB Spawn
        npc = world_crud.spawn_npc(db, spawn_req)
        
        # 2. Update Orchestrator State
        if app.orchestrator and app.orchestrator.state_manager.current_state:
            state = app.orchestrator.state_manager.current_state
            # Find location
            location = next((l for l in state.locations if l.id == loc_id), None)
            if location:
                # Convert DB model to Pydantic/Dict
                # This is tricky without full schemas, but let's try to append a dict
                npc_dict = {
                    "id": npc.id,
                    "name": npc.name,
                    "template_id": npc.template_id,
                    "coordinates": [npc.position_x, npc.position_y],
                    "hp": npc.current_hp,
                    "max_hp": npc.max_hp
                }
                if not location.npcs: location.npcs = []
                location.npcs.append(npc_dict)
                
                app.orchestrator.state_manager.save_current_game()
                app.event_bus.publish("state_updated", {})
        
        main_screen.update_log(f"Spawned {template_id}.")
        
    except Exception as e:
        logging.error(f"Spawn failed: {e}")
        main_screen.update_log(f"Spawn failed: {e}")
    finally:
        db.close()

def grant_test_items(app):
    """Adds test items to the active character."""
    logging.info("Debug: Granting items...")
    main_screen = app.root.get_screen('main_interface')
    if not main_screen.active_character_context: return
    
    char_id = main_screen.active_character_context.id
    db = CharSession()
    try:
        # 1. DB Grant
        char_services.add_item_to_character(db, char_id, "test_sword", 1)
        char_services.add_item_to_character(db, char_id, "test_potion", 5)
        
        # 2. Update Orchestrator State
        if app.orchestrator and app.orchestrator.state_manager.current_state:
            state = app.orchestrator.state_manager.current_state
            char = next((c for c in state.characters if c.id == char_id), None)
            if char:
                if not char.inventory: char.inventory = {}
                char.inventory["test_sword"] = char.inventory.get("test_sword", 0) + 1
                char.inventory["test_potion"] = char.inventory.get("test_potion", 0) + 5
                
                app.orchestrator.state_manager.save_current_game()
                app.event_bus.publish("state_updated", {})

        main_screen.update_log("Granted Test Sword and Potions.")
    except Exception as e:
        logging.error(f"Grant items failed: {e}")
    finally:
        db.close()

def heal_party(app):
    """Heals the active character."""
    logging.info("Debug: Healing...")
    main_screen = app.root.get_screen('main_interface')
    if not main_screen.active_character_context: return
    
    # We can use the rest mechanic or just hack the stats
    # Update Orchestrator State directly
    if app.orchestrator and app.orchestrator.state_manager.current_state:
        state = app.orchestrator.state_manager.current_state
        for char in state.characters:
            char.current_hp = char.max_hp
            
        app.orchestrator.state_manager.save_current_game()
        
        # Sync to DB
        db = CharSession()
        try:
            for char in state.characters:
                db_char = char_services.get_character(db, char.id)
                if db_char:
                    char_services.apply_healing(db, db_char, 9999)
        finally:
            db.close()
            
        app.event_bus.publish("state_updated", {})
        
    main_screen.update_log("Party Healed (Debug).")
