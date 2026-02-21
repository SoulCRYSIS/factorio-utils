#!/usr/bin/env python3
"""
Script to reduce rotation/animation count of spritesheets by skipping frames.
Supports bulk files, rotation vs animation skip, symmetric selection, and regroup mode.
"""

import argparse
import math
import os
import sys

from PIL import Image

# Max dimension for regroup mode
MAX_DIMENSION = 8192

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
    25: 8,
    32: 8,
    64: 8,
    128: 16,
    256: 16,
    512: 16,
}


def get_grid_layout(frame_count):
    """Determine columns (frames per row) based on mapping."""
    if frame_count in FRAME_COLUMN_MAPPING:
        return FRAME_COLUMN_MAPPING[frame_count]
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


def find_split_layout(frame_count, width, height):
    """Find (num_files, cols, rows) to split frames into files <= MAX_DIMENSION."""
    max_cols = MAX_DIMENSION // width
    max_rows = MAX_DIMENSION // height
    if max_cols < 1 or max_rows < 1:
        return None
    full_cols = get_grid_layout(frame_count)
    full_rows = math.ceil(frame_count / full_cols)
    sheet_width = full_cols * width
    sheet_height = full_rows * height
    if sheet_width <= MAX_DIMENSION and sheet_height <= MAX_DIMENSION:
        return None
    for frames_per_file in get_divisors(frame_count):
        if frames_per_file == frame_count:
            continue
        for cols in range(1, min(frames_per_file, max_cols) + 1):
            if frames_per_file % cols != 0:
                continue
            rows = frames_per_file // cols
            if rows <= max_rows:
                fw, fh = cols * width, rows * height
                if fw <= MAX_DIMENSION and fh <= MAX_DIMENSION:
                    return frame_count // frames_per_file, cols, rows
    return None


def symmetric_indices(n, skip):
    """
    Select indices symmetrically. For n=8, skip=2: keep 4 frames → 0, 2, 5, 7.
    First half: every skip-th from start. Second half: every skip-th from end.
    """
    half = n // 2
    first_half = list(range(0, half, skip))
    second_half = [n - 1 - i for i in range(0, half, skip)][::-1]
    return sorted(first_half + second_half)


def compute_selected_indices(total_frames, skip, skip_type, rotations=None, animations_per_rotation=None, symmetric=False):
    """
    Compute which frame indices to keep based on skip type and mode.
    skip_type: "linear" | "rotation" | "animation"
    """
    if skip_type == "linear":
        if symmetric:
            return symmetric_indices(total_frames, skip)
        return list(range(0, total_frames, skip))

    # Sheet is grouped by rotation: frames 0..(N-1)=rotation0, frames N..(2N-1)=rotation1, ...
    # rotation skip: keep every Nth frame within each rotation (fewer anim frames per direction)
    # animation skip: keep every Nth rotation group (fewer directions), all anim frames per rotation
    if skip_type == "rotation":
        if animations_per_rotation is None:
            raise ValueError("skip_type='rotation' requires animations_per_rotation parameter")
        rots = total_frames // animations_per_rotation
        indices = []
        for r in range(rots):
            base = r * animations_per_rotation
            if symmetric:
                keep = symmetric_indices(animations_per_rotation, skip)
            else:
                keep = list(range(0, animations_per_rotation, skip))
            for a in keep:
                indices.append(base + a)
        return indices

    if skip_type == "animation":
        if rotations is None:
            raise ValueError("skip_type='animation' requires rotations parameter")
        anims_per_rot = total_frames // rotations
        keep_rots = list(range(0, rotations, skip))
        indices = []
        for r in keep_rots:
            base = r * anims_per_rot
            for a in range(anims_per_rot):
                indices.append(base + a)
        return indices

    raise ValueError(f"Unknown skip_type: {skip_type}")


def parse_spritesheet(img, frame_count=None, frame_size=None):
    """Parse spritesheet into (frames, cols, rows, fw, fh, total_frames)."""
    img_width, img_height = img.size
    if frame_size:
        fw, fh = frame_size
        cols = img_width // fw
        rows = img_height // fh
        total_frames = cols * rows
    elif frame_count:
        total_frames = frame_count
        # Try to determine the actual layout from image dimensions
        # rather than assuming get_grid_layout's preference
        expected_cols = get_grid_layout(total_frames)
        expected_rows = math.ceil(total_frames / expected_cols)
        fw_expected = img_width // expected_cols
        fh_expected = img_height // expected_rows
        
        # Check if image dimensions match expected layout
        if img_width == expected_cols * fw_expected and img_height == expected_rows * fh_expected:
            # Standard layout matches
            cols, rows, fw, fh = expected_cols, expected_rows, fw_expected, fh_expected
        else:
            # Image has non-standard layout, need to deduce actual cols/rows
            # Try different column counts to find the actual layout
            found = False
            for test_cols in range(1, total_frames + 1):
                if total_frames % test_cols == 0 or test_cols >= total_frames:
                    test_rows = math.ceil(total_frames / test_cols)
                    if img_width % test_cols == 0 and img_height % test_rows == 0:
                        fw_test = img_width // test_cols
                        fh_test = img_height // test_rows
                        if test_cols * test_rows >= total_frames:
                            cols, rows, fw, fh = test_cols, test_rows, fw_test, fh_test
                            found = True
                            break
            if not found:
                # Fallback to expected layout
                cols, rows, fw, fh = expected_cols, expected_rows, fw_expected, fh_expected
    else:
        for count in [64, 32, 24, 16, 12, 8, 4]:
            c = get_grid_layout(count)
            r = math.ceil(count / c)
            if img_width % c == 0 and img_height % r == 0:
                total_frames = count
                cols, rows = c, r
                fw, fh = img_width // c, img_height // r
                break
        else:
            raise ValueError("Could not determine frame count. Specify --count or --size")
    frames = []
    for i in range(total_frames):
        c, r = i % cols, i // cols
        x, y = c * fw, r * fh
        if x < img_width and y < img_height:
            frames.append(img.crop((x, y, x + fw, y + fh)))
    return frames, cols, rows, fw, fh, total_frames


def reduce_single(input_path, output_path=None, skip=None, keep_indices=None,
                  frame_count=None, frame_size=None,
                  skip_type="linear", rotations=None, animations_per_rotation=None, symmetric=False,
                  save=True):
    """Reduce a single spritesheet. Returns (result_image, fw, fh, new_count)."""
    if skip is None and keep_indices is None:
        raise ValueError("Must specify either skip or keep_indices")

    with Image.open(input_path) as img:
        img = img.convert("RGBA")
        frames, cols, rows, fw, fh, total_frames = parse_spritesheet(img, frame_count, frame_size)

    if keep_indices is not None:
        selected_indices = [i for i in keep_indices if 0 <= i < len(frames)]
    else:
        selected_indices = compute_selected_indices(
            total_frames, skip, skip_type, rotations, animations_per_rotation, symmetric
        )
        selected_indices = [i for i in selected_indices if i < len(frames)]

    if not selected_indices:
        raise ValueError("No frames selected")

    selected_frames = [frames[i] for i in selected_indices]
    new_count = len(selected_frames)
    
    # When skip_type is rotation or animation, preserve rotation boundaries in layout
    if skip_type in ["rotation", "animation"]:
        if skip_type == "rotation" and animations_per_rotation is not None:
            # After skipping, how many frames per rotation?
            kept_indices_per_rot = symmetric_indices(animations_per_rotation, skip) if symmetric else list(range(0, animations_per_rotation, skip))
            frames_per_rotation = len(kept_indices_per_rot)
            # Use frames_per_rotation as column count to keep each rotation on separate rows
            new_cols = frames_per_rotation
        elif skip_type == "animation" and rotations is not None:
            # All frames from each rotation should stay together
            anims_per_rot = total_frames // rotations
            new_cols = anims_per_rot
        else:
            new_cols = get_grid_layout(new_count)
    else:
        new_cols = get_grid_layout(new_count)
    
    new_rows = math.ceil(new_count / new_cols)
    new_width = new_cols * fw
    new_height = new_rows * fh

    result = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
    for i, frame in enumerate(selected_frames):
        c, r = i % new_cols, i // new_cols
        result.paste(frame, (c * fw, r * fh))

    if save:
        if output_path is None:
            output_path = input_path  # Same name as input (overwrite)
        result.save(output_path)
    return result, fw, fh, new_count


def process_file(input_path, output_path, skip, keep_indices, frame_count, frame_size,
                 skip_type, rotations, animations_per_rotation, symmetric, verbose=True):
    """Process one file and return (output_path, result_img, fw, fh, frame_count)."""
    if verbose:
        print(f"Processing {input_path}")
    result, fw, fh, new_count = reduce_single(
        input_path, output_path, skip=skip, keep_indices=keep_indices,
        frame_count=frame_count, frame_size=frame_size,
        skip_type=skip_type, rotations=rotations,
        animations_per_rotation=animations_per_rotation, symmetric=symmetric
    )
    if verbose:
        print(f"  -> {new_count} frames, saved to {output_path}")
    return output_path, result, fw, fh, new_count


def regroup_files(file_results, output_prefix, output_dir=None, frames_per_rotation=None):
    """
    Merge multiple spritesheet results and resplit to not exceed MAX_DIMENSION.
    file_results: list of (output_path, img, fw, fh, frame_count)
    frames_per_rotation: if provided, use multiples of this as column count to keep rotations aligned
    """
    if not file_results:
        return []
    fw, fh = file_results[0][2], file_results[0][3]
    for _, img, w, h, _ in file_results[1:]:
        if w != fw or h != fh:
            raise ValueError(f"Frame size mismatch in regroup: {fw}x{fh} vs {w}x{h}")
    all_frames = []
    for file_idx, (_, img, _, _, frame_count) in enumerate(file_results):
        # Calculate actual columns from image dimensions
        img_width, img_height = img.size
        cols = img_width // fw
        print(f"  File {file_idx}: extracting {frame_count} frames from {cols} columns")
        file_frames = []
        for i in range(frame_count):
            c, r = i % cols, i // cols
            frame = img.crop((c * fw, r * fh, (c + 1) * fw, (r + 1) * fh))
            file_frames.append(frame)
        all_frames.extend(file_frames)
        print(f"  File {file_idx}: extracted frames, now have {len(all_frames)} total frames")

    total_frames = len(all_frames)
    split_result = find_split_layout(total_frames, fw, fh)
    output_paths = []

    if split_result is None:
        # Use the same logic as reduce_single for layout
        if frames_per_rotation:
            cols = frames_per_rotation
        else:
            cols = get_grid_layout(total_frames)
        rows = math.ceil(total_frames / cols)
        print(f"  Regrouping {total_frames} frames into {cols}x{rows} (frames_per_rotation={frames_per_rotation})")
        sheet = Image.new("RGBA", (cols * fw, rows * fh), (0, 0, 0, 0))
        for i, frame in enumerate(all_frames):
            c, r = i % cols, i // cols
            sheet.paste(frame, (c * fw, r * fh))
        out_path = f"{output_prefix}.png"
        if output_dir:
            out_path = os.path.join(output_dir, os.path.basename(out_path))
        sheet.save(out_path)
        output_paths.append(out_path)
        print(f"Regrouped: 1 file, {total_frames} frames -> {out_path}")
    else:
        num_files, cols, rows = split_result
        frames_per_file = cols * rows
        for i in range(num_files):
            start = i * frames_per_file
            end = start + frames_per_file
            sheet = Image.new("RGBA", (cols * fw, rows * fh), (0, 0, 0, 0))
            for j, frame in enumerate(all_frames[start:end]):
                c, r = j % cols, j // cols
                sheet.paste(frame, (c * fw, r * fh))
            out_path = f"{output_prefix}-{i + 1}.png"
            if output_dir:
                out_path = os.path.join(output_dir, os.path.basename(out_path))
            sheet.save(out_path)
            output_paths.append(out_path)
        print(f"Regrouped: {len(file_results)} files -> {num_files} files (max {MAX_DIMENSION}px)")


def reduce_rotation(input_path, output_path=None, skip=None, keep_indices=None,
                    frame_count=None, frame_size=None,
                    skip_type="linear", rotations=None, animations_per_rotation=None,
                    symmetric=False):
    """
    Reduce rotation/animation count of a spritesheet.
    For backward compatibility - delegates to reduce_single.
    """
    result, fw, fh, count = reduce_single(
        input_path, output_path, skip, keep_indices,
        frame_count, frame_size,
        skip_type, rotations, animations_per_rotation, symmetric
    )
    return result, fw, fh, count


def run_bulk(input_paths, output_dir=None, output_prefix=None, skip=None, keep_indices=None,
             frame_count=None, frame_size=None, skip_type="linear",
             rotations=None, animations_per_rotation=None, symmetric=False, regroup=False,
             delete_old=False):
    """
    Process multiple files. Returns list of output paths.
    When regroup=True, merges all reduced outputs and resplits to not exceed 8192px.
    Output uses same filename as input (overwrite). When regroup=True and delete_old=True, deletes input files.
    """
    if skip is None and keep_indices is None:
        raise ValueError("Must specify either skip or keep_indices")
    frame_size = tuple(frame_size) if frame_size else None
    results = []
    out_dir = output_dir or os.path.dirname(input_paths[0])
    prefix = output_prefix or os.path.splitext(os.path.basename(input_paths[0]))[0]
    for path in input_paths:
        print(f"Processing {path}")
        out_path = None if regroup else (os.path.join(out_dir, os.path.basename(path)) if output_dir else path)
        result, fw, fh, count = reduce_single(
            path, out_path, skip=skip, keep_indices=keep_indices,
            frame_count=frame_count, frame_size=frame_size,
            skip_type=skip_type, rotations=rotations,
            animations_per_rotation=animations_per_rotation, symmetric=symmetric,
            save=not regroup,
        )
        if not regroup:
            print(f"  -> {count} frames, saved to {out_path}")
        results.append((out_path, result, fw, fh, count))
    if regroup and results:
        # Calculate frames_per_rotation for rotation-aware layout
        frames_per_rot = None
        if skip_type == "rotation" and animations_per_rotation:
            kept_indices = symmetric_indices(animations_per_rotation, skip) if symmetric else list(range(0, animations_per_rotation, skip))
            frames_per_rot = len(kept_indices)
        regroup_files(results, os.path.splitext(prefix)[0] if prefix.endswith(".png") else prefix, out_dir, frames_per_rotation=frames_per_rot)
        if delete_old:
            for path in input_paths:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"Deleted old file: {path}")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Reduce rotation/animation count of spritesheets. Supports bulk files, symmetric selection, regroup."
    )
    parser.add_argument("inputs", nargs="+", help="Input spritesheet path(s)")
    parser.add_argument("--output", "-o", help="Output path (single file) or prefix (bulk/regroup)")
    parser.add_argument("--output-dir", help="Output directory for bulk/regroup mode")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--skip", type=int, help="Keep every Nth frame")
    group.add_argument("--indices", type=int, nargs="+", help="Specific indices to keep")

    parser.add_argument("--count", type=int, help="Total frame count in input")
    parser.add_argument("--size", type=int, nargs=2, metavar=("W", "H"), help="Frame size (width height)")

    parser.add_argument(
        "--skip-type",
        choices=["linear", "rotation", "animation"],
        default="linear",
        help="What to skip: linear (every Nth), rotation (every Nth frame within each direction), animation (every Nth direction group)"
    )
    parser.add_argument("--rotations", type=int, help="Number of rotation directions (for skip-type=animation)")
    parser.add_argument("--animations-per-rotation", type=int, help="Frames per rotation/direction (for skip-type=rotation)")
    parser.add_argument("--symmetric", action="store_true", help="Select frames symmetrically (e.g. 1,3,6,8 for 8 frames skip 2)")
    parser.add_argument("--regroup", action="store_true", help="Merge all outputs and resplit to not exceed 8192px")
    parser.add_argument("--keep-old", action="store_true", help="Keep original files (default: delete after regroup)")

    args = parser.parse_args()

    frame_size = tuple(args.size) if args.size else None
    keep_indices = args.indices

    for path in args.inputs:
        if not os.path.exists(path):
            print(f"Error: File not found: {path}")
            return 1

    try:
        if len(args.inputs) == 1 and not args.regroup:
            # Output same name as input (overwrite in place)
            output_path = args.output or args.inputs[0]
            if args.output_dir:
                output_path = os.path.join(args.output_dir, os.path.basename(output_path))
            reduce_rotation(
                args.inputs[0],
                output_path,
                skip=args.skip,
                keep_indices=keep_indices,
                frame_count=args.count,
                frame_size=frame_size,
                skip_type=args.skip_type,
                rotations=args.rotations,
                animations_per_rotation=args.animations_per_rotation,
                symmetric=args.symmetric,
            )
            return 0

        # Bulk or regroup mode
        results = []
        output_dir = args.output_dir or os.path.dirname(args.inputs[0])
        prefix = args.output or os.path.splitext(os.path.basename(args.inputs[0]))[0]

        for i, input_path in enumerate(args.inputs):
            print(f"Processing {input_path}")
            if args.regroup:
                out_path = None  # Don't save intermediate when regrouping
            else:
                # Output same name as input (overwrite in place)
                out_path = os.path.join(output_dir, os.path.basename(input_path)) if args.output_dir else input_path

            result_img, fw, fh, count = reduce_single(
                input_path, out_path,
                skip=args.skip, keep_indices=keep_indices,
                frame_count=args.count, frame_size=frame_size,
                skip_type=args.skip_type,
                rotations=args.rotations,
                animations_per_rotation=args.animations_per_rotation,
                symmetric=args.symmetric,
                save=not args.regroup,
            )
            if not args.regroup:
                print(f"  -> {count} frames, saved to {out_path}")
            results.append((out_path, result_img, fw, fh, count))

        if args.regroup and results:
            regroup_prefix = os.path.splitext(prefix)[0] if prefix.endswith(".png") else prefix
            # Calculate frames_per_rotation for rotation-aware layout
            frames_per_rot = None
            if args.skip_type == "rotation" and args.animations_per_rotation:
                kept_indices = symmetric_indices(args.animations_per_rotation, args.skip) if args.symmetric else list(range(0, args.animations_per_rotation, args.skip))
                frames_per_rot = len(kept_indices)
            regroup_files(results, regroup_prefix, output_dir, frames_per_rotation=frames_per_rot)
            # Delete old input files (replaced by regrouped output)
            if not args.keep_old:
                for input_path in args.inputs:
                    if os.path.exists(input_path):
                        os.remove(input_path)
                        print(f"Deleted old file: {input_path}")

        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
