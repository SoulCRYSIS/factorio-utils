from PIL import Image
import os
import math

def main(file_path, divide_amount):
    """
    Splits a sprite sheet into multiple files vertically.
    
    Args:
        file_path (str): Path to the input image file.
        divide_amount (int): Number of parts to split the image into.
    """
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    try:
        img = Image.open(file_path)
        width, height = img.size
        
        print(f"Processing {file_path}")
        print(f"Original size: {width}x{height}")
        
        # Calculate chunk height
        # We use ceil to ensure we cover all pixels, but for sprite sheets
        # usually we want exact division.
        if height % divide_amount != 0:
            print(f"Warning: Height {height} is not divisible by {divide_amount}. Splits might not align with frames.")
        
        chunk_height = math.ceil(height / divide_amount)
        
        base_name = os.path.splitext(file_path)[0]
        ext = os.path.splitext(file_path)[1]
        
        for i in range(divide_amount):
            top = i * chunk_height
            bottom = min((i + 1) * chunk_height, height)
            
            # If the last chunk is empty or invalid (shouldn't happen with ceil), skip
            if top >= height:
                break
                
            box = (0, top, width, bottom)
            chunk = img.crop(box)
            
            output_filename = f"{base_name}-{i+1}{ext}"
            chunk.save(output_filename)
            print(f"Saved {output_filename} ({chunk.size[0]}x{chunk.size[1]})")
            
    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        main(sys.argv[1], int(sys.argv[2]))
    else:
        print("Usage: python split_spritesheet.py <file_path> <divide_amount>")
