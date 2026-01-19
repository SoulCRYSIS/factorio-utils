#!/usr/bin/env python3
"""
Script to shift frames in a spritesheet.
"Shift by x" means cut the first x frames and move them to the end.
"""

import argparse
import math
import sys
from PIL import Image
import os

# Row length mapping: { total_frames: columns_per_row }
# Copied from auto_merge_sprites.py logic
FRAME_COLUMN_MAPPING = {
    1: 1,
    2: 2,
    3: 3,
    4: 2,
    5: 3,
    6: 3,
    7: 4,
    8: 4,
    9: 3,
    10: 5,
    12: 4,
    16: 4,
    20: 5,
    24: 6,
    30: 8, # Should be 25:8 ? Checking source... let's stick to common map
    25: 8,
    32: 8,
    64: 8,
    128: 16, # Extrapolated
}

def get_grid_layout(frame_count):
    """Determine columns (frames per row) based on mapping."""
    if frame_count in FRAME_COLUMN_MAPPING:
        return FRAME_COLUMN_MAPPING[frame_count]
    
    # Default calculation: try to be square-ish
    return math.ceil(math.sqrt(frame_count))

def shift_frames(input_path, output_path=None, shift_amount=0, 
                 frame_count=None, frame_size=None):
    """
    Shift frames of a spritesheet.
    
    Args:
        input_path: Path to input spritesheet
        output_path: Path to output spritesheet (optional)
        shift_amount: Number of frames to shift (cut from start, move to end)
        frame_count: Total frames in the input sheet (to help deduce grid)
        frame_size: Tuple (width, height) of a single frame (alternative to frame_count)
    """
    
    img = Image.open(input_path)
    img_width, img_height = img.size
    
    # Determine grid layout and frame size
    cols = 0
    rows = 0
    fw = 0
    fh = 0
    total_frames = 0
    
    if frame_size:
        fw, fh = frame_size
        cols = img_width // fw
        rows = img_height // fh
        total_frames = cols * rows
    elif frame_count:
        total_frames = frame_count
        cols = get_grid_layout(total_frames)
        rows = math.ceil(total_frames / cols)
        
        fw = img_width // cols
        fh = img_height // rows
    else:
        # Heuristic: Check if square-ish grid matches common counts
        possible_counts = [128, 64, 32, 24, 20, 16, 12, 10, 8, 4]
        found = False
        for count in possible_counts:
            c = get_grid_layout(count)
            r = math.ceil(count / c)
            if img_width % c == 0 and img_height % r == 0:
                print(f"Guessing frame count: {count} ({c}x{r} grid)")
                total_frames = count
                cols = c
                rows = r
                fw = img_width // c
                fh = img_height // r
                found = True
                break
        
        if not found:
            # Fallback: assume square frames if possible
            if img_width == img_height:
                # Could be 1 frame or 2x2 or 3x3
                 # But usually 64 frames is 8x8 which is square.
                 # If we didn't match 64, 16, 4 above...
                 pass
            
            raise ValueError("Could not determine frame count/size. Please specify --frame-count or --frame-size")

    print(f"Processing {input_path}")
    print(f"Input: {img_width}x{img_height}, {total_frames} frames ({cols}x{rows}), Frame size: {fw}x{fh}")

    # Extract frames
    frames = []
    # We only care about up to total_frames, ignoring empty slots if any (though typically factorio sheets are packed)
    # Actually, iterate through grid positions
    for i in range(total_frames):
        c = i % cols
        r = i // cols
        x = c * fw
        y = r * fh
        
        # Check bounds
        if x < img_width and y < img_height:
            frame = img.crop((x, y, x + fw, y + fh))
            frames.append(frame)

    if not frames:
        raise ValueError("No frames found!")

    # Perform shift
    # Cut first X frames -> move to end
    # e.g. [0, 1, 2, 3], shift 1 -> [1, 2, 3, 0]
    real_shift = shift_amount % len(frames)
    shifted_frames = frames[real_shift:] + frames[:real_shift]
    
    print(f"Shifted by {real_shift} frames")

    # Reconstruct image
    # We keep the same layout as input
    output_cols = cols
    output_rows = rows # Or math.ceil(len(frames) / cols)
    
    result = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    
    for i, frame in enumerate(shifted_frames):
        c = i % output_cols
        r = i // output_cols
        x = c * fw
        y = r * fh
        result.paste(frame, (x, y))

    # Save
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_shifted_{real_shift}{ext}"
        
    result.save(output_path)
    print(f"Saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Shift frames in a spritesheet (rotate sequence).')
    parser.add_argument('input', help='Input spritesheet path')
    parser.add_argument('shift', type=int, help='Number of frames to shift (cut from start, append to end)')
    parser.add_argument('--output', '-o', help='Output path')
    
    # Optional inputs for grid
    parser.add_argument('--count', type=int, help='Total frame count in input')
    parser.add_argument('--size', type=int, nargs=2, metavar=('W', 'H'), help='Frame size (width height)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        return 1
        
    try:
        shift_frames(
            args.input, 
            args.output, 
            shift_amount=args.shift,
            frame_count=args.count,
            frame_size=tuple(args.size) if args.size else None
        )
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

