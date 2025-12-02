import argparse
from PIL import Image
import numpy as np
import os

def main():
    parser = argparse.ArgumentParser(description="Mask one sprite out of another.")
    parser.add_argument("base_image", help="Path to the base image (glow)")
    parser.add_argument("mask_image", help="Path to the mask image (e.g. deep-fryer)")
    parser.add_argument("--base-shift", type=str, default="0,0", help="Shift of base image (x,y)")
    parser.add_argument("--mask-shift", type=str, default="0,0", help="Shift of mask image (x,y)")
    parser.add_argument("--output", "-o", help="Path to save the output image. Defaults to base_image name with -masked suffix.")

    args = parser.parse_args()

    # Parse shifts
    try:
        bs = [int(x.strip()) for x in args.base_shift.split(",")]
        base_shift = (bs[0], bs[1])
    except:
        print(f"Error parsing base-shift: {args.base_shift}")
        return

    try:
        ms = [int(x.strip()) for x in args.mask_shift.split(",")]
        mask_shift = (ms[0], ms[1])
    except:
        print(f"Error parsing mask-shift: {args.mask_shift}")
        return

    # Load images
    try:
        base = Image.open(args.base_image).convert("RGBA")
        mask = Image.open(args.mask_image).convert("RGBA")
    except Exception as e:
        print(f"Error loading images: {e}")
        return

    # Calculate positions
    # We want to align centers, then apply shifts.
    # Base center (relative to its top-left)
    bw, bh = base.size
    mw, mh = mask.size
    
    # Center of base image in base coordinates
    bcx, bcy = bw // 2, bh // 2
    
    # Center of mask image in mask coordinates
    mcx, mcy = mw // 2, mh // 2

    # We want to place the mask such that:
    # (Mask Center on Canvas) - (Base Center on Canvas) = (Mask Shift) - (Base Shift)
    # Let Canvas be the Base Image coordinate system.
    # Base Center on Canvas = (bcx, bcy)
    # Mask Center on Canvas = (bcx, bcy) + (mask_shift - base_shift)
    
    diff_x = mask_shift[0] - base_shift[0]
    diff_y = mask_shift[1] - base_shift[1]
    
    target_mask_cx = bcx + diff_x
    target_mask_cy = bcy + diff_y
    
    # Top-left of mask on base canvas
    mask_x = target_mask_cx - mcx
    mask_y = target_mask_cy - mcy

    # Create a full-size mask buffer
    # We can paste the mask image onto a blank canvas of base size
    full_mask = Image.new("RGBA", base.size, (0, 0, 0, 0))
    full_mask.paste(mask, (mask_x, mask_y), mask) # Paste using itself as mask to preserve transparency? 
    # Actually just paste it. If mask has transparency, we want that alpha channel in full_mask.
    # Image.paste(im, box, mask) updates only where mask is non-zero?
    # We want to simple place the mask image onto the empty canvas.
    # Since we start with empty, we can just paste.
    
    # However, simply pasting RGBA onto RGBA in PIL blends them.
    # We want the exact alpha values of the mask image to be present in full_mask.
    # So we should paste it without blending if possible, or construct it carefully.
    
    # Alternative: Use a canvas large enough to hold the mask at that position, then crop/resize?
    # Actually, just use paste. But wait, if mask has semi-transparent pixels, paste will blend with (0,0,0,0).
    # (0,0,0,0) is transparent. Blending X over Transparent results in X. So it should be fine.
    full_mask.paste(mask, (mask_x, mask_y))

    # Convert to numpy arrays for pixel manipulation
    base_arr = np.array(base).astype(float)
    mask_arr = np.array(full_mask).astype(float)

    # Separate channels
    # base_r, base_g, base_b, base_a = base_arr[..., 0], base_arr[..., 1], base_arr[..., 2], base_arr[..., 3]
    # mask_a = mask_arr[..., 3]
    
    # Masking logic:
    # "remove pixel from glow image where deep-fryer has pixel"
    # New Base Alpha = Base Alpha * (1 - Mask Alpha / 255)
    
    mask_alpha_norm = mask_arr[..., 3] / 255.0
    base_arr[..., 3] = base_arr[..., 3] * (1.0 - mask_alpha_norm)

    # Convert back to uint8
    result_arr = base_arr.astype(np.uint8)
    result_img = Image.fromarray(result_arr)

    # Save output
    if args.output:
        out_path = args.output
    else:
        base_dir = os.path.dirname(args.base_image)
        base_name = os.path.basename(args.base_image)
        name, ext = os.path.splitext(base_name)
        out_path = os.path.join(base_dir, f"{name}-masked{ext}")

    result_img.save(out_path)
    print(f"Saved masked image to {out_path}")

if __name__ == "__main__":
    main()

