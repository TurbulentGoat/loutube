<img width="1281" height="675" alt="image" src="https://github.com/user-attachments/assets/4474a94c-28c5-463d-aab6-6869d167f184" />
  
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
- Automatic media player detection
- Format selection for quality control
- You'll see this screen when you select to stream a video:
  
  <img size=50% alt="image" src="https://github.com/user-attachments/assets/fd03c79f-57e3-4c82-b877-b9a26f86d235" />

- In the screenshot above, the green column, labelled 1, shows the resolution. The further down the list it is, the higher the res. Generally the most important decider!
- The orange columns (labelled 2 & 3) display the file type as in audio or video. You need one of each!
- Then, in the red column (labelled number 3) is the ID. This contains the numbers you will use to choose the resolution.
- The one column left out just shows the size of the file.
- Sometimes a video will show no format options, so just press enter and it will attempt the default "best" choices.  
(I've only noticed this sometimes with instagram reels.)
  
  Once you have decided on a resolution you want to play, and you have settled on one video and one audio track, type e.g. 303+251, then enter. I always choose 1080p as that's the max res of my screens.  
## Configuration

Default download locations:
- Videos: `~/Videos/ytd-video`
- Music: `~/Music/ytd-music`

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
  
<img width="20%" alt="image" src="https://github.com/user-attachments/assets/72b7d81a-9db0-4d44-825a-db98b7100dcb" />
