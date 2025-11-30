from kivy.core.image import Image as CoreImage
import os

img_path = r"c:\Users\krazy\Documents\GitHub\ShatterlandsTTRPGAI\game_client\assets\graphics\ui\uipack_rpg_sheet.png"
if os.path.exists(img_path):
    im = CoreImage(img_path)
    print(f"WIDTH={im.width}")
    print(f"HEIGHT={im.height}")
else:
    print("Image not found")
