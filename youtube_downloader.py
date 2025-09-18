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

# Global variable to cache browser cookies
_cached_browser_cookies = None
_cookies_checked = False

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
            ('firefox', 'firefox'),
            ('chrome', 'chrome'),
            ('brave', 'brave'),
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
        try:
            # Just test if yt-dlp accepts the browser option - much faster than simulate
            # Using --version is faster and more reliable than --help
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

def build_base_command(url, browser_cookies=None):
    """Build the base yt-dlp command with optional cookies."""
    command = ["yt-dlp"]
    
    if browser_cookies:
        command.extend(["--cookies-from-browser", browser_cookies])
    
    return command

def is_playlist(url):
    """Check if URL is a playlist."""
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    return "list" in query_params

def list_formats(url, browser_cookies=None):
    """List available formats for a video, filtering out m3u8 and mp4 formats."""
    command = build_base_command(url, browser_cookies)
    command.extend(["--list-formats", url])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
        # Filter out m3u8 and mp4 formats from the output
        filtered_lines = []
        for line in result.stdout.split('\n'):
            if ('m3u8' not in line.lower() and 'mp4' not in line.lower()) or 'ID' in line or 'format code' in line.lower() or '---' in line:
                filtered_lines.append(line)
        return '\n'.join(filtered_lines)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Error: Failed to list formats.\n{e}")
        return None

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
        print("- Enter a specific format ID (e.g., '137+140' for video+audio)")
        print("- Enter 'best' for automatic best quality")
        print("- Enter 'worst' for lowest quality")
        print("- Enter resolution like '720p', '1080p', etc.")
        
        user_format = safe_input("Format choice: ").strip()
        
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
    """Download video with audio."""
    if output_dir is None:
        output_dir = DEFAULT_VIDEO_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    video_title = safe_input("Video title (or press Enter for auto-generated): ").strip()
    
    # Use auto-generated title if none provided
    output_template = os.path.join(output_dir, f"{video_title}.%(ext)s") if video_title else os.path.join(output_dir, "%(title)s.%(ext)s")
    
    command = build_base_command(url, browser_cookies)
    command.extend([
        "-f", "bestvideo+bestaudio/best",
        "--sponsorblock-remove", "all",
        "--progress",
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "-o", output_template,
        url,
    ])

    try:
        print(f"Downloading video (with audio) from: {url}")
        subprocess.run(command, check=True)
        print(f"Video download complete! Files saved in '{output_dir}'.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to download video.\n{e}")

def download_audio(url, browser_cookies=None, output_dir=None):
    """Download best audio only (e.g. for Music)."""
    if output_dir is None:
        base_output_dir = DEFAULT_MUSIC_DIR
    else:
        base_output_dir = output_dir
    
    # Ask for folder name
    folder_name = safe_input("Enter folder name for this download (not track title, that's next!): ").strip()
    if not folder_name:
        folder_name = "Untitled"
    
    output_dir = os.path.join(base_output_dir, folder_name)
    os.makedirs(output_dir, exist_ok=True)
    
    if is_playlist(url):
        # For playlists, let yt-dlp use automatic titles
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        print(f"Downloading playlist - using automatic track titles in folder '{folder_name}'")
    else:
        # For single tracks, also use automatic title (same as playlists)
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        print(f"Downloading single track - using automatic track title in folder '{folder_name}'")
    
    command = build_base_command(url, browser_cookies)
    command.extend([
        "-f", "bestaudio/best",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--ignore-errors",  # Continue on errors
        "--continue",  # Resume partial downloads
        "--no-warnings",  # Reduce warning messages
        "--progress",  # Show clean progress bar
        "--yes-playlist" if is_playlist(url) else "--no-playlist",
        "-o", output_template,
        url,
    ])
    
    try:
        print(f"Downloading audio from: {url}")
        subprocess.run(command, check=True)
        print(f"Audio download complete! Files saved in '{output_dir}'.")
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

def main():
    if not check_dependencies():
        return
    
    print(f"Default video directory: {DEFAULT_VIDEO_DIR}")
    print(f"Default music directory: {DEFAULT_MUSIC_DIR}")
    print("(You can modify these paths at the top of the script)")
    print("(Enter 99 at any prompt to quit)\n")
    
    # Get browser cookies only when we actually need to use yt-dlp
    browser_cookies = None
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print("What would you like to do?\n")
        print("1. Watch video (stream)")
        print("2. Download video")
        print("3. Download music")
        print("99. Quit\n")
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
            print("99. Quit\n")
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
        print("99. Quit\n")
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
            print("99. Quit\n")
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
