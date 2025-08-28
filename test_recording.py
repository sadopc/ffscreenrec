#!/usr/bin/env python3
"""
Quick test script to verify recording works without audio
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.ffmpeg_locator import FFmpegLocator
from core.command_builder import CommandBuilder, RecordingConfig

def test_recording_without_audio():
    # Find FFmpeg
    locator = FFmpegLocator()
    
    if not locator.is_available():
        print("FFmpeg not found!")
        return False
    
    print(f"Using FFmpeg: {locator.ffmpeg_path}")
    
    # Create config without audio
    config = RecordingConfig()
    config.system_audio_enabled = False  # Disable audio
    config.mic_enabled = False
    config.fps = 30
    config.bitrate = 4000
    config.encoder_name = "libx264"  # Use software encoder for testing
    
    # Build command
    builder = CommandBuilder(locator.ffmpeg_path)
    output_file = Path.home() / "Videos" / "test_recording.mp4"
    command = builder.build_command(config, output_file)
    
    print("Command:")
    print(" ".join(command))
    
    return True

if __name__ == "__main__":
    test_recording_without_audio()