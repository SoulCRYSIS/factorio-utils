#!/usr/bin/env python3
"""
Script to convert all existing (non-transparent) pixels in an image to completely opaque black.
Applies edge softening to prevent artifacts.
Transparent pixels remain transparent.
"""

import sys
from PIL import Image, ImageFilter
import argparse


def blacken_image(input_path, threshold, blur_radius, output_path=None):
    """
    Convert all existing (non-transparent) pixels to completely opaque black.
    Applies edge softening to prevent artifacts.
    
    Args:
        input_path: Path to input image
        threshold: Alpha threshold for considering a pixel non-transparent (0-255)
        output_path: Path to output image (if None, overwrites input)
    """
    # Open the image
    img = Image.open(input_path)
    
    # Convert to RGBA if not already
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Get pixel data as a list (more reliable than pixels.load())
    pixel_data = list(img.getdata())
    width, height = img.size
    
    # Convert all non-transparent pixels to fully opaque black
    new_pixel_data = []
    for r, g, b, a in pixel_data:
        # Only convert pixels that have content (alpha > threshold)
        if a > threshold:
            # Set to fully opaque black (RGB: 0,0,0, Alpha: 255)
            new_pixel_data.append((0, 0, 0, 255))
        else:
            # Transparent pixels remain transparent
            new_pixel_data.append((r, g, b, a))
    
    # Put the modified pixel data back into the image
    img.putdata(new_pixel_data)
    
    # Apply slight blur to alpha channel to soften edges and prevent artifacts
    # Split into channels
    r, g, b, a = img.split()
    
    # Apply a slight blur to the alpha channel only
    a_blurred = a.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    # Recombine: RGB channels are all black (0), use blurred alpha
    img = Image.merge('RGBA', (r, g, b, a_blurred))
    
    # Save the result
    if output_path is None:
        output_path = input_path
    
    img.save(output_path)
    print(f"Blackened image saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert all existing (non-transparent) pixels in an image to completely opaque black. Applies edge softening.'
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
    parser.add_argument(
        '-t', '--threshold',
        help='Threshold for considering a pixel non-transparent (0-255, default: 20)',
        type=int,
        default=20
    )
    parser.add_argument(
        '-b', '--blur-radius',
        help='Blur radius for edge softening (default: 0)',
        type=int,
        default=0
    )
    
    args = parser.parse_args()
    
    try:
        blacken_image(args.input, args.threshold, args.blur_radius, args.output)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

