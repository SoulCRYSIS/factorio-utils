#!/usr/bin/env python3
"""
Script to convert all existing (non-transparent) pixels in an image to completely opaque black.
Transparent pixels remain transparent.
"""

import sys
from PIL import Image
import argparse


def blacken_image(input_path, output_path=None):
    """
    Convert all pixels to completely opaque black.
    
    Args:
        input_path: Path to input image
        output_path: Path to output image (if None, overwrites input)
    """
    # Open the image
    img = Image.open(input_path)
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Get pixel data
    pixels = img.load()
    width, height = img.size
    
    # Convert all non-transparent pixels to opaque black
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # Only convert pixels that have content (alpha > 0)
            if a > 0:
                # Set to opaque black (RGB: 0,0,0, Alpha: 255)
                pixels[x, y] = (0, 0, 0, 255)
            # Transparent pixels remain transparent
    
    # Save the result
    if output_path is None:
        output_path = input_path
    
    img.save(output_path)
    print(f"Blackened image saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert all existing (non-transparent) pixels in an image to completely opaque black'
    )
    parser.add_argument(
        'input',
        help='Input image path'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output image path (default: overwrite input)',
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        blacken_image(args.input, args.output)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

