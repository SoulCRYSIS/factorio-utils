from PIL import Image
import sys
import os
from constant import *

def reverse_sprite_sheet(input_file, output_file=None):
    """
    Reverse the rotation direction of frames in a sprite sheet.
    Keeps frame 0 (north/0°) fixed and reverses frames 1-31, so rotation goes
    counter-clockwise instead of clockwise (or vice versa), while maintaining
    the same start (0°) and end (348.75°) orientations.
    
    Args:
        input_file: Path to input sprite sheet
        output_file: Path to output sprite sheet (defaults to input_file if None)
        frame_width: Width of each frame in pixels
        frame_height: Height of each frame in pixels
        frames_per_row: Number of frames per row in the sprite sheet
    """
    # Load the sprite sheet
    sheet = Image.open(input_file)
    sheet_width, sheet_height = sheet.size
    
    # Calculate number of rows and total frames
    rows = sheet_height // frame_height
    total_frames = rows * frames_per_row
    
    # Extract all frames
    frames = []
    for row in range(rows):
        for col in range(frames_per_row):
            x = col * frame_width
            y = row * frame_height
            frame = sheet.crop((x, y, x + frame_width, y + frame_height))
            frames.append(frame)
    
    # Reverse rotation direction: keep frame 0 (north) fixed, reverse frames 1-31
    # This maps: frame 1 -> frame 31, frame 2 -> frame 30, ..., frame 31 -> frame 1
    reversed_frames = [frames[0]]  # Keep frame 0 (north/0°) as is
    for i in range(1, total_frames):
        reversed_frames.append(frames[total_frames - i])  # Map frame i to frame (total_frames - i)
    frames = reversed_frames
    
    # Create new sprite sheet with reversed frames
    new_sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
    
    for index, frame in enumerate(frames):
        x = (index % frames_per_row) * frame_width
        y = (index // frames_per_row) * frame_height
        new_sheet.paste(frame, (x, y), frame)
    
    # Save the reversed sprite sheet
    if output_file is None:
        output_file = input_file
    
    new_sheet.save(output_file)
    print(f"Reversed sprite sheet saved to {output_file}")
    print(f"Total frames processed: {total_frames}")
    print(f"Layout: {frames_per_row} columns × {rows} rows")

if __name__ == "__main__":
    # Default configuration matching carriage.lua
    default_output = None  # Will overwrite input by default
    
    # Allow command line arguments
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        raise Exception("No input file provided")
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = input_file
    
    # Get script directory and adjust paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    input_path = os.path.join(project_root, input_file)
    output_path = os.path.join(project_root, output_file) if output_file else None
    
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    reverse_sprite_sheet(input_path, output_path)

