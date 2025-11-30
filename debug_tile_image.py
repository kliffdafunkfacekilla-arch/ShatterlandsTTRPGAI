import os
from kivy.core.image import Image as CoreImage
import logging

logging.basicConfig(level=logging.DEBUG)

file_path = r"C:\Users\krazy\Documents\GitHub\ShatterlandsTTRPGAI\game_client\assets\graphics\tiles\outdoor_tiles_1.png"

print(f"Checking file: {file_path}")
if os.path.exists(file_path):
    print(f"File exists. Size: {os.path.getsize(file_path)} bytes")
    
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
            print(f"Header bytes: {header}")
            if header == b'\x89PNG\r\n\x1a\n':
                print("Header confirms it is a PNG.")
            else:
                print("WARNING: Header does NOT look like a standard PNG.")
    except Exception as e:
        print(f"Error reading file: {e}")

    try:
        print("Attempting to load with Kivy CoreImage...")
        img = CoreImage(file_path)
        print(f"Load successful. Size: {img.size}")
    except Exception as e:
        print(f"Kivy load failed: {e}")
else:
    print("File does not exist.")
