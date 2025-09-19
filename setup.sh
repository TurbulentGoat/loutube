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

# Try apt first (Debian/Ubuntu systems)
if command -v apt &> /dev/null; then
    print_status "Attempting to install yt-dlp via apt..."
    if sudo apt update && sudo apt install -y yt-dlp; then
        print_success "yt-dlp installed successfully via apt"
    else
        print_warning "apt installation failed, trying alternative methods..."
        # Fall back to pipx if available
        if command -v pipx &> /dev/null; then
            print_status "Installing yt-dlp via pipx..."
            pipx install yt-dlp
        else
            print_status "pipx not found. Installing pipx first..."
            if sudo apt install -y pipx; then
                pipx install yt-dlp
            else
                print_error "Could not install pipx. Please install yt-dlp manually:"
                echo "  Option 1: sudo apt install yt-dlp"
                echo "  Option 2: pipx install yt-dlp"
                echo "  Option 3: pip install --user yt-dlp"
                exit 1
            fi
        fi
    fi
# Try yum/dnf for Red Hat systems
elif command -v yum &> /dev/null || command -v dnf &> /dev/null; then
    PKG_MGR="yum"
    if command -v dnf &> /dev/null; then
        PKG_MGR="dnf"
    fi
    print_status "Attempting to install yt-dlp via $PKG_MGR..."
    if sudo $PKG_MGR install -y yt-dlp; then
        print_success "yt-dlp installed successfully via $PKG_MGR"
    else
        print_warning "$PKG_MGR installation failed, trying pipx..."
        if command -v pipx &> /dev/null; then
            pipx install yt-dlp
        else
            sudo $PKG_MGR install -y pipx && pipx install yt-dlp
        fi
    fi
# Try pacman for Arch systems
elif command -v pacman &> /dev/null; then
    print_status "Attempting to install yt-dlp via pacman..."
    if sudo pacman -S --noconfirm yt-dlp; then
        print_success "yt-dlp installed successfully via pacman"
    else
        print_warning "pacman installation failed, trying pipx..."
        if command -v pipx &> /dev/null; then
            pipx install yt-dlp
        else
            sudo pacman -S --noconfirm python-pipx && pipx install yt-dlp
        fi
    fi
# Fall back to pip methods
else
    print_status "No system package manager found, using pip methods..."
    if command -v pipx &> /dev/null; then
        print_status "Installing yt-dlp via pipx..."
        pipx install yt-dlp
    elif command -v pip3 &> /dev/null; then
        print_status "Installing yt-dlp via pip3 (user install)..."
        pip3 install --user --upgrade yt-dlp
    elif python3 -m pip --version &> /dev/null; then
        print_status "Installing yt-dlp via python3 -m pip (user install)..."
        python3 -m pip install --user --upgrade yt-dlp
    else
        print_error "No suitable installation method found. Please install yt-dlp manually:"
        echo "  Option 1: Install pipx and run: pipx install yt-dlp"
        echo "  Option 2: Use system package manager"
        echo "  Option 3: Create virtual environment and use pip"
        exit 1
    fi
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

# Check for jp2a (for ASCII logo)
if ! command -v jp2a &> /dev/null; then
    print_status "jp2a not found. Installing for ASCII logo display..."
    
    # Try to install jp2a based on the system
    if command -v apt &> /dev/null; then
        if sudo apt update && sudo apt install -y jp2a; then
            print_success "jp2a installed successfully via apt"
        else
            print_warning "Failed to install jp2a via apt. Logo will use fallback display."
        fi
    elif command -v yum &> /dev/null; then
        if sudo yum install -y jp2a; then
            print_success "jp2a installed successfully via yum"
        else
            print_warning "Failed to install jp2a via yum. Logo will use fallback display."
        fi
    elif command -v dnf &> /dev/null; then
        if sudo dnf install -y jp2a; then
            print_success "jp2a installed successfully via dnf"
        else
            print_warning "Failed to install jp2a via dnf. Logo will use fallback display."
        fi
    elif command -v pacman &> /dev/null; then
        if sudo pacman -S --noconfirm jp2a; then
            print_success "jp2a installed successfully via pacman"
        else
            print_warning "Failed to install jp2a via pacman. Logo will use fallback display."
        fi
    elif command -v brew &> /dev/null; then
        if brew install jp2a; then
            print_success "jp2a installed successfully via brew"
        else
            print_warning "Failed to install jp2a via brew. Logo will use fallback display."
        fi
    else
        print_warning "jp2a not found and no supported package manager detected."
        echo "To install jp2a manually:"
        echo "  Ubuntu/Debian: sudo apt install jp2a"
        echo "  CentOS/RHEL:   sudo yum install jp2a"
        echo "  Arch Linux:    sudo pacman -S jp2a"
        echo "  macOS:         brew install jp2a"
        echo "Logo will use fallback display."
        echo
    fi
else
    print_success "jp2a found - ASCII logo will work"
fi

# Copy the script to the install directory
print_status "Installing YouTube downloader script..."
cp "$SCRIPT_DIR/loutube.py" "$INSTALL_DIR/loutube"
chmod +x "$INSTALL_DIR/loutube"

# Copy configuration file
print_status "Installing configuration file..."
mkdir -p "$CONFIG_DIR/yt-dlp"
cp "$SCRIPT_DIR/yt-dlp.conf" "$CONFIG_DIR/yt-dlp/config"

# Copy images if they exist
if [[ -f "$SCRIPT_DIR/loutube.png" ]]; then
    # Copy to home directory for snap access compatibility (no dot prefix)
    cp "$SCRIPT_DIR/loutube.png" "$HOME/ytdl-logo.png"
    print_status "Logo image copied to $HOME/ytdl-logo.png"
fi

print_success "Installation complete!"
echo
print_status "Usage:"
echo "  loutube                           - Interactive mode"
echo "  loutube 'https://youtube.com/...' - Direct URL"
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

print_success "Setup complete! Try running: loutube"
# TEST MARKER - If you see this comment, the update worked! $(date)
