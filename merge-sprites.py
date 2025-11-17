from PIL import Image
import math
import os
import re
from pathlib import Path
from constant import *

# Configuration
frame_folder = "temp_sprites/"          # Folder where individual frames are
frame_ext = ".png"                 # Frame file extension

# Auto-detect images and naming convention
def detect_images_and_pattern(folder, ext):
    """Detect all images in folder and extract naming pattern."""
    folder_path = Path(folder)
    if not folder_path.exists():
        raise ValueError(f"Folder '{folder}' does not exist")
    
    # Find all image files with the specified extension
    image_files = sorted([f for f in folder_path.iterdir() 
                         if f.suffix.lower() == ext.lower()])
    
    if not image_files:
        raise ValueError(f"No {ext} files found in '{folder}'")
    
    # Try to detect naming pattern
    # Pattern 1: prefix-number.ext (e.g., vangrove-1.png, vangrove-2.png)
    # Pattern 2: zero-padded number.ext (e.g., 0000.png, 0001.png)
    # Pattern 3: number.ext (e.g., 1.png, 2.png)
    
    first_name = image_files[0].stem
    prefix = None
    
    # Try pattern: prefix-number
    match = re.match(r'^(.+)-(\d+)$', first_name)
    if match:
        prefix = match.group(1)
        # Verify all files follow this pattern
        pattern_valid = all(re.match(rf'^{re.escape(prefix)}-(\d+)$', f.stem) 
                           for f in image_files)
        if pattern_valid:
            # Sort by number
            image_files.sort(key=lambda f: int(re.match(rf'^{re.escape(prefix)}-(\d+)$', f.stem).group(1)))
            return image_files, prefix
    
    # Try pattern: numeric (zero-padded or simple number)
    match = re.match(r'^(\d+)$', first_name)
    if match:
        # Verify all files are numbers
        pattern_valid = all(re.match(r'^(\d+)$', f.stem) for f in image_files)
        if pattern_valid:
            # Sort by number
            image_files.sort(key=lambda f: int(f.stem))
            return image_files, None
    
    # If no pattern matches, use alphabetical order and extract common prefix
    image_files.sort()
    # Try to find common prefix
    if len(image_files) > 1:
        common_prefix = os.path.commonprefix([f.stem for f in image_files])
        # Remove trailing non-alphanumeric characters
        prefix = re.sub(r'[^a-zA-Z0-9]+$', '', common_prefix) if common_prefix else None
    else:
        prefix = image_files[0].stem.split('-')[0] if '-' in image_files[0].stem else image_files[0].stem
    
    return image_files, prefix

# Auto-detect image sizes
def detect_image_sizes(image_files):
    """Detect sizes of all images and return max dimensions."""
    sizes = []
    for img_file in image_files:
        with Image.open(img_file) as img:
            sizes.append(img.size)
    
    # Return max width and max height to accommodate all images
    max_width = max(s[0] for s in sizes)
    max_height = max(s[1] for s in sizes)
    
    # Check if all images are the same size
    all_same_size = all(s == sizes[0] for s in sizes)
    
    return max_width, max_height, all_same_size, sizes

# Detect images and pattern
image_files, prefix = detect_images_and_pattern(frame_folder, frame_ext)
frame_count = len(image_files)

print(f"Found {frame_count} images")
if prefix:
    print(f"Detected prefix: {prefix}")
else:
    print("No common prefix detected")

# Load all frames and detect sizes
print("Loading images and detecting sizes...")
frames = []
for img_file in image_files:
    frames.append(Image.open(img_file))

frame_width, frame_height, all_same_size, individual_sizes = detect_image_sizes(image_files)

if not all_same_size:
    print(f"Warning: Images have different sizes. Using max dimensions: {frame_width}x{frame_height}")
    for i, (img_file, size) in enumerate(zip(image_files, individual_sizes)):
        if size != (frame_width, frame_height):
            print(f"  {img_file.name}: {size[0]}x{size[1]}")
else:
    print(f"All images are {frame_width}x{frame_height}")

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
    # Center smaller images if they're not the max size
    if individual_sizes[index] != (frame_width, frame_height):
        offset_x = (frame_width - individual_sizes[index][0]) // 2
        offset_y = (frame_height - individual_sizes[index][1]) // 2
        sheet.paste(frame, (x + offset_x, y + offset_y), frame)
    else:
        sheet.paste(frame, (x, y), frame)  # Use frame as mask to preserve alpha

# Determine output filename
if prefix:
    output_file = f"{prefix}{frame_ext}"
else:
    output_file = f"spritesheet{frame_ext}"

# Save the final sprite sheet
sheet.save(output_file)
print(f"Sprite sheet saved to {output_file}")
