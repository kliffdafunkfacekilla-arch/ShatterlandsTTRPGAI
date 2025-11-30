from PIL import Image
import os

src_path = r"c:\Users\krazy\Documents\GitHub\ShatterlandsTTRPGAI\game_client\assets\graphics\entities\hero_token.png"
dst_path = r"c:\Users\krazy\Documents\GitHub\ShatterlandsTTRPGAI\game_client\assets\graphics\entities\hero_sprite.png"

try:
    if os.path.exists(src_path):
        img = Image.open(src_path)
        print(f"Original size: {img.size}")
        
        # Resize to 64x64 using high quality resampling
        img_resized = img.resize((64, 64), Image.Resampling.LANCZOS)
        img_resized.save(dst_path)
        
        print(f"Saved resized image to {dst_path}")
    else:
        print("Source file not found.")
except ImportError:
    print("Pillow (PIL) not installed.")
except Exception as e:
    print(f"Error: {e}")
