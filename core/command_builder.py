from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from .logger import logger
from .encoder_detect import Encoder, CodecType, EncoderVendor


class RateControl(Enum):
    CBR = "cbr"
    VBR = "vbr"
    CRF = "crf"
    CQ = "cq"


class Container(Enum):
    MP4 = "mp4"
    MKV = "mkv"
    MOV = "mov"


@dataclass
class RecordingConfig:
    # Video source
    monitor_index: int = 0
    region: Optional[Tuple[int, int, int, int]] = None  # x, y, width, height
    fps: int = 60
    show_cursor: bool = True
    
    # Video encoding
    encoder: Optional[Encoder] = None
    encoder_name: str = "libx264"
    preset: str = "veryfast"
    rate_control: RateControl = RateControl.CBR
    bitrate: int = 8000  # kbps
    max_bitrate: int = 8000  # kbps
    buffer_size: int = 16000  # kbps
    crf: int = 23
    keyframe_interval: int = 120  # frames (2 seconds at 60fps)
    profile: str = "high"
    scale: Optional[Tuple[int, int]] = None  # output width, height
    
    # Audio
    system_audio_enabled: bool = True
    system_audio_device: str = "default"
    mic_enabled: bool = False
    mic_device: str = ""
    audio_bitrate: int = 160  # kbps
    audio_sample_rate: int = 48000
    audio_channels: int = 2
    normalize_audio: bool = True
    
    # Output
    container: Container = Container.MP4
    output_path: Path = Path.home() / "Videos" / "ScreenRec"
    file_pattern: str = "{date}_{time}_{codec}_{res}_{fps}fps"
    segment_minutes: Optional[int] = None


class CommandBuilder:
    
    def __init__(self, ffmpeg_path: Path):
        self.ffmpeg_path = ffmpeg_path
    
    def build_command(self, config: RecordingConfig, output_file: Path) -> List[str]:
        cmd = [str(self.ffmpeg_path)]
        
        # Add video input
        cmd.extend(self._build_video_input(config))
        
        # Add audio inputs
        audio_inputs, audio_filter = self._build_audio_inputs(config)
        cmd.extend(audio_inputs)
        
        # Add complex filter if needed (for audio mixing)
        if audio_filter:
            cmd.extend(["-filter_complex", audio_filter])
        
        # Add video filter (scaling)
        video_filter = self._build_video_filter(config)
        if video_filter:
            cmd.extend(["-vf", video_filter])
        
        # Add mappings
        mappings = self._build_mappings(config, bool(audio_filter))
        cmd.extend(mappings)
        
        # Add video encoder
        cmd.extend(self._build_video_encoder(config))
        
        # Add audio encoder
        cmd.extend(self._build_audio_encoder(config))
        
        # Add container-specific options
        cmd.extend(self._build_container_options(config))
        
        # Add segmenting if needed
        if config.segment_minutes:
            cmd.extend(self._build_segment_options(config))
        
        # Add output file
        cmd.append(str(output_file))
        
        logger.debug(f"Built command: {' '.join(cmd)}")
        return cmd
    
    def _build_video_input(self, config: RecordingConfig) -> List[str]:
        # Use gdigrab which is more widely available than d3d11grab
        args = ["-f", "gdigrab"]
        args.extend(["-framerate", str(config.fps)])
        
        if config.region:
            x, y, w, h = config.region
            args.extend(["-offset_x", str(x), "-offset_y", str(y)])
            args.extend(["-video_size", f"{w}x{h}"])
        
        args.extend(["-draw_mouse", "1" if config.show_cursor else "0"])
        args.extend(["-i", "desktop"])
        
        return args
    
    def _build_audio_inputs(self, config: RecordingConfig) -> Tuple[List[str], str]:
        args = []
        filter_complex = ""
        
        audio_inputs = []
        input_index = 1  # 0 is video, audio starts at 1
        
        if config.system_audio_enabled:
            # For Windows audio capture
            if config.system_audio_device == "default" or not config.system_audio_device:
                # Skip audio if no valid device specified
                # We'll add a workaround by not including audio for now
                logger.warning("Default audio device not properly configured, skipping audio")
            else:
                # Use the actual device name with dshow
                args.extend(["-f", "dshow", "-i", f"audio={config.system_audio_device}"])
                audio_inputs.append(input_index)
                input_index += 1
        
        if config.mic_enabled and config.mic_device:
            args.extend(["-f", "wasapi", "-i", config.mic_device])
            audio_inputs.append(input_index)
            input_index += 1
        
        # Build filter complex for mixing if we have multiple audio inputs
        if len(audio_inputs) > 1:
            inputs_str = "".join([f"[{i}:a]" for i in audio_inputs])
            filter_parts = [
                f"{inputs_str}amix=inputs={len(audio_inputs)}:duration=longest:dropout_transition=3"
            ]
            
            if config.normalize_audio:
                filter_parts.append("dynaudnorm=f=150:g=31")
            
            filter_complex = ",".join(filter_parts) + "[aout]"
        
        return args, filter_complex
    
    def _build_video_filter(self, config: RecordingConfig) -> str:
        filters = []
        
        if config.scale:
            w, h = config.scale
            filters.append(f"scale={w}:{h}:flags=bicubic")
        
        return ",".join(filters) if filters else ""
    
    def _build_mappings(self, config: RecordingConfig, has_audio_filter: bool) -> List[str]:
        args = ["-map", "0:v"]  # Always map video from first input
        
        if has_audio_filter:
            args.extend(["-map", "[aout]"])
        elif config.system_audio_enabled or config.mic_enabled:
            # Map first audio stream
            args.extend(["-map", "1:a"])
        
        return args
    
    def _build_video_encoder(self, config: RecordingConfig) -> List[str]:
        encoder = config.encoder or self._get_encoder_by_name(config.encoder_name)
        
        if not encoder:
            # Fallback to libx264
            return self._build_libx264_encoder(config)
        
        if encoder.vendor == EncoderVendor.NVIDIA:
            return self._build_nvenc_encoder(config, encoder)
        elif encoder.vendor == EncoderVendor.INTEL:
            return self._build_qsv_encoder(config, encoder)
        elif encoder.vendor == EncoderVendor.AMD:
            return self._build_amf_encoder(config, encoder)
        else:
            return self._build_software_encoder(config, encoder)
    
    def _build_nvenc_encoder(self, config: RecordingConfig, encoder: Encoder) -> List[str]:
        args = ["-c:v", encoder.name]
        args.extend(["-preset", config.preset])
        args.extend(["-tune", "hq"])
        
        if config.rate_control == RateControl.CBR:
            args.extend(["-rc", "cbr"])
            args.extend(["-b:v", f"{config.bitrate}k"])
            args.extend(["-maxrate", f"{config.max_bitrate}k"])
            args.extend(["-bufsize", f"{config.buffer_size}k"])
        elif config.rate_control == RateControl.VBR:
            args.extend(["-rc", "vbr"])
            args.extend(["-b:v", f"{config.bitrate}k"])
            args.extend(["-maxrate", f"{config.max_bitrate}k"])
        elif config.rate_control == RateControl.CQ:
            args.extend(["-rc", "constqp"])
            args.extend(["-cq", str(config.crf)])
        
        args.extend(["-g", str(config.keyframe_interval)])
        
        # AV1 doesn't support these options
        if encoder.codec != CodecType.AV1:
            args.extend(["-bf", "2"])
            args.extend(["-spatial-aq", "1"])
            args.extend(["-aq-strength", "8"])
        
        if encoder.codec == CodecType.H264:
            args.extend(["-profile:v", config.profile])
        
        args.extend(["-pix_fmt", "yuv420p"])
        
        return args
    
    def _build_qsv_encoder(self, config: RecordingConfig, encoder: Encoder) -> List[str]:
        args = ["-c:v", encoder.name]
        args.extend(["-preset:v", config.preset])
        
        if config.rate_control == RateControl.CBR:
            args.extend(["-b:v", f"{config.bitrate}k"])
            args.extend(["-maxrate", f"{config.max_bitrate}k"])
            args.extend(["-bufsize", f"{config.buffer_size}k"])
        else:
            args.extend(["-global_quality", "26"])
        
        args.extend(["-look_ahead", "1"])
        args.extend(["-g", str(config.keyframe_interval)])
        args.extend(["-pix_fmt", "nv12"])
        
        return args
    
    def _build_amf_encoder(self, config: RecordingConfig, encoder: Encoder) -> List[str]:
        args = ["-c:v", encoder.name]
        args.extend(["-quality", config.preset])
        
        if config.rate_control == RateControl.CBR:
            args.extend(["-rc", "cbr"])
            args.extend(["-vb", f"{config.bitrate}k"])
        else:
            args.extend(["-rc", "vbr_peak"])
            args.extend(["-vb", f"{config.bitrate}k"])
        
        args.extend(["-g", str(config.keyframe_interval)])
        args.extend(["-pix_fmt", "yuv420p"])
        
        return args
    
    def _build_software_encoder(self, config: RecordingConfig, encoder: Encoder) -> List[str]:
        if encoder.name == "libx264":
            return self._build_libx264_encoder(config)
        elif encoder.name == "libx265":
            return self._build_libx265_encoder(config)
        elif encoder.name == "libsvtav1":
            return self._build_libsvtav1_encoder(config)
        else:
            return self._build_libaom_encoder(config)
    
    def _build_libx264_encoder(self, config: RecordingConfig) -> List[str]:
        args = ["-c:v", "libx264"]
        args.extend(["-preset", config.preset])
        
        if config.rate_control == RateControl.CRF:
            args.extend(["-crf", str(config.crf)])
        else:
            args.extend(["-b:v", f"{config.bitrate}k"])
            args.extend(["-maxrate", f"{config.max_bitrate}k"])
            args.extend(["-bufsize", f"{config.buffer_size}k"])
        
        args.extend(["-profile:v", config.profile])
        args.extend(["-g", str(config.keyframe_interval)])
        args.extend(["-pix_fmt", "yuv420p"])
        
        return args
    
    def _build_libx265_encoder(self, config: RecordingConfig) -> List[str]:
        args = ["-c:v", "libx265"]
        args.extend(["-preset", config.preset])
        
        if config.rate_control == RateControl.CRF:
            args.extend(["-crf", str(config.crf)])
        else:
            args.extend(["-b:v", f"{config.bitrate}k"])
            args.extend(["-maxrate", f"{config.max_bitrate}k"])
            args.extend(["-bufsize", f"{config.buffer_size}k"])
        
        args.extend(["-g", str(config.keyframe_interval)])
        args.extend(["-pix_fmt", "yuv420p"])
        
        return args
    
    def _build_libaom_encoder(self, config: RecordingConfig) -> List[str]:
        args = ["-c:v", "libaom-av1"]
        args.extend(["-cpu-used", "5"])  # Speed preset
        
        if config.rate_control == RateControl.CRF:
            args.extend(["-crf", str(config.crf)])
        else:
            args.extend(["-b:v", f"{config.bitrate}k"])
        
        args.extend(["-g", str(config.keyframe_interval)])
        args.extend(["-pix_fmt", "yuv420p"])
        
        return args
    
    def _build_libsvtav1_encoder(self, config: RecordingConfig) -> List[str]:
        args = ["-c:v", "libsvtav1"]
        args.extend(["-preset", "6"])  # Speed preset (0-13, lower is slower)
        
        if config.rate_control == RateControl.CRF:
            args.extend(["-crf", str(config.crf)])
        else:
            args.extend(["-b:v", f"{config.bitrate}k"])
            args.extend(["-maxrate", f"{config.max_bitrate}k"])
            args.extend(["-bufsize", f"{config.buffer_size}k"])
        
        args.extend(["-g", str(config.keyframe_interval)])
        args.extend(["-pix_fmt", "yuv420p"])
        
        return args
    
    def _build_audio_encoder(self, config: RecordingConfig) -> List[str]:
        if not config.system_audio_enabled and not config.mic_enabled:
            return []
        
        args = ["-c:a", "aac"]
        args.extend(["-b:a", f"{config.audio_bitrate}k"])
        args.extend(["-ar", str(config.audio_sample_rate)])
        args.extend(["-ac", str(config.audio_channels)])
        
        return args
    
    def _build_container_options(self, config: RecordingConfig) -> List[str]:
        args = []
        
        if config.container == Container.MP4:
            args.extend(["-movflags", "+faststart"])
        
        return args
    
    def _build_segment_options(self, config: RecordingConfig) -> List[str]:
        segment_time = config.segment_minutes * 60
        args = [
            "-f", "segment",
            "-segment_time", str(segment_time),
            "-reset_timestamps", "1"
        ]
        return args
    
    def _get_encoder_by_name(self, name: str) -> Optional[Encoder]:
        from .encoder_detect import EncoderDetector
        return EncoderDetector.ENCODERS.get(name)