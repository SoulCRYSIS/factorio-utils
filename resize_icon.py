import os
import sys
import argparse
from PIL import Image

def get_crop_box(width, height, crop_pos):
    min_dim = min(width, height)
    
    # Calculate coordinates for the square crop
    if crop_pos == 'center':
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
    elif crop_pos == 'top-left':
        left = 0
        top = 0
    elif crop_pos == 'top-right':
        left = width - min_dim
        top = 0
    elif crop_pos == 'bottom-left':
        left = 0
        top = height - min_dim
    elif crop_pos == 'bottom-right':
        left = width - min_dim
        top = height - min_dim
    elif crop_pos == 'top':
        left = (width - min_dim) / 2
        top = 0
    elif crop_pos == 'bottom':
        left = (width - min_dim) / 2
        top = height - min_dim
    elif crop_pos == 'left':
        left = 0
        top = (height - min_dim) / 2
    elif crop_pos == 'right':
        left = width - min_dim
        top = (height - min_dim) / 2
    else:
        # Default to center
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2

    right = left + min_dim
    bottom = top + min_dim
    
    return (left, top, right, bottom)

def process_image(file_path, target_size, crop_pos):
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            
            # Skip if already target size
            if width == target_size and height == target_size:
                return False

            print(f"Processing {os.path.basename(file_path)} ({width}x{height}) -> {target_size}x{target_size} [Crop: {crop_pos}]")

            # 1. Crop to 1:1 ratio
            crop_box = get_crop_box(width, height, crop_pos)
            img_cropped = img.crop(crop_box)

            # 2. Downscale to target_size
            img_resized = img_cropped.resize((target_size, target_size), Image.Resampling.LANCZOS)

            # Save
            img_resized.save(file_path)
            return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main(folder_path, size=64, crop_pos="top-left"):
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a directory")
        sys.exit(1)

    count = 0
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".png"):
                file_path = os.path.join(root, file)
                if process_image(file_path, size, crop_pos):
                    count += 1

    print(f"Done. Resized {count} images.")

if __name__ == "__main__":
    main()
