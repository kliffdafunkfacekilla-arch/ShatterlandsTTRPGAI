import os
from typing import List, Dict, Optional

class LoreManager:
    def __init__(self, lore_dir: str = "AI-TTRPG/lore"):
        # Resolve absolute path relative to the project root if needed, 
        # but for now assume the path is correct relative to CWD or absolute.
        # Ideally, we should make this robust.
        if not os.path.isabs(lore_dir):
            # Assuming running from project root
            self.lore_dir = os.path.abspath(lore_dir)
        else:
            self.lore_dir = lore_dir
            
        self.lore_cache: Dict[str, str] = {}
        self._load_lore()

    def _load_lore(self):
        if not os.path.exists(self.lore_dir):
            print(f"Lore directory not found: {self.lore_dir}")
            return

        for filename in os.listdir(self.lore_dir):
            if filename.endswith(".txt"):
                filepath = os.path.join(self.lore_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self.lore_cache[filename] = f.read()
                except Exception as e:
                    print(f"Error loading lore file {filename}: {e}")

    def get_lore_context(self, tags: List[str] = None) -> str:
        """
        Retrieves relevant lore context based on tags.
        """
        if not self.lore_cache:
            return ""

        context = []
        
        # If no tags provided, default to foundations if available
        if not tags:
             if "foundations.txt" in self.lore_cache:
                 return self.lore_cache["foundations.txt"]
             # If no foundations, return a generic message or empty
             return ""

        # Normalize tags
        normalized_tags = [t.lower() for t in tags]

        # Simple mapping strategy
        # 1. Check filenames against tags
        # 2. Specific mappings (e.g. "forest" -> "Canopy_Clans.txt")
        
        # Mapping helper
        # TODO: Move this to a config or make it dynamic
        keyword_map = {
            "forest": ["Canopy_Clans.txt"],
            "jungle": ["Canopy_Clans.txt"],
            "tree": ["Canopy_Clans.txt"],
            "coast": ["Coastal_Theocracy.txt"],
            "ocean": ["Coastal_Theocracy.txt"],
            "water": ["Coastal_Theocracy.txt"],
            "volcano": ["Iron_Caldera.txt"],
            "mountain": ["Iron_Caldera.txt"],
            "iron": ["Iron_Caldera.txt"],
            "trade": ["Economy.txt"],
            "money": ["Economy.txt"],
            "shop": ["Economy.txt"],
            "economy": ["Economy.txt"]
        }

        relevant_files = set()

        for tag in normalized_tags:
            # Direct filename match
            for filename in self.lore_cache.keys():
                if tag in filename.lower():
                    relevant_files.add(filename)
            
            # Keyword map match
            if tag in keyword_map:
                for mapped_file in keyword_map[tag]:
                    if mapped_file in self.lore_cache:
                        relevant_files.add(mapped_file)

        # If we found specific files, load them
        if relevant_files:
            for filename in relevant_files:
                context.append(f"--- {filename} ---\n{self.lore_cache[filename]}")
        else:
            # Fallback: if tags were provided but no match found, 
            # maybe return foundations as a safe bet?
            if "foundations.txt" in self.lore_cache:
                context.append(self.lore_cache["foundations.txt"])

        return "\n\n".join(context)
