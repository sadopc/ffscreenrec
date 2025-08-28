# FFScreenRec

A modern Python GUI screen recorder for Windows with hardware acceleration, live preview, and audio mixing.

## Features

### Video Recording
- **Hardware-accelerated encoding** with NVIDIA NVENC, Intel QSV, and AMD AMF
- **Multiple codec support**: H.264, H.265 (HEVC), and AV1
- **Screen capture modes**: Full desktop, specific monitor, or custom region
- **Live preview** with low-latency display
- **Configurable frame rates** from 1-144 FPS
- **Optional cursor capture**
- **Video scaling** to any resolution (4K, 1440p, 1080p, 720p, custom)

### Audio Recording
- **System audio capture** via WASAPI loopback
- **Microphone recording** with device selection
- **Audio mixing** with automatic normalization
- **Configurable bitrate and sample rate**

### Encoding Options
- **Rate control modes**: CBR, VBR, CRF/CQ
- **Customizable bitrate** with buffer control
- **Adjustable GOP/keyframe interval**
- **Profile selection** (baseline, main, high)
- **Hardware encoder auto-detection**
- **Automatic software fallback**

### Output Formats
- **Container formats**: MP4, MKV, MOV
- **Fast-start optimization** for MP4
- **Custom filename patterns** with date/time/codec/resolution placeholders
- **Configurable output directory**

### User Interface
- **Dark theme** with gray color scheme
- **Embedded live preview** (no separate window)
- **Real-time recording statistics** (duration, file size, FPS, dropped frames)
- **Recording profiles** for quick setup
- **Settings persistence** across sessions

## Requirements

- Windows 10/11 (64-bit)
- Python 3.11 or higher
- FFmpeg (bundled or system-installed)
- DirectX 11 capable GPU (for hardware encoding)
- 8GB RAM recommended
- 1GB free disk space for installation

## Installation

### From Source

1. Clone the repository:
```bash
git clone https://github.com/sadopc/ffscreenrec.git
cd ffscreenrec
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

### Pre-built Executable

Download the latest release from the [Releases](https://github.com/sadopc/ffscreenrec/releases) page and run `FFScreenRec.exe`.

## FFmpeg Setup

The application requires FFmpeg to function. You have three options:

1. **Bundled**: Place `ffmpeg.exe` and `ffprobe.exe` in the `assets` folder
2. **System PATH**: Install FFmpeg and add it to your system PATH
3. **Custom location**: The app will prompt you to select FFmpeg location on first run

Download FFmpeg from: https://ffmpeg.org/download.html

## Usage

### Quick Start

1. Launch FFScreenRec
2. Select your video source (monitor or region)
3. Choose a recording profile or customize settings
4. Click "Start Recording" (or press Ctrl+R)
5. Click "Stop Recording" (or press Ctrl+S) when done
6. Find your recording in the output folder

### Recording Profiles

Pre-configured profiles for common use cases:

- **1080p60 Streaming**: Optimized for live streaming (H.264, 8 Mbps CBR)
- **1440p60 Gaming**: High-quality gaming capture (H.264/HEVC, 14 Mbps CBR)
- **4K30 Quality**: Maximum quality recording (HEVC, 32 Mbps CBR)

### Keyboard Shortcuts

- `Ctrl+R`: Start recording
- `Ctrl+S`: Stop recording
- `Ctrl+Q`: Exit application

### Advanced Settings

#### Video Settings
- **Codec**: Select based on your hardware capabilities
- **Preset**: Balance between encoding speed and quality
- **Rate Control**: CBR for consistent bitrate, VBR for better quality, CRF for size/quality balance
- **Bitrate**: Higher = better quality but larger files
- **GOP**: Keyframe interval (lower = better seeking, higher = better compression)

#### Audio Settings
- **System Audio**: Records desktop sound (games, videos, music)
- **Microphone**: Records voice input
- **Mix**: Combines both sources with optional normalization

## Troubleshooting

### FFmpeg Not Found
- Download FFmpeg from the official website
- Place in `assets` folder or add to PATH
- Restart the application

### No Hardware Encoders Detected
- Update GPU drivers to latest version
- Ensure hardware encoding is enabled in GPU settings
- Application will automatically fall back to software encoding

### Recording Fails to Start
- Check available disk space
- Verify output directory is writable
- Try software encoder (libx264) as fallback
- Check Windows audio privacy settings for audio recording

### Poor Performance
- Lower recording resolution or frame rate
- Use hardware encoder if available
- Close unnecessary applications
- Disable preview during recording

### Audio Not Recording
- Check Windows sound settings
- Ensure correct audio devices are selected
- Verify application has microphone permissions
- Try refreshing audio devices in the app

## Building from Source

### Create Executable

```bash
pip install pyinstaller
pyinstaller ffscreenrec.spec
```

The executable will be created in the `dist` folder.

### Running Tests

```bash
python -m pytest tests/
```

Or run specific tests:
```bash
python tests/test_command_builder.py
python tests/test_encoder_detect.py
```

## Configuration

Settings are stored in `%APPDATA%\FFScreenRec\settings.json`

### File Naming Pattern

Use these placeholders in the filename pattern:
- `{date}`: Current date (YYYYMMDD)
- `{time}`: Current time (HHMMSS)
- `{codec}`: Video codec used
- `{res}`: Output resolution
- `{fps}`: Frame rate

Example: `{date}_{time}_{codec}_{res}_{fps}fps` produces `20240327_143022_h264_1920x1080_60fps.mp4`

## Known Issues

- Region selection may not work correctly with multiple DPI settings
- Some USB microphones may not appear in device list
- Preview framerate limited to 30 FPS to reduce CPU usage
- AV1 encoding significantly slower than H.264/H.265

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

### Third-Party Components

- **FFmpeg**: Licensed under GPL/LGPL (included as separate binary)
- **PySide6**: Licensed under LGPL  
- **Python Libraries**: Various open-source licenses (see requirements.txt)

The FFmpeg binary is included as a separate executable and is not linked to this application. Users should comply with FFmpeg's licensing terms.

## Credits

- FFmpeg: https://ffmpeg.org/
- PySide6: https://doc.qt.io/qtforpython/
- Icons from: [Icon source]

## Support

For issues, feature requests, or questions:
- Open an issue on [GitHub](https://github.com/sadopc/ffscreenrec/issues)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Disclaimer

This software is provided "as is" without warranty of any kind. Screen recording may be subject to local laws and platform terms of service. Users are responsible for complying with applicable regulations.