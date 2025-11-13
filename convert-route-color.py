from PIL import Image
import sys
import os
import glob

def rgb_to_hsv(r, g, b):
    """Convert RGB to HSV color space."""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    delta = max_val - min_val
    
    # Value
    v = max_val
    
    # Saturation
    if max_val == 0:
        s = 0
    else:
        s = delta / max_val
    
    # Hue
    if delta == 0:
        h = 0
    elif max_val == r:
        h = ((g - b) / delta) % 6
    elif max_val == g:
        h = (b - r) / delta + 2
    else:
        h = (r - g) / delta + 4
    h = h * 60
    
    return h, s, v

def is_blue_pixel(r, g, b, threshold=30):
    """
    Check if a pixel is blue.
    Blue pixels have:
    - High blue component relative to red and green
    - Hue in the blue range (200-260 degrees)
    """
    # Simple check: blue is significantly higher than red and green
    if b > r + threshold and b > g + threshold:
        return True
    
    # More sophisticated HSV check
    h, s, v = rgb_to_hsv(r, g, b)
    # Blue hue range: 200-260 degrees, with sufficient saturation
    if 200 <= h <= 260 and s > 0.3 and v > 0.2:
        return True
    
    return False

def convert_blue_to_orange(input_file, output_file=None):
    """
    Convert blue pixels to orange in an image.
    Preserves transparency and non-blue pixels.
    """
    # Load the image
    img = Image.open(input_file)
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Get pixel data
    pixels = img.load()
    width, height = img.size
    
    # Orange color (bright orange, similar to Factorio's orange)
    orange_r, orange_g, orange_b = 255, 140, 0  # Bright orange
    
    # Count converted pixels for reporting
    converted_count = 0
    total_pixels = 0
    
    # Process each pixel
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            
            # Skip fully transparent pixels
            if a == 0:
                continue
            
            total_pixels += 1
            
            # Check if pixel is blue
            if is_blue_pixel(r, g, b):
                # Preserve the original alpha and brightness
                # Blend orange with original brightness
                original_brightness = max(r, g, b) / 255.0
                
                # Scale orange to match original brightness
                new_r = int(orange_r * original_brightness)
                new_g = int(orange_g * original_brightness)
                new_b = int(orange_b * original_brightness)
                
                pixels[x, y] = (new_r, new_g, new_b, a)
                converted_count += 1
    
    # Save the converted image
    if output_file is None:
        output_file = input_file
    
    img.save(output_file)
    print(f"Converted {converted_count}/{total_pixels} pixels in {os.path.basename(input_file)}")
    return converted_count, total_pixels

def find_route_sprite_files(project_root):
    """Find all route sprite files."""
    files = []
    
    # Main route sprite
    route_file = os.path.join(project_root, "graphics", "entity", "route", "route.png")
    if os.path.exists(route_file):
        files.append(route_file)
    
    # Legacy straight rail sprites
    legacy_straight_dir = os.path.join(project_root, "graphics", "entity", "legacy-straight-rail")
    if os.path.exists(legacy_straight_dir):
        pattern = os.path.join(legacy_straight_dir, "*.png")
        files.extend(glob.glob(pattern))
    
    # Legacy curved rail sprites
    legacy_curved_dir = os.path.join(project_root, "graphics", "entity", "legacy-curved-rail")
    if os.path.exists(legacy_curved_dir):
        pattern = os.path.join(legacy_curved_dir, "*.png")
        files.extend(glob.glob(pattern))
    
    return files

if __name__ == "__main__":
    # Get script directory and project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Find all route sprite files
    sprite_files = find_route_sprite_files(project_root)
    
    if not sprite_files:
        print("No route sprite files found!")
        sys.exit(1)
    
    print(f"Found {len(sprite_files)} route sprite file(s)")
    print("Converting blue pixels to orange...")
    print("-" * 60)
    
    total_converted = 0
    total_pixels = 0
    
    # Process each file
    for sprite_file in sprite_files:
        try:
            converted, pixels = convert_blue_to_orange(sprite_file)
            total_converted += converted
            total_pixels += pixels
        except Exception as e:
            print(f"Error processing {os.path.basename(sprite_file)}: {e}")
    
    print("-" * 60)
    print(f"Conversion complete!")
    print(f"Total: {total_converted}/{total_pixels} pixels converted across {len(sprite_files)} file(s)")

