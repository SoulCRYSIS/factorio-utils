import os
import sys
import shutil
import zipfile
import json
import argparse
import platform
import subprocess

def get_mod_info(info_path):
    if not os.path.exists(info_path):
        print(f"Error: info.json not found in {info_path}")
        sys.exit(1)
    
    with open(info_path, 'r') as f:
        try:
            data = json.load(f)
            return data.get('name'), data.get('version')
        except json.JSONDecodeError:
            print("Error: Failed to parse info.json")
            sys.exit(1)

def get_factorio_mods_dir():
    system = platform.system()
    if system == "Linux":
        return os.path.expanduser("~/.factorio/mods")
    elif system == "Darwin":
        return os.path.expanduser("~/Library/Application Support/factorio/mods")
    elif system == "Windows":
        appdata = os.getenv('APPDATA')
        if appdata:
            return os.path.join(appdata, "Factorio", "mods")
        else:
            # Fallback for the specific user case mentioned
            return r"C:\Users\SoulCRYSIS\AppData\Roaming\Factorio\mods"
    else:
        print(f"Warning: Unknown OS {system}, defaulting to Linux path")
        return os.path.expanduser("~/.factorio/mods")

def main():
    parser = argparse.ArgumentParser(description="Package Factorio mod")
    parser.add_argument("-l", "--local", action="store_true", help="Export to current directory instead of Factorio mods folder")
    parser.add_argument("-g", "--graphics", action="store_true", help="Package graphics folder only")
    parser.add_argument("-x", "--exclude-ext", help="Comma-separated list of file extensions to exclude")
    
    args = parser.parse_args()
    
    script_dir = os.getcwd() # Assumption: script run from root or logic handles it. 
    # Aligning with shell script: "Get the directory where the script is called from" -> SCRIPT_DIR="$(pwd)"
    # However, python script location might be different. Let's assume run from project root for now, or detect.
    # The shell script was located in factorio-utils but run from root usually or expected pwd to be project root.
    # Let's verify project root by checking for info.json or factorio-utils folder.
    
    if os.path.exists(os.path.join(script_dir, "factorio-utils")):
        project_root = script_dir
    elif os.path.basename(script_dir) == "factorio-utils":
        project_root = os.path.dirname(script_dir)
    else:
        # Fallback to current dir
        project_root = script_dir

    if args.graphics:
        info_json_path = os.path.join(project_root, "graphics", "info.json")
    else:
        info_json_path = os.path.join(project_root, "info.json")

    mod_name, mod_version = get_mod_info(info_json_path)
    
    if not mod_name or not mod_version:
        print("Error: Failed to read mod name or version from info.json")
        sys.exit(1)

    print(f"Packaging {mod_name} v{mod_version}...")

    mod_folder_name = f"{mod_name}_{mod_version}"
    zip_name = f"{mod_folder_name}.zip"
    
    # Temp dir
    import tempfile
    temp_base = tempfile.mkdtemp()
    temp_mod_dir = os.path.join(temp_base, mod_folder_name)
    os.makedirs(temp_mod_dir)
    
    try:
        # Files to include
        if args.graphics:
            # Graphics mode: include everything inside graphics/ + info.json logic
            # Shell script copied graphics/* to temp_mod_dir
            # And manually copied info.json
            
            # Copy info.json
            shutil.copy2(info_json_path, os.path.join(temp_mod_dir, "info.json"))
            
            graphics_dir = os.path.join(project_root, "graphics")
            if os.path.exists(graphics_dir):
                for item in os.listdir(graphics_dir):
                    s = os.path.join(graphics_dir, item)
                    d = os.path.join(temp_mod_dir, item)
                    if item == "info.json": 
                        continue # Already copied/handled
                    
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                        
            # Also handle "graphic" if it exists? Shell script checked both.
            graphic_dir = os.path.join(project_root, "graphic")
            if os.path.exists(graphic_dir):
                 for item in os.listdir(graphic_dir):
                    s = os.path.join(graphic_dir, item)
                    d = os.path.join(temp_mod_dir, item)
                    if os.path.exists(d): continue # Don't overwrite if collision?
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)

        else:
            # Normal mode
            files_to_include = [
                "info.json", "data.lua", "data-fixes.lua", "data-final-fixes.lua",
                "control.lua", "settings.lua", "constants.lua", "thumbnail.png",
                "logics", "logic", "prototypes", "prototype", "locale", "changelog.txt"
            ]
            
            for item in files_to_include:
                src = os.path.join(project_root, item)
                dst = os.path.join(temp_mod_dir, item)
                
                if os.path.exists(src):
                    print(f"  Copying {item}...")
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                else:
                    print(f"  Warning: {item} not found, skipping...")

        # Extensions to exclude
        extensions_to_exclude = {"blend", "blend1", "xcf", "psd", "DS_Store", "clip"}
        if args.exclude_ext:
            extensions_to_exclude.update([e.strip() for e in args.exclude_ext.split(',')])

        print("Removing excluded file extensions...")
        for root, dirs, files in os.walk(temp_mod_dir):
            for file in files:
                ext = file.split('.')[-1]
                if ext in extensions_to_exclude or file in extensions_to_exclude:
                    file_path = os.path.join(root, file)
                    print(f"  Removing {file}...")
                    os.remove(file_path)

        # Create Zip
        print(f"Creating {zip_name}...")
        zip_path = os.path.join(temp_base, zip_name)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_mod_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_base)
                    zipf.write(file_path, arcname)

        # Move Zip
        if args.local:
            dest_dir = project_root
        else:
            dest_dir = get_factorio_mods_dir()
            if not os.path.exists(dest_dir):
                print(f"Creating mods directory: {dest_dir}")
                os.makedirs(dest_dir)
        
        final_dest = os.path.join(dest_dir, zip_name)
        
        # Remove existing zip at destination if exists
        if os.path.exists(final_dest):
             print(f"Removing existing {zip_name}...")
             os.remove(final_dest)

        print(f"Moving {zip_name} to {dest_dir}...")
        shutil.move(zip_path, final_dest)
        
        if os.path.exists(final_dest):
            size_bytes = os.path.getsize(final_dest)
            import math
            if size_bytes == 0:
                size_str = "0B"
            else:
                size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
                i = int(math.floor(math.log(size_bytes, 1024)))
                p = math.pow(1024, i)
                s = round(size_bytes / p, 2)
                size_str = "%s %s" % (s, size_name[i])
            
            print("Success! Mod packaged and exported.")
            print(f"Location: {final_dest}")
            print(f"Size: {size_str}")
        else:
             print(f"Error: Failed to move {zip_name} to destination")
             sys.exit(1)

    finally:
        # Cleanup
        shutil.rmtree(temp_base)

if __name__ == "__main__":
    main()

