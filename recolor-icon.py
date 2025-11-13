#!/usr/bin/env python3
"""
Script to recolor PNG images to match a specific style (e.g., dark icon style).
Can convert images to dark/black tones while preserving alpha channel.
"""

import argparse
from PIL import Image, ImageEnhance
import os


def recolor_to_dark(input_path, output_path=None, target_color=(40, 40, 40), preserve_shading=True, alpha_threshold=10):
    """
    Recolor a PNG image to dark tones similar to icon style.
    
    Args:
        input_path: Path to input PNG file
        output_path: Path to output PNG file (optional)
        target_color: RGB tuple for the target dark color (default: dark gray)
        preserve_shading: If True, preserves brightness variations from original
        alpha_threshold: Minimum alpha value to consider (0-255)
    """
    # Load the image
    img = Image.open(input_path)
    
    # Ensure image has alpha channel
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Get pixel data
    pixels = img.load()
    width, height = img.size
    
    # Create new image
    result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    result_pixels = result.load()
    
    # Process each pixel
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            
            # Skip nearly transparent pixels
            if a < alpha_threshold:
                result_pixels[x, y] = (0, 0, 0, 0)
                continue
            
            if preserve_shading:
                # Calculate brightness of original pixel (0.0 to 1.0)
                brightness = (r + g + b) / (3 * 255.0)
                
                # Apply brightness to target color
                new_r = int(target_color[0] * brightness)
                new_g = int(target_color[1] * brightness)
                new_b = int(target_color[2] * brightness)
                
                # Ensure at least some visibility for non-black pixels
                if brightness > 0 and new_r == 0 and new_g == 0 and new_b == 0:
                    new_r = new_g = new_b = 1
            else:
                # Use target color directly
                new_r, new_g, new_b = target_color
            
            # Keep original alpha
            result_pixels[x, y] = (new_r, new_g, new_b, a)
    
    # Determine output path
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_recolored{ext}"
    
    # Save the result
    result.save(output_path, 'PNG')
    
    print(f"Recolored image saved to: {output_path}")
    print(f"Target color: RGB{target_color}")
    print(f"Size: {width}x{height}")


def recolor_to_black(input_path, output_path=None, preserve_shading=True):
    """
    Recolor to pure black (like the shortcut icon style).
    """
    return recolor_to_dark(input_path, output_path, target_color=(0, 0, 0), preserve_shading=preserve_shading)


def recolor_custom(input_path, output_path=None, hex_color=None, rgb_color=None, preserve_shading=True):
    """
    Recolor to custom color specified as hex or RGB.
    """
    if hex_color:
        # Convert hex to RGB
        hex_color = hex_color.lstrip('#')
        rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    if rgb_color is None:
        rgb_color = (40, 40, 40)  # Default dark gray
    
    return recolor_to_dark(input_path, output_path, target_color=rgb_color, preserve_shading=preserve_shading)


def main():
    parser = argparse.ArgumentParser(
        description='Recolor PNG images to match icon style (dark/black tones)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert to black (like route-shortcut icon)
  %(prog)s input.png --black
  
  # Convert to dark gray with shading preserved
  %(prog)s input.png --rgb 40 40 40
  
  # Convert to specific hex color
  %(prog)s input.png --hex "#282828"
  
  # Flat color (no shading preservation)
  %(prog)s input.png --black --no-shading
  
  # Specify output file
  %(prog)s input.png --black --output output.png
        """
    )
    
    parser.add_argument('input', help='Input PNG file path')
    parser.add_argument('--output', '-o', help='Output PNG file path (optional)')
    
    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument('--black', action='store_true', 
                            help='Convert to pure black (icon style)')
    color_group.add_argument('--hex', help='Target color as hex (e.g., #282828)')
    color_group.add_argument('--rgb', nargs=3, type=int, metavar=('R', 'G', 'B'),
                            help='Target color as RGB values (0-255)')
    
    parser.add_argument('--no-shading', action='store_true',
                       help='Use flat color (don\'t preserve brightness variations)')
    parser.add_argument('--alpha-threshold', type=int, default=10,
                       help='Minimum alpha value to process (0-255, default: 10)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    preserve_shading = not args.no_shading
    
    try:
        if args.black:
            recolor_to_black(args.input, output_path=args.output, preserve_shading=preserve_shading)
        elif args.hex:
            recolor_custom(args.input, output_path=args.output, hex_color=args.hex, 
                          preserve_shading=preserve_shading)
        elif args.rgb:
            rgb_tuple = tuple(args.rgb)
            recolor_custom(args.input, output_path=args.output, rgb_color=rgb_tuple,
                          preserve_shading=preserve_shading)
        else:
            # Default to dark gray
            print("No color specified, using default dark gray (40, 40, 40)")
            recolor_to_dark(args.input, output_path=args.output, preserve_shading=preserve_shading)
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

