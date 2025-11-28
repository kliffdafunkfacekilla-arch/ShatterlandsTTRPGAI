# Shatterlands TTRPG - Developer Documentation

## Architecture Overview

Shatterlands is a **local-first, event-driven TTRPG engine** built as a Python monolith.

### Key Design Principles

1. **Local-First**: No network dependency (except optional AI DM)
2. **Data-Driven**: Game rules defined in JSON
3. **Event-Driven**: Reactive UI via Event Bus
4. **Modular**: Clear separation of concerns
5. **JSON Persistence**: No database required

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Kivy UI Layer                       │
│  (game_client/views/*.py)                              │
│  - Screens subscribe to Event Bus                       │
│  - Call Orchestrator methods directly                   │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│                   Orchestrator                          │
│  (AI-TTRPG/monolith/orchestrator.py)                   │
│  - Central game coordinator                             │
│  - Delegates to managers                                │
│  - Publishes events                                     │
└──┬───────┬──────────┬───────────┬──────────────────────┘
   │       │          │           │
   ▼       ▼          ▼           ▼
┌─────┐ ┌──────┐  ┌──────┐  ┌────────────┐
│State│ │Event │  │Rules │  │AI Content  │
│Mgr  │ │ Bus  │  │ Set  │  │Manager     │
└─────┘ └──────┘  └──────┘  └────────────┘
   │                  │           │
   ▼                  ▼           ▼
┌─────────┐     ┌──────────┐ ┌──────────┐
│Save Mgr │     │Data JSON │ │Gemini API│
│(JSON)   │     │Files     │ │(Optional)│
└─────────┘     └──────────┘ └──────────┘
```

---

## Core Components

### 1. Orchestrator

**Path**: `AI-TTRPG/monolith/orchestrator.py`

**Purpose**: Central coordinator for all game logic.

**Key Methods**:
```python
async def initialize_engine()
    """Load rules, setup managers"""

async def start_new_game(character_paths: List[str])
    """Create new game from character JSON files"""

async def load_game(slot_name: str)
    """Load saved game state"""

def get_current_state() -> SaveGameData
    """Get current game state"""

def get_active_player() -> CharacterSave
    """Get currently active character"""

async def handle_player_action(player_id, action_type, **kwargs)
    """Process player actions (MOVE, ABILITY, etc.)"""
```

**Usage**:
```python
from monolith.orchestrator import Orchestrator

orch = Orchestrator()
await orch.initialize_engine()
result = await orch.start_new_game(["char1.json", "char2.json"])
```

---

### 2. Event Bus

**Path**: `AI-TTRPG/monolith/event_bus.py`

**Purpose**: Pub/sub system for decoupled communication.

**Key Methods**:
```python
def subscribe(event_name: str, callback: Callable)
    """Subscribe to event"""

async def publish(event_name: str, **kwargs)
    """Publish event to all subscribers"""
```

**Events**:
- `engine.initialized` - Engine ready
- `game.started` - New game created
- `game.loaded` - Save loaded
- `player.turn_start` - Turn changed
- `action.ability` - Ability used
- `game.state_updated` - State changed

**Usage**:
```python
from monolith.event_bus import get_event_bus

bus = get_event_bus()

# Subscribe
def on_turn(player_id, **kwargs):
    print(f"Turn: {player_id}")

bus.subscribe("player.turn_start", on_turn)

# Publish
await bus.publish("player.turn_start", player_id="hero1")
```

---

### 3. GameStateManager

**Path**: `AI-TTRPG/monolith/orchestrator.py` (inner class)

**Purpose**: Manage game state and hotseat rotation.

**Key Methods**:
```python
def switch_active_player() -> CharacterSave
    """Rotate to next player"""

def save_current_game(slot_name: str) -> dict
    """Save game state to JSON"""
```

**State Structure**:
```python
class SaveGameData(BaseModel):
    campaign_id: str
    turn_number: int
    active_player_id: str
    characters: List[CharacterSave]
    # ... other fields
```

---

### 4. Save Manager

**Path**: `AI-TTRPG/monolith/modules/save_manager.py`

**Purpose**: JSON-based persistence.

**Key Functions**:
```python
def save_game(slot_name: str, data: SaveGameData) -> dict
    """Write game state to JSON file"""

def load_game(slot_name: str) -> SaveGameData
    """Read and validate JSON save"""

def scan_saves() -> Dict[str, SaveFile]
    """List all available saves"""
```

**Save Location**: `./saves/{slot_name}.json`

---

### 5. RuleSetContainer

**Path**: `AI-TTRPG/monolith/modules/rules_pkg/data_loader_enhanced.py`

**Purpose**: Singleton for validated game rules.

**Key Methods**:
```python
def load_and_validate_all() -> dict
    """Load all JSON data files"""

# Access via singleton
from rules_pkg.data_loader_enhanced import RuleSetContainer

rules = RuleSetContainer()
ability = rules.get_ability("fireball")
talent = rules.get_talent("Overpowering Presence")
```

**Data Loaded**:
- Stats (12)
- Skills (72)
- Abilities (531)
- Talents (42)
- Status effects
- Equipment
- Character creation data

---

### 6. Talent Logic

**Path**: `AI-TTRPG/monolith/modules/rules_pkg/talent_logic_enhanced.py`

**Purpose**: Generic talent/ability resolution.

**Key Functions**:
```python
def resolve_talent_action(
    source_character: CharacterSave,
    talent_id: str,
    target_id: Optional[str],
    context: Optional[Dict]
) -> Dict[str, Any]
    """Execute talent effects"""

def resolve_ability_action(...) 
    """Execute ability effects"""
```

**Effect Handlers**:
- `damage` - Deal damage
- `heal` - Restore HP
- `buff` - Stat bonuses
- `status` - Apply effects
- `resource_restore` - Restore stamina/composure
- ... and 8 more

---

### 7. AI Content Manager

**Path**: `AI-TTRPG/monolith/modules/ai_dm_pkg/llm_handler_enhanced.py`

**Purpose**: Async AI narrative generation with caching.

**Key Methods**:
```python
async def generate_narrative_async(
    prompt_text: str,
    char_context: Dict,
    loc_context: Dict,
    recent_log: Optional[List],
    action_type: str,
    use_cache: bool = True
) -> str
    """Generate AI narrative (non-blocking)"""

def get_cache_stats() -> dict
    """Get cache hit/miss statistics"""

def shutdown()
    """Clean shutdown of threads"""
```

**Features**:
- Thread-safe caching
- Pre-generation support
- Context window management
- FIFO eviction

---

## Data Flow

### Starting a New Game

```
1. UI: user selects character JSON files
   ↓
2. UI: orchestrator.start_new_game(files)
   ↓
3. Orchestrator: load JSON files
   ↓
4. Orchestrator: validate with Pydantic
   ↓
5. GameStateManager: create initial state
   ↓
6. GameStateManager: save to ./saves/autosave.json
   ↓
7. Event Bus: publish "game.started"
   ↓
8. UI: receives event, navigates to main_interface
```

### Player Action

```
1. UI: user clicks to move
   ↓
2. UI: orchestrator.handle_player_action(...)
   ↓
3. Orchestrator: validate action
   ↓
4. Orchestrator: apply effects
   ↓
5. GameStateManager: update state
   ↓
6. SaveManager: auto-save
   ↓
7. Event Bus: publish "action.move"
   ↓
8. UI: receives event, updates display
```

---

## File Structure

```
ShatterlandsTTRPGAI/
├── game_client/               # Kivy UI
│   ├── main.py               # App entry point
│   └── views/                # UI screens
│       ├── main_interface_screen.py
│       ├── game_setup_screen_refactored.py
│       ├── load_game_screen.py
│       └── event_bus_pattern.py  # Reference
│
├── AI-TTRPG/monolith/        # Backend
│   ├── orchestrator.py       # Central coordinator
│   ├── event_bus.py          # Pub/sub system
│   └── modules/
│       ├── save_manager.py   # JSON persistence
│       ├── save_schemas.py   # Pydantic models
│       ├── rules_pkg/
│       │   ├── data_loader_enhanced.py
│       │   ├── talent_logic_enhanced.py
│       │   └── data/         # JSON game data
│       └── ai_dm_pkg/
│           └── llm_handler_enhanced.py
│
├── characters/               # Character JSON files
├── saves/                    # Save game JSON files
│
└── Tests/
    ├── test_phase1_quick.py
    ├── test_phase2_data_layer.py
    ├── test_phase4_talents.py
    └── test_phase5_ai_dm.py
```

---

## Adding New Features

### Adding a New Action Type

1. **Define action in Orchestrator**:
```python
async def _handle_new_action(self, player_id, **kwargs):
    # Your logic here
    result = {...}
    await self.event_bus.publish("action.new_action", result=result)
    return result
```

2. **Add to action dispatcher**:
```python
async def handle_player_action(self, ...):
    if action_type == "NEW_ACTION":
        return await self._handle_new_action(...)
```

3. **Subscribe in UI**:
```python
app.event_bus.subscribe("action.new_action", self.on_new_action)
```

### Adding a New Effect Type

1. **Create handler in talent_logic_enhanced.py**:
```python
def _handle_new_effect(source, target, params, context):
    # Effect logic
    return {"type": "new_effect", "applied": True}
```

2. **Register in EFFECT_HANDLERS**:
```python
EFFECT_HANDLERS["new_effect_type"] = _handle_new_effect
```

3. **Use in JSON**:
```json
{
  "modifiers": [
    {"type": "new_effect_type", "param": "value"}
  ]
}
```

---

## Testing

### Running Tests

```bash
# Core architecture
python test_phase1_quick.py

# Data validation
python test_phase2_data_layer.py

# Talent system
python test_phase4_talents.py

# AI DM
python test_phase5_ai_dm.py
```

### Writing Tests

```python
import asyncio
from monolith.orchestrator import Orchestrator

def test_new_feature():
    orch = Orchestrator()
    asyncio.run(orch.initialize_engine())
    
    result = asyncio.run(orch.my_new_method())
    
    assert result["success"] == True
```

---

## Performance

### Optimization Tips

1. **Cache Frequently Accessed Data**
   - Rules are cached in RuleSetContainer (singleton)
   - AI narratives cached in AIContentManager

2. **Async Operations**
   - AI generation uses ThreadPoolExecutor
   - Event Bus uses async/await

3. **Lazy Loading**
   - Assets loaded on demand
   - Screens created once

### Profiling

```python
import cProfile

cProfile.run('asyncio.run(orchestrator.start_new_game(files))')
```

---

## API Reference

### Orchestrator API

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `initialize_engine()` | - | - | Load rules, setup |
| `start_new_game()` | `character_paths` | `dict` | Create new game |
| `load_game()` | `slot_name` | `dict` | Load save |
| `get_current_state()` | - | `SaveGameData` | Get state |
| `get_active_player()` | - | `CharacterSave` | Get active |
| `handle_player_action()` | `player_id`, `action_type`, `**kwargs` | `dict` | Process action |

### Event Bus API

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `subscribe()` | `event_name`, `callback` | - | Subscribe |
| `publish()` | `event_name`, `**kwargs` | - | Publish |

---

## Troubleshooting

### Common Issues

**Import Errors**:
- Ensure monolith is in Python path
- Check relative imports

**Event Not Firing**:
- Verify subscription before publish
- Check event name spelling
- Ensure async/await used correctly

**Save/Load Fails**:
- Check JSON syntax
- Verify Pydantic schema matches
- Review console for validation errors

---

## Contributing

### Code Style

- **PEP 8** compliance
- **Type hints** on public methods
- **Docstrings** for all classes/functions
- **Comments** for complex logic

### Pull Request Process

1. Create feature branch
2. Write tests
3. Update documentation
4. Submit PR with description

---

## Resources

- **User Guide**: `USER_GUIDE.md`
- **Modding Guide**: `MODDING_GUIDE.md`
- **Test Reports**: `.gemini/antigravity/brain/.../test_report_*.md`
- **Walkthrough**: `.gemini/antigravity/brain/.../walkthrough.md`

---

**Happy Developing!** 🚀
