#!/usr/bin/env python3
"""
Script to create a circular shape (circle, ring, or arc) and save as PNG.
Supports generating single direction (default) or 4 directional frames (North, East, South, West).
"""

import argparse
import sys
from PIL import Image, ImageDraw

def hex_to_rgb(hex_color):
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_single_shape(radius, inner_radius, rgb, alpha, width, height, angle_span, center_angle):
    """
    Helper to create a single shape image.
    
    Args:
        radius: Outer radius
        inner_radius: Inner radius
        rgb: RGB tuple
        alpha: Alpha value (0-255)
        width: Image width
        height: Image height
        angle_span: Total angle span
        center_angle: The center angle of the arc in degrees (0=East, 90=South, 180=West, 270=North)
    """
    # Super-sampling for anti-aliasing
    scale = 4
    w_ss = width * scale
    h_ss = height * scale
    
    cx = w_ss / 2
    cy = h_ss / 2
    
    r_out = radius * scale
    r_in = inner_radius * scale
    
    # Create mask
    mask = Image.new('L', (w_ss, h_ss), 0)
    draw_mask = ImageDraw.Draw(mask)
    
    if angle_span >= 360:
        start = 0
        end = 360
    else:
        half_angle = angle_span / 2
        start = center_angle - half_angle
        end = center_angle + half_angle
    
    bbox_out = [cx - r_out, cy - r_out, cx + r_out, cy + r_out]
    draw_mask.pieslice(bbox_out, start=start, end=end, fill=255)
    
    if r_in > 0:
        bbox_in = [cx - r_in, cy - r_in, cx + r_in, cy + r_in]
        draw_mask.pieslice(bbox_in, start=start, end=end, fill=0)
    
    # Create final alpha channel
    alpha_factor = alpha / 255.0
    final_alpha = mask.point(lambda p: int(p * alpha_factor))
    
    # Create RGB image
    solid_rgb = Image.new('RGB', (w_ss, h_ss), rgb)
    
    # Combine RGB and Alpha
    result = Image.merge('RGBA', (*solid_rgb.split(), final_alpha))
    
    # Downsample
    result = result.resize((width, height), Image.Resampling.LANCZOS)
    return result

def create_shape(output_path, radius, inner_radius, color_hex, alpha, width, height, angle, directions=1):
    """
    Create circular shape(s).
    
    Args:
        ...
        directions: Number of directions (1 or 4).
                   If 4, creates a sprite sheet with North, East, South, West.
    """
    # Parse color
    try:
        rgb = hex_to_rgb(color_hex)
    except ValueError:
        print(f"Error: Invalid color format '{color_hex}'. Use hex (e.g. #FF0000)", file=sys.stderr)
        sys.exit(1)
        
    if directions == 1:
        # Default behavior: Single image centered North (270 degrees)
        result = create_single_shape(radius, inner_radius, rgb, alpha, width, height, angle, 270)
        final_output = result
        print(f"Created single frame (North/Up).")
        
    elif directions == 4:
        # create 4 frames: N, E, S, W
        # N=270, E=0, S=90, W=180
        center_angles = [90, 0, 270, 180]
        frames = []
        for i, center in enumerate(center_angles):
            frames.append(create_single_shape(radius, inner_radius, rgb, alpha, width, height, angle, center))
            
        # Combine into horizontal strip
        total_width = width * 4
        final_output = Image.new('RGBA', (total_width, height), (0,0,0,0))
        for i, frame in enumerate(frames):
            final_output.paste(frame, (i * width, 0))
            
        print(f"Created 4 frames (N, E, S, W).")
        
    else:
        print(f"Error: only directions=1 or 4 are supported.", file=sys.stderr)
        sys.exit(1)
    
    final_output.save(output_path)
    print(f"Saved to {output_path}")
    print(f"Size: {final_output.width}x{final_output.height}, Radius: {radius}, Inner: {inner_radius}, Angle: {angle}")


def main():
    parser = argparse.ArgumentParser(description="Create a circular shape/arc PNG.")
    parser.add_argument('output', help="Output PNG file path")
    parser.add_argument('--radius', '-r', type=float, required=True, help="Outer radius")
    parser.add_argument('--inner-radius', '-ir', type=float, default=0, help="Inner radius (default 0)")
    parser.add_argument('--color', '-c', type=str, default="#FFFFFF", help="Color hex (default #FFFFFF)")
    parser.add_argument('--alpha', '-a', type=int, default=255, help="Alpha 0-255 (default 255)")
    parser.add_argument('--size', '-s', type=str, required=True, help="Image size WxH (e.g. 64x64) or N (NxN)")
    parser.add_argument('--angle', type=float, default=360, help="Angle span in degrees (default 360)")
    parser.add_argument('--directions', '-d', type=int, default=1, help="Number of directions: 1 or 4 (default 1). If 4, creates N,E,S,W strip.")
    
    args = parser.parse_args()
    
    # Parse size
    if 'x' in args.size.lower():
        try:
            w, h = map(int, args.size.lower().split('x'))
        except ValueError:
            print("Error: Invalid size format. Use WxH (e.g. 64x64)", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            w = h = int(args.size)
        except ValueError:
            print("Error: Invalid size format. Use integer or WxH", file=sys.stderr)
            sys.exit(1)
            
    create_shape(args.output, args.radius, args.inner_radius, args.color, args.alpha, w, h, args.angle, args.directions)

if __name__ == "__main__":
    main()
