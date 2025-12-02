#!/usr/bin/env python3
"""
Script to cut a cross shape from the middle of an image (remove central columns and rows).
Stitches the remaining 4 corners together.
Default cut size is 192px.
"""

import sys
from PIL import Image
import argparse


def cut_cross(input_path, cut_size, output_path=None):
    """
    Remove a cross shape from the center of the image.
    
    Args:
        input_path: Path to input image
        cut_size: Size of the cross to cut (width and height)
        output_path: Path to output image (if None, overwrites input)
    """
    # Open the image
    img = Image.open(input_path)
    width, height = img.size
    
    # Calculate dimensions
    center_x = width // 2
    center_y = height // 2
    half_cut = cut_size // 2
    
    # Define boundaries of the central cross
    # Left of vertical strip
    x1 = center_x - half_cut
    # Right of vertical strip
    x2 = center_x + half_cut
    
    # Top of horizontal strip
    y1 = center_y - half_cut
    # Bottom of horizontal strip
    y2 = center_y + half_cut
    
    # Ensure boundaries are within image
    x1 = max(0, x1)
    x2 = min(width, x2)
    y1 = max(0, y1)
    y2 = min(height, y2)
    
    # Define the 4 corners
    # box = (left, upper, right, lower)
    tl_box = (0, 0, x1, y1)
    tr_box = (x2, 0, width, y1)
    bl_box = (0, y2, x1, height)
    br_box = (x2, y2, width, height)
    
    # Crop the corners
    tl = img.crop(tl_box)
    tr = img.crop(tr_box)
    bl = img.crop(bl_box)
    br = img.crop(br_box)
    
    # Calculate new dimensions
    new_width = tl.width + tr.width
    new_height = tl.height + bl.height
    
    if new_width == 0 or new_height == 0:
        print("Error: Resulting image would have 0 width or height. Cut size too large?")
        return

    # Create new image
    new_img = Image.new(img.mode, (new_width, new_height))
    
    # Paste corners
    new_img.paste(tl, (0, 0))
    new_img.paste(tr, (tl.width, 0))
    new_img.paste(bl, (0, tl.height))
    new_img.paste(br, (tl.width, tl.height))
    
    # Save the result
    if output_path is None:
        output_path = input_path
    
    new_img.save(output_path)
    print(f"Processed {input_path}: {width}x{height} -> {new_width}x{new_height} (Cut {cut_size}px)")


def main():
    parser = argparse.ArgumentParser(
        description='Cut a cross shape from the middle of an image (remove central columns and rows).'
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
        '-s', '--size',
        help='Size of the cross to cut in pixels (default: 192)',
        type=int,
        default=192
    )
    
    args = parser.parse_args()
    
    try:
        cut_cross(args.input, args.size, args.output)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

