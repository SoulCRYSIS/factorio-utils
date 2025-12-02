#!/usr/bin/env python3
"""
Script to desaturate PNG images (make them greyish) without darkening them.
Useful for creating "raw" versions of icons.
"""

import argparse
import os
from PIL import Image, ImageEnhance

def desaturate_image(input_path, output_path=None, factor=0.5):
    """
    Desaturate an image.

    Args:
        input_path: Path to input PNG file
        output_path: Path to output PNG file (optional)
        factor: Saturation factor (0.0 = grayscale, 1.0 = original, >1.0 = oversaturated)
    """
    # Load the image
    try:
        img = Image.open(input_path)
    except Exception as e:
        print(f"Error opening image {input_path}: {e}")
        return False

    # Ensure image has alpha channel
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Separate alpha channel to preserve transparency perfectly
    # (though ImageEnhance usually handles it, explicitly separating is safer for edge cases)
    # Actually ImageEnhance.Color works on RGB, it might affect Alpha if not careful?
    # Documentation says it works on RGB images. For RGBA, it might treat Alpha as color channel?
    # Let's separate alpha just in case.
    
    r, g, b, a = img.split()
    rgb_img = Image.merge('RGB', (r, g, b))
    
    converter = ImageEnhance.Color(rgb_img)
    desaturated_rgb = converter.enhance(factor)
    
    # Combine back with original alpha
    r_new, g_new, b_new = desaturated_rgb.split()
    result = Image.merge('RGBA', (r_new, g_new, b_new, a))

    # Determine output path if not provided
    if output_path is None:
        directory, filename = os.path.split(input_path)
        output_filename = f"raw-{filename}"
        output_path = os.path.join(directory, output_filename)

    # Save the result
    try:
        result.save(output_path, 'PNG')
        print(f"Desaturated image saved to: {output_path}")
        print(f"Saturation factor: {factor}")
        return True
    except Exception as e:
        print(f"Error saving image {output_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Desaturate PNG images (make them greyish) to create "raw" icon variants.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create raw-icon.png (completely desaturated)
  %(prog)s graphics/icons/my-icon.png
  
  # Partially desaturate (50% color)
  %(prog)s graphics/icons/my-icon.png --factor 0.5
        """
    )
    
    parser.add_argument('input', help='Input PNG file path')
    parser.add_argument('--factor', type=float, default=0.5,
                       help='Saturation factor (0.0=grayscale, 1.0=original). Default: 0.5')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        return 1
        
    success = desaturate_image(args.input, factor=args.factor)
    return 0 if success else 1

if __name__ == '__main__':
    exit(main())

