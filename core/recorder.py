import subprocess
import threading
import queue
import time
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
from enum import Enum
from PySide6.QtCore import QObject, Signal, QProcess, QIODevice
from .logger import logger
from .command_builder import CommandBuilder, RecordingConfig


class RecorderState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    STOPPING = "stopping"
    ERROR = "error"


class RecorderStats:
    def __init__(self):
        self.duration = 0.0
        self.file_size = 0
        self.dropped_frames = 0
        self.fps = 0.0
        self.bitrate = 0.0
        self.encoder_used = ""


class Recorder(QObject):
    # Signals
    state_changed = Signal(RecorderState)
    stats_updated = Signal(RecorderStats)
    log_output = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, ffmpeg_path: Path):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.command_builder = CommandBuilder(ffmpeg_path)
        self.process: Optional[QProcess] = None
        self.state = RecorderState.IDLE
        self.config: Optional[RecordingConfig] = None
        self.output_file: Optional[Path] = None
        self.stats = RecorderStats()
        self.start_time: Optional[float] = None
        self._stop_requested = False
    
    def start_recording(self, config: RecordingConfig) -> bool:
        if self.state == RecorderState.ERROR:
            # Reset from error state
            self.state = RecorderState.IDLE
            logger.info("Reset recorder from error state")
        
        if self.state != RecorderState.IDLE:
            logger.warning(f"Cannot start recording in state {self.state}")
            return False
        
        try:
            # Validate config
            if not self._validate_config(config):
                return False
            
            self.config = config
            self.output_file = self._generate_output_filename(config)
            
            # Ensure output directory exists
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Build command
            command = self.command_builder.build_command(config, self.output_file)
            logger.info(f"FFmpeg command: {' '.join(command)}")
            
            # Start process
            self.process = QProcess()
            self.process.readyReadStandardError.connect(self._handle_stderr)
            self.process.finished.connect(self._handle_finished)
            self.process.errorOccurred.connect(self._handle_error)
            
            # Start the process
            program = command[0]
            args = command[1:]
            self.process.start(program, args)
            
            if not self.process.waitForStarted(5000):  # 5 second timeout
                self.error_occurred.emit("Failed to start FFmpeg process")
                return False
            
            self.state = RecorderState.RECORDING
            self.state_changed.emit(self.state)
            self.start_time = time.time()
            self._stop_requested = False
            
            # Start stats update thread
            self._start_stats_thread()
            
            logger.info(f"Recording started: {self.output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.error_occurred.emit(str(e))
            return False
    
    def stop_recording(self) -> None:
        if self.state != RecorderState.RECORDING:
            logger.warning(f"Cannot stop recording in state {self.state}")
            return
        
        self.state = RecorderState.STOPPING
        self.state_changed.emit(self.state)
        self._stop_requested = True
        
        if self.process:
            # Send 'q' to stdin for graceful shutdown
            self.process.write(b'q')
            
            # Wait for process to finish
            if not self.process.waitForFinished(5000):
                # Force terminate if graceful shutdown fails
                logger.warning("Graceful shutdown failed, terminating process")
                self.process.terminate()
                if not self.process.waitForFinished(3000):
                    self.process.kill()
    
    def _validate_config(self, config: RecordingConfig) -> bool:
        # Check if output path is writable
        try:
            test_file = config.output_path / ".test_write"
            config.output_path.mkdir(parents=True, exist_ok=True)
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            self.error_occurred.emit(f"Output path not writable: {e}")
            return False
        
        # Check if encoder is available
        if not config.encoder and not config.encoder_name:
            self.error_occurred.emit("No encoder specified")
            return False
        
        return True
    
    def _generate_output_filename(self, config: RecordingConfig) -> Path:
        now = datetime.now()
        
        # Get resolution string
        if config.scale:
            res = f"{config.scale[0]}x{config.scale[1]}"
        elif config.region:
            res = f"{config.region[2]}x{config.region[3]}"
        else:
            res = "desktop"
        
        # Get codec string
        codec = config.encoder.codec.value if config.encoder else "h264"
        
        # Format filename
        replacements = {
            "{date}": now.strftime("%Y%m%d"),
            "{time}": now.strftime("%H%M%S"),
            "{codec}": codec,
            "{res}": res,
            "{fps}": str(config.fps)
        }
        
        filename = config.file_pattern
        for key, value in replacements.items():
            filename = filename.replace(key, value)
        
        # Add extension
        filename += f".{config.container.value}"
        
        return config.output_path / filename
    
    def _handle_stderr(self):
        if not self.process:
            return
        
        data = self.process.readAllStandardError()
        text = data.data().decode('utf-8', errors='ignore')
        
        # Parse FFmpeg output for stats
        self._parse_ffmpeg_output(text)
        
        # Emit log output
        for line in text.strip().split('\n'):
            if line:
                self.log_output.emit(line)
    
    def _parse_ffmpeg_output(self, text: str):
        import re
        
        # Parse frame rate
        fps_match = re.search(r'fps=\s*(\d+\.?\d*)', text)
        if fps_match:
            self.stats.fps = float(fps_match.group(1))
        
        # Parse bitrate
        bitrate_match = re.search(r'bitrate=\s*(\d+\.?\d*)kbits/s', text)
        if bitrate_match:
            self.stats.bitrate = float(bitrate_match.group(1))
        
        # Parse time
        time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', text)
        if time_match:
            hours = int(time_match.group(1))
            minutes = int(time_match.group(2))
            seconds = float(time_match.group(3))
            self.stats.duration = hours * 3600 + minutes * 60 + seconds
        
        # Parse dropped frames
        drop_match = re.search(r'frame=\s*(\d+).*dup=\s*(\d+).*drop=\s*(\d+)', text)
        if drop_match:
            self.stats.dropped_frames = int(drop_match.group(3))
        
        self.stats_updated.emit(self.stats)
    
    def _handle_finished(self, exit_code, exit_status):
        logger.info(f"Recording finished with code {exit_code}")
        
        if self._stop_requested or exit_code == 0:
            self.state = RecorderState.IDLE
        else:
            self.state = RecorderState.ERROR
            self.error_occurred.emit(f"FFmpeg exited with code {exit_code}")
        
        self.state_changed.emit(self.state)
        self.process = None
    
    def _handle_error(self, error):
        logger.error(f"Process error: {error}")
        self.state = RecorderState.ERROR
        self.state_changed.emit(self.state)
        self.error_occurred.emit(f"Process error: {error}")
    
    def _start_stats_thread(self):
        def update_stats():
            while self.state == RecorderState.RECORDING:
                if self.output_file and self.output_file.exists():
                    self.stats.file_size = self.output_file.stat().st_size
                
                if self.start_time:
                    self.stats.duration = time.time() - self.start_time
                
                self.stats_updated.emit(self.stats)
                time.sleep(1)
        
        thread = threading.Thread(target=update_stats, daemon=True)
        thread.start()
    
    def get_state(self) -> RecorderState:
        return self.state
    
    def get_output_file(self) -> Optional[Path]:
        return self.output_file
    
    def get_stats(self) -> RecorderStats:
        return self.stats