from PIL import Image
import math
import os
import re
import shutil
from pathlib import Path

# === CONFIGURATION ===

# Row length mapping: { total_frames: columns_per_row }
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
    32: 8,
    64: 8,
    128: 8,
    256: 16,
    512: 16,
    1024: 32,
}

# Max dimension (width or height) per output file. Exceeding this splits into multiple files.
MAX_DIMENSION = 8192

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
BLENDER_RENDER_ROOT = PROJECT_ROOT / "blender" / "Render"

def get_files_sorted(folder_path):
    """Get all png files in folder sorted by the number in their filename."""
    if not folder_path.exists():
        print(f"Warning: Folder {folder_path} does not exist.")
        return []
    
    files = [f for f in folder_path.iterdir() if f.suffix.lower() == '.png']
    
    def sort_key(f):
        # Extract the last sequence of digits as the frame number
        numbers = re.findall(r'\d+', f.stem)
        if numbers:
            return int(numbers[-1])
        return f.stem

    return sorted(files, key=sort_key)

def get_image_size(files):
    """Get size of images and ensure they are all the same."""
    if not files:
        return 0, 0
    
    first_img = Image.open(files[0])
    width, height = first_img.size
    first_img.close()
    
    for f in files[1:]:
        with Image.open(f) as img:
            if img.size != (width, height):
                raise ValueError(f"Image size mismatch! {files[0].name} is {width}x{height}, but {f.name} is {img.size}")
    
    return width, height

def get_columns(frame_count):
    """Determine columns (frames per row) based on mapping."""
    if frame_count in FRAME_COLUMN_MAPPING:
        return FRAME_COLUMN_MAPPING[frame_count]
    
    print(f"Warning: Frame count {frame_count} not in mapping. Using default calculation.")
    return math.ceil(math.sqrt(frame_count))

def get_divisors(n):
    """Return divisors of n in descending order (largest first)."""
    divisors = []
    i = 1
    while i * i <= n:
        if n % i == 0:
            divisors.append(i)
            if i != n // i:
                divisors.append(n // i)
        i += 1
    return sorted(divisors, reverse=True)

def find_split_layout(frame_count, width, height, is_one_row, row_length=None):
    """
    Find frames_per_file and (cols, rows) so that:
    - frame_count % frames_per_file == 0
    - Each file fits within MAX_DIMENSION x MAX_DIMENSION
    - All files have identical layout
    row_length overrides is_one_row and auto column detection when provided.
    Returns (frames_per_file, cols, rows) or None if no split needed.
    """
    max_cols = MAX_DIMENSION // width
    max_rows = MAX_DIMENSION // height
    if max_cols < 1 or max_rows < 1:
        raise ValueError(f"Frame size {width}x{height} exceeds max dimension {MAX_DIMENSION}")

    if row_length is None and is_one_row:
        # Single row: split by columns only
        if frame_count <= max_cols:
            return None
        for cols_per_file in get_divisors(frame_count):
            if cols_per_file <= max_cols:
                return frame_count // cols_per_file, cols_per_file, 1
        return 1, 1, 1  # 1 frame per file fallback
    else:
        # Grid: find largest divisor that fits
        full_cols = row_length if row_length is not None else get_columns(frame_count)
        full_rows = math.ceil(frame_count / full_cols)
        sheet_width = full_cols * width
        sheet_height = full_rows * height
        if sheet_width <= MAX_DIMENSION and sheet_height <= MAX_DIMENSION:
            return None

        if row_length is not None:
            # cols is fixed; only look for frames_per_file that are multiples of row_length
            cols = row_length
            if cols * width > MAX_DIMENSION:
                raise ValueError(f"row_length {row_length} * frame width {width} exceeds max dimension {MAX_DIMENSION}")
            for frames_per_file in get_divisors(frame_count):
                if frames_per_file == frame_count:
                    continue
                if frames_per_file % cols != 0:
                    continue
                rows = frames_per_file // cols
                if rows * height <= MAX_DIMENSION:
                    return frame_count // frames_per_file, cols, rows
            raise ValueError(f"Cannot split {frame_count} frames with row_length={row_length} to fit {MAX_DIMENSION}")
        else:
            for frames_per_file in get_divisors(frame_count):
                if frames_per_file == frame_count:
                    continue
                for cols in range(1, min(frames_per_file, max_cols) + 1):
                    if frames_per_file % cols != 0:
                        continue
                    rows = frames_per_file // cols
                    if rows <= max_rows:
                        file_width = cols * width
                        file_height = rows * height
                        if file_width <= MAX_DIMENSION and file_height <= MAX_DIMENSION:
                            return frame_count // frames_per_file, cols, rows
            raise ValueError(f"Cannot split {frame_count} frames of {width}x{height} to fit {MAX_DIMENSION}")

def _parse_frame_size(frame_size, source_width, source_height):
    """Parse frame_size to (width, height). None = use source size."""
    if frame_size is None:
        return source_width, source_height
    if isinstance(frame_size, int):
        return frame_size, frame_size
    return frame_size[0], frame_size[1]

def process_component(component, prefix, destination, is_plant=False, is_one_row=False, frame_size=None, row_length=None):
    if not component["enabled"]:
        return

    source_path = BLENDER_RENDER_ROOT / component["source_dir"]
    files = get_files_sorted(source_path)
    
    if not files:
        print(f"[{component['name']}] No files found in {source_path}")
        return

    frame_count = len(files)
    source_width, source_height = get_image_size(files)
    
    # Resize frames first, before any layout/limit calculations
    target_width, target_height = _parse_frame_size(frame_size, source_width, source_height)
    frames = []
    for file_path in files:
        with Image.open(file_path) as img:
            if frame_size and img.size != (target_width, target_height):
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            frames.append(img.copy())
    
    width, height = target_width, target_height
    print(f"[{component['name']}] Found {frame_count} frames. Size: {width}x{height}" + (f" (resized from {source_width}x{source_height})" if frame_size else ""))
    
    destination_root = PROJECT_ROOT / destination
    destination_root.mkdir(parents=True, exist_ok=True)
    
    split_result = find_split_layout(frame_count, width, height, is_one_row, row_length)
    
    if split_result is None:
        # Single file - use original layout
        if row_length is not None:
            cols = row_length
            rows = math.ceil(frame_count / cols)
        elif is_one_row:
            cols = frame_count
            rows = 1
        else:
            cols = get_columns(frame_count)
            rows = math.ceil(frame_count / cols)
        sheet_width = cols * width
        sheet_height = rows * height
        print(f"[{component['name']}] Creating spritesheet: {sheet_width}x{sheet_height} ({cols}x{rows})")
        sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
        for i, img in enumerate(frames):
            col, row = i % cols, i // cols
            sheet.paste(img, (col * width, row * height))
        output_path = destination_root / f"{prefix}{component['suffix']}.png"
        sheet.save(output_path)
        output_paths = [output_path]
        print(f"[{component['name']}] Saved to {output_path}")
    else:
        # Multiple files - each with identical layout
        num_files, cols, rows = split_result
        frames_per_file = cols * rows
        print(f"[{component['name']}] Splitting into {num_files} files, each {cols}x{rows} frames ({frames_per_file} frames/file)")
        output_paths = []
        for file_idx in range(num_files):
            start = file_idx * frames_per_file
            end = start + frames_per_file
            frame_slice = frames[start:end]
            sheet_width = cols * width
            sheet_height = rows * height
            sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
            for i, img in enumerate(frame_slice):
                col, row = i % cols, i // cols
                sheet.paste(img, (col * width, row * height))
            output_filename = f"{prefix}{component['suffix']}-{file_idx + 1}.png"
            output_path = destination_root / output_filename
            sheet.save(output_path)
            output_paths.append(output_path)
            print(f"[{component['name']}] Saved file {file_idx + 1}/{num_files} to {output_path}")
    
    # Handle Plant Specific Logic (copy all output files)
    if is_plant and output_paths:
        needs_split = len(output_paths) > 1
        if component['name'] == "Object":
            for i, src in enumerate(output_paths):
                suffix_part = f"-{i + 1}" if needs_split else ""
                harvest_path = destination_root / f"{prefix}-harvest{suffix_part}.png"
                shutil.copy2(src, harvest_path)
                print(f"[{component['name']}] Created Plant copy: {harvest_path}")
                normal_path = destination_root / f"{prefix}-normal{suffix_part}.png"
                shutil.copy2(src, normal_path)
                print(f"[{component['name']}] Created Plant copy: {normal_path}")
        elif component['name'] == "Shadow":
            for i, src in enumerate(output_paths):
                suffix_part = f"-{i + 1}" if needs_split else ""
                harvest_shadow_path = destination_root / f"{prefix}-harvest-shadow{suffix_part}.png"
                shutil.copy2(src, harvest_shadow_path)
                print(f"[{component['name']}] Created Plant copy: {harvest_shadow_path}")

def main(prefix, destination, include_object=True, include_shadow=True, include_reflection=True, include_glow=True, is_plant=False, is_one_row=False, frame_size=None, row_length=None):
    """
    frame_size:  Resize each frame before merge. None = use original size.
                 int (e.g. 1024) = square resize to 1024x1024.
                 (width, height) = resize to specific dimensions.
    row_length:  Fixed number of frames per row. Skips auto column detection when set.
                 Overrides is_one_row.
    """
    print(f"Processing sprites for prefix: {prefix}")
    print(f"Destination: {destination}")
    if frame_size:
        print(f"Frame resize: {frame_size}")
    if row_length is not None:
        print(f"Row length: {row_length} (manual)")
    if is_plant:
        print("Mode: Plant (Generating extra copies)")
    
    components = [
        {
            "name": "Object",
            "source_dir": "Object",
            "suffix": "",
            "enabled": include_object
        },
        {
            "name": "Shadow",
            "source_dir": "Shadow",
            "suffix": "-shadow",
            "enabled": include_shadow
        },
        {
            "name": "Reflection",
            "source_dir": "WaterReflection",
            "suffix": "-water-reflection",
            "enabled": include_reflection
        },
        {
            "name": "Glow",
            "source_dir": "Light A Reduced",
            "suffix": "-glow",
            "enabled": include_glow
        }
    ]
    
    for component in components:
        try:
            process_component(component, prefix, destination, is_plant, is_one_row, frame_size, row_length)
        except Exception as e:
            print(f"Error processing {component['name']}: {e}")

