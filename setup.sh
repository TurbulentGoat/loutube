#!/bin/bash

# YouTube Downloader Setup Script
# This script sets up the YouTube downloader for easy system-wide use

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=== YouTube Downloader Setup ==="
echo

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

# Install yt-dlp
print_status "Installing/updating yt-dlp..."
YTDLP_INSTALLED=false

# Try pip installation first
print_status "Attempting to install yt-dlp via pip..."
echo "Installing yt-dlp via pip typically provides the newest upstream version."

# Choose pip executable
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    PIP_CMD="python3 -m pip"
fi

# Try user installation first (safer)
print_status "Trying user installation (--user)..."
if $PIP_CMD install --user yt-dlp &> /dev/null; then
    print_success "yt-dlp installed via pip (user installation)."
    YTDLP_INSTALLED=true
else
    print_warning "User installation failed. Trying with --break-system-packages..."
    
    # Ask for permission to use --break-system-packages
    if [[ $EUID -ne 0 ]]; then
        echo "This may require sudo and --break-system-packages flag."
        read -r -p "Try system installation with sudo? [y/N] " response
        response=${response,,}
        
        if [[ "$response" == "y" || "$response" == "yes" ]]; then
            if sudo $PIP_CMD install yt-dlp --break-system-packages &> /dev/null; then
                print_success "yt-dlp installed via pip (system installation)."
                YTDLP_INSTALLED=true
            else
                print_warning "Pip installation failed. Trying package managers..."
            fi
        else
            print_status "Skipping pip installation. Trying package managers..."
        fi
    else
        # Running as root
        if $PIP_CMD install yt-dlp --break-system-packages &> /dev/null; then
            print_success "yt-dlp installed via pip."
            YTDLP_INSTALLED=true
        else
            print_warning "Pip installation failed. Trying package managers..."
        fi
    fi
fi

# Fallback to package managers if pip failed
if [[ "$YTDLP_INSTALLED" == false ]]; then
    print_status "Trying package manager installation..."
    
    # Detect package manager and install
    if command -v apt &> /dev/null; then
        print_status "Using apt (Debian/Ubuntu)..."
        if sudo apt update && sudo apt install -y yt-dlp; then
            print_success "yt-dlp installed via apt."
            YTDLP_INSTALLED=true
        fi
    elif command -v yum &> /dev/null; then
        print_status "Using yum (CentOS/RHEL)..."
        if sudo yum install -y yt-dlp; then
            print_success "yt-dlp installed via yum."
            YTDLP_INSTALLED=true
        fi
    elif command -v dnf &> /dev/null; then
        print_status "Using dnf (Fedora)..."
        if sudo dnf install -y yt-dlp; then
            print_success "yt-dlp installed via dnf."
            YTDLP_INSTALLED=true
        fi
    elif command -v pacman &> /dev/null; then
        print_status "Using pacman (Arch Linux)..."
        if sudo pacman -S --noconfirm yt-dlp; then
            print_success "yt-dlp installed via pacman."
            YTDLP_INSTALLED=true
        fi
    elif command -v brew &> /dev/null; then
        print_status "Using brew (macOS)..."
        if brew install yt-dlp; then
            print_success "yt-dlp installed via brew."
            YTDLP_INSTALLED=true
        fi
    else
        print_error "No supported package manager found."
        print_error "Please install yt-dlp manually:"
        echo "  • Via pip: pip3 install --user yt-dlp"
        echo "  • Or download from: https://github.com/yt-dlp/yt-dlp/releases"
        exit 1
    fi
fi

# Verify yt-dlp installation
if ! command -v yt-dlp &> /dev/null; then
    print_error "yt-dlp installation failed or not in PATH."
    echo "Please install yt-dlp manually and re-run this script."
    exit 1
fi

print_success "yt-dlp is available: $(yt-dlp --version 2>/dev/null | head -n1)"

# Recommend nightly build update
echo
print_status "yt-dlp Nightly Build Recommendation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
print_warning "IMPORTANT: For best compatibility and latest features, we recommend using the nightly build."
echo
echo "Why use the nightly build?"
echo "  • Latest bug fixes and improvements"
echo "  • Better support for new sites and formats"
echo "  • Enhanced extractors for YouTube and other platforms"
echo "  • More stable downloads with latest fixes"
echo
echo "The nightly build is generally stable and recommended by the yt-dlp developers."
echo "Package manager versions can be outdated and may have compatibility issues."
echo
print_status "Current version: $(yt-dlp --version 2>/dev/null | head -n1)"

read -r -p "Would you like to update to the latest nightly build now? [Y/n] " response
response=${response,,}

if [[ "$response" != "n" && "$response" != "no" ]]; then
    print_status "Updating to nightly build..."
    echo "This may take a moment to download and install..."
    
    if yt-dlp --update-to nightly; then
        print_success "Successfully updated to nightly build!"
        echo "New version: $(yt-dlp --version 2>/dev/null | head -n1)"
    else
        print_warning "Failed to update to nightly build."
        print_status "This might be due to:"
        echo "  • Permission issues (try with sudo if needed)"
        echo "  • Network connectivity"
        echo "  • Installation method restrictions"
        echo
        print_status "You can manually update later using: yt-dlp --update-to nightly"
        echo "Or reinstall using pip: pip3 install --upgrade --user yt-dlp[default]"
    fi
else
    print_status "Skipping nightly update."
    print_warning "Consider updating later for the best experience:"
    echo "  yt-dlp --update-to nightly"
fi

echo

# Check for VLC (optional but recommended)
if ! command -v vlc &> /dev/null; then
    print_warning "VLC not found. Video streaming will not work."
    echo "To install VLC:"
    echo "  Ubuntu/Debian: sudo apt install vlc"
    echo "  CentOS/RHEL:   sudo yum install vlc"
    echo "  Arch Linux:    sudo pacman -S vlc"
    echo "  macOS:         brew install --cask vlc"
    echo
else
    print_success "VLC found: streaming feature will work."
fi

# Copy the script to the install directory
print_status "Installing YouTube downloader script..."
if [[ ! -f "$SCRIPT_DIR/loutube.py" ]]; then
    print_error "loutube.py not found in $SCRIPT_DIR"
    print_error "Make sure loutube.py is in the same directory as this setup script."
    exit 1
fi

cp "$SCRIPT_DIR/loutube.py" "$INSTALL_DIR/loutube"
chmod +x "$INSTALL_DIR/loutube"

# Copy configuration file
print_status "Installing configuration file..."
if [[ -f "$SCRIPT_DIR/yt-dlp.conf" ]]; then
    mkdir -p "$CONFIG_DIR/yt-dlp"
    cp "$SCRIPT_DIR/yt-dlp.conf" "$CONFIG_DIR/yt-dlp/config"
    print_success "Configuration file installed."
else
    print_warning "yt-dlp.conf not found. Creating basic configuration..."
    mkdir -p "$CONFIG_DIR/yt-dlp"
    cat > "$CONFIG_DIR/yt-dlp/config" << 'EOF'
# Basic yt-dlp configuration for loutube
--format "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
--merge-output-format mp4
--write-thumbnail
--embed-thumbnail
--write-description
--write-info-json
--embed-chapters
--embed-subs
--write-auto-subs
--sub-langs "en.*,en"
--sponsorblock-mark all
--sponsorblock-remove sponsor,selfpromo,interaction,intro,outro
EOF
    print_success "Basic configuration file created."
fi

# Create default directories
print_status "Creating default directories..."
mkdir -p "$HOME/Videos/ytd-video"
mkdir -p "$HOME/Music/ytd-music"

# Final verification
print_status "Verifying installation..."
if command -v loutube &> /dev/null; then
    print_success "Installation complete and verified!"
else
    print_warning "loutube command not found. You may need to restart your terminal."
fi

echo
print_success "Setup complete!"
echo
print_status "Usage:"
echo "  loutube 'https://youtube.com/...' - Direct URL"
echo "  loutube --help                   - Show help"
echo "  loutube --config                 - Show configuration"
echo "  loutube --recent                 - Show recent downloads"
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

print_status "Maintenance tips:"
echo "  • Keep yt-dlp updated: yt-dlp --update-to nightly"
echo "  • Check for issues: loutube --config"
echo
print_success "Try running: loutube https://www.youtube.com/watch?v=dQw4w9WgXcQ"
