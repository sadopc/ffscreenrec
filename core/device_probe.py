import subprocess
import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from .logger import logger
from .ffmpeg_locator import FFmpegLocator


@dataclass
class VideoDevice:
    name: str
    index: int
    width: int
    height: int
    refresh_rate: int
    is_primary: bool = False
    
    def __str__(self):
        primary = " (Primary)" if self.is_primary else ""
        return f"Display {self.index} ({self.width}×{self.height}@{self.refresh_rate}Hz){primary}"


@dataclass
class AudioDevice:
    name: str
    device_id: str
    is_output: bool  # True for system/loopback, False for microphone
    is_default: bool = False
    
    def __str__(self):
        return self.name


class DeviceProbe:
    def __init__(self, ffmpeg_locator: FFmpegLocator):
        self.ffmpeg = ffmpeg_locator
        self._video_devices: List[VideoDevice] = []
        self._audio_devices: List[AudioDevice] = []
    
    def probe_all(self) -> None:
        self.probe_video_devices()
        self.probe_audio_devices()
    
    def probe_video_devices(self) -> List[VideoDevice]:
        self._video_devices.clear()
        
        # Use tkinter for display detection as it's more reliable
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            width = root.winfo_screenwidth()
            height = root.winfo_screenheight()
            root.destroy()
            
            device = VideoDevice(
                name="Display 1",
                index=0,
                width=width,
                height=height,
                refresh_rate=60,
                is_primary=True
            )
            self._video_devices.append(device)
        except:
            # Fallback to common resolution
            logger.warning("Could not detect display, using default 1920x1080")
            device = VideoDevice(
                name="Display 1",
                index=0,
                width=1920,
                height=1080,
                refresh_rate=60,
                is_primary=True
            )
            self._video_devices.append(device)
        
        logger.info(f"Found {len(self._video_devices)} video devices")
        return self._video_devices
    
    def probe_audio_devices(self) -> List[AudioDevice]:
        self._audio_devices.clear()
        
        if not self.ffmpeg.is_available():
            logger.error("FFmpeg not available for audio device probing")
            return self._audio_devices
        
        # List WASAPI devices using FFmpeg
        try:
            cmd = [
                str(self.ffmpeg.ffmpeg_path),
                "-hide_banner",
                "-list_devices", "true",
                "-f", "dshow",
                "-i", "dummy"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            # Parse the output
            output = result.stderr  # FFmpeg outputs to stderr
            
            # Extract audio devices
            audio_section = False
            for line in output.split('\n'):
                if 'DirectShow audio devices' in line:
                    audio_section = True
                    continue
                elif 'DirectShow video devices' in line:
                    audio_section = False
                    continue
                
                if audio_section:
                    # Look for device lines like: [dshow @ ...] "Microphone (Realtek Audio)"
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        device_name = match.group(1)
                        
                        # Determine if it's output (system) or input (mic)
                        is_output = any(keyword in device_name.lower() 
                                      for keyword in ['stereo mix', 'wave out', 'speakers', 'output'])
                        
                        device = AudioDevice(
                            name=device_name,
                            device_id=device_name,  # For WASAPI, we use the name as ID
                            is_output=is_output,
                            is_default=('default' in device_name.lower())
                        )
                        self._audio_devices.append(device)
            
            # Don't add default device if we couldn't find any
            # The user will need to select a real device from the list
            
        except Exception as e:
            logger.error(f"Failed to probe audio devices: {e}")
            
            # Don't add fallback devices - recording without audio is better than failing
            pass
        
        logger.info(f"Found {len(self._audio_devices)} audio devices")
        return self._audio_devices
    
    def get_video_devices(self) -> List[VideoDevice]:
        if not self._video_devices:
            self.probe_video_devices()
        return self._video_devices
    
    def get_audio_devices(self, output_only=False, input_only=False) -> List[AudioDevice]:
        if not self._audio_devices:
            self.probe_audio_devices()
        
        devices = self._audio_devices
        if output_only:
            devices = [d for d in devices if d.is_output]
        elif input_only:
            devices = [d for d in devices if not d.is_output]
        
        return devices
    
    def refresh(self) -> None:
        self.probe_all()