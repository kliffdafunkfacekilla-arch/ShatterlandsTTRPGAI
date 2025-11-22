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
        
        # 2. Move Party
        main_screen = app.root.get_screen('main_interface')
        if main_screen.active_character_context:
            char_id = main_screen.active_character_context.id
            # Move to (10, 10)
            main_screen.move_player_to(10, 10) 
            # But move_player_to only works in current map. We need to force location change.
            
            # We need to use the monolith API directly to change location_id
            from monolith.modules import character as character_api
            character_api.update_character_location(char_id, target_loc_id, [10, 10])
            
            # Refresh UI
            main_screen.on_enter()
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
        world_crud.spawn_npc(db, spawn_req)
        main_screen.update_log(f"Spawned {template_id}.")
        # Refresh map
        main_screen.on_enter()
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
        char_services.add_item_to_character(db, char_id, "test_sword", 1)
        char_services.add_item_to_character(db, char_id, "test_potion", 5)
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
    main_screen.on_rest()
    main_screen.update_log("Party Healed (Debug Rest).")
