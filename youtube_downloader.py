#!/usr/bin/env python3

import os
import subprocess
import urllib.parse
import sys
import platform
from pathlib import Path

# Configuration - Users can modify these paths
DEFAULT_VIDEO_DIR = os.path.join(Path.home(), "Videos", "ytd-video")
DEFAULT_MUSIC_DIR = os.path.join(Path.home(), "Music", "ytd-music")

def display_logo():
    """Display ASCII art logo for the program."""
    try:
        # Try multiple locations for the logo
        possible_paths = [
            # Installed location (snap-compatible, no dot prefix)
            os.path.join(Path.home(), "ytdl-logo.png"),
            # Development/source directory
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "loutube.png"),
            # Legacy locations
            os.path.join(Path.home(), ".ytdl-logo.png"),
            os.path.join(Path.home(), ".local", "share", "ytdl", "loutube.png")
        ]
        
        logo_path = None
        for path in possible_paths:
            if os.path.exists(path):
                logo_path = path
                break
        
        if logo_path:
            # Use ascii-image-converter command exactly as provided
            command = [
                "ascii-image-converter", 
                "-C", 
                "-m", "+* #%@", 
                logo_path, 
                "-W", "125", 
                "--complex"
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(result.stdout)
                return
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    except Exception:
        pass
    
    # Fallback: Use the pre-generated ASCII art if ascii-image-converter is not available
    fallback_ascii = """+++++********************************++++++++++++++++++++++++++++++++++++++++++***********++++++++++++*### +++++++++++++++++++
+*************************************++++++#@@@ ++++++++++++++++++++++++++++*@@@@@@@@@@@@+++++++++++ @@@#+++++++++++++++++++
+***************** ********************+++++#@@@#+++++++++++++++++++++++++++++   #@@@@   *+++++++++++ @@@#+++++++++++++++++++
***************  ***** ****************+++++#@@@ ++++++++++****+++++++++++++++++++@@@%+++++++++++++++ @@@ +****+++++++****+++
*************** @@%# *******************++++#@@@ +++++++*%@@@@@@%*++%@@@*++@@@@++*@@@%++ @@@%++ @@@#+ @@@%%@@@@%+++*%@@@@@@%+
*************** @@@@@%#  ***************++++#@@@ +++++++@@@%++%@@@++%@@@*++@@@@++*@@@%++*@@@%++ @@@#+ @@@@*+#@@@#+*@@@#+*@@@%
*************** @@@@@@@@@# *************++++#@@@ ++++++ @@@#++#@@@ +%@@@*++@@@@++*@@@%++*@@@%++ @@@#+ @@@#++*@@@%+#@@@*++@@@@
*************** @@@@@%#  ***************++++#@@@ ++++++#@@@#++#@@@#+%@@@*++@@@@++*@@@%++*@@@%++ @@@#+ @@@#++*@@@@+#@@@% #@@@@
*************** @@%# *******************++++#@@@#++++++#@@@#++#@@@#+%@@@*++@@@@++*@@@%++*@@@%++ @@@#+ @@@#++*@@@@+#@@@%%%####
***************  ***** ****************+++++#@@@ ++++++#@@@#++#@@@ +%@@@*++@@@@++*@@@%++ @@@%++ @@@#+ @@@ ++*@@@%+#@@@*++****
+***************** ********************+++++#@@@#*****+*@@@%++%@@@++%@@@ + @@@@++*@@@%++*@@@%++%@@@#+ @@@%++%@@@#+*@@@#++@@@@
+*************************************++++++#@@@@@@@@@*+ %@@@@@@%*++*@@@@@%#@@@++*@@@%+++#@@@@@#@@@#+ @@@%@@@@@#+++ @@@@@@@%+
++++********************************++++++++**********++++**  *+++++++*  *++***+++****++++** *++***+++***++***+++++++** **+++"""
    
    print(fallback_ascii)

# Global variable to cache browser cookies
_cached_browser_cookies = None
_cookies_checked = False

def get_brave_snap_path():
    """
    Get a generic Brave browser snap path by detecting the user's home directory
    and finding the active Brave snap profile.
    Returns the Brave browser path or None if not found.
    """
    try:
        import glob
        
        # Get current user's home directory
        home_dir = str(Path.home())
        
        # Look for Brave snap directories (they have version numbers)
        brave_snap_pattern = os.path.join(home_dir, "snap", "brave", "*", ".config", "BraveSoftware", "Brave-Browser", "Default")
        brave_paths = glob.glob(brave_snap_pattern)
        
        if brave_paths:
            # Sort by version number (highest first) and return the most recent
            brave_paths.sort(key=lambda x: int(x.split("/")[-5]) if x.split("/")[-5].isdigit() else 0, reverse=True)
            # Format as brave:path for yt-dlp
            return f"brave:{brave_paths[0]}"
        
        return None
    except (ImportError, IndexError, ValueError, OSError):
        return None

def get_browser_cookies_fast():
    """
    Quickly find available browser cookies using a much faster method.
    Returns the browser cookie string for yt-dlp, or None if none found.
    """
    global _cached_browser_cookies, _cookies_checked
    
    # Return cached result if already checked
    if _cookies_checked:
        return _cached_browser_cookies
    
    system = platform.system().lower()
    
    # Common browser paths by OS  
    browser_paths = {
        'linux': [  # Linux
            ('brave-snap', get_brave_snap_path()),  # Generic Brave snap path (try first)
            ('brave', 'brave'),
            ('firefox', 'firefox'),
            ('chrome', 'chrome'),
            ('chromium', 'chromium'),
            ('edge', 'edge'),
        ],
        'darwin': [  # macOS
            ('firefox', 'firefox'),
            ('chrome', 'chrome'),
            ('brave', 'brave'),
            ('safari', 'safari'),
            ('edge', 'edge'),
        ],
        'windows': [  # Windows
            ('firefox', 'firefox'),
            ('chrome', 'chrome'),
            ('brave', 'brave'),
            ('edge', 'edge'),
        ]
    }
    
    if system not in browser_paths:
        _cookies_checked = True
        return None
    
    # Quick test - just check if yt-dlp recognizes the browser option (much faster than full simulation)
    for browser_name, browser_key in browser_paths[system]:
        # Skip if browser_key is None (e.g., when Brave snap path not found)
        if browser_key is None:
            continue
            
        try:
            # Just test if yt-dlp accepts the browser option
            test_command = [
                "yt-dlp", 
                "--cookies-from-browser", browser_key,
                "--version"  # This just tests if the browser option is valid, returns immediately
            ]
            result = subprocess.run(test_command, capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                print(f"Using cookies from {browser_name}")
                _cached_browser_cookies = browser_key
                _cookies_checked = True
                return browser_key
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    print("Warning: Could not find browser cookies. Some videos may be unavailable.")
    _cookies_checked = True
    return None

def get_browser_cookies():
    """Legacy function name - calls the fast version"""
    return get_browser_cookies_fast()

def find_config_file():
    """Find the yt-dlp configuration file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_locations = [
        # Portable config (same directory as script)
        os.path.join(script_dir, "yt-dlp.conf"),
        # User config directories
        os.path.join(Path.home(), ".config", "yt-dlp", "config"),
        os.path.join(Path.home(), ".yt-dlp", "config"),
        os.path.join(Path.home(), "yt-dlp.conf"),
        # System config
        "/etc/yt-dlp/config",
        "/etc/yt-dlp.conf"
    ]
    
    for config_path in config_locations:
        if os.path.exists(config_path):
            return config_path
    return None

def build_base_command(url, browser_cookies=None):
    """Build the base yt-dlp command with optional cookies and config."""
    command = ["yt-dlp"]
    
    # Add configuration file if it exists
    config_file = find_config_file()
    if config_file:
        command.extend(["--config-location", config_file])
    
    if browser_cookies:
        command.extend(["--cookies-from-browser", browser_cookies])
    
    return command

def is_playlist(url):
    """Check if URL is a playlist."""
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    return "list" in query_params

def list_formats(url, browser_cookies=None):
    """List available formats for a video, filtering out m3u8 and mp4 formats and unwanted columns."""
    command = build_base_command(url, browser_cookies)
    command.extend(["--list-formats", url])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
        # Filter out m3u8 and mp4 formats from the output and format columns
        filtered_lines = []
        for line in result.stdout.split('\n'):
            if ('m3u8' not in line.lower() and 'mp4' not in line.lower()) or 'ID' in line or 'format code' in line.lower() or '---' in line:
                # Parse and filter columns for each line
                filtered_line = filter_format_columns(line)
                if filtered_line:
                    filtered_lines.append(filtered_line)
        return '\n'.join(filtered_lines)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Error: Failed to list formats.\n{e}")
        return None

def filter_format_columns(line):
    """Filter format line to show only ID, FILESIZE, VCODEC, ACODEC, and MORE columns."""
    # Skip empty lines
    if not line.strip():
        return ""
    
    # Handle header line
    if 'ID' in line and 'FILESIZE' in line:
        # Create simplified header
        return "ID       FILESIZE    VCODEC       ACODEC       MORE"
    
    # Handle separator line
    if '---' in line:
        return "---      --------    ------       ------       ----"
    
    # Parse yt-dlp format which uses pipe separators |
    # Format: ID EXT RESOLUTION FPS CH | FILESIZE TBR PROTO | VCODEC VBR ACODEC ABR ASR MORE INFO
    try:
        # Split by pipe separators
        if '|' in line:
            sections = line.split('|')
            if len(sections) >= 3:
                # Section 1: ID EXT RESOLUTION FPS CH
                first_section = sections[0].strip().split()
                id_part = first_section[0] if len(first_section) > 0 else ""
                
                # Section 2: FILESIZE TBR PROTO
                second_section = sections[1].strip().split()
                filesize_part = second_section[0] if len(second_section) > 0 else ""
                
                # Section 3: VCODEC VBR ACODEC ABR ASR MORE INFO
                third_section = sections[2].strip().split()
                vcodec_part = third_section[0] if len(third_section) > 0 else ""
                acodec_part = third_section[2] if len(third_section) > 2 else ""
                
                # More info is everything after ABR ASR (positions 3+)
                more_parts = " ".join(third_section[4:]) if len(third_section) > 4 else ""
                
                # Format the output with consistent spacing
                return f"{id_part:<8} {filesize_part:<11} {vcodec_part:<12} {acodec_part:<12} {more_parts}"
        
        # If no pipes found, return original line (might be a different format)
        return line
        
    except (IndexError, ValueError):
        return line  # Return original line if parsing fails

def watch_video(url, browser_cookies=None):
    """Stream video at selected quality using VLC."""
    print("Fetching available formats...")
    formats_output = list_formats(url, browser_cookies)
    
    if not formats_output:
        print("Could not retrieve format list. Using default format.")
        format_code = "best[height>=720]/best"
    else:
        print("\nAvailable formats:")
        print(formats_output)
        
        print("\nEnter format selection:")
        print("- Enter a specific format ID (e.g., '137+140' for video+audio from the ID column)")        
        user_format = safe_input("\nFormat choice: ").strip()
        
        if not user_format:
            format_code = "best[height>=720]/best"
            print("No format specified, using default.")
        else:
            format_code = user_format
    
    command = build_base_command(url, browser_cookies)
    command.extend([
        "-f", format_code,
        "--sponsorblock-remove", "all",
        "-o", "-",
        url
    ])
    
    vlc_command = ["vlc", "--play-and-exit", "-"]
    
    try:
        print(f"Streaming video with format '{format_code}' from: {url}")
        # Check if VLC is available
        subprocess.run(["vlc", "--version"], capture_output=True, check=True)
        
        # Pipe yt-dlp output directly to VLC
        yt_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        vlc_process = subprocess.Popen(vlc_command, stdin=yt_process.stdout, stderr=subprocess.PIPE)
        yt_process.stdout.close()
        vlc_process.communicate()
        print("Streaming complete!")
    except FileNotFoundError:
        print("Error: VLC media player not found. Please install VLC to use streaming feature.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to stream video.\n{e}")
    except KeyboardInterrupt:
        print("\nStreaming interrupted by user.")

def download_video(url, browser_cookies=None, output_dir=None):
    """Download video with audio using high-quality defaults."""
    if output_dir is None:
        output_dir = DEFAULT_VIDEO_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    video_title = safe_input("Video title (or press Enter for auto-generated): ").strip()
    
    # Use auto-generated title if none provided
    output_template = os.path.join(output_dir, f"{video_title}.%(ext)s") if video_title else os.path.join(output_dir, "%(title)s.%(ext)s")
    
    command = build_base_command(url, browser_cookies)
    command.extend([
        # High quality video with audio, prefer h264+aac for compatibility
        "-f", "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[vcodec=h264]+bestaudio[acodec=aac]/bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",  # Ensure mp4 container for compatibility
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "-o", output_template,
        url,
    ])

    try:
        print(f"Downloading high-quality video from: {url}")
        subprocess.run(command, check=True)
        print(f"Video download complete! Files saved in '{output_dir}'.")
        print("Note: Video includes chapters, subtitles, and metadata if available.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to download video.\n{e}")

def download_audio(url, browser_cookies=None, output_dir=None):
    """Download best audio only with high quality settings."""
    if output_dir is None:
        base_output_dir = DEFAULT_MUSIC_DIR
    else:
        base_output_dir = output_dir
    
    # Ask for folder name
    folder_name = safe_input("Enter folder name for this download: ").strip()
    if not folder_name:
        folder_name = "Untitled"
    
    output_dir = os.path.join(base_output_dir, folder_name)
    os.makedirs(output_dir, exist_ok=True)
    
    if is_playlist(url):
        print(f"Downloading playlist to folder '{folder_name}'")
        # For playlists, add track numbers
        output_template = os.path.join(output_dir, "%(playlist_index)02d - %(title)s.%(ext)s")
    else:
        print(f"Downloading single track to folder '{folder_name}'")
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    
    command = build_base_command(url, browser_cookies)
    command.extend([
        "-f", "bestaudio[acodec=aac]/bestaudio/best",  # Prefer AAC for better quality
        "--extract-audio",
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "-o", output_template,
        url,
    ])
    
    try:
        print(f"Downloading high-quality audio from: {url}")
        subprocess.run(command, check=True)
        print(f"Audio download complete! Files saved in '{output_dir}'.")
        print("Note: Audio includes metadata, thumbnails, and chapter information if available.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to download audio.\n{e}")

def download_video_no_audio(url, browser_cookies=None, output_dir=None):
    """Download video only, no audio track."""
    if output_dir is None:
        output_dir = DEFAULT_VIDEO_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    title = safe_input("Video title (or press Enter for auto-generated): ").strip()
    
    if title:
        output_template = os.path.join(output_dir, f"{title}_video_only.%(ext)s")
    else:
        output_template = os.path.join(output_dir, "%(title)s_video_only.%(ext)s")
    
    command = build_base_command(url, browser_cookies)
    command.extend([
        "-f", "bestvideo",
        "--sponsorblock-remove", "all",
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "-o", output_template,
        url,
    ])
    
    try:
        print(f"Downloading video only from: {url}")
        subprocess.run(command, check=True)
        print(f"Video-only download complete! Files saved in '{output_dir}'.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to download video only.\n{e}")

def download_audio_from_video(url, browser_cookies=None, output_dir=None):
    """Extract audio from a video track."""
    if output_dir is None:
        output_dir = DEFAULT_MUSIC_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    title = safe_input("Output audio title (or press Enter for auto-generated): ").strip()
    
    output_template = os.path.join(output_dir, f"{title}.%(ext)s") if title else os.path.join(output_dir, "%(title)s.%(ext)s")
    
    command = build_base_command(url, browser_cookies)
    command.extend([
        "-f", "bestvideo+bestaudio",
        "--sponsorblock-remove", "all",
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_template,
        url,
    ])
    
    try:
        print(f"Downloading and extracting audio from video: {url}")
        subprocess.run(command, check=True)
        print(f"Extracted audio complete! Files saved in '{output_dir}'.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to extract audio.\n{e}")

def check_for_quit(user_input):
    """Check if user wants to quit and exit if so."""
    if user_input.strip() == "99":
        print("Goodbye!")
        sys.exit(0)
    return user_input

def safe_input(prompt):
    """Input wrapper that checks for quit command."""
    user_input = input(prompt)
    return check_for_quit(user_input)

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except FileNotFoundError:
        print("Error: yt-dlp is not installed or not in PATH.")
        print("Please install it with: pip install yt-dlp")
        return False
    return True

def show_help():
    """Display help information."""
    help_text = """
YouTube Downloader & Streamer - Usage Guide

BASIC USAGE:
  ytdl                                    Interactive mode
  ytdl "https://youtube.com/watch?v=..."  Direct download
  ytdl --help                            Show this help
  ytdl --config                          Show current configuration

FEATURES:
  • High-quality video downloads (up to 1080p) with H.264+AAC
  • Premium audio extraction with metadata and thumbnails  
  • Direct streaming to VLC without downloading
  • Automatic SponsorBlock integration (removes ads/sponsors)
  • Smart browser cookie detection for private content
  • Playlist support with automatic track numbering

DIRECTORIES:
  Videos: {DEFAULT_VIDEO_DIR}
  Music:  {DEFAULT_MUSIC_DIR}
  
CONFIG FILE:
  The script uses yt-dlp.conf for default settings.
  Location: ~/.config/yt-dlp/config (or same directory as script)
  
TIPS:
  • Enter 99 at any prompt to quit
  • Leave titles blank for auto-generated names
  • VLC required for streaming feature
  • Cookies automatically detected from browsers

For more information, visit: https://github.com/TurbulentGoat/youtube-downloader
""".format(DEFAULT_VIDEO_DIR=DEFAULT_VIDEO_DIR, DEFAULT_MUSIC_DIR=DEFAULT_MUSIC_DIR)
    print(help_text)

def show_config():
    """Display current configuration information."""
    print("=== YouTube Downloader Configuration ===\n")
    
    # Script info
    script_path = os.path.abspath(__file__)
    print(f"Script location: {script_path}")
    
    # Config file info
    config_file = find_config_file()
    if config_file:
        print(f"Config file: {config_file}")
        print("Config status: ✓ Found")
        
        # Show some key settings from config
        try:
            with open(config_file, 'r') as f:
                content = f.read()
                print("\nKey settings from config file:")
                
                # Extract some important settings
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '--format' in line:
                            print(f"  Quality: {line}")
                        elif '--audio-format' in line:
                            print(f"  Audio: {line}")
                        elif '--sponsorblock' in line:
                            print(f"  SponsorBlock: {line}")
                        elif '--embed-chapters' in line:
                            print(f"  Chapters: {line}")
        except Exception as e:
            print(f"Could not read config: {e}")
    else:
        print("Config file: None found")
        print("Config status: ⚠ Using built-in defaults")
    
    print(f"\nDefault directories:")
    print(f"  Videos: {DEFAULT_VIDEO_DIR}")
    print(f"  Music:  {DEFAULT_MUSIC_DIR}")
    
    # Check dependencies
    print(f"\nDependency status:")
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, check=True)
        print(f"  yt-dlp: ✓ {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"  yt-dlp: ✗ Not found or not working")
    
    try:
        subprocess.run(["vlc", "--version"], capture_output=True, check=True)
        print(f"  VLC: ✓ Available (streaming works)")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"  VLC: ⚠ Not found (streaming unavailable)")
    
    # Browser cookie status
    print(f"\nBrowser cookie detection:")
    browser_cookies = get_browser_cookies_fast()
    if browser_cookies:
        print(f"  Status: ✓ Using cookies from browser")
    else:
        print(f"  Status: ⚠ No browser cookies found")
    
    print(f"\nFor help: python3 {os.path.basename(__file__)} --help")

def main():
    # Check for help or config flags
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h', 'help']:
            show_help()
            return
        elif sys.argv[1] in ['--config', '-c', 'config']:
            show_config()
            return
        
    if not check_dependencies():
        return
    
    # Display ASCII logo
    display_logo()
    print()
    
    # Show configuration info
    config_file = find_config_file()
    if config_file:
        print(f"✓ Using configuration: {config_file}")
    else:
        print("! No configuration file found - using built-in defaults")
    
    print(f"📁 Video directory: {DEFAULT_VIDEO_DIR}")
    print(f"🎵 Music directory: {DEFAULT_MUSIC_DIR}")
    print("💡 Tip: Enter 99 at any prompt to quit, or use --help for more info\n")
    
    # Get browser cookies only when we actually need to use yt-dlp
    browser_cookies = None
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print("What would you like to do?\n")
        print("1. Watch video (stream)")
        print("2. Download video")
        print("3. Download music")
        print("99. Quit (can be used any time)\n")
        action = safe_input("Enter your choice (1, 2, 3, or 99): ").strip()
        print("")
        
        # Get cookies only now when we need them
        if action in ["1", "2", "3"]:
            browser_cookies = get_browser_cookies()
            
        if action == "1":
            watch_video(url, browser_cookies)
        elif action == "2":
            # Video download options
            print("For video downloads, choose an option:\n")
            print("1. Video with audio")
            print("2. Video only (no audio)")
            print("3. Audio only (extracted from video)")
            print("99. Quit (can be used any time)\n")
            opt = safe_input("Enter your choice (1, 2, 3, or 99): ").strip()
            print("")
            if opt == "1":
                download_video(url, browser_cookies)
            elif opt == "2":
                download_video_no_audio(url, browser_cookies)
            elif opt == "3":
                download_audio_from_video(url, browser_cookies)
            else:
                print("Invalid option. Exiting.")
        elif action == "3":
            # Music download - automatically handles playlist detection
            download_audio(url, browser_cookies)
        elif action == "99":
            pass  # Already handled by safe_input
        else:
            print("Invalid choice. Exiting.")
    else:
        print("Select download type:\n")
        print("1. Video")
        print("2. Music")
        print("99. Quit (can be used any time)\n")
        choice = safe_input("Enter your choice (1, 2, or 99): ").strip()
        print("")
        if choice not in ("1", "2", "99"):
            print("Invalid choice. Exiting.")
            return

        url = safe_input("Enter the link: ").strip()
        if not url:
            print("Error: No URL provided.")
            return

        # Get cookies only now when we need them
        browser_cookies = get_browser_cookies()

        if choice == "2":
            download_audio(url, browser_cookies)
        elif choice == "1":
            print("For video downloads, choose an option:\n")
            print("1. Video with audio")
            print("2. Video only (no audio)")
            print("3. Audio only (extracted from video)")
            print("99. Quit (can be used any time)\n")
            opt = safe_input("Enter your choice (1, 2, 3, or 99): ").strip()
            print("")
            if opt == "1":
                download_video(url, browser_cookies)
            elif opt == "2":
                download_video_no_audio(url, browser_cookies)
            elif opt == "3":
                download_audio_from_video(url, browser_cookies)
            else:
                print("Invalid option. Exiting.")

if __name__ == "__main__":
    main()
