# Shatterlands TTRPG - User Guide

## Getting Started

### Installation

1. **Requirements**
   - Python 3.8+
   - Kivy (UI framework)
   - See `requirements.txt` for full dependencies

2. **Setup**
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch**
   ```bash
   python game_client/main.py
   ```

---

## Main Menu

When the application starts, you'll see:
- **New Game** - Start a new adventure
- **Load Game** - Continue a saved game
- **Settings** - Configure the application
- **Exit** - Close the application

---

## Starting a New Game

### Method 1: File Chooser (Recommended)

1. Click **New Game**
2. File chooser will open
3. Navigate to `./characters/` folder
4. Select **2-4 character JSON files**
5. Click **Start Adventure**

### Requirements
- Minimum: 2 characters
- Maximum: 4 characters
- File format: `.json`

### Example Character Files
Character JSON files should be in `./characters/` directory:
- `warrior.json`
- `mage.json`
- `rogue.json`
- `cleric.json`

---

## Hotseat Multiplayer

### How It Works
The game supports **hotseat multiplayer** where players take turns on the same computer.

### Taking Turns
1. **Active Player** is shown in the party panel (highlighted)
2. Take your action (move, ability, dialogue)
3. Click **End Turn** to pass control
4. Next player becomes active

### Switching Characters
- Click any character in the **Party Panel** to view their stats
- Only the **active character** can take actions

---

## Saving Your Game

### Auto-Save
The game automatically saves after every action.

### Manual Save
1. Click **Save Game** button (top menu)
2. Enter a save name (default: character_date_time)
3. Click **Save**
4. Confirmation appears

### Save Location
Saves are stored in `./saves/` directory as JSON files.

---

## Loading a Game

1. Click **Load Game** from main menu
2. List of saves appears with:
   - Save name
   - Number of characters
   - Date/time saved
3. Click on a save to load it
4. Game state restores completely

---

## Gameplay

### Movement
- Click on the map to move your character
- Only passable tiles can be entered
- Active character moves when you click

### Using Abilities
1. Select ability from ability panel
2. Choose target (if required)
3. Ability resolves automatically
4. Effects and narrative appear

### Dialogue
- Click on NPCs to start conversations
- Choose dialogue options
- Story progresses based on choices

### Inventory
- Click **Inventory** button (top menu)
- View items, equipment, consumables
- Use or equip items

---

## AI Dungeon Master (Optional)

### Setup
To enable AI-generated narratives:

1. Get a Google Gemini API key from: https://makersuite.google.com/app/apikey
2. Set environment variable:
   ```bash
   # Windows
   set GOOGLE_API_KEY=your_key_here
   
   # Linux/Mac
   export GOOGLE_API_KEY=your_key_here
   ```
3. Restart the application

### Using AI DM
- Type in the **DM Input box** (right panel)
- Press Enter
- AI generates narrative response
- UI remains responsive (async generation)

### Performance
- First generation: 3-5 seconds
- Cached responses: Instant
- Narratives are cached for speed

---

## Character Sheet

View detailed character information:

1. Click **Character** button (top menu)
2. See:
   - Stats (Might, Finesse, Logic, etc.)
   - Skills and proficiencies
   - Talents and abilities
   - Equipment and inventory
   - Current status effects

---

## Tips & Tricks

### Performance
- Game runs locally (no internet needed except AI DM)
- Save files are small JSON (easy to backup)
- Multiple saves supported

### Modding
- Characters are JSON files (easy to create/edit)
- See MODDING_GUIDE.md for custom content

### Troubleshooting

**Game won't start:**
- Check console for errors
- Ensure all dependencies installed
- Verify character JSON files are valid

**Can't load save:**
- Check `./saves/` directory exists
- Verify save file is valid JSON
- Try a different save

**AI DM not working:**
- Verify GOOGLE_API_KEY is set
- Check internet connection
- Review console for API errors

---

## Controls

### Keyboard
- **ESC** - Close popups
- **Enter** - Submit DM input

### Mouse
- **Click** - Move, select, interact
- **Scroll** - Navigate lists and logs

---

## Support

For issues or questions:
1. Check console output for errors
2. Verify JSON file formats
3. Review documentation
4. Check GitHub issues

---

## Quick Reference

| Action | How To |
|--------|--------|
| New Game | Main Menu → New Game → Select JSON files |
| Save Game | Top Menu → Save Game → Enter name |
| Load Game | Main Menu → Load Game → Click save |
| Move | Click on map |
| Use Ability | Select from ability panel |
| Talk to NPC | Click on NPC sprite |
| End Turn | Click End Turn button |
| View Character | Top Menu → Character |
| Open Inventory | Top Menu → Inventory |

---

**Enjoy your adventure in the Shatterlands!**
