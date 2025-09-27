# Video Downloader, Streamer, & Basic Editor

A Python script for downloading and streaming videos from sites such as YouTueb, Facebook, Instagram, Reddit, and music from sites such as YouTube Music using yt-dlp. Supports video downloads, audio extraction, and direct streaming to media players. Now with some basic ffmpeg editing tools.

## Features

- **Stream videos directly** to VLC or other media players without downloading
- **Download videos** in various formats with audio
- **Extract audio only** (MP3 format) for music
- **Download video without audio** for specific use cases
- **Smart media player detection** - tries VLC first, falls back to system defaults
- **SponsorBlock integration** - automatically removes sponsored segments
- **Playlist support** - handle single videos or entire playlists
- **Livestreams!** It now detects if you are trying to watch/download a livestream.

## Editing Tools

So far, the following are available:

- Trim video (keep original quality)
- Transcode video (change quality/codec)
- Convert format only (no quality change)
- Convert to GIF
- Add black bars for Instagram (post/reel/story)

With more to come!

You can select a video file by one of the following methods:

- Recent downloads (previous 20)
- Browse specific folder
- Enter file path manually

## Removed auto cookie passing for Youtube URLs.

I have decided to change the code that passes cookies automatically as I found out youtube bans accounts if they download too much. It still passes cooking/credentials to social media so yout can download from those, but nothing is passed to youtube. Fuck youtube. 

Instructions on [this page](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp) to add the necessary code if you want to add cookies to dowload from social media platforms.

## Requirements

- Python 3.6 or higher
- yt-dlp: Will install when you run setup.sh if it is not already installed. (Ensure to keep up to date with the most recent nightly builds!)
- A media player (VLC is recommended, or system default)

## Installation

0.5. Install Python 3.6+ from [python.org](https://python.org)
1. In terminal, go to whichever directory you want to install it.
2. Run this to take care of the installation and file permissions:
 ```
  git clone https://github.com/TurbulentGoat/loutube.git && \
  cd loutube && \
  chmod +x setup.sh && \
  ./setup.sh
 ```
Now you can use the script from anywhere by simply typing, for example:
  ```bash
  loutube "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  ```

## Usage

### Quick Command (after installation)
```bash
loutube "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
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

## Additional useful commands:  
`loutube --help      # Show detailed help`  
`loutube --recent    # Show recent downloads`  
`loutube --config    # Show current configuration`  

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

**"No media player found"**: Install VLC from [videolan.org](https://www.videolan.org/vlc/) or ensure you have a default video player set

**Videos won't stream**: Some networks block YouTube traffic - try a different network or VPN

**Permission errors**: Ensure you have write access to your home directory

## License

This script is provided as-is for personal use. Respect YouTube's Terms of Service and copyright laws when using this tool.

## Support
If you would like to help me out, I have a stripe account set up which can securely accept payments,[here ](https://buy.stripe.com/14A5kDgJ87vFh2I2nQ5J607).  
  
Or, if you'd rather, you can scan this QR code:  
  
<img width="20%" alt="image" src="https://github.com/user-attachments/assets/72b7d81a-9db0-4d44-825a-db98b7100dcb" />
