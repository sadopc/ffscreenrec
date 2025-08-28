import subprocess
import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from enum import Enum
from .logger import logger
from .ffmpeg_locator import FFmpegLocator


class CodecType(Enum):
    H264 = "h264"
    H265 = "h265"
    HEVC = "hevc"
    AV1 = "av1"
    
    def __str__(self):
        if self == CodecType.H265:
            return "HEVC"
        return self.value.upper()


class EncoderVendor(Enum):
    NVIDIA = "nvidia"
    INTEL = "intel"
    AMD = "amd"
    SOFTWARE = "software"


@dataclass
class Encoder:
    name: str
    codec: CodecType
    vendor: EncoderVendor
    is_hardware: bool
    presets: List[str]
    rate_controls: List[str]  # CBR, VBR, CQ, CRF
    
    def __str__(self):
        hw = "HW" if self.is_hardware else "SW"
        return f"{self.codec} ({self.vendor.value.capitalize()} {hw})"
    
    def get_display_name(self):
        if self.vendor == EncoderVendor.SOFTWARE:
            # Differentiate between different software encoders
            if self.name == "libsvtav1":
                return f"{self.codec} (SVT-AV1)"
            elif self.name == "libaom-av1":
                return f"{self.codec} (AOM)"
            else:
                return f"{self.codec} (CPU)"
        else:
            vendor_names = {
                EncoderVendor.NVIDIA: "NVENC",
                EncoderVendor.INTEL: "QSV",
                EncoderVendor.AMD: "AMF"
            }
            return f"{self.codec} ({vendor_names[self.vendor]})"


class EncoderDetector:
    
    # Encoder definitions
    ENCODERS = {
        # NVIDIA NVENC
        "h264_nvenc": Encoder(
            "h264_nvenc", CodecType.H264, EncoderVendor.NVIDIA, True,
            ["p1", "p2", "p3", "p4", "p5", "p6", "p7"],
            ["cbr", "vbr", "cq"]
        ),
        "hevc_nvenc": Encoder(
            "hevc_nvenc", CodecType.H265, EncoderVendor.NVIDIA, True,
            ["p1", "p2", "p3", "p4", "p5", "p6", "p7"],
            ["cbr", "vbr", "cq"]
        ),
        "av1_nvenc": Encoder(
            "av1_nvenc", CodecType.AV1, EncoderVendor.NVIDIA, True,
            ["p1", "p2", "p3", "p4", "p5", "p6", "p7"],
            ["cbr", "vbr", "cq"]
        ),
        
        # Intel QSV
        "h264_qsv": Encoder(
            "h264_qsv", CodecType.H264, EncoderVendor.INTEL, True,
            ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            ["cbr", "vbr", "cqp", "icq", "la_icq"]
        ),
        "hevc_qsv": Encoder(
            "hevc_qsv", CodecType.H265, EncoderVendor.INTEL, True,
            ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            ["cbr", "vbr", "cqp", "icq", "la_icq"]
        ),
        "av1_qsv": Encoder(
            "av1_qsv", CodecType.AV1, EncoderVendor.INTEL, True,
            ["veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            ["cbr", "vbr", "cqp"]
        ),
        
        # AMD AMF
        "h264_amf": Encoder(
            "h264_amf", CodecType.H264, EncoderVendor.AMD, True,
            ["speed", "balanced", "quality"],
            ["cbr", "vbr_peak", "vbr_latency", "cqp"]
        ),
        "hevc_amf": Encoder(
            "hevc_amf", CodecType.H265, EncoderVendor.AMD, True,
            ["speed", "balanced", "quality"],
            ["cbr", "vbr_peak", "vbr_latency", "cqp"]
        ),
        "av1_amf": Encoder(
            "av1_amf", CodecType.AV1, EncoderVendor.AMD, True,
            ["speed", "balanced", "quality"],
            ["cbr", "vbr_peak", "cqp"]
        ),
        
        # Software encoders
        "libx264": Encoder(
            "libx264", CodecType.H264, EncoderVendor.SOFTWARE, False,
            ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            ["crf", "cbr", "vbr"]
        ),
        "libx265": Encoder(
            "libx265", CodecType.H265, EncoderVendor.SOFTWARE, False,
            ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            ["crf", "cbr", "vbr"]
        ),
        "libaom-av1": Encoder(
            "libaom-av1", CodecType.AV1, EncoderVendor.SOFTWARE, False,
            ["0", "1", "2", "3", "4", "5", "6", "7", "8"],
            ["crf", "cbr", "vbr"]
        ),
        "libsvtav1": Encoder(
            "libsvtav1", CodecType.AV1, EncoderVendor.SOFTWARE, False,
            ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
            ["crf", "cbr", "vbr"]
        )
    }
    
    def __init__(self, ffmpeg_locator: FFmpegLocator):
        self.ffmpeg = ffmpeg_locator
        self.available_encoders: Dict[str, Encoder] = {}
        self._detected = False
    
    def detect_encoders(self) -> Dict[str, Encoder]:
        if self._detected:
            return self.available_encoders
        
        self.available_encoders.clear()
        
        if not self.ffmpeg.is_available():
            logger.error("FFmpeg not available for encoder detection")
            # Add software encoders as fallback
            for name, encoder in self.ENCODERS.items():
                if encoder.vendor == EncoderVendor.SOFTWARE:
                    self.available_encoders[name] = encoder
            return self.available_encoders
        
        try:
            # Get list of encoders from FFmpeg
            cmd = [str(self.ffmpeg.ffmpeg_path), "-hide_banner", "-encoders"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                output = result.stdout
                
                # Check each known encoder
                for encoder_name, encoder_info in self.ENCODERS.items():
                    # Look for encoder in output
                    pattern = rf"^\s*V[^\s]*\s+{re.escape(encoder_name)}\s+"
                    if re.search(pattern, output, re.MULTILINE):
                        # Test if encoder is actually usable
                        if self._test_encoder(encoder_name):
                            self.available_encoders[encoder_name] = encoder_info
                            logger.info(f"Detected encoder: {encoder_name}")
                        else:
                            logger.debug(f"Encoder listed but not usable: {encoder_name}")
        
        except Exception as e:
            logger.error(f"Failed to detect encoders: {e}")
        
        # Always ensure software encoders are available as fallback
        if "libx264" not in self.available_encoders:
            self.available_encoders["libx264"] = self.ENCODERS["libx264"]
        
        self._detected = True
        logger.info(f"Total available encoders: {len(self.available_encoders)}")
        return self.available_encoders
    
    def _test_encoder(self, encoder_name: str) -> bool:
        """Test if an encoder actually works"""
        try:
            # Create a minimal test command
            cmd = [
                str(self.ffmpeg.ffmpeg_path),
                "-f", "lavfi",
                "-i", "testsrc=duration=0.1:size=320x240:rate=1",
                "-c:v", encoder_name,
                "-pix_fmt", "yuv420p",  # Required for hardware encoders
                "-frames:v", "1",
                "-f", "null",
                "-"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=5,
                check=False
            )
            
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"Encoder test failed for {encoder_name}: {e}")
            return False
    
    def get_available_by_codec(self, codec: CodecType) -> List[Encoder]:
        """Get all available encoders for a specific codec"""
        if not self._detected:
            self.detect_encoders()
        
        return [enc for enc in self.available_encoders.values() if enc.codec == codec]
    
    def get_hardware_encoders(self) -> List[Encoder]:
        """Get all available hardware encoders"""
        if not self._detected:
            self.detect_encoders()
        
        return [enc for enc in self.available_encoders.values() if enc.is_hardware]
    
    def get_best_encoder(self, codec: CodecType, prefer_hardware: bool = True) -> Optional[Encoder]:
        """Get the best available encoder for a codec"""
        encoders = self.get_available_by_codec(codec)
        
        if not encoders:
            return None
        
        if prefer_hardware:
            # Prefer hardware encoders in order: NVIDIA > Intel > AMD > Software
            priority = [EncoderVendor.NVIDIA, EncoderVendor.INTEL, 
                       EncoderVendor.AMD, EncoderVendor.SOFTWARE]
            
            for vendor in priority:
                for enc in encoders:
                    if enc.vendor == vendor:
                        return enc
        
        # Return first available
        return encoders[0] if encoders else None
    
    def refresh(self) -> None:
        """Re-detect encoders"""
        self._detected = False
        self.detect_encoders()