#!/usr/bin/env python3
"""
Crop all frames of one or more spritesheet files to the smallest equal-size
bounding box that fits every frame's non-transparent content across all files.

Only transparent pixels are cropped — no content is lost.
Replaces files in place.

Multi-file usage (split spritesheets like foo-1.png, foo-2.png):
    Pass a list of paths. All files must share the same frame size.
    The union bounding box is computed over every frame in every file,
    so the crop is identical and consistent across all parts.
"""

import math
import os
import sys

from PIL import Image


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def parse_layout(img_width, img_height, frame_count, frames_w=None, frames_h=None):
    """
    Determine (cols, rows, fw, fh) for a single spritesheet file.

    Priority:
    1. frames_w and frames_h both given → use directly
    2. Only frames_w given  → rows = ceil(frame_count / cols)
    3. Only frames_h given  → cols = ceil(frame_count / rows)
    4. Neither              → infer from image dimensions and frame_count
    """
    if frames_w and frames_h:
        cols, rows = frames_w, frames_h
    elif frames_w:
        cols = frames_w
        rows = math.ceil(frame_count / cols)
    elif frames_h:
        rows = frames_h
        cols = math.ceil(frame_count / rows)
    else:
        best = None
        for c in range(1, frame_count + 1):
            r = math.ceil(frame_count / c)
            if img_width % c == 0 and img_height % r == 0:
                fw_t = img_width // c
                fh_t = img_height // r
                if best is None or fw_t * fh_t > best[2] * best[3]:
                    best = (c, r, fw_t, fh_t)
        if best is None:
            raise ValueError(
                f"Cannot infer layout for {img_width}x{img_height} with {frame_count} frames. "
                "Provide frames_w or frames_h."
            )
        cols, rows = best[0], best[1]

    fw = img_width // cols
    fh = img_height // rows
    return cols, rows, fw, fh


def extract_frames(img, cols, rows, fw, fh, frame_count):
    """Extract individual PIL frame crops from a spritesheet image."""
    frames = []
    for i in range(frame_count):
        col = i % cols
        row = i // cols
        x, y = col * fw, row * fh
        frames.append(img.crop((x, y, x + fw, y + fh)))
    return frames


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def union_bbox(all_frames):
    """
    Return (left, top, right, bottom) — the tightest box containing all
    non-transparent pixels across all supplied frames.
    Returns None when every frame is fully transparent.
    """
    min_l = min_t = None
    max_r = max_b = None

    for frame in all_frames:
        bb = frame.getchannel("A").getbbox()
        if bb is None:
            continue
        l, t, r, b = bb
        min_l = l if min_l is None else min(min_l, l)
        min_t = t if min_t is None else min(min_t, t)
        max_r = r if max_r is None else max(max_r, r)
        max_b = b if max_b is None else max(max_b, b)

    return None if min_l is None else (min_l, min_t, max_r, max_b)


def _load_file(path, frame_count, frames_w, frames_h):
    """Open a spritesheet and return (img, cols, rows, fw, fh, frames)."""
    with Image.open(path) as img:
        img = img.convert("RGBA")
        w, h = img.size
        cols, rows, fw, fh = parse_layout(w, h, frame_count, frames_w, frames_h)
        frames = extract_frames(img, cols, rows, fw, fh, frame_count)
    return cols, rows, fw, fh, frames


def _write_file(path, frames, cols, rows, new_fw, new_fh, bbox):
    """Crop every frame by bbox and write a new spritesheet to path."""
    left, top, right, bottom = bbox
    new_sheet_w = cols * new_fw
    new_sheet_h = rows * new_fh
    result = Image.new("RGBA", (new_sheet_w, new_sheet_h), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        cropped = frame.crop((left, top, right, bottom))
        col = i % cols
        row = i // cols
        result.paste(cropped, (col * new_fw, row * new_fh))
    result.save(path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def crop_frames(
    input_paths,
    frame_count,
    frames_w=None,
    frames_h=None,
):
    """
    Crop spritesheet frames to the smallest equal-size bounding box that
    covers every frame's non-transparent content across all supplied files.

    Replaces files in place.

    Parameters
    ----------
    input_paths : str | list[str]
        Single path or list of paths for split spritesheets (e.g. foo-1.png,
        foo-2.png).  All files must share the same frame size.
    frame_count : int
        Number of frames **per file**.
    frames_w : int, optional
        Columns (frames per row) per file.
    frames_h : int, optional
        Rows per file.

    Returns
    -------
    dict with keys: new_fw, new_fh, shift_x, shift_y,
                    total_old_bytes, total_new_bytes
    """
    if isinstance(input_paths, str):
        input_paths = [input_paths]

    for p in input_paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"File not found: {p}")

    # ── Load all files ───────────────────────────────────────────────────────
    file_data = []   # list of (path, cols, rows, fw, fh, frames, old_bytes)
    fw_ref = fh_ref = None

    for path in input_paths:
        old_bytes = os.path.getsize(path)
        cols, rows, fw, fh, frames = _load_file(path, frame_count, frames_w, frames_h)

        if fw_ref is None:
            fw_ref, fh_ref = fw, fh
        elif fw != fw_ref or fh != fh_ref:
            raise ValueError(
                f"Frame size mismatch: {path} has {fw}x{fh}, "
                f"expected {fw_ref}x{fh_ref}"
            )

        file_data.append((path, cols, rows, fw, fh, frames, old_bytes))

    fw, fh = fw_ref, fh_ref

    # ── Compute union bbox over ALL frames from ALL files ────────────────────
    all_frames = [f for *_, frames, _ in file_data for f in frames]
    bbox = union_bbox(all_frames)

    if bbox is None:
        print("All frames are fully transparent — nothing to crop.")
        return None

    left, top, right, bottom = bbox
    new_fw = right - left
    new_fh = bottom - top

    # Center shift (same for every file since bbox and fw/fh are shared)
    shift_x = (left + new_fw / 2.0) - (fw / 2.0)
    shift_y = (top + new_fh / 2.0) - (fh / 2.0)

    already_min = (new_fw == fw and new_fh == fh)

    # ── Write results ────────────────────────────────────────────────────────
    total_old = total_new = 0

    for path, cols, rows, fw_f, fh_f, frames, old_bytes in file_data:
        total_old += old_bytes
        img_w_old = cols * fw_f
        img_h_old = rows * fh_f

        if already_min:
            print(f"{path}")
            print(f"  No transparent border — already at minimum size ({fw}x{fh}).")
            total_new += old_bytes
            continue

        _write_file(path, frames, cols, rows, new_fw, new_fh, bbox)
        new_bytes = os.path.getsize(path)
        total_new += new_bytes

        size_diff = new_bytes - old_bytes
        size_diff_pct = size_diff / old_bytes * 100 if old_bytes else 0

        print(f"{path}")
        print(f"  Layout      : {cols}x{rows} ({frame_count} frames)")
        print(f"  Frame size  : {fw}x{fh}  →  {new_fw}x{new_fh}")
        print(f"  Sheet size  : {img_w_old}x{img_h_old}  →  {cols * new_fw}x{rows * new_fh}")
        print(f"  File size   : {old_bytes:,} B  →  {new_bytes:,} B  ({size_diff:+,} B, {size_diff_pct:+.1f}%)")

    if not already_min:
        print(f"  Center shift: ({shift_x:+.1f}, {shift_y:+.1f}) px  (x=right/left, y=down/up)")
        if len(file_data) > 1:
            diff = total_new - total_old
            pct = diff / total_old * 100 if total_old else 0
            print(f"  Total       : {total_old:,} B  →  {total_new:,} B  ({diff:+,} B, {pct:+.1f}%)")

    return {
        "new_fw": new_fw,
        "new_fh": new_fh,
        "shift_x": shift_x,
        "shift_y": shift_y,
        "total_old_bytes": total_old,
        "total_new_bytes": total_new,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Crop spritesheet frames to the smallest equal-size bounding box "
            "(transparent trim only). Supports split spritesheets (foo-1.png foo-2.png)."
        )
    )
    parser.add_argument("inputs", nargs="+", help="Spritesheet PNG path(s)")
    parser.add_argument("--count", type=int, required=True, help="Frames per file")
    parser.add_argument("--frames-w", type=int, help="Columns (frames per row)")
    parser.add_argument("--frames-h", type=int, help="Rows per file")

    args = parser.parse_args()

    try:
        crop_frames(
            args.inputs,
            args.count,
            frames_w=args.frames_w,
            frames_h=args.frames_h,
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
