#!/usr/bin/env python3
"""
Script to create icon mipmap by scaling input image to 64x64, 32x32, 16x16, 8x8
and placing them horizontally (left to right, big to small) in a single PNG.
All mipmaps are top-aligned.
"""

import argparse
from PIL import Image
import os
import sys


def create_mipmap(input_path, output_path=None):
    """
    Create mipmap from input icon.
    
    Args:
        input_path: Path to input PNG file
        output_path: Path to output PNG file (optional)
    """
    # Load the image
    img = Image.open(input_path)
    
    # Check if image is square
    width, height = img.size
    if width != height:
        raise ValueError(f"Input image must be square, but got {width}x{height}")
    
    # Ensure image has alpha channel
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Define mipmap sizes (big to small)
    sizes = [64, 32, 16, 8]
    
    # Create resized versions
    mipmaps = []
    for size in sizes:
        # Resize using high-quality resampling (LANCZOS)
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        mipmaps.append(resized)
    
    # Calculate total width (sum of all mipmap widths)
    total_width = sum(sizes)
    # Height is the largest mipmap height
    total_height = sizes[0]  # 64
    
    # Create output image with transparent background
    result = Image.new('RGBA', (total_width, total_height), (0, 0, 0, 0))
    
    # Paste mipmaps horizontally, left to right, top-aligned
    x_offset = 0
    for mipmap in mipmaps:
        result.paste(mipmap, (x_offset, 0), mipmap)
        x_offset += mipmap.width
    
    # Determine output path
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}{ext}"
    
    # Save the result
    result.save(output_path, 'PNG')
    
    print(f"Mipmap created: {output_path}")
    print(f"Output size: {total_width}x{total_height}")
    print(f"Mipmap sizes: {' x '.join(map(str, sizes))}")


def main():
    parser = argparse.ArgumentParser(
        description='Create icon mipmap (64x64, 32x32, 16x16, 8x8) in a single PNG',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create mipmap with default output name
  %(prog)s icon.png
  
  # Specify output file
  %(prog)s icon.png --output icon_mipmap.png
        """
    )
    
    parser.add_argument('input', help='Input PNG file path')
    parser.add_argument('--output', '-o', help='Output PNG file path (optional)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1
    
    try:
        create_mipmap(args.input, output_path=args.output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())

