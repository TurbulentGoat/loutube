#!/bin/bash

# YouTube Downloader Update Script
# Updates yt-dlp to the latest version and refreshes the script if installed system-wide

echo "=== YouTube Downloader Update ==="
echo

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Update yt-dlp
print_status "Updating yt-dlp to the latest version..."
if command -v pip3 &> /dev/null; then
    pip3 install --upgrade yt-dlp
else
    python3 -m pip install --upgrade yt-dlp
fi

# Check new version
if command -v yt-dlp &> /dev/null; then
    new_version=$(yt-dlp --version 2>&1)
    print_success "yt-dlp updated to version: $new_version"
else
    echo "Warning: Could not verify yt-dlp installation"
fi

# Update system installation if it exists
if command -v ytdl &> /dev/null; then
    ytdl_path=$(which ytdl)
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    print_status "Updating system installation at: $ytdl_path"
    
    # Check if we can write to the installation directory
    if [[ -w "$ytdl_path" ]]; then
        cp "$script_dir/youtube_downloader.py" "$ytdl_path"
        print_success "System installation updated"
    else
        echo "Note: Need sudo permissions to update system installation"
        echo "Run: sudo cp youtube_downloader.py $ytdl_path"
    fi
fi

print_success "Update complete!"
echo
echo "What's new in recent updates:"
echo "• Better configuration file support"
echo "• Improved video quality selection (H.264+AAC)"
echo "• Enhanced audio downloads with metadata"
echo "• Automatic chapter and subtitle embedding"
echo "• Better browser cookie detection"
echo "• More reliable error handling"