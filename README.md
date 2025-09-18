# YouTube Downloader & Streamer

A Python script for downloading and streaming YouTube videos using yt-dlp. Supports video downloads, audio extraction, and direct streaming to media players.

## Features

- **Stream videos directly** to VLC or other media players without downloading
- **Download videos** in various formats with audio
- **Extract audio only** (MP3 format) for music
- **Download video without audio** for specific use cases
- **Automatic browser cookie detection** for accessing private/restricted videos *1
- **Cross-platform support** for Windows, macOS, and Linux
- **Smart media player detection** - tries VLC first, falls back to system defaults
- **SponsorBlock integration** - automatically removes sponsored segments
- **Playlist support** - handle single videos or entire playlists

## Cookies are tricky! *1

A note on cookies: I have put some basic searches in the script to find & use the cookies from your browser, but this will likely fail. If you want to download a video that is behind a login, such as a friend's video on Insta, follow the instructions on [this page](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp) to add the neccessary code.

## Requirements

- Python 3.6 or higher
- yt-dlp: `pip install yt-dlp`
- A media player (VLC recommended, or system default)

## Installation

1. Install Python 3.6+ from [python.org](https://python.org)
2. Install yt-dlp:
   ```bash
   pip install yt-dlp
   ```
3. Download the script to a directory in your PATH (e.g., `/usr/local/bin/` on Unix systems)
4. Make it executable and rename it for easy access:
   ```bash
   chmod +x /path/to/youtube_downloader.py
   mv /path/to/youtube_downloader.py /usr/local/bin/download
   ```
5. (Optional) Install VLC for best streaming experience

Now you can use the script from anywhere by simply typing:
```bash
download "https://youtube.com/watch?v=..."
```

### Alternative Installation (if you don't have PATH access)

If you can't modify system directories, you can create an alias in your shell:
```bash
# Add this to your ~/.bashrc, ~/.zshrc, or equivalent
alias download='/full/path/to/youtube_downloader.py'
```

## Usage

### Quick Command (after installation)
```bash
download "https://youtube.com/watch?v=..."
```

### Interactive Mode
```bash
download
```
Follow the prompts to select download type and enter URL.

### Traditional Python Mode
```bash
python youtube_downloader.py "https://youtube.com/watch?v=..."
```

## Download Options

**Video Downloads:**
- Video with audio (standard download)
- Video only (no audio track)
- Audio only (extracted as MP3)

**Audio Downloads:**
- High-quality MP3 extraction
- Automatic metadata preservation

**Streaming:**
- Direct playback without downloading
- Format selection for quality control
- Automatic media player detection

## Configuration

Default download locations:
- Videos: `~/Videos/youtube-downloads`
- Music: `~/Music/youtube-downloads`

You can modify these paths by editing the variables at the top of the script.

## Browser Support

The script automatically detects cookies from common browsers:
- Chrome/Chromium
- Firefox
- Safari (macOS)
- Microsoft Edge
- Brave

This allows access to videos that require login or are region-restricted.

## Troubleshooting

**"python not found"**: Ensure Python is installed and added to system PATH

**"yt-dlp not found"**: Try `python -m pip install yt-dlp` instead of `pip install yt-dlp`

**"No media player found"**: Install VLC from [videolan.org](https://www.videolan.org/vlc/) or ensure you have a default video player set

**Videos won't stream**: Some networks block YouTube traffic - try a different network or VPN

**Permission errors**: Ensure you have write access to your home directory

## License

This script is provided as-is for personal use. Respect YouTube's Terms of Service and copyright laws when using this tool.

## Support
If you would like to help me out, I have a stripe account set up which can securely accept payments,[here ](https://buy.stripe.com/14A5kDgJ87vFh2I2nQ5J607).  
  
Or, if you'd rather, you can scan this QR code:  
  
<img width="25%" alt="image" src="https://github.com/user-attachments/assets/72b7d81a-9db0-4d44-825a-db98b7100dcb" />
