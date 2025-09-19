#!/bin/bash

# YouTube Downloader Setup Script
# This script sets up the YouTube downloader for easy system-wide use

set -e  # Exit on any error

echo "=== YouTube Downloader Setup ==="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_warning "Running as root. This will install system-wide."
    INSTALL_DIR="/usr/local/bin"
    CONFIG_DIR="/etc"
else
    print_status "Running as user. This will install for current user only."
    INSTALL_DIR="$HOME/.local/bin"
    CONFIG_DIR="$HOME/.config"
    
    # Create directories if they don't exist
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        print_status "Adding $INSTALL_DIR to PATH..."
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        export PATH="$HOME/.local/bin:$PATH"
        print_success "Added to PATH. You may need to restart your terminal or run: source ~/.bashrc"
    fi
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_status "Checking dependencies..."

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed."
    echo "Please install Python 3 first:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  CentOS/RHEL:   sudo yum install python3 python3-pip"
    echo "  Arch Linux:    sudo pacman -S python python-pip"
    echo "  macOS:         brew install python3"
    exit 1
fi

# Check for pip
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    print_error "pip is required but not installed."
    echo "Please install pip first:"
    echo "  Ubuntu/Debian: sudo apt install python3-pip"
    echo "  CentOS/RHEL:   sudo yum install python3-pip"
    exit 1
fi

# Install yt-dlp
print_status "Installing/updating yt-dlp..."
if command -v pip3 &> /dev/null; then
    pip3 install --upgrade yt-dlp
else
    python3 -m pip install --upgrade yt-dlp
fi

# Check for VLC (optional but recommended)
if ! command -v vlc &> /dev/null; then
    print_warning "VLC not found. Video streaming will not work."
    echo "To install VLC:"
    echo "  Ubuntu/Debian: sudo apt install vlc"
    echo "  CentOS/RHEL:   sudo yum install vlc"
    echo "  Arch Linux:    sudo pacman -S vlc"
    echo "  macOS:         brew install --cask vlc"
    echo
fi

# Copy the script to the install directory
print_status "Installing YouTube downloader script..."
cp "$SCRIPT_DIR/youtube_downloader.py" "$INSTALL_DIR/ytdl"
chmod +x "$INSTALL_DIR/ytdl"

# Copy configuration file
print_status "Installing configuration file..."
mkdir -p "$CONFIG_DIR/yt-dlp"
cp "$SCRIPT_DIR/yt-dlp.conf" "$CONFIG_DIR/yt-dlp/config"

# Copy images if they exist
if [[ -f "$SCRIPT_DIR/loutube.png" ]]; then
    cp "$SCRIPT_DIR/loutube.png" "$INSTALL_DIR/"
fi

print_success "Installation complete!"
echo
print_status "Usage:"
echo "  ytdl                           - Interactive mode"
echo "  ytdl 'https://youtube.com/...' - Direct URL"
echo
print_status "Configuration:"
echo "  Config file: $CONFIG_DIR/yt-dlp/config"
echo "  Edit this file to change default behavior"
echo
print_status "Default directories:"
echo "  Videos: ~/Videos/ytd-video"
echo "  Music:  ~/Music/ytd-music"
echo
if [[ $EUID -ne 0 && ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    print_warning "You may need to restart your terminal or run:"
    echo "  source ~/.bashrc"
fi

print_success "Setup complete! Try running: ytdl"