#!/usr/bin/env python3
"""
Script to reverse the rotation direction of frames in a sprite sheet.
Keeps frame 0 (north/0°) fixed and reverses frames 1-N.
Can process single files or entire folders.
"""

from PIL import Image
import sys
import os
import argparse
import math
from pathlib import Path

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

def determine_grid(img_width, img_height, frame_count=None, frame_size=None):
    """
    Determine grid layout (cols, rows, frame_width, frame_height, total_frames).
    """
    if frame_size:
        fw, fh = frame_size
        cols = img_width // fw
        rows = img_height // fh
        total_frames = cols * rows
        return cols, rows, fw, fh, total_frames

    if frame_count:
        total_frames = frame_count
        cols = get_grid_layout(total_frames)
        rows = math.ceil(total_frames / cols)
        fw = img_width // cols
        fh = img_height // rows
        return cols, rows, fw, fh, total_frames
    
    # Heuristic detection
    possible_counts = [64, 32, 24, 16, 12, 8, 4]
    for count in possible_counts:
        c = get_grid_layout(count)
        r = math.ceil(count / c)
        if img_width % c == 0 and img_height % r == 0:
            print(f"Guessing frame count: {count} ({c}x{r} grid)")
            fw = img_width // c
            fh = img_height // r
            return c, r, fw, fh, count
            
    raise ValueError("Could not determine frame count/size. Please specify frame_count or frame_size.")

def reverse_sprite_sheet(input_file, output_file=None, frame_count=None, frame_size=None):
    """
    Reverse the rotation direction of frames in a sprite sheet.
    
    Args:
        input_file: Path to input sprite sheet
        output_file: Path to output sprite sheet (defaults to input_file if None)
        frame_count: Total frames (optional, for auto-detection)
        frame_size: (width, height) tuple (optional, for auto-detection)
    """
    # Load the sprite sheet
    try:
        sheet = Image.open(input_file)
    except Exception as e:
        print(f"Error opening {input_file}: {e}")
        return

    sheet_width, sheet_height = sheet.size
    
    try:
        cols, rows, frame_width, frame_height, total_frames = determine_grid(
            sheet_width, sheet_height, frame_count, frame_size
        )
    except ValueError as e:
        print(f"Skipping {input_file}: {e}")
        return

    print(f"Processing {os.path.basename(input_file)}: {total_frames} frames ({cols}x{rows}), Frame size: {frame_width}x{frame_height}")

    # Extract all frames
    frames = []
    for i in range(total_frames):
        c = i % cols
        r = i // cols
        x = c * frame_width
        y = r * frame_height
        
        # Check bounds (handle potential empty space at end of sheet)
        if x < sheet_width and y < sheet_height:
             frame = sheet.crop((x, y, x + frame_width, y + frame_height))
             frames.append(frame)

    # If we extracted more frames than real content (e.g. grid implies 8x8=64 but only 60 used?), 
    # we usually assume standard full sheets for rotations.
    # If frames count < total_frames, we might have issue.
    if len(frames) < total_frames:
        print(f"Warning: Expected {total_frames} frames but could only extract {len(frames)}. Using extracted count.")
        total_frames = len(frames)

    # Reverse rotation direction: keep frame 0 (north/0°) fixed, reverse frames 1 to N-1
    # This maps: frame 1 -> frame N-1, frame 2 -> frame N-2, ...
    reversed_frames = [frames[0]]  # Keep frame 0 (north/0°) as is
    for i in range(1, total_frames):
        reversed_frames.append(frames[total_frames - i])  # Map frame i to frame (total_frames - i)
    
    # If there were unused slots in the grid (e.g. 5 frames in 3x2 grid), 
    # we should handle them carefully. But for rotation sheets, usually all slots are used or it's a strip.
    # If total_frames != len(frames), we have an issue with the logic above. 
    # Assuming standard rotation sheets are packed densely or completely.
    
    frames = reversed_frames
    
    # Create new sprite sheet with reversed frames
    new_sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
    
    for index, frame in enumerate(frames):
        c = index % cols
        r = index // cols
        x = c * frame_width
        y = r * frame_height
        new_sheet.paste(frame, (x, y))
    
    # Save the reversed sprite sheet
    if output_file is None:
        base, ext = os.path.splitext(input_file)
        # Avoid double suffix if running multiple times or on patterned names
        if "_reversed" in base:
            output_file = input_file
        else:
            output_file = f"{base}_reversed{ext}"
    
    new_sheet.save(output_file)
    print(f"Saved to {output_file}")


def process_path(path, output=None, frame_count=None, frame_size=None, recursive=False):
    """
    Process a file or directory.
    """
    p = Path(path)
    if not p.exists():
        print(f"Error: {path} does not exist")
        return

    if p.is_file():
        if p.suffix.lower() == '.png':
            reverse_sprite_sheet(str(p), output, frame_count, frame_size)
    elif p.is_dir():
        files = sorted(p.glob('**/*.png' if recursive else '*.png'))
        if not files:
            print(f"No PNG files found in {path}")
            return
            
        print(f"Found {len(files)} PNG files in {path}")
        for file in files:
            # For directories, output is either in-place (None) or we need a strategy.
            # If output is specified and it's a dir, mirror structure?
            # Simpler: if input is dir, output arg is treated as output dir or ignored (in-place).
            
            out_file = None
            if output:
                out_path = Path(output)
                if out_path.suffix: # Looks like a file
                    print("Warning: Output path looks like a file but input is a directory. Ignoring output path for batch processing.")
                else:
                    # Mirror path relative to input dir
                    rel_path = file.relative_to(p)
                    out_file = out_path / rel_path
                    out_file.parent.mkdir(parents=True, exist_ok=True)
            
            reverse_sprite_sheet(str(file), str(out_file) if out_file else None, frame_count, frame_size)

def main():
    parser = argparse.ArgumentParser(description='Reverse rotation direction of spritesheets.')
    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('--output', '-o', help='Output file or directory (optional)')
    parser.add_argument('--count', type=int, help='Total frame count (force)')
    parser.add_argument('--size', type=int, nargs=2, metavar=('W', 'H'), help='Frame size (width height)')
    parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    
    args = parser.parse_args()
    
    process_path(
        args.input, 
        args.output, 
        frame_count=args.count, 
        frame_size=tuple(args.size) if args.size else None,
        recursive=args.recursive
    )

if __name__ == "__main__":
    sys.exit(main())

