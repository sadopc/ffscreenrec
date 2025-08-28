"""
FFmpeg locator module for FFScreenRec

Copyright 2024 FFScreenRec Contributors
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from .logger import logger


class FFmpegLocator:
    def __init__(self):
        self.ffmpeg_path: Optional[Path] = None
        self.ffprobe_path: Optional[Path] = None
        self._locate_ffmpeg()
    
    def _locate_ffmpeg(self) -> None:
        # Check bundled location first (for PyInstaller)
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent.parent
        
        bundled_ffmpeg = base_path / "assets" / "ffmpeg.exe"
        bundled_ffprobe = base_path / "assets" / "ffprobe.exe"
        
        if bundled_ffmpeg.exists() and bundled_ffprobe.exists():
            self.ffmpeg_path = bundled_ffmpeg
            self.ffprobe_path = bundled_ffprobe
            logger.info(f"Using bundled FFmpeg from {bundled_ffmpeg}")
            return
        
        # Check system PATH
        ffmpeg_system = shutil.which("ffmpeg")
        ffprobe_system = shutil.which("ffprobe")
        
        if ffmpeg_system and ffprobe_system:
            self.ffmpeg_path = Path(ffmpeg_system)
            self.ffprobe_path = Path(ffprobe_system)
            logger.info(f"Using system FFmpeg from {ffmpeg_system}")
            return
        
        # Check common installation locations on Windows
        common_paths = [
            Path("C:/ffmpeg/bin"),
            Path("C:/Program Files/ffmpeg/bin"),
            Path("C:/Program Files (x86)/ffmpeg/bin"),
            Path.home() / "ffmpeg" / "bin"
        ]
        
        for path in common_paths:
            ffmpeg_exe = path / "ffmpeg.exe"
            ffprobe_exe = path / "ffprobe.exe"
            if ffmpeg_exe.exists() and ffprobe_exe.exists():
                self.ffmpeg_path = ffmpeg_exe
                self.ffprobe_path = ffprobe_exe
                logger.info(f"Found FFmpeg in {path}")
                return
        
        logger.warning("FFmpeg not found in standard locations")
    
    def is_available(self) -> bool:
        return self.ffmpeg_path is not None and self.ffmpeg_path.exists()
    
    def get_version(self) -> Optional[str]:
        if not self.is_available():
            return None
        
        try:
            result = subprocess.run(
                [str(self.ffmpeg_path), "-version"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if lines:
                    return lines[0].strip()
        except Exception as e:
            logger.error(f"Failed to get FFmpeg version: {e}")
        
        return None
    
    def prompt_for_location(self) -> Optional[Path]:
        # This will be called from UI if FFmpeg not found
        pass