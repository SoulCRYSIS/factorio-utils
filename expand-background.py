#!/usr/bin/env python3
"""
Script to expand the transparent background of a PNG image.
Adds transparent padding around an image.
"""

import argparse
from PIL import Image
import os


def expand_background(input_path, output_path=None, top=0, bottom=0, left=0, right=0, all_sides=None):
    """
    Expand the transparent background of a PNG image.
    
    Args:
        input_path: Path to input PNG file
        output_path: Path to output PNG file (optional, defaults to input_expanded.png)
        top: Pixels to add to top
        bottom: Pixels to add to bottom
        left: Pixels to add to left
        right: Pixels to add to right
        all_sides: Pixels to add to all sides (overrides individual values if set)
    """
    # Load the image
    img = Image.open(input_path)
    
    # Ensure image has alpha channel
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # If all_sides is specified, use it for all directions
    if all_sides is not None:
        top = bottom = left = right = all_sides
    
    # Calculate new dimensions
    original_width, original_height = img.size
    new_width = original_width + left + right
    new_height = original_height + top + bottom
    
    # Create new image with transparent background
    expanded = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
    
    # Paste original image at the offset position
    expanded.paste(img, (left, top), img)
    
    # Determine output path
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_expanded{ext}"
    
    # Save the result
    expanded.save(output_path, 'PNG')
    
    print(f"Expanded image saved to: {output_path}")
    print(f"Original size: {original_width}x{original_height}")
    print(f"New size: {new_width}x{new_height}")
    print(f"Padding: top={top}, bottom={bottom}, left={left}, right={right}")


def main():
    parser = argparse.ArgumentParser(
        description='Expand the transparent background of a PNG image',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add 10 pixels to all sides
  %(prog)s input.png --all 10
  
  # Add 20 pixels to top and bottom, 30 to left and right
  %(prog)s input.png --top 20 --bottom 20 --left 30 --right 30
  
  # Specify output file
  %(prog)s input.png --all 15 --output output.png
  
  # Different padding for each side
  %(prog)s input.png --top 5 --bottom 10 --left 15 --right 20
        """
    )
    
    parser.add_argument('input', help='Input PNG file path')
    parser.add_argument('--output', '-o', help='Output PNG file path (optional)')
    parser.add_argument('--all', '-a', type=int, help='Pixels to add to all sides')
    parser.add_argument('--top', '-t', type=int, default=0, help='Pixels to add to top')
    parser.add_argument('--bottom', '-b', type=int, default=0, help='Pixels to add to bottom')
    parser.add_argument('--left', '-l', type=int, default=0, help='Pixels to add to left')
    parser.add_argument('--right', '-r', type=int, default=0, help='Pixels to add to right')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        return 1
    
    # Validate that at least some padding is specified
    if args.all is None and args.top == 0 and args.bottom == 0 and args.left == 0 and args.right == 0:
        print("Error: No padding specified. Use --all or specify individual sides.")
        parser.print_help()
        return 1
    
    try:
        expand_background(
            args.input,
            output_path=args.output,
            top=args.top,
            bottom=args.bottom,
            left=args.left,
            right=args.right,
            all_sides=args.all
        )
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())

