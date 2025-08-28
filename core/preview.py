import threading
import time
import numpy as np
import ctypes
import ctypes.wintypes
from typing import Optional, Callable, Tuple
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter, QCursor
from .logger import logger


class ScreenPreview(QObject):
    # Signal emitted when a new frame is ready
    frame_ready = Signal(QPixmap)
    error_occurred = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.capture_backend = None
        self.is_running = False
        self.target_fps = 20
        self.monitor_index = 0
        self.region: Optional[Tuple[int, int, int, int]] = None
        self.scale_size: Tuple[int, int] = (640, 360)
        self.show_cursor = True
        
        self._init_capture_backend()
        self.timer = QTimer()
        self.timer.timeout.connect(self._capture_frame)
    
    def _init_capture_backend(self):
        # Try to use dxcam first (fastest on Windows)
        try:
            import dxcam
            self.capture_backend = "dxcam"
            self.camera = dxcam.create()
            logger.info("Using dxcam for preview")
        except ImportError:
            logger.info("dxcam not available, trying mss")
            try:
                import mss
                self.capture_backend = "mss"
                self.sct = mss.mss()
                logger.info("Using mss for preview")
            except ImportError:
                logger.info("mss not available, trying PIL")
                try:
                    from PIL import ImageGrab
                    self.capture_backend = "pil"
                    logger.info("Using PIL for preview")
                except ImportError:
                    logger.error("No screen capture backend available")
                    self.capture_backend = None
    
    def start_preview(self, monitor_index: int = 0, region: Optional[Tuple[int, int, int, int]] = None):
        if self.is_running:
            return
        
        self.monitor_index = monitor_index
        self.region = region
        self.is_running = True
        
        # Start timer for capturing frames
        interval_ms = int(1000 / self.target_fps)
        self.timer.start(interval_ms)
        
        logger.info(f"Preview started at {self.target_fps} FPS")
    
    def stop_preview(self):
        if not self.is_running:
            return
        
        self.is_running = False
        self.timer.stop()
        logger.info("Preview stopped")
    
    def set_target_fps(self, fps: int):
        self.target_fps = max(1, min(fps, 60))
        if self.is_running:
            self.timer.setInterval(int(1000 / self.target_fps))
    
    def set_scale_size(self, width: int, height: int):
        self.scale_size = (width, height)
    
    def set_show_cursor(self, show: bool):
        self.show_cursor = show
    
    def _capture_frame(self):
        if not self.is_running:
            return
        
        try:
            if self.capture_backend == "dxcam":
                self._capture_dxcam()
            elif self.capture_backend == "mss":
                self._capture_mss()
            elif self.capture_backend == "pil":
                self._capture_pil()
        except Exception as e:
            logger.error(f"Preview capture error: {e}")
            self.error_occurred.emit(str(e))
    
    def _capture_dxcam(self):
        try:
            import dxcam
            
            if self.region:
                x, y, w, h = self.region
                frame = self.camera.grab(region=(x, y, x + w, y + h))
                capture_offset = (x, y)
            else:
                frame = self.camera.grab()
                capture_offset = (0, 0)
            
            if frame is not None:
                if self.show_cursor:
                    frame = self._add_cursor_to_frame(frame, capture_offset)
                self._process_frame(frame)
        except Exception as e:
            logger.debug(f"dxcam capture error: {e}")
    
    def _capture_mss(self):
        try:
            import mss
            import numpy as np
            
            if self.region:
                x, y, w, h = self.region
                monitor = {"left": x, "top": y, "width": w, "height": h}
                capture_offset = (x, y)
            else:
                monitor = self.sct.monitors[self.monitor_index + 1]
                capture_offset = (monitor["left"], monitor["top"])
            
            screenshot = self.sct.grab(monitor)
            
            # Convert to numpy array
            frame = np.array(screenshot)
            # Remove alpha channel if present
            if frame.shape[2] == 4:
                frame = frame[:, :, :3]
            
            if self.show_cursor:
                frame = self._add_cursor_to_frame(frame, capture_offset)
            
            self._process_frame(frame)
        except Exception as e:
            logger.debug(f"mss capture error: {e}")
    
    def _capture_pil(self):
        try:
            from PIL import ImageGrab
            import numpy as np
            
            if self.region:
                x, y, w, h = self.region
                bbox = (x, y, x + w, y + h)
                screenshot = ImageGrab.grab(bbox=bbox, include_layered_windows=False)
                capture_offset = (x, y)
            else:
                screenshot = ImageGrab.grab(include_layered_windows=False)
                capture_offset = (0, 0)
            
            # Convert to numpy array
            frame = np.array(screenshot)
            
            if self.show_cursor:
                frame = self._add_cursor_to_frame(frame, capture_offset)
            
            self._process_frame(frame)
        except Exception as e:
            logger.debug(f"PIL capture error: {e}")
    
    def _add_cursor_to_frame(self, frame: np.ndarray, capture_offset: Tuple[int, int]) -> np.ndarray:
        """Add cursor overlay to the captured frame"""
        try:
            # Get cursor position
            cursor_info = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor_info))
            
            cursor_x = cursor_info.x - capture_offset[0]
            cursor_y = cursor_info.y - capture_offset[1]
            
            # Check if cursor is within the captured region
            h, w = frame.shape[:2]
            if 0 <= cursor_x < w and 0 <= cursor_y < h:
                # Draw a simple crosshair cursor (can be enhanced with actual cursor icon)
                cursor_size = 10
                cursor_thickness = 2
                
                # Horizontal line
                y_start = max(0, cursor_y - cursor_thickness // 2)
                y_end = min(h, cursor_y + cursor_thickness // 2 + 1)
                x_left = max(0, cursor_x - cursor_size)
                x_right = min(w, cursor_x + cursor_size)
                
                if y_start < y_end:
                    frame[y_start:y_end, x_left:x_right] = [255, 255, 255]
                
                # Vertical line
                x_start = max(0, cursor_x - cursor_thickness // 2)
                x_end = min(w, cursor_x + cursor_thickness // 2 + 1)
                y_top = max(0, cursor_y - cursor_size)
                y_bottom = min(h, cursor_y + cursor_size)
                
                if x_start < x_end:
                    frame[y_top:y_bottom, x_start:x_end] = [255, 255, 255]
                    
        except Exception as e:
            logger.debug(f"Failed to add cursor: {e}")
        
        return frame
    
    def _process_frame(self, frame: np.ndarray):
        try:
            # Ensure frame is in the right format
            if frame is None or frame.size == 0:
                return
            
            # Convert BGR to RGB if needed
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                # Assume BGR format for dxcam, convert to RGB
                if self.capture_backend == "dxcam":
                    frame = frame[:, :, ::-1]
            
            # Scale the frame
            h, w = frame.shape[:2]
            target_w, target_h = self.scale_size
            
            # Calculate scaling to maintain aspect ratio
            scale = min(target_w / w, target_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # Use PIL for resizing if available, otherwise use simple slicing
            try:
                from PIL import Image
                pil_image = Image.fromarray(frame.astype('uint8'))
                pil_image = pil_image.resize((new_w, new_h), Image.Resampling.BILINEAR)
                frame = np.array(pil_image)
            except ImportError:
                # Simple downsampling
                step_h = max(1, h // new_h)
                step_w = max(1, w // new_w)
                frame = frame[::step_h, ::step_w]
                new_h, new_w = frame.shape[:2]
            
            # Convert to QImage
            if len(frame.shape) == 3:
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                
                if ch == 3:
                    qt_format = QImage.Format_RGB888
                elif ch == 4:
                    qt_format = QImage.Format_RGBA8888
                else:
                    return
                
                qimage = QImage(frame.data.tobytes(), w, h, bytes_per_line, qt_format)
            else:
                # Grayscale
                h, w = frame.shape
                bytes_per_line = w
                qimage = QImage(frame.data.tobytes(), w, h, bytes_per_line, QImage.Format_Grayscale8)
            
            # Convert to QPixmap
            pixmap = QPixmap.fromImage(qimage)
            
            # Emit the signal
            self.frame_ready.emit(pixmap)
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")