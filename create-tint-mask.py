#!/usr/bin/env python3
"""
Create a tint mask for the carriage engine by keeping only copper/orange-brown parts
and removing white/gray iron parts, then reducing opacity to 0.3
"""

from PIL import Image
import numpy as np
import sys
import os

def is_copper_color(r, g, b):
    """
    Determine if a pixel is a copper/orange-brown color vs iron/gray color.
    Copper colors have warm tones with more red than blue.
    Iron colors are grayscale or cool-toned with balanced RGB or more blue.
    """
    # Skip very dark pixels (shadows/black) - they're not part of the mask
    if r < 30 and g < 30 and b < 30:
        return False
    
    # Copper colors have characteristics:
    # - Red channel is higher than blue
    # - Some warmth (red + green > blue)
    # - Not grayscale (channels have variation)
    
    # Check if it's grayscale (iron-like)
    max_channel = max(r, g, b)
    min_channel = min(r, g, b)
    channel_diff = max_channel - min_channel
    
    # If channels are very similar, it's grayscale (iron)
    if channel_diff < 15:
        return False
    
    # Check for warm tones (copper)
    # Copper should have: r > b and (r + g) > (b + some threshold)
    warmth = (r + g * 0.8) - (b * 1.5)
    
    if warmth > 10 and r > b:
        return True
    
    return False

def create_tint_mask(input_path, output_path, opacity=0.3, reverse=False):
    """
    Create a tint mask by keeping only copper-colored pixels
    If reverse=True, keeps iron parts and removes copper parts instead
    """
    print(f"Loading image: {input_path}")
    if reverse:
        print("Reverse mode: keeping iron parts, removing copper parts")
    img = Image.open(input_path)
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Convert to numpy array for processing
    img_array = np.array(img)
    
    # Create output array (start with copy)
    output_array = np.copy(img_array)
    
    # Get dimensions
    height, width = img_array.shape[:2]
    
    print(f"Processing {width}x{height} image...")
    
    # Process each pixel
    pixels_kept = 0
    pixels_removed = 0
    
    for y in range(height):
        for x in range(width):
            r, g, b, a = img_array[y, x]
            
            # If pixel is already transparent, keep it transparent
            if a == 0:
                continue
            
            # Check if this is a copper color
            is_copper = is_copper_color(r, g, b)
            
            # Determine if we should keep this pixel based on reverse flag
            should_keep = is_copper if not reverse else not is_copper
            
            if should_keep:
                # Convert to grayscale (preserve luminosity/tone) and set opacity
                # Use standard luminosity formula
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                output_array[y, x, 0] = gray  # R
                output_array[y, x, 1] = gray  # G
                output_array[y, x, 2] = gray  # B
                output_array[y, x, 3] = int(a * opacity)  # A
                pixels_kept += 1
            else:
                # Remove unwanted colors (make transparent)
                output_array[y, x, 3] = 0
                pixels_removed += 1
    
    if reverse:
        print(f"Pixels kept (iron): {pixels_kept}")
        print(f"Pixels removed (copper): {pixels_removed}")
    else:
        print(f"Pixels kept (copper): {pixels_kept}")
        print(f"Pixels removed (iron): {pixels_removed}")
    
    # Convert back to image
    output_img = Image.fromarray(output_array, 'RGBA')
    
    # Save the result
    print(f"Saving mask to: {output_path}")
    output_img.save(output_path, 'PNG')
    print("Done!")

def main():
    if len(sys.argv) < 2:
        print("Usage: python create-tint-mask.py <input_image> [output_image] [opacity] [--reverse]")
        print("Example: python create-tint-mask.py ../graphics/entity/carriage-engine/main.png")
        print("Options:")
        print("  --reverse    Keep iron parts and remove copper parts instead")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    # Check for --reverse flag
    reverse = '--reverse' in sys.argv
    if reverse:
        sys.argv.remove('--reverse')
    
    # Default output path
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        # Generate output path by adding "-mask" before extension
        base, ext = os.path.splitext(input_path)
        suffix = "mask"
        output_path = f"{base}{suffix}{ext}"
    
    # Optional opacity parameter
    opacity = 0.3
    if len(sys.argv) >= 4:
        opacity = float(sys.argv[3])
    
    create_tint_mask(input_path, output_path, opacity, reverse)

if __name__ == "__main__":
    main()

