from PIL import Image, ImageDraw

def create_placeholder_tiles(path):
    # Create a 256x256 image (enough for 4x4 64px tiles)
    img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    tile_size = 64
    
    colors = [
        (34, 139, 34, 255),   # Forest Green (Grass)
        (139, 69, 19, 255),   # Saddle Brown (Dirt)
        (65, 105, 225, 255),  # Royal Blue (Water)
        (128, 128, 128, 255)  # Gray (Stone)
    ]
    
    for y in range(4):
        for x in range(4):
            color = colors[(x + y) % len(colors)]
            rect = [x * tile_size, y * tile_size, (x + 1) * tile_size - 1, (y + 1) * tile_size - 1]
            draw.rectangle(rect, fill=color, outline=(255, 255, 255, 128))
            
            # Add some text to identify tile ID if needed, but simple color is enough
            
    img.save(path)
    print(f"Created placeholder tiles at {path}")

if __name__ == "__main__":
    create_placeholder_tiles(r"C:\Users\krazy\Documents\GitHub\ShatterlandsTTRPGAI\game_client\assets\graphics\tiles\outdoor_tiles_1.png")
