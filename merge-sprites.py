from PIL import Image
import math
from constant import *

# Configuration

frame_folder = "temp_sprites/"          # Folder where individual frames are
frame_ext = ".png"                 # Frame file extension
output_file = "spritesheet.png"    # Output sprite sheet

# Load all frames
frames = [Image.open(f"{frame_folder}{i:04d}{frame_ext}") for i in range(frame_count)]

# Assume all frames are the same size
frame_width, frame_height = frames[0].size

# Compute sheet size
rows = math.ceil(frame_count / frames_per_row)
sheet_width = frames_per_row * frame_width
sheet_height = rows * frame_height

# Create the new image
sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))  # Transparent background

# Paste frames into the sheet
for index, frame in enumerate(frames):
    x = (index % frames_per_row) * frame_width
    y = (index // frames_per_row) * frame_height
    sheet.paste(frame, (x, y), frame)  # Use frame as mask to preserve alpha

# Save the final sprite sheet
sheet.save(output_file)
print(f"Sprite sheet saved to {output_file}")
