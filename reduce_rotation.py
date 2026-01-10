#!/usr/bin/env python3
"""
Script to reduce rotation count of a spritesheet by skipping frames.
Useful for reducing file size or matching rotation counts (e.g., 64 -> 16).
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

def reduce_rotation(input_path, output_path=None, skip=None, keep_indices=None, 
                   frame_count=None, frame_size=None):
    """
    Reduce rotation count of a spritesheet.
    
    Args:
        input_path: Path to input spritesheet
        output_path: Path to output spritesheet (optional)
        skip: Keep every Nth frame (e.g., 4 to keep 0, 4, 8...)
        keep_indices: List of specific indices to keep (0-based)
        frame_count: Total frames in the input sheet (to help deduce grid)
        frame_size: Tuple (width, height) of a single frame (alternative to frame_count)
    """
    if skip is None and keep_indices is None:
        raise ValueError("Must specify either 'skip' or 'keep_indices'")
    
    img = Image.open(input_path)
    img_width, img_height = img.size
    
    # Determine grid layout and frame size
    cols = 0
    rows = 0
    fw = 0
    fh = 0
    
    if frame_size:
        fw, fh = frame_size
        cols = img_width // fw
        rows = img_height // fh
        total_frames = cols * rows
        # Check if dimensions match
        if cols * fw != img_width or rows * fh != img_height:
             print(f"Warning: Image size {img_width}x{img_height} is not a multiple of frame size {fw}x{fh}")
    elif frame_count:
        total_frames = frame_count
        cols = get_grid_layout(total_frames)
        rows = math.ceil(total_frames / cols)
        
        fw = img_width // cols
        fh = img_height // rows
        
        # Verify
        if fw * cols != img_width:
             # Sometimes sheets are not full
             # e.g. 5 frames in 3x2 grid. Width is 3*w.
             pass
        
        # Recalculate based on image dimensions to be precise
        # Assuming uniform grid
        fw = img_width // cols
        fh = img_height // rows
    else:
        # Try to guess based on common Factorio numbers
        # 64 rotations is common for vehicles. 
        # 32, 16, 8, 4, 1.
        
        # Heuristic: Check if square-ish grid matches common counts
        possible_counts = [64, 32, 24, 16, 12, 8, 4]
        found = False
        for count in possible_counts:
            c = get_grid_layout(count)
            r = math.ceil(count / c)
            if img_width % c == 0 and img_height % r == 0:
                # Check aspect ratio of frame?
                # Usually frames are somewhat square or known aspect
                w = img_width // c
                h = img_height // r
                # If we assume frames are roughly square? Not always true.
                print(f"Guessing frame count: {count} ({c}x{r} grid)")
                total_frames = count
                cols = c
                rows = r
                fw = w
                fh = h
                found = True
                break
        
        if not found:
            raise ValueError("Could not determine frame count/size. Please specify --frame-count or --frame-size")

    print(f"Processing {input_path}")
    print(f"Input: {img_width}x{img_height}, {total_frames} frames ({cols}x{rows}), Frame size: {fw}x{fh}")

    # Extract frames
    frames = []
    for i in range(total_frames):
        c = i % cols
        r = i // cols
        x = c * fw
        y = r * fh
        
        # Check bounds
        if x < img_width and y < img_height:
            frame = img.crop((x, y, x + fw, y + fh))
            frames.append(frame)
    
    # Select frames
    selected_frames = []
    if keep_indices:
        for idx in keep_indices:
            if 0 <= idx < len(frames):
                selected_frames.append(frames[idx])
            else:
                print(f"Warning: Index {idx} out of bounds (0-{len(frames)-1})")
    elif skip:
        # User said "skip by 4" -> keep 0, 4, 8...
        # So step = skip
        for i in range(0, len(frames), skip):
            selected_frames.append(frames[i])
            
    if not selected_frames:
        raise ValueError("No frames selected!")

    new_count = len(selected_frames)
    print(f"Reduced from {len(frames)} to {new_count} frames")

    # Determine new grid
    new_cols = get_grid_layout(new_count)
    new_rows = math.ceil(new_count / new_cols)
    
    new_width = new_cols * fw
    new_height = new_rows * fh
    
    print(f"Output: {new_width}x{new_height} ({new_cols}x{new_rows})")

    # Create new image
    result = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
    
    for i, frame in enumerate(selected_frames):
        c = i % new_cols
        r = i // new_cols
        x = c * fw
        y = r * fh
        result.paste(frame, (x, y))

    # Save
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_reduced_{new_count}{ext}"
        
    result.save(output_path)
    print(f"Saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Reduce rotation count of spritesheet.')
    parser.add_argument('input', help='Input spritesheet path')
    parser.add_argument('--output', '-o', help='Output path')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--skip', type=int, help='Keep every Nth frame (e.g. 4)')
    group.add_argument('--indices', type=int, nargs='+', help='Specific indices to keep')
    
    # Optional inputs for grid
    parser.add_argument('--count', type=int, help='Total frame count in input')
    parser.add_argument('--size', type=int, nargs=2, metavar=('W', 'H'), help='Frame size (width height)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        return 1
        
    try:
        reduce_rotation(
            args.input, 
            args.output, 
            skip=args.skip, 
            keep_indices=args.indices,
            frame_count=args.count,
            frame_size=tuple(args.size) if args.size else None
        )
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

