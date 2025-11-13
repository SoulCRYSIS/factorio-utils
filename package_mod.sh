#!/bin/bash

# Script to package the Factorio mod and move it to the mods directory
# Usage: ./package_mod.sh [--local]
#   --local or -l: Export to current directory instead of Factorio mods folder

# Parse command line arguments
EXPORT_LOCAL=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--local)
            EXPORT_LOCAL=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--local]"
            echo "  --local, -l: Export to current directory instead of Factorio mods folder"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Read version and name from info.json
if [ ! -f "$SCRIPT_DIR/info.json" ]; then
    echo "Error: info.json not found in $SCRIPT_DIR"
    exit 1
fi

MOD_NAME=$(grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' "$SCRIPT_DIR/info.json" | sed 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
MOD_VERSION=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$SCRIPT_DIR/info.json" | sed 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

if [ -z "$MOD_NAME" ] || [ -z "$MOD_VERSION" ]; then
    echo "Error: Failed to read mod name or version from info.json"
    exit 1
fi

echo "Packaging ${MOD_NAME} v${MOD_VERSION}..."

MOD_FOLDER="${MOD_NAME}_${MOD_VERSION}"
ZIP_NAME="${MOD_FOLDER}.zip"
FACTORIO_MODS_DIR="$HOME/Library/Application Support/factorio/mods"
TEMP_DIR="/tmp/${MOD_FOLDER}"

# List of files and folders to include in the package
FILES_TO_INCLUDE=(
    "info.json"
    "data.lua"
    "control.lua"
    "settings.lua"
    "constants.lua"
    "thumbnail.png"
    "graphics"
    "logic"
    "prototypes"
    "locale"
)

# Change to the script directory
cd "$SCRIPT_DIR"

# Remove old zip if it exists
if [ -f "$ZIP_NAME" ]; then
    echo "Removing existing $ZIP_NAME..."
    rm "$ZIP_NAME"
fi

# Remove old temp directory if it exists
if [ -d "$TEMP_DIR" ]; then
    echo "Removing old temp directory..."
    rm -rf "$TEMP_DIR"
fi

# Create temporary directory with correct structure
echo "Creating temporary directory: $TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Copy mod files to temp directory
echo "Copying mod files..."
for item in "${FILES_TO_INCLUDE[@]}"; do
    if [ -e "$item" ]; then
        echo "  Copying $item..."
        cp -r "$item" "$TEMP_DIR/"
    else
        echo "  Warning: $item not found, skipping..."
    fi
done

# Change to parent directory of temp folder and create zip
echo "Creating $ZIP_NAME..."
cd /tmp
zip -r "$ZIP_NAME" "$MOD_FOLDER"

# Check if zip was created successfully
if [ ! -f "/tmp/$ZIP_NAME" ]; then
    echo "Error: Failed to create $ZIP_NAME"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Move the zip to the appropriate location
if [ "$EXPORT_LOCAL" = true ]; then
    # Move to current directory (where script is located)
    echo "Moving $ZIP_NAME to current directory..."
    mv "/tmp/$ZIP_NAME" "$SCRIPT_DIR/"
    DESTINATION="$SCRIPT_DIR/$ZIP_NAME"
else
    # Move to the Factorio mods directory
    # Create the mods directory if it doesn't exist
    if [ ! -d "$FACTORIO_MODS_DIR" ]; then
        echo "Creating mods directory: $FACTORIO_MODS_DIR"
        mkdir -p "$FACTORIO_MODS_DIR"
    fi
    echo "Moving $ZIP_NAME to $FACTORIO_MODS_DIR..."
    mv "/tmp/$ZIP_NAME" "$FACTORIO_MODS_DIR/"
    DESTINATION="$FACTORIO_MODS_DIR/$ZIP_NAME"
fi

# Clean up temp directory
rm -rf "$TEMP_DIR"

# Verify the file was moved successfully
if [ -f "$DESTINATION" ]; then
    echo "Success! Mod packaged and exported."
    echo "Location: $DESTINATION"
else
    echo "Error: Failed to move $ZIP_NAME to destination"
    exit 1
fi

