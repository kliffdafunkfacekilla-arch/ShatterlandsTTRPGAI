import os
from kivy.core.image import Image as CoreImage

image_path = r"c:\Users\krazy\Documents\GitHub\ShatterlandsTTRPGAI\game_client\assets\graphics\entities\hero_token.png"

if os.path.exists(image_path):
    try:
        img = CoreImage(image_path)
        print(f"Image: {os.path.basename(image_path)}")
        print(f"Dimensions: {img.width}x{img.height}")
        print(f"Texture Size: {img.texture.size}")
    except Exception as e:
        print(f"Error loading image: {e}")
else:
    print("File not found.")
