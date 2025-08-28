import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from .logger import logger
from .command_builder import RecordingConfig, RateControl, Container
from .encoder_detect import CodecType


@dataclass
class AppSettings:
    # Window settings
    window_geometry: Dict[str, int] = field(default_factory=lambda: {
        "x": 100, "y": 100, "width": 1200, "height": 700
    })
    
    # Default recording config
    default_config: Dict[str, Any] = field(default_factory=lambda: {
        "monitor_index": 0,
        "fps": 60,
        "show_cursor": True,
        "encoder_name": "libx264",
        "preset": "veryfast",
        "rate_control": "cbr",
        "bitrate": 8000,
        "max_bitrate": 8000,
        "buffer_size": 16000,
        "crf": 23,
        "keyframe_interval": 120,
        "profile": "high",
        "system_audio_enabled": True,
        "system_audio_device": "default",
        "mic_enabled": False,
        "mic_device": "",
        "audio_bitrate": 160,
        "audio_sample_rate": 48000,
        "audio_channels": 2,
        "normalize_audio": True,
        "container": "mp4",
        "file_pattern": "{date}_{time}_{codec}_{res}_{fps}fps",
        "segment_minutes": None
    })
    
    # Output path
    output_path: str = field(default_factory=lambda: str(Path.home() / "Videos" / "ScreenRec"))
    
    # Recent files
    recent_files: list = field(default_factory=list)
    max_recent_files: int = 10
    
    # FFmpeg path (if custom)
    ffmpeg_path: Optional[str] = None
    
    # First run flag
    first_run: bool = True
    
    # Preferred encoders by codec
    preferred_encoders: Dict[str, str] = field(default_factory=dict)


class SettingsProfile:
    def __init__(self, name: str, config: RecordingConfig):
        self.name = name
        self.config = config


class SettingsManager:
    
    DEFAULT_PROFILES = {
        "1080p60 Streaming": {
            "scale": (1920, 1080),
            "fps": 60,
            "encoder_name": "h264_nvenc",
            "preset": "p5",
            "rate_control": "cbr",
            "bitrate": 8000,
            "max_bitrate": 8000,
            "buffer_size": 16000,
            "keyframe_interval": 120,
            "profile": "high"
        },
        "1440p60 Gaming": {
            "scale": (2560, 1440),
            "fps": 60,
            "encoder_name": "h264_nvenc",
            "preset": "p5",
            "rate_control": "cbr",
            "bitrate": 14000,
            "max_bitrate": 14000,
            "buffer_size": 28000,
            "keyframe_interval": 120,
            "profile": "high"
        },
        "4K30 Quality": {
            "scale": (3840, 2160),
            "fps": 30,
            "encoder_name": "hevc_nvenc",
            "preset": "p5",
            "rate_control": "cbr",
            "bitrate": 32000,
            "max_bitrate": 32000,
            "buffer_size": 64000,
            "keyframe_interval": 60,
            "profile": "main10" if "10" in "main10" else "main"
        }
    }
    
    def __init__(self):
        self.settings_dir = Path(os.getenv('APPDATA')) / "FFScreenRec"
        self.settings_file = self.settings_dir / "settings.json"
        self.profiles_file = self.settings_dir / "profiles.json"
        self.settings = AppSettings()
        self.custom_profiles: Dict[str, Dict] = {}
        
        self._ensure_settings_dir()
        self.load()
    
    def _ensure_settings_dir(self):
        self.settings_dir.mkdir(parents=True, exist_ok=True)
    
    def load(self):
        # Load main settings
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    
                    # Update settings with loaded data
                    for key, value in data.items():
                        if hasattr(self.settings, key):
                            setattr(self.settings, key, value)
                    
                    self.settings.first_run = False
                    logger.info("Settings loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
        
        # Load custom profiles
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file, 'r') as f:
                    self.custom_profiles = json.load(f)
                    logger.info(f"Loaded {len(self.custom_profiles)} custom profiles")
            except Exception as e:
                logger.error(f"Failed to load profiles: {e}")
    
    def save(self):
        try:
            # Save main settings
            with open(self.settings_file, 'w') as f:
                json.dump(asdict(self.settings), f, indent=2)
            
            # Save custom profiles
            with open(self.profiles_file, 'w') as f:
                json.dump(self.custom_profiles, f, indent=2)
            
            logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def get_recording_config(self) -> RecordingConfig:
        """Create RecordingConfig from current settings"""
        config = RecordingConfig()
        
        # Apply default config
        for key, value in self.settings.default_config.items():
            if hasattr(config, key):
                # Convert string enums back to enum types
                if key == "rate_control":
                    value = RateControl[value.upper()]
                elif key == "container":
                    value = Container[value.upper()]
                elif key == "output_path":
                    value = Path(value)
                
                setattr(config, key, value)
        
        # Set output path
        config.output_path = Path(self.settings.output_path)
        
        return config
    
    def update_recording_config(self, config: RecordingConfig):
        """Update settings from RecordingConfig"""
        # Convert config to dict
        config_dict = {}
        
        for key in self.settings.default_config.keys():
            if hasattr(config, key):
                value = getattr(config, key)
                
                # Convert enums to strings
                if isinstance(value, (RateControl, Container)):
                    value = value.value
                elif isinstance(value, Path):
                    value = str(value)
                
                config_dict[key] = value
        
        self.settings.default_config = config_dict
        self.settings.output_path = str(config.output_path)
    
    def add_recent_file(self, file_path: Path):
        """Add a file to recent files list"""
        file_str = str(file_path)
        
        # Remove if already exists
        if file_str in self.settings.recent_files:
            self.settings.recent_files.remove(file_str)
        
        # Add to beginning
        self.settings.recent_files.insert(0, file_str)
        
        # Limit list size
        if len(self.settings.recent_files) > self.settings.max_recent_files:
            self.settings.recent_files = self.settings.recent_files[:self.settings.max_recent_files]
        
        self.save()
    
    def get_all_profiles(self) -> Dict[str, Dict]:
        """Get all profiles (default + custom)"""
        profiles = self.DEFAULT_PROFILES.copy()
        profiles.update(self.custom_profiles)
        return profiles
    
    def save_custom_profile(self, name: str, config: RecordingConfig):
        """Save a custom profile"""
        profile_dict = {}
        
        # Convert config to dict for relevant fields
        for key in ["scale", "fps", "encoder_name", "preset", "rate_control",
                   "bitrate", "max_bitrate", "buffer_size", "keyframe_interval", "profile"]:
            if hasattr(config, key):
                value = getattr(config, key)
                if isinstance(value, RateControl):
                    value = value.value
                profile_dict[key] = value
        
        self.custom_profiles[name] = profile_dict
        self.save()
    
    def delete_custom_profile(self, name: str) -> bool:
        """Delete a custom profile"""
        if name in self.custom_profiles:
            del self.custom_profiles[name]
            self.save()
            return True
        return False
    
    def apply_profile(self, profile_name: str, config: RecordingConfig) -> bool:
        """Apply a profile to a RecordingConfig"""
        profiles = self.get_all_profiles()
        
        if profile_name not in profiles:
            return False
        
        profile = profiles[profile_name]
        
        for key, value in profile.items():
            if hasattr(config, key):
                # Convert string enums back to enum types
                if key == "rate_control":
                    value = RateControl[value.upper()]
                
                setattr(config, key, value)
        
        return True
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = AppSettings()
        self.custom_profiles.clear()
        self.save()