from PIL import Image
import math
import os
import re
from pathlib import Path

# === CONFIGURATION ===

# Row length mapping: { total_frames: columns_per_row }
FRAME_COLUMN_MAPPING = {
    1: 1,
    2: 2,
    3: 3,
    4: 2,
    5: 3,
    6: 3,
    7: 4,
    8: 4,
    9: 3,
    10: 5,
    12: 4,
    16: 4,
    20: 5,
    24: 6,
    32: 8,
    64: 8,
}

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
BLENDER_RENDER_ROOT = PROJECT_ROOT / "blender" / "Render"

def get_files_sorted(folder_path):
    """Get all png files in folder sorted by the number in their filename."""
    if not folder_path.exists():
        print(f"Warning: Folder {folder_path} does not exist.")
        return []
    
    files = [f for f in folder_path.iterdir() if f.suffix.lower() == '.png']
    
    def sort_key(f):
        # Extract the last sequence of digits as the frame number
        numbers = re.findall(r'\d+', f.stem)
        if numbers:
            return int(numbers[-1])
        return f.stem

    return sorted(files, key=sort_key)

def get_image_size(files):
    """Get size of images and ensure they are all the same."""
    if not files:
        return 0, 0
    
    first_img = Image.open(files[0])
    width, height = first_img.size
    first_img.close()
    
    for f in files[1:]:
        with Image.open(f) as img:
            if img.size != (width, height):
                raise ValueError(f"Image size mismatch! {files[0].name} is {width}x{height}, but {f.name} is {img.size}")
    
    return width, height

def get_columns(frame_count):
    """Determine columns (frames per row) based on mapping."""
    if frame_count in FRAME_COLUMN_MAPPING:
        return FRAME_COLUMN_MAPPING[frame_count]
    
    print(f"Warning: Frame count {frame_count} not in mapping. Using default calculation.")
    return math.ceil(math.sqrt(frame_count))

import shutil

def process_component(component, prefix, destination, is_plant=False):
    if not component["enabled"]:
        return

    source_path = BLENDER_RENDER_ROOT / component["source_dir"]
    files = get_files_sorted(source_path)
    
    if not files:
        print(f"[{component['name']}] No files found in {source_path}")
        return

    frame_count = len(files)
    width, height = get_image_size(files)
    
    print(f"[{component['name']}] Found {frame_count} frames. Size: {width}x{height}")
    
    cols = get_columns(frame_count)
    rows = math.ceil(frame_count / cols)
    
    sheet_width = cols * width
    sheet_height = rows * height
    
    print(f"[{component['name']}] Creating spritesheet: {sheet_width}x{sheet_height} ({cols}x{rows})")
    
    sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
    
    for i, file_path in enumerate(files):
        with Image.open(file_path) as img:
            col = i % cols
            row = i // cols
            x = col * width
            y = row * height
            sheet.paste(img, (x, y))
            
    destination_root = PROJECT_ROOT / destination
    
    # Ensure destination exists
    destination_root.mkdir(parents=True, exist_ok=True)
    
    output_filename = f"{prefix}{component['suffix']}.png"
    output_path = destination_root / output_filename
    
    sheet.save(output_path)
    print(f"[{component['name']}] Saved to {output_path}")
    
    # Handle Plant Specific Logic
    if is_plant:
        if component['name'] == "Object":
            # Create harvest (copy of object)
            harvest_path = destination_root / f"{prefix}-harvest.png"
            shutil.copy2(output_path, harvest_path)
            print(f"[{component['name']}] Created Plant copy: {harvest_path}")
            
            # Create normal (copy of object)
            normal_path = destination_root / f"{prefix}-normal.png"
            shutil.copy2(output_path, normal_path)
            print(f"[{component['name']}] Created Plant copy: {normal_path}")
            
        elif component['name'] == "Shadow":
            # Create harvest-shadow (copy of shadow)
            harvest_shadow_path = destination_root / f"{prefix}-harvest-shadow.png"
            shutil.copy2(output_path, harvest_shadow_path)
            print(f"[{component['name']}] Created Plant copy: {harvest_shadow_path}")

def main(prefix, destination, include_object=True, include_shadow=True, include_reflection=True, include_glow=True, is_plant=False):
    print(f"Processing sprites for prefix: {prefix}")
    print(f"Destination: {destination}")
    if is_plant:
        print("Mode: Plant (Generating extra copies)")
    
    components = [
        {
            "name": "Object",
            "source_dir": "Object",
            "suffix": "",
            "enabled": include_object
        },
        {
            "name": "Shadow",
            "source_dir": "Shadow",
            "suffix": "-shadow",
            "enabled": include_shadow
        },
        {
            "name": "Reflection",
            "source_dir": "WaterReflection",
            "suffix": "-water-reflection",
            "enabled": include_reflection
        },
        {
            "name": "Glow",
            "source_dir": "Light A Reduced",
            "suffix": "-glow",
            "enabled": include_glow
        }
    ]
    
    for component in components:
        try:
            process_component(component, prefix, destination, is_plant)
        except Exception as e:
            print(f"Error processing {component['name']}: {e}")

