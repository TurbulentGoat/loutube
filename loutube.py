#!/usr/bin/env python3
import os
import subprocess
import urllib.parse
import sys
import platform
import signal
import time
import json
import re
import glob
import shutil
from pathlib import Path

# Global cache for browser cookies
_cached_browser_cookies = None
_cookies_checked = False

YOUTUBE_HOST_SUFFIXES = (
    "youtube.com",
    "youtube-nocookie.com",
)

def draw_progress_counter(percentage, speed="", eta="", downloaded="", total=""):
    """Display a simple percentage counter on a single line."""
    # Clamp percentage to 0-100 range
    percentage = max(0, min(100, percentage))
    
    # Build the progress line with just the percentage
    progress_line = f"Progress: {percentage:6.1f}%"
    
    # Add additional info if available
    if downloaded and total and total != "N/A":
        progress_line += f" ({downloaded}/{total})"
    elif downloaded:
        progress_line += f" ({downloaded})"
    
    if speed and speed != "Unknown":
        progress_line += f" at {speed}"
    if eta and eta not in {"Unknown", "N/A"}:
        progress_line += f" ETA {eta}"

    # Get previous length for padding
    previous_length = getattr(draw_progress_counter, "_prev_length", 0)
    padding = " " * max(0, previous_length - len(progress_line))

    sys.stdout.write("\r" + progress_line + padding)
    sys.stdout.flush()

    draw_progress_counter._prev_length = len(progress_line)

def parse_progress_line(line):
    """Parse yt-dlp progress line and extract percentage, speed, eta, etc."""
    # Look for patterns like "Downloaded X of Y (Z%) at Aspeed ETA Btime"
    match = re.search(r'Downloaded\s+([^\s]+)\s+of\s+([^\s]+)\s+\(([0-9.]+)%\)\s+at\s+([^\s]+)\s+ETA\s+([^\s]+)', line)
    if match:
        downloaded = match.group(1)
        total = match.group(2)
        percentage = float(match.group(3))
        speed = match.group(4)
        eta = match.group(5)
        return {
            'percentage': percentage,
            'downloaded': downloaded,
            'total': total,
            'speed': speed,
            'eta': eta
        }
    
    # Alternative pattern for cases where total might be "N/A" or format is different
    match2 = re.search(r'Downloaded\s+([^\s]+)\s+of\s+([^\s]+)\s+\(\s*([0-9.]+)%\s*\)', line)
    if match2:
        downloaded = match2.group(1)
        total = match2.group(2)
        percentage = float(match2.group(3))
        # Extract speed and ETA if they exist after the percentage
        speed_match = re.search(r'at\s+([^\s]+)', line)
        eta_match = re.search(r'ETA\s+([^\s]+)', line)
        speed = speed_match.group(1) if speed_match else "Unknown"
        eta = eta_match.group(1) if eta_match else "Unknown"
        return {
            'percentage': percentage,
            'downloaded': downloaded,
            'total': total,
            'speed': speed,
            'eta': eta
        }
    
    return None

def run_with_progress_counter(command, cwd=None):
    """Run a command and display a simple percentage counter instead of vertical progress"""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
        cwd=cwd
    )
    
    draw_progress_counter._prev_length = 0
    had_progress = False

    try:
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a progress line
            progress_info = parse_progress_line(line)
            if progress_info:
                # Update progress counter
                draw_progress_counter(
                    progress_info['percentage'],
                    downloaded=progress_info['downloaded'],
                    total=progress_info['total'],
                    speed=progress_info['speed'],
                    eta=progress_info['eta']
                )
                had_progress = True
            else:
                # If it's not a progress line and it's not just another download info line
                # Print it, but first move to a new line if we had a progress counter
                if 'Downloaded' not in line and '[download]' not in line.lower():
                    if had_progress:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        draw_progress_counter._prev_length = 0
                        had_progress = False
                    print(line)
                # Also show important messages even if they contain 'Downloaded'
                elif any(keyword in line.lower() for keyword in ['error', 'warning', 'finished', 'complete']):
                    if had_progress:
                        sys.stdout.write("\n")
                        sys.stdout.flush()
                        draw_progress_counter._prev_length = 0
                        had_progress = False
                    print(line)
        
        # Wait for process to complete
        process.wait()
        
        # Print final newline after progress counter
        if had_progress:
            sys.stdout.write("\n")
            sys.stdout.flush()
            draw_progress_counter._prev_length = 0

        return process.returncode
        
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        sys.stdout.write("\nDownload interrupted by user.\n")
        sys.stdout.flush()
        draw_progress_counter._prev_length = 0
        raise
def _normalize_host(netloc):
    """Return lower-cased host without credentials or port."""
    if not netloc:
        return ""
    host = netloc.lower()
    if "@" in host:
        host = host.split("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]
    return host


def is_youtube_url(url):
    """Return True if URL points to a YouTube-owned domain."""
    if not url:
        return False
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False

    host = _normalize_host(parsed.netloc)

    if not host:
        return False

    if host in {"youtu.be", "www.youtu.be"}:
        return True

    for suffix in YOUTUBE_HOST_SUFFIXES:
        if host == suffix or host.endswith(f".{suffix}"):
            return True

    return False


def get_brave_snap_path():
    """
    Get a generic Brave browser snap path by detecting the user's home directory
    and finding the active Brave snap profile.
    Returns the Brave browser path or None if not found.
    """
    try:
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

def add_browser_cookies(command, url):
    """Add browser cookies to yt-dlp command when appropriate (NOT for YouTube URLs)."""
    # IMPORTANT: Never add cookies to YouTube URLs for privacy/security
    if url and not is_youtube_url(url) and "--cookies-from-browser" not in command:
        browser_cookies = get_browser_cookies_fast()
        if browser_cookies:
            command.extend(["--cookies-from-browser", browser_cookies])
    return command

# Configuration - Users can modify these paths
DEFAULT_VIDEO_DIR = os.path.join(Path.home(), "Videos", "ytd-video")
DEFAULT_MUSIC_DIR = os.path.join(Path.home(), "Music", "ytd-music")

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

def build_base_command(url):
    command = ["yt-dlp"]
    
    # Add configuration file if it exists
    config_file = find_config_file()
    if config_file:
        command.extend(["--config-location", config_file])
    
    # Reduce verbose output
    command.extend([
        "--no-write-info-json",
        "--progress-template", "Downloaded %(progress._downloaded_bytes_str)s of %(progress._total_bytes_str)s (%(progress._percent_str)s) at %(progress._speed_str)s ETA %(progress._eta_str)s"
    ])
    
    return add_browser_cookies(command, url)

def build_streaming_command(url):
    """Build yt-dlp command for streaming - excludes problematic remux options."""
    command = ["yt-dlp"]
    
    # Add configuration file if it exists
    config_file = find_config_file()
    if config_file:
        command.extend(["--config-location", config_file])
    
    # Disable options that don't work with streaming and reduce verbose output
    command.extend([
        "--no-write-info-json",
        "--progress-template", "Downloaded %(progress._downloaded_bytes_str)s of %(progress._total_bytes_str)s (%(progress._percent_str)s) at %(progress._speed_str)s ETA %(progress._eta_str)s"
    ])
    
    return add_browser_cookies(command, url)

def is_playlist(url):
    """Check if URL is a playlist."""
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    return "list" in query_params

def sanitize_filename(filename):
    """Sanitize filename by removing or replacing invalid characters."""
    if not filename:
        return "Unknown"
    
    # Replace invalid characters with safe alternatives
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length to avoid filesystem issues
    if len(filename) > 200:
        filename = filename[:200] + "..."
    
    return filename if filename else "Unknown"

def sanitize_path(path_str):
    """Sanitize/normalize a filesystem path: expand user, normalize, and return absolute path."""
    if not path_str:
        return path_str
    try:
        expanded = os.path.expanduser(path_str)
        normalized = os.path.normpath(expanded)
        return normalized
    except Exception:
        return path_str

def get_playlist_info(url):
    """Extract playlist/album information from URL using yt-dlp."""
    command = build_base_command(url)
    command.extend([
        "--dump-json",
        "--flat-playlist",
        "--no-download",
        url
    ])
    
    try:
        print("Detecting playlist information...")
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Warning: Could not extract playlist info: {result.stderr}")
            return None
        
        # Parse the first line of JSON output (playlist info)
        lines = result.stdout.strip().split('\n')
        if not lines or not lines[0]:
            return None
            
        try:
            playlist_data = json.loads(lines[0])
        except json.JSONDecodeError:
            print("Warning: Could not parse playlist information")
            return None
        
        # Extract relevant information
        playlist_info = {}
        
        # Get playlist title
        playlist_title = playlist_data.get('title', '')
        if playlist_title:
            playlist_info['title'] = sanitize_filename(playlist_title)
        
        # Get uploader/channel name
        uploader = playlist_data.get('uploader', '') or playlist_data.get('channel', '')
        if uploader:
            playlist_info['uploader'] = sanitize_filename(uploader)
        
        # Detect if this looks like an album
        is_album = detect_album_pattern(playlist_title, uploader)
        playlist_info['is_album'] = is_album
        
        return playlist_info
        
    except subprocess.TimeoutExpired:
        print("Warning: Timeout while fetching playlist information")
        return None
    except Exception as e:
        print(f"Warning: Error extracting playlist info: {e}")
        return None

def detect_album_pattern(title, uploader):
    """Detect if playlist looks like a music album based on title and uploader."""
    if not title:
        return False
    
    title_lower = title.lower()
    
    # Common album indicators
    album_keywords = [
        'album', 'ep', 'mixtape', 'lp', 'compilation', 'soundtrack', 
        'ost', 'single', 'deluxe', 'remastered', 'greatest hits',
        'the best of', 'collection', 'anthology'
    ]
    
    # Check if title contains album keywords
    for keyword in album_keywords:
        if keyword in title_lower:
            return True
    
    # Check if uploader looks like an artist (common patterns)
    if uploader:
        uploader_lower = uploader.lower()
        # Skip obvious non-artist channels
        non_artist_keywords = [
            'music', 'records', 'entertainment', 'official', 'vevo',
            'channel', 'tv', 'radio', 'network', 'media', 'productions'
        ]
        
        is_likely_artist = True
        for keyword in non_artist_keywords:
            if keyword in uploader_lower:
                is_likely_artist = False
                break
        
        # If uploader seems like an artist and title is relatively short, it's probably an album
        if is_likely_artist and len(title.split()) <= 6:
            return True
    
    return False

def generate_auto_folder_name(url):
    """Generate folder name automatically based on playlist/video information."""
    if not is_playlist(url):
        # For single videos, try to get video info
        return get_single_video_info(url)
    
    playlist_info = get_playlist_info(url)
    
    if not playlist_info:
        return "Unknown Playlist"
    
    title = playlist_info.get('title', 'Unknown Playlist')
    uploader = playlist_info.get('uploader', '')
    is_album = playlist_info.get('is_album', False)
    
    if is_album and uploader and uploader.lower() not in title.lower():
        # Format as "Album Name - Artist Name" for albums
        folder_name = f"{title} - {uploader}"
    elif uploader and uploader.lower() not in title.lower():
        # Format as "Playlist Name - Channel Name" for regular playlists
        folder_name = f"{title} - {uploader}"
    else:
        # Just use the title if uploader is already included or missing
        folder_name = title
    
    print(f"Auto-detected folder name: '{folder_name}'")
    return folder_name

def get_single_video_info(url):
    """Get information for a single video."""
    command = build_base_command(url)
    command.extend([
        "--dump-json",
        "--no-download",
        url
    ])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            return "Unknown Video"
        
        video_data = json.loads(result.stdout)
        title = video_data.get('title', 'Unknown Video')
        uploader = video_data.get('uploader', '')
        
        if uploader and uploader.lower() not in title.lower():
            return f"{sanitize_filename(title)} - {sanitize_filename(uploader)}"
        else:
            return sanitize_filename(title)
            
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return "Unknown Video"

def is_live_stream(url):
    """Return True if the given URL refers to a live stream (according to yt-dlp metadata)."""
    command = build_base_command(url)
    command.extend([
        "--dump-json",
        "--no-download",
        url
    ])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        if result.returncode != 0 or not result.stdout:
            return False
        data = json.loads(result.stdout)
        # yt-dlp may use 'is_live' or 'live_status' fields
        if data.get('is_live') is True:
            return True
        live_status = data.get('live_status')
        if isinstance(live_status, str) and live_status.lower() in ('is_live', 'live'):
            return True
        return False
    except Exception:
        return False

def get_direct_stream_url(url):
    """Return a direct playable URL (usually an m3u8) that VLC can open directly.

    Uses yt-dlp -g which prints direct URLs for video and audio streams; we return the
    first non-empty line which is usually the combined stream or video stream.
    """
    # For direct stream retrieval avoid reading config (which may request writing files)
    command = ["yt-dlp", "--no-config", "--no-write-info-json"]
    command = add_browser_cookies(command, url)
    command.extend(["-g", url])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return None
        # yt-dlp may print one or multiple lines; pick the first non-empty
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                return line
        return None
    except Exception:
        return None

def list_formats(url):
    """List available formats for a video, filtering out m3u8 and mp4 formats and unwanted columns."""
    command = build_streaming_command(url)
    command.extend(["--list-formats", url])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
        # Filter out m3u8 format from the output and format columns
        filtered_lines = []
        for line in result.stdout.split('\n'):
            if ('m3u8' not in line.lower()) or 'ID' in line or 'format code' in line.lower() or '---' in line:
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
    
    # Parse yt-dlp format which uses pipe separators | (2025 releases also use box characters)
    # Format: ID EXT RESOLUTION FPS CH | FILESIZE TBR PROTO | VCODEC VBR ACODEC ABR ASR MORE INFO
    try:
        parsed_line = line.replace('│', '|')
        # Split by pipe separators
        if '|' in parsed_line:
            sections = parsed_line.split('|')
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
    
def check_vlc_compatibility():
    """Check if VLC is available for streaming."""
    try:
        # Simple VLC availability check
        result = subprocess.run(
            ["vlc", "--version"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        
        if result.returncode == 0:
            return True, "VLC is available for streaming"
        else:
            return False, "VLC not responding properly"
            
    except subprocess.TimeoutExpired:
        return False, "VLC response timeout"
    except FileNotFoundError:
        return False, "VLC not found - please install VLC media player"
    except Exception as e:
        return False, f"VLC check failed: {str(e)}"

def watch_video(url):
    """Stream video at selected quality using VLC."""
    print("Fetching available formats...")
    formats_output = list_formats(url)

    # Detect live streams and provide recording options
    live = is_live_stream(url)
    if live:
        print("\nDetected a live stream!")
        print("Options for live streams:")
        print("  1) Open direct stream URL in VLC (may be lower latency)")
        print("  2) Record the live stream from its start (if available) using yt-dlp --live-from-start")
        print("  3) Start recording from now (begin recording current live session)")
        choice = safe_input("Enter choice (1-3): ").strip()
        if not choice:
            choice = "1"
    else:
        choice = None

    # Always initialize so it's safe later
    user_format = ""

    if not formats_output:
        print("Could not retrieve format list. Using config file default.")
        format_code = None  # Let config file handle default
    else:
        print("\nAvailable formats:")
        print(formats_output)

        print("\nEnter format selection:")
        print("- Enter a specific format ID (e.g., '137+140' for video+audio from the ID column)")        
        print("- Press enter to select the highest quality video & audio.")
        user_format = safe_input("\nFormat choice: ").strip()

        if not user_format:
            format_code = None  # Let config file handle default format
            print("No format specified, using config file default.")
        else:
            format_code = user_format

    # Build yt-dlp command for streaming (excludes remux options)
    command = build_streaming_command(url)
    if format_code:  # Only add format if user specified one
        command.extend(["-f", format_code])
    command.extend([
        "-o", "-",  # Output to stdout for streaming
        url
    ])

    # VLC launch logic goes here...
    vlc_command = ["vlc", "--no-video-title-show", "--avcodec-hw=none", "-"]
    # We'll start yt-dlp and VLC together below (single controlled flow).
    yt_process = None
    vlc_process = None
    
    # Signal handler for clean shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, cleaning up...")
        if yt_process and yt_process.poll() is None:
            yt_process.terminate()
        if vlc_process and vlc_process.poll() is None:
            vlc_process.terminate()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print(f"Streaming video with format '{format_code}' from: {url}")
        
        # Check VLC compatibility
        vlc_ok, vlc_message = check_vlc_compatibility()
        if not vlc_ok:
            print(f"VLC Error: {vlc_message}")
            return
        
        print("Starting video stream... (Press Ctrl+C to stop)")
        print("Note: VLC will open in a separate window")
        
        # If this is a live stream and the user selected option 2 (direct URL), try to open that
        if live and choice == "1":
            direct = get_direct_stream_url(url)
            if direct:
                print(f"Opening direct stream URL in VLC: {direct}")
                vlc_process = subprocess.Popen([
                    "vlc", "--no-video-title-show", "--avcodec-hw=none", direct
                ])
                vlc_process.wait()
                return
            else:
                print("Could not retrieve direct stream URL, falling back to piping via yt-dlp.")
        # If this is a live stream and user selected recording from start, launch yt-dlp with --live-from-start
        if live and choice == "2":
            record_dir = safe_input("Output directory for recording (or press Enter for default Videos): ").strip() or DEFAULT_VIDEO_DIR
            os.makedirs(record_dir, exist_ok=True)
            out_template = os.path.join(record_dir, "%(title)s.%(ext)s")
            # Use build_base_command for consistency
            record_cmd = build_base_command(url)
            record_cmd.extend(["--live-from-start", "-o", out_template, url])
            print("Recording live stream from its start using yt-dlp (this may re-download already available segments)...")
            # Run in the output directory so yt-dlp won't write side files into the repo
            subprocess.run(record_cmd, cwd=record_dir)
            return

        # If user chose to start recording from now, run yt-dlp writing to file from the current point
        if live and choice == "3":
            record_dir = safe_input("Output directory for recording (or press Enter for default Videos): ").strip() or DEFAULT_VIDEO_DIR
            os.makedirs(record_dir, exist_ok=True)
            out_template = os.path.join(record_dir, "%(title)s.%(ext)s")
            record_cmd = build_base_command(url)
            record_cmd.extend(["-o", out_template, url])
            print("Recording live stream from now (Ctrl+C to stop recording)...")
            try:
                subprocess.run(record_cmd, cwd=record_dir)
            except KeyboardInterrupt:
                print("Recording stopped by user.")
            return

        # Start yt-dlp process (default streaming behavior)
        # Ensure yt-dlp runs in a safe directory so it doesn't write side files into the repo
        os.makedirs(DEFAULT_VIDEO_DIR, exist_ok=True)
        yt_process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            bufsize=0,  # Unbuffered
            cwd=DEFAULT_VIDEO_DIR,
        )
        
        # Give yt-dlp a moment to start
        time.sleep(1)
        
        # Check if yt-dlp started successfully
        if yt_process.poll() is not None:
            stderr_output = yt_process.stderr.read().decode('utf-8', errors='ignore')
            print(f"yt-dlp failed to start: {stderr_output}")
            return
        
        print("yt-dlp started, launching VLC...")
        
        # Start VLC process
        vlc_process = subprocess.Popen(
            vlc_command, 
            stdin=yt_process.stdout, 
            stdout=subprocess.DEVNULL,  # Suppress VLC output
            stderr=subprocess.DEVNULL   # Suppress VLC errors
        )
        
        # Close our copy of the pipe
        yt_process.stdout.close()
        
        print("VLC launched! The video should start playing shortly.")
        
        # Wait for VLC to complete (with timeout protection)
        try:
            vlc_stdout, vlc_stderr = vlc_process.communicate(timeout=7200)  # 2 hour timeout
            
            # Check exit codes
            if vlc_process.returncode == 0:
                print("Streaming completed successfully!")
            elif vlc_process.returncode == 1:
                print("Streaming ended (user closed VLC or stream ended)")
            else:
                print(f"VLC exited with code {vlc_process.returncode}")
                if vlc_stderr:
                    print(f"VLC error output: {vlc_stderr.decode('utf-8', errors='ignore')}")
                    
        except subprocess.TimeoutExpired:
            print("Stream timeout reached, stopping...")
            vlc_process.terminate()
            try:
                vlc_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                vlc_process.kill()
                
    except FileNotFoundError:
        print("Error: VLC media player not found. Please install VLC to use streaming feature.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to start streaming.\n{e}")
    except KeyboardInterrupt:
        print("\nStreaming interrupted by user.")
    except Exception as e:
        print(f"Unexpected error during streaming: {e}")
    finally:
        # Ensure processes are properly cleaned up
        if yt_process and yt_process.poll() is None:
            print("Cleaning up yt-dlp process...")
            yt_process.terminate()
            try:
                yt_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                yt_process.kill()
        if vlc_process and vlc_process.poll() is None:
            print("Cleaning up VLC process...")
            vlc_process.terminate()
            try:
                vlc_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                vlc_process.kill()
        # Exit the script after streaming to prevent re-opening VLC
        sys.exit(0)

def download_video(url, output_dir=None):
    """Download video with audio using config file defaults."""
    if output_dir is None:
        output_dir = DEFAULT_VIDEO_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    video_title = safe_input("Video title (or press Enter for auto-generated): ").strip()
    
    # Use auto-generated title if none provided
    output_template = os.path.join(output_dir, f"{video_title}.%(ext)s") if video_title else os.path.join(output_dir, "%(title)s.%(ext)s")
    
    command = build_base_command(url)
    command.extend([
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "-o", output_template,
        url,
    ])

    try:
        print(f"Downloading high-quality video from: {url}")
        print(f"Output directory: {output_dir}")
        print("Starting download... (this may take a few moments)")
        print("Progress:")
        
        returncode = run_with_progress_counter(command, cwd=output_dir)
        if returncode == 0:
            print(f"✓ Video download complete!")
            print(f"Files saved in: {output_dir}")
            print(f"To open folder: nautilus '{output_dir}' &")
            print("Note: Video includes chapters, subtitles, and metadata (from config).")
        else:
            print(f"Error: Download failed with return code {returncode}")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to download video.\n{e}")
        print(f"Command that failed: {' '.join(command)}")
    except KeyboardInterrupt:
        print("Download interrupted by user.")

def record_live(url, output_dir=None, from_start=False):
    """Record a live stream to disk. If from_start is True, use --live-from-start to try and capture from the very beginning."""
    if output_dir is None:
        output_dir = DEFAULT_VIDEO_DIR
    os.makedirs(output_dir, exist_ok=True)
    out_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    cmd = build_base_command(url)
    if from_start:
        cmd.append("--live-from-start")
    cmd.extend(["-o", out_template, url])

    print(f"Recording live stream to: {output_dir} (from_start={from_start})")
    print("Progress:")
    try:
        returncode = run_with_progress_counter(cmd, cwd=output_dir)
        if returncode == 0:
            print("Recording finished")
        else:
            print(f"Error: Recording failed with return code {returncode}")
    except subprocess.CalledProcessError as e:
        print(f"Error while recording live stream: {e}")
    except KeyboardInterrupt:
        print("Recording stopped by user.")

def analyze_live_stream_availability(url):
    """Analyze what's available from a live stream before downloading."""
    print("Analysing live stream availability...")
    
    try:
        # Get stream info without downloading
        command = ["yt-dlp", "--dump-json", "--no-download", url]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            print("Could not analyse stream")
            return None
            
        data = json.loads(result.stdout)
        
        # Check for fragments (indicates segmented live stream)
        has_fragments = False
        fragment_count = 0
        
        if 'formats' in data:
            for fmt in data['formats']:
                if 'fragments' in fmt and fmt['fragments']:
                    has_fragments = True
                    fragment_count = max(fragment_count, len(fmt['fragments']))
        
        duration = data.get('duration', 0)
        title = data.get('title', 'Unknown')
        
        print(f"📊 Stream Analysis for '{title}':")
        print(f"   • Total duration: {duration/60:.1f} minutes" if duration else "   • Duration: Unknown")
        print(f"   • Uses segments: {'Yes' if has_fragments else 'No'}")
        if has_fragments:
            approx_available = fragment_count * 2  # Most fragments are ~2 seconds
            print(f"   • Available segments: {fragment_count} (~{approx_available} seconds)")
            
            if approx_available < 60:
                print(f"   ⚠️  WARNING: Only {approx_available} seconds available!")
            elif approx_available < duration * 0.1:
                print(f"   ⚠️  WARNING: Only small portion of stream available!")
            else:
                print(f"   ✅ Good availability for --live-from-start")
        
        return {
            'duration': duration,
            'has_fragments': has_fragments,
            'fragment_count': fragment_count,
            'available_seconds': fragment_count * 2 if has_fragments else None
        }
        
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        print(f"❌ Analysis failed: {e}")
        return None

def download_live_from_start(url, output_dir=None):
    """Download a live stream from the start using --live-from-start option."""
    if output_dir is None:
        output_dir = DEFAULT_VIDEO_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("Live Stream Download from Beginning")
    print("This will attempt to download the stream from its beginning using --live-from-start.")
    
    # Analyze what's available first
    analysis = analyze_live_stream_availability(url)
    
    # Check if this is a Facebook live stream
    parsed_url = urllib.parse.urlparse(url)
    is_facebook = "facebook.com" in parsed_url.netloc.lower()
    
    # Provide warnings based on analysis
    should_warn = False
    if analysis and analysis['available_seconds']:
        if analysis['available_seconds'] < 60:
            should_warn = True
            print(f"\nWARNING: Only ~{analysis['available_seconds']} seconds appear to be available!")
        elif is_facebook and analysis['available_seconds'] < 300:  # 5 minutes
            should_warn = True
            print(f"\nFacebook Live Limitation: Only ~{analysis['available_seconds']} seconds available")
    elif is_facebook:
        should_warn = True
        print("\nWARNING: Facebook Live Stream Detected!")
    
    if should_warn:
        print("Limitations:")
        if is_facebook:
            print("• Facebook only keeps recent segments (~20 seconds) available")
            print("• --live-from-start rarely works with Facebook for full streams")
        print("• You may only get a short clip, not the full stream")
        
        choice = safe_input("\nContinue anyway? (y/N): ").strip().lower()
        if choice != 'y':
            print("Cancelled. Try option 1 (regular download) instead.")
            return
    
    print("\nNote: This only works if the platform supports it and has archived the stream from the start.")
    print("If this fails or only downloads a short segment, try the regular download option instead.\n")
    
    video_title = safe_input("Video title (or press Enter for auto-generated): ").strip()
    
    # Use custom title if provided, otherwise use default template
    if video_title:
        output_template = os.path.join(output_dir, f"{sanitize_filename(video_title)}.%(ext)s")
    else:
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    
    command = build_base_command(url)
    command.extend([
        "--live-from-start",  # Download from start of live stream
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "-o", output_template,
        url,
    ])

    try:
        print(f"Downloading live stream from start: {url}")
        print(f"Output directory: {output_dir}")
        print("Starting download... (this may take considerable time for long streams)")
        if is_facebook:
            print("⚠️  Facebook limitation: May only download recent segments")
        print("Progress:")
        
        returncode = run_with_progress_counter(command, cwd=output_dir)
        if returncode == 0:
            print("✓ Live stream download complete!")
        else:
            print(f"Error: Download failed with return code {returncode}")
            return
        print(f"Files saved in: {output_dir}")
        print(f"To open folder: nautilus '{output_dir}' &")
        
        if is_facebook:
            print("\n📋 Facebook Live Stream Notes:")
            print("• If you only got ~20 seconds, this is a Facebook limitation")
            print("• Facebook only keeps recent stream segments available")
            print("• For longer recordings, try using OBS or similar tools during the live stream")
        else:
            print("Note: Downloaded from stream start with full quality and metadata.")
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error: Failed to download live stream from start.\n{e}")
        print(f"Command that failed: {' '.join(command)}")
        
        if is_facebook:
            print(f"\n🔍 Facebook Live Stream Troubleshooting:")
            print("• This is common with Facebook - they don't store full streams")
            print("• Only recent segments (~20 seconds) are typically available")
            print("• Try option 1 (regular download) - it may get the same result")
            print("• For future streams, consider using screen recording software")
            print("• Some third-party Facebook downloading tools may work better")
        else:
            print(f"\n🔍 General Live Stream Troubleshooting:")
            print("• The platform may not support downloading from start")
            print("• The stream may have ended or been removed")
            print("• Try option 1 (download from current point) instead")
            print("• Some platforms only keep recent segments available")
        
        print(f"\n💡 Alternative Solutions:")
        print("• Use option 1 for regular download (may get same content)")
        if is_facebook:
            print("• Try Facebook's 'Save Video' feature if available")
            print("• Check if the streamer will upload a recording later") 
            print("• Use browser extensions designed for Facebook videos")
        print("• Try external recording software like OBS Studio for future streams")
        print("• Check if the stream will be archived as a regular video later")
        
        # Offer to try regular download
        if is_facebook:
            retry_choice = safe_input("\nWould you like to try regular download instead? (y/N): ").strip().lower()
            if retry_choice == 'y':
                print("\n🔄 Attempting regular download...")
                download_video(url, output_dir)
                return

def download_audio(url, output_dir=None):
    """Download best audio only using config file defaults."""
    if output_dir is None:
        base_output_dir = DEFAULT_MUSIC_DIR
    else:
        base_output_dir = output_dir
    
    # Ask for folder name with auto-detection option
    print("Folder name options:")
    print("   • Press Enter to attempt to auto-detect from playlist/video info (not great),")
    print("   • Type a custom folder name\n")
    folder_name = safe_input("Folder name, or Enter: ").strip()
    
    if not folder_name:
        # Auto-detect folder name
        folder_name = generate_auto_folder_name(url)
        print(f"Using auto-detected folder: '{folder_name}'")
    else:
        print(f"Using custom folder: '{folder_name}'")
    
    # Sanitise folder name
    folder_name = sanitize_filename(folder_name)
    
    output_dir = os.path.join(base_output_dir, folder_name)
    os.makedirs(output_dir, exist_ok=True)
    
    if is_playlist(url):
        print(f"Downloading playlist to folder '{folder_name}'")
        # For playlists, add track numbers
        output_template = os.path.join(output_dir, "%(playlist_index)02d - %(title)s.%(ext)s")
    else:
        print(f"Downloading single track to folder '{folder_name}'")
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    
    command = build_base_command(url)
    command.extend([
        "--extract-audio",
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "-o", output_template,
        url,
    ])
    
    try:
        print(f"Downloading high-quality audio from: {url}")
        print(f"Output directory: {output_dir}")
        print("Starting download... (this may take a few moments)")
        print("Progress:")
        
        returncode = run_with_progress_counter(command, cwd=output_dir)
        if returncode == 0:
            print("✓ Audio download complete!")
        else:
            print(f"Error: Download failed with return code {returncode}")
            return
        print(f"Files saved in: {output_dir}")
        print(f"To open folder: nautilus '{output_dir}' &")
        print("Note: Audio format, quality, and metadata handled by config file.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to download audio.\n{e}")
        print(f"Command that failed: {' '.join(command)}")

def download_video_no_audio(url, output_dir=None):
    """Download video only, no audio track."""
    if output_dir is None:
        output_dir = DEFAULT_VIDEO_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    title = safe_input("Video title (or press Enter for auto-generated): ").strip()
    
    if title:
        output_template = os.path.join(output_dir, f"{title}_video_only.%(ext)s")
    else:
        output_template = os.path.join(output_dir, "%(title)s_video_only.%(ext)s")
    
    command = build_base_command(url)
    command.extend([
        "-f", "bestvideo",  # Override config for video-only
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "-o", output_template,
        url,
    ])
    
    try:
        print(f"Downloading video only from: {url}")
        print("Starting download... (this may take a few moments)")
        print("Progress:")
        
        returncode = run_with_progress_counter(command, cwd=output_dir)
        if returncode == 0:
            print(f"✓ Video-only download complete! Files saved in '{output_dir}'.")
        else:
            print(f"Error: Download failed with return code {returncode}")
            return
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to download video only.\n{e}")

def download_audio_from_video(url, output_dir):
    """Download audio only from a video or playlist."""
    sanitized_dir = sanitize_path(output_dir)
    os.makedirs(sanitized_dir, exist_ok=True)
    output_template = os.path.join(sanitized_dir, "%(title)s.%(ext)s")

    command = build_base_command(url)
    command.extend([
        "--extract-audio",
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "-o", output_template,
        url,
    ])

    try:
        print(f"Downloading and extracting audio from video: {url}")
        print("Starting download... (this may take a few moments)")
        print("Progress:")
        
        returncode = run_with_progress_counter(command, cwd=sanitized_dir)
        if returncode == 0:
            print(f"✓ Extracted audio complete! Files saved in '{sanitized_dir}'.")
        else:
            print(f"Error: Download failed with return code {returncode}")
            return
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to extract audio.\n{e}")

def check_for_quit(user_input):
    """Check if user wants to quit and exit if so."""
    if user_input.strip() == "99":
        print("Goodbye!")
        sys.exit(0)
    return user_input

def safe_input(prompt):
    """Wrapper around input() that handles Ctrl-D and quit keywords safely."""
    try:
        return check_for_quit(input(prompt))
    except EOFError:
        return ""

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except FileNotFoundError:
        print("Error: yt-dlp is not installed or not in PATH.")
        return False
    return True

def show_help():
    """Display help information."""
    help_text = """
YouTube Downloader & Streamer - Usage Guide

BASIC USAGE:
  loutube "https://youtube.com/watch?v=..."  Direct download
  loutube --help                             Show this help
  loutube --config                           Show current configuration
  loutube --recent                           Show recent downloads
  loutube --edit                             Launch video editor
  loutube --ascii                            Play ASCII art files

FEATURES:
  • High-quality video downloads (up to 1080p) with H.264+AAC
  • Premium audio extraction with metadata and thumbnails  
  • Direct streaming to VLC without downloading
  • Live stream download from beginning option (--live-from-start)
  • Integrated video editor with ffmpeg (trim, transcode, format conversion, GIF creation, Instagram padding, audio extraction, frame rate changes, speed adjustment)
  • Special effects: ASCII art converter, datamoshing (glitch art), time-lapse with motion trails
  • Automatic SponsorBlock integration (removes ads/sponsors)
  • Playlist support with automatic track numbering
  • AUTO-DETECTION: Automatically detects playlist/album names
    - Albums: "Album Name - Artist Name"
    - Playlists: "Playlist Name - Channel Name"
    - Single videos: "Video Title - Channel Name"

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
  • ffmpeg required for video editing features
  • Folder names auto-detected from playlist metadata
  • Video editor supports recent downloads, folder browsing, and manual file selection

For more information, visit: https://github.com/TurbulentGoat/youtube-downloader
""".format(DEFAULT_VIDEO_DIR=DEFAULT_VIDEO_DIR, DEFAULT_MUSIC_DIR=DEFAULT_MUSIC_DIR)
    print(help_text)

def show_recent_downloads():
    """Show recently downloaded files."""
    print("=== Recent Downloads ===\n")
    
    # Check both video and music directories
    directories = {
        "Videos": DEFAULT_VIDEO_DIR,
        "Music": DEFAULT_MUSIC_DIR
    }
    
    for dir_type, dir_path in directories.items():
        if os.path.exists(dir_path):
            print(f"{dir_type} directory: {dir_path}")
            try:
                # Get files sorted by modification time (newest first)
                files = []
                for file in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file)
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        files.append((file, stat.st_mtime, stat.st_size))
                
                files.sort(key=lambda x: x[1], reverse=True)  # Sort by modification time
                
                # Show last 5 files
                recent_files = files[:5]
                if recent_files:
                    for file, mtime, size in recent_files:
                        # Format file size
                        if size > 1024*1024*1024:
                            size_str = f"{size/(1024*1024*1024):.1f}GB"
                        elif size > 1024*1024:
                            size_str = f"{size/(1024*1024):.1f}MB"
                        else:
                            size_str = f"{size/1024:.1f}KB"
                        
                        # Format date
                        date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
                        print(f"  • {file} ({size_str}) - {date_str}")
                    
                    if len(files) > 5:
                        print(f"  ... and {len(files) - 5} more files")
                    
                    print(f"To open this folder: nautilus '{dir_path}' &")
                else:
                    print(f"  No files found in {dir_path}")
            except Exception as e:
                print(f"  Error reading directory: {e}")
        else:
            print(f"{dir_type} directory: {dir_path} (not created yet)")
        print()

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
        print("Config status: Found")
        
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
        print("Config status: Using built-in defaults")
    
    print(f"\nDefault directories:")
    print(f"  Videos: {DEFAULT_VIDEO_DIR}")
    print(f"  Music:  {DEFAULT_MUSIC_DIR}")
    
    # Check dependencies
    print(f"\nDependency status:")
    try:
        result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, check=True)
        print(f"  yt-dlp: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"  yt-dlp: Not found or not working")
    
    try:
        subprocess.run(["vlc", "--version"], capture_output=True, check=True)
        print(f"  VLC: Available (streaming works)")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"  VLC: Not found (streaming unavailable)")
    
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print(f"  ffmpeg: Available (video editing works)")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"  ffmpeg: Not found (video editing unavailable)")

# === VIDEO EDITING FUNCTIONS ===

def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

def get_video_info(filepath):
    """Get video information using ffprobe."""
    try:
        # Get duration
        duration_result = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", filepath
        ], capture_output=True, text=True, timeout=10)
        
        duration = ""
        if duration_result.returncode == 0 and duration_result.stdout.strip():
            duration_sec = float(duration_result.stdout.strip())
            hours = int(duration_sec // 3600)
            minutes = int((duration_sec % 3600) // 60)
            seconds = int(duration_sec % 60)
            duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Get resolution
        resolution_result = subprocess.run([
            "ffprobe", "-v", "quiet", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", filepath
        ], capture_output=True, text=True, timeout=10)
        
        resolution = ""
        if resolution_result.returncode == 0 and resolution_result.stdout.strip():
            width, height = resolution_result.stdout.strip().split(',')
            resolution = f"{width}x{height}"
            
            # Add quality label
            height_int = int(height)
            if height_int >= 2160:
                quality = "4K (2160p)"
            elif height_int >= 1440:
                quality = "1440p (2K)"
            elif height_int >= 1080:
                quality = "1080p (Full HD)"
            elif height_int >= 720:
                quality = "720p (HD)"
            elif height_int >= 480:
                quality = "480p (SD)"
            else:
                quality = f"{height_int}p"
            
            resolution = f"{resolution} ({quality})"
        
        # Get file size
        file_size = ""
        if os.path.exists(filepath):
            size_bytes = os.path.getsize(filepath)
            if size_bytes >= 1024**3:
                file_size = f"{size_bytes / (1024**3):.1f} GB"
            elif size_bytes >= 1024**2:
                file_size = f"{size_bytes / (1024**2):.1f} MB"
            else:
                file_size = f"{size_bytes / 1024:.1f} KB"
        
        return {
            'duration': duration,
            'resolution': resolution,
            'file_size': file_size
        }
    except Exception as e:
        print(f"Warning: Could not get video info: {e}")
        return {'duration': 'Unknown', 'resolution': 'Unknown', 'file_size': 'Unknown'}

def validate_output_path(output_path):
    """Validate and suggest output filename if file exists."""
    counter = 1
    base_path = os.path.splitext(output_path)[0]
    extension = os.path.splitext(output_path)[1]
    original_path = output_path
    
    while os.path.exists(output_path):
        overwrite = safe_input(f"File '{os.path.basename(output_path)}' already exists. Overwrite? (y/N): ").strip().lower()
        if overwrite == 'y':
            break
        else:
            output_path = f"{base_path}_{counter}{extension}"
            print(f"Suggested filename: {os.path.basename(output_path)}")
            use_suggested = safe_input("Use this filename? (y/N): ").strip().lower()
            if use_suggested == 'y':
                break
            else:
                new_filename = safe_input("Enter new filename: ").strip()
                if new_filename:
                    output_path = os.path.join(os.path.dirname(output_path), new_filename)
                else:
                    output_path = f"{base_path}_{counter}{extension}"
        counter += 1
    
    return output_path

def trim_video(input_file):
    """Trim video keeping original quality."""
    print(f"\n=== Trim Video: {os.path.basename(input_file)} ===")
    
    # Show video info
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    start_time = safe_input("Enter start time (format: hh:mm:ss or mm:ss or ss): ").strip()
    if not start_time:
        print("No start time provided. Aborting.")
        return
    
    end_time = safe_input("Enter end time (format: hh:mm:ss or mm:ss or ss): ").strip()
    if not end_time:
        print("No end time provided. Aborting.")
        return
    
    output_filename = safe_input("Enter output filename (with extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_filename = f"{base_name}_trimmed.mp4"
        print(f"Using default filename: {output_filename}")
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename)
    output_path = validate_output_path(output_path)
    
    print(f"\n=== Trim Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"Start time: {start_time}")
    print(f"End time: {end_time}")
    print(f"Output: {os.path.basename(output_path)}")
    
    confirm = safe_input("\nProceed with trimming? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("Trimming video...")
    try:
        # Check for CUDA support
        cuda_check = subprocess.run(["ffmpeg", "-hwaccels"], capture_output=True, text=True)
        use_cuda = "cuda" in cuda_check.stdout if cuda_check.returncode == 0 else False
        
        if use_cuda:
            cmd = ["ffmpeg", "-hwaccel", "cuda", "-ss", start_time, "-i", input_file, 
                   "-to", end_time, "-c", "copy", output_path]
        else:
            cmd = ["ffmpeg", "-ss", start_time, "-i", input_file, 
                   "-to", end_time, "-c", "copy", output_path]
        
        result = subprocess.run(cmd, check=True, cwd=os.path.dirname(input_file))
        print(f"✓ Trimming completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during trimming: {e}")

def transcode_video(input_file):
    """Transcode video to change quality/bitrate."""
    print(f"\n=== Transcode Video: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    print("Enter target video bitrate in kbps:")
    print("Examples: 500 (low quality), 1000 (medium), 2000 (good), 3000+ (high quality)")
    bitrate_str = safe_input("Video bitrate (kbps): ").strip()
    
    try:
        bitrate = int(bitrate_str)
        if bitrate <= 0:
            raise ValueError("Bitrate must be positive")
    except ValueError:
        print("Invalid bitrate. Aborting.")
        return
    
    output_filename = safe_input("Enter output filename (with extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_filename = f"{base_name}_transcoded.mp4"
        print(f"Using default filename: {output_filename}")
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename)
    output_path = validate_output_path(output_path)
    
    print(f"\n=== Transcode Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"Target bitrate: {bitrate} kbps")
    print(f"Output: {os.path.basename(output_path)}")
    
    confirm = safe_input("\nProceed with transcoding? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("Transcoding video...")
    try:
        # Check for NVIDIA GPU support
        encoders_check = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        use_nvenc = "h264_nvenc" in encoders_check.stdout if encoders_check.returncode == 0 else False
        
        if use_nvenc:
            print("Using NVIDIA GPU acceleration (h264_nvenc)")
            cmd = ["ffmpeg", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda", 
                   "-i", input_file, "-c:v", "h264_nvenc", "-b:v", f"{bitrate}k",
                   "-minrate", f"{bitrate}k", "-maxrate", f"{bitrate}k", 
                   "-bufsize", f"{bitrate * 2}k", "-c:a", "aac", output_path]
        else:
            print("Using CPU encoding (libx264)")
            cmd = ["ffmpeg", "-i", input_file, "-c:v", "libx264", "-b:v", f"{bitrate}k",
                   "-minrate", f"{bitrate}k", "-maxrate", f"{bitrate}k", 
                   "-bufsize", f"{bitrate * 2}k", "-c:a", "aac", output_path]
        
        result = subprocess.run(cmd, check=True, cwd=os.path.dirname(input_file))
        print(f"✓ Transcoding completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during transcoding: {e}")

def convert_format(input_file):
    """Convert video format without re-encoding."""
    print(f"\n=== Convert Format: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    output_filename = safe_input("Enter output filename (with extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_filename = f"{base_name}_converted.mp4"
        print(f"Using default filename: {output_filename}")
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename)
    output_path = validate_output_path(output_path)
    
    print(f"\n=== Format Conversion Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"Output: {os.path.basename(output_path)}")
    print("Note: This will copy streams without re-encoding (fast, no quality loss)")
    
    confirm = safe_input("\nProceed with format conversion? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("Converting format...")
    try:
        cmd = ["ffmpeg", "-i", input_file, "-c", "copy", output_path]
        result = subprocess.run(cmd, check=True, cwd=os.path.dirname(input_file))
        print(f"✓ Format conversion completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during conversion: {e}")

def convert_to_gif(input_file):
    """Convert video to GIF."""
    print(f"\n=== Convert to GIF: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    print("Do you want to convert the entire video or a specific time range?")
    print("1. Entire video")
    print("2. Specific time range (trim first)")
    trim_choice = safe_input("Choice (1-2): ").strip()
    
    start_time = ""
    duration_seconds = ""
    
    if trim_choice == "2":
        start_time = safe_input("Enter start time (format: hh:mm:ss or mm:ss or ss): ").strip()
        if not start_time:
            print("No start time provided. Aborting.")
            return
        
        duration_input = safe_input("Enter duration in seconds (how long the GIF should be): ").strip()
        try:
            duration_seconds = str(int(duration_input))
        except ValueError:
            print("Invalid duration. Aborting.")
            return
    
    print("\nGIF Quality Settings:")
    gif_width = safe_input("Width (0 = keep original width, or specify pixels like 480, 720, 1080): ").strip()
    
    if gif_width == "0" or not gif_width:
        scale_filter = "scale=-1:-1"
    else:
        try:
            width = int(gif_width)
            scale_filter = f"scale={width}:-1"
        except ValueError:
            print("Invalid width. Using original width.")
            scale_filter = "scale=-1:-1"
    
    print("Frame rate (fps) - lower = smaller file size:")
    print("Examples: 10 (smooth), 5 (medium), 2 (choppy but small)")
    gif_fps_input = safe_input("Frame rate: ").strip()
    
    try:
        gif_fps = int(gif_fps_input)
        if gif_fps < 1 or gif_fps > 60:
            raise ValueError("FPS out of range")
    except ValueError:
        print("Invalid frame rate. Using default of 10 fps.")
        gif_fps = 10
    
    output_filename = safe_input("Enter output filename (with .gif extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_filename = f"{base_name}.gif"
    elif not output_filename.endswith('.gif'):
        output_filename += '.gif'
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename)
    output_path = validate_output_path(output_path)
    
    print(f"\n=== GIF Conversion Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    if start_time:
        print(f"Start time: {start_time}")
        print(f"Duration: {duration_seconds} seconds")
    else:
        print("Range: Entire video")
    print(f"Width: {'Original' if scale_filter == 'scale=-1:-1' else gif_width + 'px'}")
    print(f"Frame rate: {gif_fps} fps")
    print(f"Output: {os.path.basename(output_path)}")
    
    confirm = safe_input("\nProceed with GIF conversion? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("Converting to GIF...")
    try:
        # Create temporary palette file
        temp_palette = os.path.join(os.path.dirname(input_file), "temp_palette.png")
        
        # Build palette generation command
        palette_cmd = ["ffmpeg", "-y"]
        if start_time:
            palette_cmd.extend(["-ss", start_time])
        palette_cmd.extend(["-i", input_file])
        if duration_seconds:
            palette_cmd.extend(["-t", duration_seconds])
        palette_cmd.extend(["-vf", f"fps={gif_fps},{scale_filter}:flags=lanczos,palettegen=stats_mode=diff", temp_palette])
        
        # Generate palette
        subprocess.run(palette_cmd, check=True, cwd=os.path.dirname(input_file))
        
        # Build GIF generation command
        gif_cmd = ["ffmpeg", "-y"]
        if start_time:
            gif_cmd.extend(["-ss", start_time])
        gif_cmd.extend(["-i", input_file, "-i", temp_palette])
        if duration_seconds:
            gif_cmd.extend(["-t", duration_seconds])
        gif_cmd.extend(["-lavfi", f"fps={gif_fps},{scale_filter}:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle", output_path])
        
        # Generate GIF
        subprocess.run(gif_cmd, check=True, cwd=os.path.dirname(input_file))
        
        # Clean up temporary palette
        if os.path.exists(temp_palette):
            os.remove(temp_palette)
        
        print(f"✓ GIF conversion completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        # Clean up temporary palette on error
        temp_palette = os.path.join(os.path.dirname(input_file), "temp_palette.png")
        if os.path.exists(temp_palette):
            os.remove(temp_palette)
        print(f"✗ Error during GIF conversion: {e}")

def add_padding(input_file):
    """Add black bars for Instagram formats."""
    print(f"\n=== Add Padding: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    print("Instagram Padding Presets:")
    print("1) Square (1080x1080)")
    print("2) Portrait (1080x1350)")
    print("3) Landscape (1080x566)")
    print("4) Story/Reel (1080x1920)")
    print("5) Custom size")
    preset_choice = safe_input("Choose a preset (1-5): ").strip()
    
    if preset_choice == "1":
        out_w, out_h = 1080, 1080
    elif preset_choice == "2":
        out_w, out_h = 1080, 1350
    elif preset_choice == "3":
        out_w, out_h = 1080, 566
    elif preset_choice == "4":
        out_w, out_h = 1080, 1920
    elif preset_choice == "5":
        try:
            out_w = int(safe_input("Enter output width (pixels): ").strip())
            out_h = int(safe_input("Enter output height (pixels): ").strip())
        except ValueError:
            print("Invalid dimensions. Aborting.")
            return
    else:
        print("Invalid choice. Aborting.")
        return
    
    print("\nChoose output type:")
    print("1) Video (mp4, keep audio)")
    print("2) GIF (no audio)")
    out_type = safe_input("Choice (1-2): ").strip()
    
    output_filename = safe_input("Enter output filename (with extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        if out_type == "2":
            output_filename = f"{base_name}_padded.gif"
        else:
            output_filename = f"{base_name}_padded.mp4"
        print(f"Using default filename: {output_filename}")
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename)
    output_path = validate_output_path(output_path)
    
    print(f"\n=== Padding Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"Output resolution: {out_w}x{out_h}")
    print(f"Output: {os.path.basename(output_path)}")
    
    confirm = safe_input("\nProceed with padding? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    # Build scale+pad filter
    vf = f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black"
    
    try:
        if out_type == "1":
            print("Applying padding to video...")
            if output_path.endswith('.mp4'):
                cmd = ["ffmpeg", "-i", input_file, "-vf", vf, "-c:v", "libx264", 
                       "-c:a", "aac", "-movflags", "+faststart", output_path]
            else:
                cmd = ["ffmpeg", "-i", input_file, "-vf", vf, "-c:a", "copy", output_path]
            
            subprocess.run(cmd, check=True, cwd=os.path.dirname(input_file))
            
        else:  # GIF
            print("GIF frame rate (fps) - lower = smaller file size:")
            print("Examples: 15 (smooth), 10 (good), 5 (medium), 2 (small)")
            gif_fps_input = safe_input("Frame rate: ").strip()
            
            try:
                gif_fps = int(gif_fps_input)
                if gif_fps < 1 or gif_fps > 30:
                    raise ValueError("FPS out of range")
            except ValueError:
                print("Invalid frame rate. Using default of 10 fps.")
                gif_fps = 10
            
            # Ensure .gif extension
            if not output_filename.endswith('.gif'):
                output_filename += '.gif'
                output_path = os.path.join(os.path.dirname(input_file), output_filename)
            
            print(f"Converting padded GIF at {gif_fps} fps...")
            
            # Generate palette for padded frames
            temp_palette = os.path.join(os.path.dirname(input_file), "temp_palette_pad.png")
            palette_cmd = ["ffmpeg", "-y", "-i", input_file, "-vf", 
                          f"{vf},fps={gif_fps},palettegen=stats_mode=diff", temp_palette]
            subprocess.run(palette_cmd, check=True, cwd=os.path.dirname(input_file))
            
            # Create GIF using palette
            gif_cmd = ["ffmpeg", "-y", "-i", input_file, "-i", temp_palette, "-lavfi",
                      f"{vf},fps={gif_fps}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle", 
                      output_path]
            subprocess.run(gif_cmd, check=True, cwd=os.path.dirname(input_file))
            
            # Clean up
            if os.path.exists(temp_palette):
                os.remove(temp_palette)
        
        print(f"✓ Padding completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        # Clean up on error
        temp_palette = os.path.join(os.path.dirname(input_file), "temp_palette_pad.png")
        if os.path.exists(temp_palette):
            os.remove(temp_palette)
        print(f"✗ Error during padding: {e}")

def extract_audio(input_file):
    """Extract audio as MP3."""
    print(f"\n=== Extract Audio: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    print("Audio Quality Settings:")
    print("1. High quality (320k)")
    print("2. Good quality (192k)")
    print("3. Medium quality (128k)")
    print("4. Low quality (96k)")
    print("5. Custom bitrate")
    quality_choice = safe_input("Choose quality (1-5): ").strip()
    
    if quality_choice == "1":
        bitrate = "320k"
    elif quality_choice == "2":
        bitrate = "192k"
    elif quality_choice == "3":
        bitrate = "128k"
    elif quality_choice == "4":
        bitrate = "96k"
    elif quality_choice == "5":
        custom_bitrate = safe_input("Enter bitrate (e.g., 256k): ").strip()
        if custom_bitrate:
            bitrate = custom_bitrate
        else:
            bitrate = "192k"
            print("Using default: 192k")
    else:
        bitrate = "192k"
        print("Using default: 192k")
    
    output_filename = safe_input("Enter output filename (without extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_filename = f"{base_name}_audio"
        print(f"Using default filename: {output_filename}")
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename + ".mp3")
    output_path = validate_output_path(output_path)
    
    print(f"\n=== Audio Extraction Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"Quality: {bitrate}")
    print(f"Output: {os.path.basename(output_path)}")
    
    confirm = safe_input("\nProceed with audio extraction? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("Extracting audio...")
    try:
        cmd = ["ffmpeg", "-i", input_file, "-vn", "-acodec", "libmp3lame", "-ab", bitrate, output_path]
        subprocess.run(cmd, check=True, cwd=os.path.dirname(input_file))
        print(f"✓ Audio extraction completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during audio extraction: {e}")

def remove_audio(input_file):
    """Remove audio completely from video."""
    print(f"\n=== Remove Audio: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    output_filename = safe_input("Enter output filename (with extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        extension = os.path.splitext(os.path.basename(input_file))[1]
        output_filename = f"{base_name}_silent{extension}"
        print(f"Using default filename: {output_filename}")
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename)
    output_path = validate_output_path(output_path)
    
    print(f"\n=== Audio Removal Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"Output: {os.path.basename(output_path)}")
    print("Note: Video will be copied without re-encoding (fast, no quality loss)")
    
    confirm = safe_input("\nProceed with audio removal? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("Removing audio...")
    try:
        cmd = ["ffmpeg", "-i", input_file, "-an", "-c:v", "copy", output_path]
        subprocess.run(cmd, check=True, cwd=os.path.dirname(input_file))
        print(f"✓ Audio removal completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during audio removal: {e}")

def change_framerate(input_file):
    """Change video frame rate."""
    print(f"\n=== Change Frame Rate: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    print("Common frame rates:")
    print("• 60 fps (smooth, gaming)")
    print("• 30 fps (standard)")
    print("• 24 fps (cinematic)")
    print("• 15 fps (lower quality)")
    print("• 10 fps (slideshow-like)")
    
    fps_input = safe_input("Enter target frame rate (fps): ").strip()
    
    try:
        fps = float(fps_input)
        if fps <= 0 or fps > 120:
            print("Frame rate must be between 0 and 120 fps.")
            return
    except ValueError:
        print("Invalid frame rate. Aborting.")
        return
    
    output_filename = safe_input("Enter output filename (with extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        extension = os.path.splitext(os.path.basename(input_file))[1]
        output_filename = f"{base_name}_{fps}fps{extension}"
        print(f"Using default filename: {output_filename}")
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename)
    output_path = validate_output_path(output_path)
    
    print(f"\n=== Frame Rate Change Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"Target frame rate: {fps} fps")
    print(f"Output: {os.path.basename(output_path)}")
    print("Note: Audio will be copied without changes")
    
    confirm = safe_input("\nProceed with frame rate change? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("Changing frame rate...")
    try:
        cmd = ["ffmpeg", "-i", input_file, "-vf", f"fps={fps}", "-c:a", "copy", output_path]
        subprocess.run(cmd, check=True, cwd=os.path.dirname(input_file))
        print(f"✓ Frame rate change completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during frame rate change: {e}")

def slow_down_video(input_file):
    """Slow down video and audio."""
    print(f"\n=== Slow Down Video: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    print("Slow down options:")
    print("• Enter percentage slower (e.g., 25 for 25% slower)")
    print("• Or enter speed multiplier (e.g., 0.5 for half speed)")
    
    speed_input = safe_input("Enter slowdown percentage or speed multiplier: ").strip()
    
    try:
        speed_value = float(speed_input)
        
        if speed_value > 1 and speed_value <= 99:
            # User entered percentage (e.g., 25 for 25% slower)
            speed_multiplier = 1 - (speed_value / 100)
            percentage_slower = speed_value
        elif speed_value > 0 and speed_value <= 1:
            # User entered multiplier (e.g., 0.5 for half speed)
            speed_multiplier = speed_value
            percentage_slower = (1 - speed_value) * 100
        else:
            print("Invalid input. Use percentage (1-99) or multiplier (0.01-1.0).")
            return
    except ValueError:
        print("Invalid input. Aborting.")
        return
    
    # Calculate PTS multiplier (inverse of speed for video)
    pts_multiplier = 1 / speed_multiplier
    
    output_filename = safe_input("Enter output filename (with extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        extension = os.path.splitext(os.path.basename(input_file))[1]
        output_filename = f"{base_name}_slow_{int(percentage_slower)}pct{extension}"
        print(f"Using default filename: {output_filename}")
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename)
    output_path = validate_output_path(output_path)
    
    print(f"\n=== Slow Down Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"Speed: {speed_multiplier:.2f}x ({percentage_slower:.1f}% slower)")
    print(f"Output: {os.path.basename(output_path)}")
    print("Note: Both video and audio will be slowed down proportionally")
    
    confirm = safe_input("\nProceed with slowing down? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("Slowing down video and audio...")
    try:
        # Use filter_complex to slow down both video and audio
        cmd = ["ffmpeg", "-i", input_file, 
               "-filter_complex", f"[0:v]setpts={pts_multiplier}*PTS[v];[0:a]atempo={speed_multiplier}[a]",
               "-map", "[v]", "-map", "[a]", output_path]
        
        subprocess.run(cmd, check=True, cwd=os.path.dirname(input_file))
        print(f"✓ Video slowdown completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during video slowdown: {e}")

def get_recent_video_files(limit=20):
    """Get recently downloaded video files from both directories."""
    video_files = []
    
    # Check both video and music directories
    directories = [DEFAULT_VIDEO_DIR, DEFAULT_MUSIC_DIR]
    
    for directory in directories:
        if os.path.exists(directory):
            # Look for video files recursively
            patterns = ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.webm', '*.m4v', '*.flv']
            
            for pattern in patterns:
                files = glob.glob(os.path.join(directory, '**', pattern), recursive=True)
                for file in files:
                    try:
                        mtime = os.path.getmtime(file)
                        size = os.path.getsize(file)
                        video_files.append({
                            'path': file,
                            'name': os.path.basename(file),
                            'mtime': mtime,
                            'size': size,
                            'directory': os.path.dirname(file)
                        })
                    except OSError:
                        continue
    
    # Sort by modification time (newest first) and limit
    video_files.sort(key=lambda x: x['mtime'], reverse=True)
    return video_files[:limit]

def select_video_file():
    """Interactive video file selection."""
    print("\n=== Select Video File ===")
    print("1. Recent downloads")
    print("2. Browse specific folder")
    print("3. Enter file path manually")
    print("99. Back to main menu")
    
    choice = safe_input("\nEnter your choice (1-3, 99): ").strip()
    
    if choice == "99":
        return None
    elif choice == "1":
        # Recent files
        recent_files = get_recent_video_files()
        
        if not recent_files:
            print("No recent video files found.")
            return None
        
        print(f"\n=== Recent Video Files ===")
        for i, file_info in enumerate(recent_files, 1):
            size_mb = file_info['size'] / (1024 * 1024)
            print(f"{i:2d}. {file_info['name']} ({size_mb:.1f} MB)")
            print(f"     {file_info['directory']}")
        
        print(f"{len(recent_files) + 1:2d}. Browse specific folder")
        print("99. Back")
        
        file_choice = safe_input(f"\nSelect file (1-{len(recent_files)}, {len(recent_files) + 1}, 99): ").strip()
        
        if file_choice == "99":
            return None
        elif file_choice == str(len(recent_files) + 1):
            return select_video_file()  # Recurse to folder browse
        else:
            try:
                index = int(file_choice) - 1
                if 0 <= index < len(recent_files):
                    return recent_files[index]['path']
                else:
                    print("Invalid selection.")
                    return None
            except ValueError:
                print("Invalid input.")
                return None
                
    elif choice == "2":
        # Browse folder
        folder_path = safe_input("Enter folder path (drag and drop supported): ").strip()
        folder_path = folder_path.strip('\'"')  # Remove quotes
        
        if not folder_path:
            return None
        
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            print("Invalid folder path.")
            return None
        
        # Find video files in folder
        video_files = []
        patterns = ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.webm', '*.m4v', '*.flv']
        
        for pattern in patterns:
            files = glob.glob(os.path.join(folder_path, pattern))
            video_files.extend(files)
        
        if not video_files:
            print("No video files found in the specified folder.")
            return None
        
        video_files.sort()
        
        print(f"\n=== Video Files in {folder_path} ===")
        for i, file_path in enumerate(video_files, 1):
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            print(f"{i:2d}. {os.path.basename(file_path)} ({file_size:.1f} MB)")
        
        print("99. Back")
        
        file_choice = safe_input(f"\nSelect file (1-{len(video_files)}, 99): ").strip()
        
        if file_choice == "99":
            return None
        
        try:
            index = int(file_choice) - 1
            if 0 <= index < len(video_files):
                return video_files[index]
            else:
                print("Invalid selection.")
                return None
        except ValueError:
            print("Invalid input.")
            return None
            
    elif choice == "3":
        # Manual path entry
        file_path = safe_input("Enter video file path (drag and drop supported): ").strip()
        file_path = file_path.strip('\'"')  # Remove quotes
        
        if not file_path:
            return None
        
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            print("File does not exist.")
            return None
        
        return file_path
    
    else:
        print("Invalid choice.")
        return None

def show_file_metadata():
    """Show metadata for a video file with basic or full info options."""
    print("\n=== File Metadata Viewer ===")
    
    # Get file path from user
    file_path = safe_input("Enter video file path (drag and drop supported): ").strip()
    file_path = file_path.strip('\'"')  # Remove quotes if drag and dropped
    
    if not file_path:
        print("No file path provided.")
        return
    
    # Expand user path and normalize
    file_path = os.path.expanduser(file_path)
    file_path = os.path.normpath(file_path)
    
    if not os.path.exists(file_path):
        print(f"File does not exist: {file_path}")
        return
    
    if not os.path.isfile(file_path):
        print(f"Path is not a file: {file_path}")
        return
    
    # Choose info level
    print("\nSelect info level:")
    print("1. Basic info (essential details only)")
    print("2. Full info (comprehensive analysis)")
    print("99. Back to main menu")
    
    choice = safe_input("Enter your choice (1, 2, or 99): ").strip()
    
    if choice == "99":
        return
    elif choice not in ["1", "2"]:
        print("Invalid choice.")
        return
    
    print(f"\nAnalysing: {os.path.basename(file_path)}")
    print("=" * 60)
    
    # Check which tools are available
    tools_available = []
    
    # Check for mediainfo (preferred for comprehensive info)
    try:
        subprocess.run(["mediainfo", "--version"], capture_output=True, check=True)
        tools_available.append("mediainfo")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Check for ffprobe (part of ffmpeg)
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        tools_available.append("ffprobe")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Check for exiftool
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
        tools_available.append("exiftool")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    if not tools_available:
        print("No metadata tools found. Please install at least one of:")
        print("- mediainfo: sudo apt install mediainfo")
        print("- ffprobe (part of ffmpeg): sudo apt install ffmpeg")
        print("- exiftool: sudo apt install libimage-exiftool-perl")
        return
    
    # Show basic or full info based on user choice
    if choice == "1":
        show_basic_metadata(file_path, tools_available)
    else:
        show_full_metadata(file_path, tools_available)

def show_basic_metadata(file_path, tools_available):
    """Show basic metadata information."""
    try:
        if "mediainfo" in tools_available:
            result = subprocess.run(["mediainfo", file_path], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                
                # Extract only basic info fields
                basic_fields = [
                    'Complete name', 'Format', 'Format version', 'File size', 
                    'Duration', 'Overall bit rate', 'Frame rate'
                ]
                
                for line in lines:
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if any(field in key for field in basic_fields):
                            print(f"{key:<35} : {value}")
            else:
                print("Failed to run mediainfo")
        
        elif "ffprobe" in tools_available:
            # Fallback to ffprobe if mediainfo not available
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-print_format", "default", 
                "-show_format", file_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                print(f"Complete name                       : {file_path}")
                
                for line in lines:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if key == "format_name":
                            print(f"Format                              : {value}")
                        elif key == "duration":
                            duration_sec = float(value)
                            minutes = int(duration_sec // 60)
                            seconds = int(duration_sec % 60)
                            ms = int((duration_sec % 1) * 1000)
                            print(f"Duration                            : {minutes} min {seconds} s {ms} ms")
                        elif key == "size":
                            size_mb = int(value) / (1024 * 1024)
                            print(f"File size                           : {size_mb:.2f} MiB")
                        elif key == "bit_rate":
                            bit_rate_kb = int(value) // 1000
                            print(f"Overall bit rate                    : {bit_rate_kb} kb/s")
            else:
                print("Failed to run ffprobe")
        else:
            print("No suitable tools available for basic metadata extraction")
    
    except subprocess.TimeoutExpired:
        print("Timeout occurred while analysing file")
    except Exception as e:
        print(f"Error analysing file: {e}")
    
    print("\n" + "=" * 60)
    input("Press Enter to continue...")

def show_full_metadata(file_path, tools_available):
    """Show comprehensive metadata information."""
    try:
        if "mediainfo" in tools_available:
            print("\n--- MediaInfo ---")
            result = subprocess.run(["mediainfo", file_path], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                # Filter out less useful information and format nicely
                lines = result.stdout.split('\n')
                useful_lines = []
                current_section = ""
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Section headers (General, Video, Audio, etc.)
                    if not line.startswith(' ') and ':' not in line and line:
                        current_section = line
                        if current_section in ['General', 'Video', 'Audio']:
                            useful_lines.append(f"\n{current_section}")
                    # Useful metadata fields
                    elif ':' in line and current_section in ['General', 'Video', 'Audio']:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Filter for useful fields
                        useful_fields = [
                            'Complete name', 'Format', 'Format profile', 'Codec ID', 
                            'File size', 'Duration', 'Overall bit rate', 'Frame rate',
                            'Bit rate', 'Width', 'Height', 'Display aspect ratio',
                            'Color space', 'Chroma subsampling', 'Bit depth', 
                            'Scan type', 'Writing library', 'Writing application',
                            'Sampling rate', 'Channel layout', 'Compression mode'
                        ]
                        
                        if any(field in key for field in useful_fields):
                            useful_lines.append(f"{key:<35} : {value}")
                
                for line in useful_lines:
                    print(line)
            else:
                print("Failed to run mediainfo")
        
        if "ffprobe" in tools_available:
            print("\n--- FFprobe ---")
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-print_format", "default", 
                "-show_format", "-show_streams", file_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                in_format = False
                in_video_stream = False
                in_audio_stream = False
                
                for line in lines:
                    line = line.strip()
                    if line == "[FORMAT]":
                        in_format = True
                        print("\nFormat:")
                        continue
                    elif line == "[/FORMAT]":
                        in_format = False
                        continue
                    elif line == "[STREAM]":
                        continue
                    elif line == "[/STREAM]":
                        in_video_stream = False
                        in_audio_stream = False
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        
                        if in_format:
                            useful_format_fields = [
                                'filename', 'nb_streams', 'format_name', 'format_long_name',
                                'duration', 'size', 'bit_rate'
                            ]
                            if key in useful_format_fields:
                                print(f"  {key:<20} : {value}")
                        
                        elif key == "codec_type":
                            if value == "video":
                                in_video_stream = True
                                print(f"\nVideo Stream:")
                            elif value == "audio":
                                in_audio_stream = True
                                print(f"\nAudio Stream:")
                        
                        elif in_video_stream:
                            useful_video_fields = [
                                'codec_name', 'codec_long_name', 'width', 'height',
                                'r_frame_rate', 'avg_frame_rate', 'pix_fmt', 'bit_rate'
                            ]
                            if key in useful_video_fields:
                                print(f"  {key:<20} : {value}")
                        
                        elif in_audio_stream:
                            useful_audio_fields = [
                                'codec_name', 'codec_long_name', 'sample_rate',
                                'channels', 'channel_layout', 'bit_rate'
                            ]
                            if key in useful_audio_fields:
                                print(f"  {key:<20} : {value}")
            else:
                print("Failed to run ffprobe")
    
    except subprocess.TimeoutExpired:
        print("Timeout occurred while analysing file")
    except Exception as e:
        print(f"Error analysing file: {e}")
    
    print("\n" + "=" * 60)
    input("Press Enter to continue...")

def ascii_art_converter(input_file):
    """Convert video to colored ASCII art that plays back in terminal."""
    print(f"\n=== ASCII Art Video Converter: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    print("ASCII Art Options:")
    print("1. High detail (larger terminal output)")
    print("2. Medium detail (balanced)")
    print("3. Low detail (compact, faster)")
    print("4. Custom size")
    
    detail_choice = safe_input("Choose detail level (1-4): ").strip()
    
    if detail_choice == "1":
        width, height = 160, 60
    elif detail_choice == "2":
        width, height = 120, 40
    elif detail_choice == "3":
        width, height = 80, 24
    elif detail_choice == "4":
        try:
            width = int(safe_input("Enter width in characters (e.g., 80): ").strip())
            height = int(safe_input("Enter height in characters (e.g., 24): ").strip())
            if width <= 0 or height <= 0:
                raise ValueError("Dimensions must be positive")
        except ValueError:
            print("Invalid dimensions. Using medium detail.")
            width, height = 120, 40
    else:
        print("Invalid choice. Using medium detail.")
        width, height = 120, 40
    
    print("\nOutput Format:")
    print("1. Colored ASCII (requires terminal with color support)")
    print("2. Monochrome ASCII")
    print("3. Both")
    
    color_choice = safe_input("Choose format (1-3): ").strip()
    
    output_filename = safe_input("Enter output filename (without extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_filename = f"{base_name}_ascii"
        print(f"Using default filename: {output_filename}")
    
    output_dir = os.path.dirname(input_file)
    
    print(f"\n=== ASCII Conversion Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"ASCII size: {width}x{height} characters")
    print(f"Output: {output_filename}.txt (colored) and/or {output_filename}_mono.txt")
    print("Note: Large videos may take significant time to process")
    
    confirm = safe_input("\nProceed with ASCII conversion? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    try:
        # Method 1: Try using libcaca output device (requires terminal display)
        print("Note: ASCII art conversion will create frame sequences that can be converted to text")
        
        # Create colored ASCII version using caca output device
        if color_choice in ["1", "3"]:
            print("Creating colored ASCII frames...")
            colored_output = os.path.join(output_dir, f"{output_filename}.txt")
            colored_output = validate_output_path(colored_output)
            
            # Extract frames and use external tools for ASCII conversion
            frames_dir = os.path.join(output_dir, f"temp_frames_{output_filename}")
            os.makedirs(frames_dir, exist_ok=True)
            
            # Extract frames at low frame rate
            cmd = ["ffmpeg", "-i", input_file, 
                   "-vf", f"scale={width}:{height}:flags=lanczos,fps=2", 
                   "-y", os.path.join(frames_dir, "frame_%04d.png")]
            
            subprocess.run(cmd, check=True, cwd=output_dir)
            
            # Try to use img2txt if available (from libcaca-utils)
            try:
                subprocess.run(["img2txt", "--version"], capture_output=True, check=True)
                
                # Convert each frame to ASCII
                ascii_frames = []
                frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
                
                for frame_file in frame_files:
                    frame_path = os.path.join(frames_dir, frame_file)
                    result = subprocess.run(["img2txt", "--width", str(width), "--height", str(height), 
                                           "--gamma", "1.0", frame_path], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        ascii_frames.append(result.stdout)
                
                # Save ASCII animation with frame separators
                with open(colored_output, 'w') as f:
                    f.write(f"# ASCII Art Animation: {os.path.basename(input_file)}\n")
                    f.write(f"# Frames: {len(ascii_frames)} | Resolution: {width}x{height}\n")
                    f.write("# Generated by Loutube ASCII Art Converter\n\n")
                    for i, frame in enumerate(ascii_frames):
                        f.write(frame)
                        if i < len(ascii_frames) - 1:  # Don't add separator after last frame
                            f.write("\n" + "="*60 + "\n")
                
                print(f"✓ Colored ASCII animation saved: {colored_output}")
                
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("img2txt not found. Install libcaca-utils: sudo apt install libcaca-utils")
                # Fallback: create a simple text representation
                with open(colored_output, 'w') as f:
                    f.write(f"ASCII Art Video: {os.path.basename(input_file)}\n")
                    f.write(f"Frames extracted to: {frames_dir}\n")
                    f.write("Install 'libcaca-utils' package for full ASCII conversion\n")
                print(f"✓ Frame extraction completed: {frames_dir}")
            
            # Clean up frames directory
            shutil.rmtree(frames_dir, ignore_errors=True)
        
        # Create monochrome ASCII version using jp2a if available
        if color_choice in ["2", "3"]:
            print("Creating monochrome ASCII art...")
            mono_output = os.path.join(output_dir, f"{output_filename}_mono.txt")
            mono_output = validate_output_path(mono_output)
            
            # Try jp2a first (better ASCII art tool)
            try:
                subprocess.run(["jp2a", "--version"], capture_output=True, check=True)
                
                # Extract frames for jp2a conversion
                frames_dir = os.path.join(output_dir, f"temp_frames_mono_{output_filename}")
                os.makedirs(frames_dir, exist_ok=True)
                
                cmd = ["ffmpeg", "-i", input_file, 
                       "-vf", f"scale={width}:{height}:flags=lanczos,fps=2", 
                       "-y", os.path.join(frames_dir, "frame_%04d.jpg")]
                
                subprocess.run(cmd, check=True, cwd=output_dir)
                
                # Convert frames with jp2a
                ascii_frames = []
                frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.jpg')])
                
                for frame_file in frame_files:
                    frame_path = os.path.join(frames_dir, frame_file)
                    result = subprocess.run(["jp2a", "--width", str(width), "--height", str(height), 
                                           frame_path], capture_output=True, text=True)
                    if result.returncode == 0:
                        ascii_frames.append(result.stdout)
                
                # Save ASCII animation with frame separators
                with open(mono_output, 'w') as f:
                    f.write(f"# ASCII Art Animation: {os.path.basename(input_file)}\n")
                    f.write(f"# Frames: {len(ascii_frames)} | Resolution: {width}x{height}\n")
                    f.write("# Generated by Loutube ASCII Art Converter\n\n")
                    for i, frame in enumerate(ascii_frames):
                        f.write(frame)
                        if i < len(ascii_frames) - 1:  # Don't add separator after last frame
                            f.write("\n" + "-"*60 + "\n")
                
                print(f"✓ Monochrome ASCII animation saved: {mono_output}")
                
                # Clean up
                shutil.rmtree(frames_dir, ignore_errors=True)
                
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("jp2a not found. Creating alternative ASCII representation...")
                
                # Fallback: Use FFmpeg to create a simple character representation
                temp_frames = os.path.join(output_dir, f"temp_simple_{output_filename}.jpg")
                
                # Extract a single frame and create a simple representation
                cmd = ["ffmpeg", "-i", input_file, "-vf", f"scale={width//4}:{height//4}", 
                       "-vframes", "1", "-y", temp_frames]
                subprocess.run(cmd, check=True, cwd=output_dir)
                
                with open(mono_output, 'w') as f:
                    f.write(f"ASCII Art Video: {os.path.basename(input_file)}\n")
                    f.write(f"Resolution: {width}x{height} characters\n")
                    f.write("Install 'jp2a' for full ASCII conversion: sudo apt install jp2a\n")
                    f.write("Or install 'libcaca-utils': sudo apt install libcaca-utils\n\n")
                    
                    # Simple character representation
                    chars = "$@B%&WM#oahkbdpqwmZO0QLCJUYXzcvunxrjft/|()1{[]?*-_+~<>i!lI;:,^."
                    for y in range(height//8):
                        line = ""
                        for x in range(width//4):
                            # Simple pattern based on position
                            intensity = (x + y) % len(chars)
                            line += chars[intensity]
                        f.write(line + "\n")
                
                print(f"✓ Simple ASCII representation saved: {mono_output}")
                
                # Clean up
                if os.path.exists(temp_frames):
                    os.remove(temp_frames)
        
        print("\n✓ ASCII art conversion completed!")
        print("\nTo get full ASCII art functionality, install:")
        print("• For colored ASCII: sudo apt install libcaca-utils")
        print("• For monochrome ASCII: sudo apt install jp2a")
        print("• Both tools provide much better results than basic conversion")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during ASCII conversion: {e}")
        print("\nFor better ASCII art conversion, install these tools:")
        print("• sudo apt install libcaca-utils  # For img2txt")
        print("• sudo apt install jp2a           # For JPEG to ASCII")
        print("• sudo apt install caca-utils     # Alternative libcaca tools")

def play_ascii_art():
    """Play ASCII art files like animated GIFs in terminal."""
    print("\n=== ASCII Art Player ===")
    print("This will play ASCII art files created by the ASCII converter.")
    
    # Get file path
    ascii_file = safe_input("Enter ASCII art file path (drag and drop supported): ").strip()
    ascii_file = ascii_file.strip('\'"')  # Remove quotes if drag and dropped
    
    if not ascii_file:
        print("No file provided.")
        return
    
    ascii_file = os.path.expanduser(ascii_file)
    
    if not os.path.exists(ascii_file):
        print(f"File does not exist: {ascii_file}")
        return
    
    print(f"\nLoading ASCII art file: {os.path.basename(ascii_file)}")
    
    try:
        with open(ascii_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Detect frame separators and split into frames
        frames = []
        
        # Try different separator patterns
        if "=" * 60 in content:  # Our new colored ASCII separator
            frames = content.split("=" * 60 + "\n")
        elif "-" * 60 in content:  # Our new monochrome ASCII separator  
            frames = content.split("-" * 60 + "\n")
        elif "=" * 20 in content:  # Legacy colored ASCII separator
            frames = content.split("=" * 20 + "\n")
        elif "-" * 20 in content:  # Legacy monochrome ASCII separator  
            frames = content.split("-" * 20 + "\n")
        elif "\n\n" in content:  # Double newline separator
            frames = content.split("\n\n")
        else:
            # Single frame or unknown format
            frames = [content]
        
        # Clean up frames
        frames = [frame.strip() for frame in frames if frame.strip()]
        
        if len(frames) <= 1:
            print("This appears to be a static ASCII art file (single frame).")
            print("Displaying content:")
            print("-" * 50)
            print(content)
            print("-" * 50)
            return
        
        print(f"Found {len(frames)} frames")
        
        # Playback options
        print("\nPlayback Options:")
        print("1. Slow (0.5 fps)")
        print("2. Normal (2 fps)")  
        print("3. Fast (5 fps)")
        print("4. Very fast (10 fps)")
        print("5. Custom speed")
        
        speed_choice = safe_input("Choose playback speed (1-5): ").strip()
        
        if speed_choice == "1":
            fps = 0.5
        elif speed_choice == "2":
            fps = 2.0
        elif speed_choice == "3": 
            fps = 5.0
        elif speed_choice == "4":
            fps = 10.0
        elif speed_choice == "5":
            custom_fps = safe_input("Enter FPS (0.1-30): ").strip()
            try:
                fps = float(custom_fps)
                fps = max(0.1, min(30.0, fps))
            except ValueError:
                fps = 2.0
                print("Invalid FPS. Using 2.0")
        else:
            fps = 2.0
            print("Invalid choice. Using normal speed (2 fps)")
        
        frame_delay = 1.0 / fps
        
        print(f"\nStarting ASCII animation at {fps} fps")
        print("Press Ctrl+C to stop playback\n")
        
        try:
            import time
            loop_count = 0
            
            while True:
                for i, frame in enumerate(frames):
                    # Clear screen (works on most terminals)
                    print("\033[2J\033[H", end="")
                    
                    # Display frame info
                    print(f"Frame {i+1}/{len(frames)} | Loop {loop_count+1} | {fps} fps | Press Ctrl+C to stop")
                    print("-" * 60)
                    print(frame)
                    print("-" * 60)
                    
                    time.sleep(frame_delay)
                
                loop_count += 1
                
                # Ask if user wants to continue after first loop
                if loop_count == 1:
                    print(f"\nLoop 1 completed. Animation will continue...")
                    time.sleep(1)
        
        except KeyboardInterrupt:
            print(f"\n\n✓ ASCII animation stopped after {loop_count} loops")
            print("Thanks for watching!")
            
    except Exception as e:
        print(f"Error reading ASCII file: {e}")

def create_ascii_player_script():
    """Create a standalone ASCII art player script."""
    print("\n=== Create ASCII Player Script ===")
    
    script_content = '''#!/usr/bin/env python3
"""
Standalone ASCII Art Player
Usage: python3 ascii_player.py <ascii_file.txt> [fps]
"""

import sys
import os
import time

def play_ascii_file(filename, fps=2.0):
    """Play ASCII art file with animation."""
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Detect frames
        frames = []
        if "=" * 20 in content:
            frames = content.split("=" * 20 + "\\n")
        elif "-" * 20 in content:
            frames = content.split("-" * 20 + "\\n")
        elif "\\n\\n" in content:
            frames = content.split("\\n\\n")
        else:
            frames = [content]
        
        frames = [frame.strip() for frame in frames if frame.strip()]
        
        if len(frames) <= 1:
            print("Static ASCII art:")
            print("-" * 50)
            print(content)
            print("-" * 50)
            return
        
        frame_delay = 1.0 / fps
        print(f"Playing {len(frames)} frames at {fps} fps (Press Ctrl+C to stop)\\n")
        
        loop_count = 0
        while True:
            for i, frame in enumerate(frames):
                print("\\033[2J\\033[H", end="")  # Clear screen
                print(f"Frame {i+1}/{len(frames)} | Loop {loop_count+1} | {fps} fps")
                print("-" * 50)
                print(frame)
                time.sleep(frame_delay)
            loop_count += 1
            
    except KeyboardInterrupt:
        print(f"\\n\\nStopped after {loop_count} loops. Goodbye!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ascii_player.py <ascii_file.txt> [fps]")
        print("Example: python3 ascii_player.py video_ascii.txt 5")
        sys.exit(1)
    
    filename = sys.argv[1]
    fps = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    
    play_ascii_file(filename, fps)
'''
    
    script_path = safe_input("Enter path to save ASCII player script (default: ascii_player.py): ").strip()
    if not script_path:
        script_path = "ascii_player.py"
    
    script_path = os.path.abspath(script_path)
    
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        
        print(f"✓ ASCII player script created: {script_path}")
        print(f"\\nUsage examples:")
        print(f"  python3 {script_path} video_ascii.txt")
        print(f"  python3 {script_path} video_ascii.txt 5  # 5 fps")
        print(f"  ./{os.path.basename(script_path)} video_ascii.txt  # If executable")
        
    except Exception as e:
        print(f"Error creating script: {e}")

def datamoshing_effect(input_file):
    """Create datamoshing effect by deliberately corrupting video compression."""
    print(f"\n=== Datamoshing Effect: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    print("Datamoshing Intensity:")
    print("1. Mild (subtle glitching)")
    print("2. Medium (noticeable corruption)")
    print("3. Heavy (extreme glitch effects)")
    print("4. Extreme (heavily corrupted)")
    
    intensity = safe_input("Choose intensity (1-4): ").strip()
    
    if intensity == "1":
        # Remove every 10th I-frame
        iframe_interval = 10
        noise_level = 0.01
    elif intensity == "2":
        # Remove every 5th I-frame
        iframe_interval = 5
        noise_level = 0.02
    elif intensity == "3":
        # Remove every 3rd I-frame
        iframe_interval = 3
        noise_level = 0.05
    elif intensity == "4":
        # Remove every 2nd I-frame
        iframe_interval = 2
        noise_level = 0.1
    else:
        print("Invalid choice. Using medium intensity.")
        iframe_interval = 5
        noise_level = 0.02
    
    print("\nDatamoshing Style:")
    print("1. I-frame removal (classic flowing effect)")
    print("2. Noise injection (digital corruption)")
    print("3. Motion vector corruption")
    print("4. Combined effects")
    
    style_choice = safe_input("Choose style (1-4): ").strip()
    
    output_filename = safe_input("Enter output filename (with extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_filename = f"{base_name}_datamosh.mp4"
        print(f"Using default filename: {output_filename}")
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename)
    output_path = validate_output_path(output_path)
    
    print(f"\n=== Datamoshing Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"Intensity: {['Mild', 'Medium', 'Heavy', 'Extreme'][int(intensity)-1]}")
    print(f"Style: {['I-frame removal', 'Noise injection', 'Motion vector corruption', 'Combined'][int(style_choice)-1] if style_choice in ['1','2','3','4'] else 'I-frame removal'}")
    print(f"Output: {os.path.basename(output_path)}")
    print("Note: Results are intentionally corrupted/glitched")
    
    confirm = safe_input("\nProceed with datamoshing? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("Creating datamosh effect...")
    try:
        if style_choice == "1" or not style_choice in ["1", "2", "3", "4"]:
            # I-frame removal method
            print("Applying I-frame removal datamoshing...")
            cmd = ["ffmpeg", "-i", input_file,
                   "-c:v", "libx264", "-g", str(iframe_interval * 30), 
                   "-bf", "2", "-b_strategy", "0",
                   "-sc_threshold", "1000000", 
                   "-c:a", "copy", "-y", output_path]
            
        elif style_choice == "2":
            # Noise injection method
            print("Applying noise injection datamoshing...")
            cmd = ["ffmpeg", "-i", input_file,
                   "-vf", f"noise=alls={int(noise_level*100)}:allf=t+u",
                   "-c:v", "libx264", "-crf", "30",
                   "-c:a", "copy", "-y", output_path]
            
        elif style_choice == "3":
            # Motion vector corruption (using temporal noise)
            print("Applying motion vector corruption...")
            cmd = ["ffmpeg", "-i", input_file,
                   "-vf", f"noise=alls={int(noise_level*50)}:allf=t,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc",
                   "-c:v", "libx264", "-crf", "25",
                   "-c:a", "copy", "-y", output_path]
            
        elif style_choice == "4":
            # Combined effects
            print("Applying combined datamoshing effects...")
            cmd = ["ffmpeg", "-i", input_file,
                   "-vf", f"noise=alls={int(noise_level*30)}:allf=t+u",
                   "-c:v", "libx264", "-g", str(iframe_interval * 20), 
                   "-bf", "3", "-b_strategy", "0", "-crf", "28",
                   "-sc_threshold", "1000000",
                   "-c:a", "copy", "-y", output_path]
        
        subprocess.run(cmd, check=True, cwd=os.path.dirname(input_file))
        print(f"✓ Datamoshing effect completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during datamoshing: {e}")

def timelapse_motion_trails(input_file):
    """Create time-lapse with motion trails effect."""
    print(f"\n=== Time-lapse with Motion Trails: {os.path.basename(input_file)} ===")
    
    info = get_video_info(input_file)
    print(f"Duration: {info['duration']}")
    print(f"Resolution: {info['resolution']}")
    print(f"File size: {info['file_size']}")
    print()
    
    print("Time-lapse Speed:")
    print("1. 2x speed (mild time-lapse)")
    print("2. 4x speed (moderate time-lapse)")
    print("3. 8x speed (fast time-lapse)")
    print("4. 16x speed (very fast time-lapse)")
    print("5. Custom speed")
    
    speed_choice = safe_input("Choose speed (1-5): ").strip()
    
    if speed_choice == "1":
        speed_factor = 2.0
    elif speed_choice == "2":
        speed_factor = 4.0
    elif speed_choice == "3":
        speed_factor = 8.0
    elif speed_choice == "4":
        speed_factor = 16.0
    elif speed_choice == "5":
        custom_speed = safe_input("Enter speed multiplier (e.g., 6.5): ").strip()
        try:
            speed_factor = float(custom_speed)
            if speed_factor <= 1.0 or speed_factor > 100.0:
                speed_factor = 4.0
                print("Using default speed: 4x")
        except ValueError:
            speed_factor = 4.0
            print("Invalid speed. Using default: 4x")
    else:
        speed_factor = 4.0
        print("Invalid choice. Using default: 4x")
    
    print("\nMotion Trail Settings:")
    print("Trail Length (how long trails persist):")
    print("1. Short trails (0.5 seconds)")
    print("2. Medium trails (1 second)")
    print("3. Long trails (2 seconds)")
    print("4. Very long trails (4 seconds)")
    
    trail_choice = safe_input("Choose trail length (1-4): ").strip()
    
    if trail_choice == "1":
        trail_frames = int(15 * 0.5)  # 15 fps * 0.5 sec
    elif trail_choice == "2":
        trail_frames = int(15 * 1.0)  # 15 fps * 1 sec
    elif trail_choice == "3":
        trail_frames = int(15 * 2.0)  # 15 fps * 2 sec
    elif trail_choice == "4":
        trail_frames = int(15 * 4.0)  # 15 fps * 4 sec
    else:
        trail_frames = int(15 * 1.0)
        print("Invalid choice. Using medium trails.")
    
    print("\nTrail Intensity:")
    print("1. Subtle (light ghosting)")
    print("2. Medium (balanced)")
    print("3. Strong (heavy trails)")
    
    intensity_choice = safe_input("Choose intensity (1-3): ").strip()
    
    if intensity_choice == "1":
        trail_alpha = 0.3
    elif intensity_choice == "2":
        trail_alpha = 0.5
    elif intensity_choice == "3":
        trail_alpha = 0.7
    else:
        trail_alpha = 0.5
        print("Invalid choice. Using medium intensity.")
    
    output_filename = safe_input("Enter output filename (with extension): ").strip()
    if not output_filename:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_filename = f"{base_name}_timelapse_trails.mp4"
        print(f"Using default filename: {output_filename}")
    
    output_path = os.path.join(os.path.dirname(input_file), output_filename)
    output_path = validate_output_path(output_path)
    
    print(f"\n=== Time-lapse Motion Trails Summary ===")
    print(f"Input: {os.path.basename(input_file)}")
    print(f"Speed: {speed_factor}x")
    print(f"Trail length: {trail_frames / 15:.1f} seconds")
    print(f"Trail intensity: {['Subtle', 'Medium', 'Strong'][int(intensity_choice)-1] if intensity_choice in ['1','2','3'] else 'Medium'}")
    print(f"Output: {os.path.basename(output_path)}")
    print("Note: Processing may take considerable time for long videos")
    
    confirm = safe_input("\nProceed with time-lapse motion trails? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print("Creating time-lapse with motion trails...")
    try:
        # Calculate PTS for speed change
        pts_factor = 1.0 / speed_factor
        
        # Create motion trails using tmix filter with multiple inputs
        # The tmix filter blends multiple frames together to create trails
        filter_complex = (
            f"[0:v]setpts={pts_factor}*PTS,fps=30[spedup];"
            f"[spedup]tmix=frames={trail_frames}:weights='{' '.join([str(trail_alpha ** i) for i in range(trail_frames)])}'"
        )
        
        cmd = ["ffmpeg", "-i", input_file,
               "-filter_complex", filter_complex,
               "-c:v", "libx264", "-crf", "20",
               "-preset", "medium", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "128k",
               "-y", output_path]
        
        subprocess.run(cmd, check=True, cwd=os.path.dirname(input_file))
        print(f"✓ Time-lapse with motion trails completed successfully!")
        print(f"Output saved: {output_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error during time-lapse creation: {e}")
        print("Note: This effect requires significant processing power and time")

def video_editor_menu():
    """Main video editor menu."""
    if not check_ffmpeg():
        print("Error: ffmpeg is not installed or not in PATH")
        print("Please install ffmpeg first: https://ffmpeg.org/download.html")
        return
    
    while True:
        selected_file = select_video_file()
        
        if not selected_file:
            break
        
        print(f"\n=== Video Editor - {os.path.basename(selected_file)} ===")
        print("=== Basic Operations ===")
        print("1. Trim video (keep original quality)")
        print("2. Transcode video (change quality/codec)")
        print("3. Convert format only (no quality change)")
        print("4. Convert to GIF")
        print("5. Add black bars for Instagram (post/reel/story)")
        print("6. Extract audio as MP3")
        print("7. Remove audio completely")
        print("8. Change frame rate")
        print("9. Slow down video and audio")
        print()
        print("=== Special Effects ===")
        print("11. ASCII Art Video Converter (terminal playback)")
        print("12. Datamoshing Effect (glitch art)")
        print("13. Time-lapse with Motion Trails")
        print()
        print("=== ASCII Utilities ===")
        print("14. Play ASCII Art File (animate in terminal)")
        print("15. Create ASCII Player Script (standalone)")
        print()
        print("10. Select different file")
        print("99. Back to main menu")
        
        operation = safe_input("\nEnter your choice (1-9, 11-16, 10, 99): ").strip()
        
        if operation == "99":
            break
        elif operation == "1":
            trim_video(selected_file)
        elif operation == "2":
            transcode_video(selected_file)
        elif operation == "3":
            convert_format(selected_file)
        elif operation == "4":
            convert_to_gif(selected_file)
        elif operation == "5":
            add_padding(selected_file)
        elif operation == "6":
            extract_audio(selected_file)
        elif operation == "7":
            remove_audio(selected_file)
        elif operation == "8":
            change_framerate(selected_file)
        elif operation == "9":
            slow_down_video(selected_file)
        elif operation == "10":
            continue  # Loop back to file selection
        elif operation == "11":
            ascii_art_converter(selected_file)
        elif operation == "12":
            datamoshing_effect(selected_file)
        elif operation == "13":
            timelapse_motion_trails(selected_file)
        elif operation == "14":
            play_ascii_art()
        elif operation == "15":
            create_ascii_player_script()
        else:
            print("Invalid choice.")
        
        if operation in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "11", "12", "13", "14", "15"]:
            # Ask if user wants to perform another operation on the same file
            another = safe_input("\nPerform another operation on this file? (y/N): ").strip().lower()
            if another != 'y':
                break

    
def main():
    # Check for help or config flags
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h', 'help']:
            show_help()
            return
        elif sys.argv[1] in ['--config', '-c', 'config']:
            show_config()
            return
        elif sys.argv[1] in ['--recent', '-r', 'recent']:
            show_recent_downloads()
            return
        elif sys.argv[1] in ['--edit', '-e', 'edit']:
            video_editor_menu()
            return
        elif sys.argv[1] in ['--ascii', '-a', 'ascii']:
            play_ascii_art()
            return
        
    if not check_dependencies():
        return
    
    # Show configuration info
    config_file = find_config_file()
    print("\nThanks for using Loutube! A wrapper for 'YT-DLP', making it easier to use!\n")
    print("To find your downloads, go to:")
    print(f"Videos are downloaded to: {DEFAULT_VIDEO_DIR}")
    print(f"Music is downloaded to: {DEFAULT_MUSIC_DIR}")
    
    # Browser cookies will be requested when needed (not upfront)
    browser_cookies = None
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print("\nWhat would you like to do?")
        print("1. Watch video (stream)")
        print("2. Download video")
        print("3. Download music")
        print("4. Edit videos")
        print("5. View file metadata")
        print("6. Play ASCII art file")
        print("99. Quit\n")
        action = safe_input("Enter your choice (1, 2, 3, 4, 5, 6, or 99): ").strip()
        print("")
        

        if action == "1":
            watch_video(url)
        elif action == "2":
            # Video download options
            print("\nFor video downloads, choose an option:")
            print("1. Video with audio")
            print("2. Video only (no audio)")
            print("3. Audio only (extracted from video)")
            print("4. Download livestream from the beginning of the stream")
            print("99. Quit\n")
            opt = safe_input("Enter your choice (1, 2, 3, 4, or 99): ").strip()
            print("")
            if opt == "1":
                download_video(url)
            elif opt == "2":
                download_video_no_audio(url)
            elif opt == "3":
                custom_dir = safe_input("Output directory (or press Enter for default music folder): ").strip()
                output_dir = custom_dir if custom_dir else DEFAULT_MUSIC_DIR
                download_audio_from_video(url, output_dir)
            elif opt == "4":
                download_live_from_start(url)
            else:
                print("Invalid option. Exiting.")
        elif action == "3":
            # Music download - automatically handles playlist detection
            download_audio(url)
        elif action == "4":
            # Video editor
            video_editor_menu()
        elif action == "5":
            # File metadata viewer
            show_file_metadata()
        elif action == "6":
            # ASCII art player
            play_ascii_art()
        elif action == "99":
            pass  # Already handled by safe_input
        else:
            print("Invalid choice. Exiting.")
    else:
        print("\nSelect option:")
        print("1. Download video")
        print("2. Download music")
        print("3. Edit videos")
        print("4. View file metadata")
        print("5. Play ASCII art file")
        print("99. Quit\n")
        choice = safe_input("Enter your choice (1, 2, 3, 4, 5, or 99): ").strip()
        print("")
        if choice not in ("1", "2", "3", "4", "5", "99"):
            print("Invalid choice. Exiting.")
            return

        if choice == "3":
            # Video editor
            video_editor_menu()
        elif choice == "4":
            # File metadata viewer
            show_file_metadata()
        elif choice == "5":
            # ASCII art player
            play_ascii_art()
        else:
            url = safe_input("Enter the link: ").strip()
            if not url:
                print("Error: No URL provided.")
                return

            if choice == "2":
                download_audio(url)
            elif choice == "1":
                print("For video downloads, choose an option:")
                print("1. Video with audio")
                print("2. Video only (no audio)")
                print("3. Audio only (extracted from video)")
                print("99. Quit\n")
                opt = safe_input("Enter your choice (1, 2, 3, or 99): ").strip()
                print("")
                if opt == "1":
                    download_video(url)
                elif opt == "2":
                    download_video_no_audio(url)
                elif opt == "3":
                    custom_dir = safe_input("Output directory (or press Enter for default music folder): ").strip()
                    output_dir = custom_dir if custom_dir else DEFAULT_MUSIC_DIR
                    download_audio_from_video(url, output_dir)
                else:
                    print("Invalid option. Exiting.")

if __name__ == "__main__":
    main()
