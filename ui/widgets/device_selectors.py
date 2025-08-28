from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QLabel, QPushButton, QCheckBox, QSpinBox,
                             QGroupBox, QGridLayout)
from PySide6.QtCore import Signal, Qt
from typing import List, Optional
import sys
sys.path.append('../../')
from core.device_probe import VideoDevice, AudioDevice, DeviceProbe
from core.encoder_detect import Encoder, CodecType


class VideoSourceSelector(QWidget):
    # Signals
    device_changed = Signal(object)  # VideoDevice
    region_requested = Signal()
    cursor_toggled = Signal(bool)
    fps_changed = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.devices: List[VideoDevice] = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Video source group
        group = QGroupBox("Video Source")
        group_layout = QGridLayout(group)
        
        # Monitor selector
        group_layout.addWidget(QLabel("Monitor:"), 0, 0)
        self.monitor_combo = QComboBox()
        self.monitor_combo.currentIndexChanged.connect(self._on_monitor_changed)
        group_layout.addWidget(self.monitor_combo, 0, 1, 1, 2)
        
        # Region capture
        self.region_btn = QPushButton("Select Region")
        self.region_btn.clicked.connect(self.region_requested.emit)
        group_layout.addWidget(self.region_btn, 1, 0, 1, 3)
        
        # FPS selector
        group_layout.addWidget(QLabel("FPS:"), 2, 0)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 144)
        self.fps_spin.setValue(60)
        self.fps_spin.setSuffix(" fps")
        self.fps_spin.valueChanged.connect(self.fps_changed.emit)
        group_layout.addWidget(self.fps_spin, 2, 1)
        
        # Quick FPS presets
        fps_layout = QHBoxLayout()
        for fps in [15, 30, 60]:
            btn = QPushButton(f"{fps}")
            btn.setMaximumWidth(40)
            btn.clicked.connect(lambda checked, f=fps: self.fps_spin.setValue(f))
            fps_layout.addWidget(btn)
        group_layout.addLayout(fps_layout, 2, 2)
        
        # Cursor toggle
        self.cursor_check = QCheckBox("Show cursor")
        self.cursor_check.setChecked(True)
        self.cursor_check.toggled.connect(self.cursor_toggled.emit)
        group_layout.addWidget(self.cursor_check, 3, 0, 1, 3)
        
        layout.addWidget(group)
        
        # Apply styling
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #444;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #2a2a2a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                background-color: #2a2a2a;
            }
            QComboBox, QSpinBox {
                background-color: #333;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
                min-height: 20px;
            }
            QComboBox:hover, QSpinBox:hover {
                border-color: #777;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #666;
            }
            QPushButton:pressed {
                background-color: #353535;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #555;
                border-radius: 3px;
                background-color: #333;
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border-color: #0d7377;
            }
        """)
    
    def set_devices(self, devices: List[VideoDevice]):
        self.devices = devices
        self.monitor_combo.clear()
        
        for device in devices:
            self.monitor_combo.addItem(str(device), device)
    
    def get_selected_device(self) -> Optional[VideoDevice]:
        if self.monitor_combo.currentIndex() >= 0:
            return self.monitor_combo.currentData()
        return None
    
    def get_fps(self) -> int:
        return self.fps_spin.value()
    
    def get_show_cursor(self) -> bool:
        return self.cursor_check.isChecked()
    
    def _on_monitor_changed(self, index: int):
        if index >= 0:
            device = self.monitor_combo.currentData()
            if device:
                self.device_changed.emit(device)


class AudioSourceSelector(QWidget):
    # Signals
    system_device_changed = Signal(object)  # AudioDevice
    mic_device_changed = Signal(object)  # AudioDevice
    system_toggled = Signal(bool)
    mic_toggled = Signal(bool)
    refresh_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.system_devices: List[AudioDevice] = []
        self.mic_devices: List[AudioDevice] = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Audio source group
        group = QGroupBox("Audio Source")
        group_layout = QVBoxLayout(group)
        
        # System audio
        system_layout = QHBoxLayout()
        self.system_check = QCheckBox("System Audio:")
        self.system_check.setChecked(True)
        self.system_check.toggled.connect(self._on_system_toggled)
        system_layout.addWidget(self.system_check)
        
        self.system_combo = QComboBox()
        self.system_combo.currentIndexChanged.connect(self._on_system_changed)
        system_layout.addWidget(self.system_combo, 1)
        group_layout.addLayout(system_layout)
        
        # Microphone
        mic_layout = QHBoxLayout()
        self.mic_check = QCheckBox("Microphone:")
        self.mic_check.toggled.connect(self._on_mic_toggled)
        mic_layout.addWidget(self.mic_check)
        
        self.mic_combo = QComboBox()
        self.mic_combo.setEnabled(False)
        self.mic_combo.currentIndexChanged.connect(self._on_mic_changed)
        mic_layout.addWidget(self.mic_combo, 1)
        group_layout.addLayout(mic_layout)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh Devices")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        group_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(group)
        
        # Apply styling
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #444;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #2a2a2a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                background-color: #2a2a2a;
            }
            QComboBox {
                background-color: #333;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
                min-height: 20px;
            }
            QComboBox:hover:enabled {
                border-color: #777;
            }
            QComboBox:disabled {
                background-color: #2a2a2a;
                color: #666;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #666;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #555;
                border-radius: 3px;
                background-color: #333;
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border-color: #0d7377;
            }
        """)
    
    def set_system_devices(self, devices: List[AudioDevice]):
        self.system_devices = devices
        self.system_combo.clear()
        
        if not devices:
            self.system_combo.addItem("No audio devices found", None)
            self.system_check.setChecked(False)
            self.system_check.setEnabled(False)
        else:
            self.system_check.setEnabled(True)
            for device in devices:
                self.system_combo.addItem(device.name, device)
    
    def set_mic_devices(self, devices: List[AudioDevice]):
        self.mic_devices = devices
        self.mic_combo.clear()
        
        if not devices:
            self.mic_combo.addItem("No microphone found", None)
            self.mic_check.setChecked(False)
            self.mic_check.setEnabled(False)
        else:
            self.mic_check.setEnabled(True)
            for device in devices:
                self.mic_combo.addItem(device.name, device)
    
    def get_system_device(self) -> Optional[AudioDevice]:
        if self.system_check.isChecked() and self.system_combo.currentIndex() >= 0:
            return self.system_combo.currentData()
        return None
    
    def get_mic_device(self) -> Optional[AudioDevice]:
        if self.mic_check.isChecked() and self.mic_combo.currentIndex() >= 0:
            return self.mic_combo.currentData()
        return None
    
    def _on_system_toggled(self, checked: bool):
        self.system_combo.setEnabled(checked)
        self.system_toggled.emit(checked)
    
    def _on_mic_toggled(self, checked: bool):
        self.mic_combo.setEnabled(checked)
        self.mic_toggled.emit(checked)
    
    def _on_system_changed(self, index: int):
        if index >= 0:
            device = self.system_combo.currentData()
            if device:
                self.system_device_changed.emit(device)
    
    def _on_mic_changed(self, index: int):
        if index >= 0:
            device = self.mic_combo.currentData()
            if device:
                self.mic_device_changed.emit(device)


class EncoderSelector(QWidget):
    # Signals
    encoder_changed = Signal(object)  # Encoder
    preset_changed = Signal(str)
    rate_control_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.encoders: List[Encoder] = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Video encoder group
        group = QGroupBox("Video Encoder")
        group_layout = QGridLayout(group)
        
        # Codec selector
        group_layout.addWidget(QLabel("Codec:"), 0, 0)
        self.codec_combo = QComboBox()
        self.codec_combo.currentIndexChanged.connect(self._on_codec_changed)
        group_layout.addWidget(self.codec_combo, 0, 1)
        
        # Preset selector
        group_layout.addWidget(QLabel("Preset:"), 1, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.currentTextChanged.connect(self.preset_changed.emit)
        group_layout.addWidget(self.preset_combo, 1, 1)
        
        # Rate control
        group_layout.addWidget(QLabel("Rate Control:"), 2, 0)
        self.rate_combo = QComboBox()
        self.rate_combo.currentTextChanged.connect(self.rate_control_changed.emit)
        group_layout.addWidget(self.rate_combo, 2, 1)
        
        layout.addWidget(group)
        
        # Apply styling
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #444;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #2a2a2a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                background-color: #2a2a2a;
            }
            QComboBox {
                background-color: #333;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #777;
            }
            QLabel {
                color: #ccc;
            }
        """)
    
    def set_encoders(self, encoders: List[Encoder]):
        self.encoders = encoders
        self.codec_combo.clear()
        
        # Group encoders by codec
        codec_groups = {}
        for encoder in encoders:
            display_name = encoder.get_display_name()
            if encoder.codec not in codec_groups:
                codec_groups[encoder.codec] = []
            codec_groups[encoder.codec].append((display_name, encoder))
        
        # Add to combo
        for codec in [CodecType.H264, CodecType.H265, CodecType.AV1]:
            if codec in codec_groups:
                for display_name, encoder in codec_groups[codec]:
                    self.codec_combo.addItem(display_name, encoder)
    
    def get_selected_encoder(self) -> Optional[Encoder]:
        if self.codec_combo.currentIndex() >= 0:
            return self.codec_combo.currentData()
        return None
    
    def get_preset(self) -> str:
        return self.preset_combo.currentText()
    
    def get_rate_control(self) -> str:
        return self.rate_combo.currentText()
    
    def _on_codec_changed(self, index: int):
        if index >= 0:
            encoder = self.codec_combo.currentData()
            if encoder:
                # Update presets
                self.preset_combo.clear()
                self.preset_combo.addItems(encoder.presets)
                
                # Select middle preset
                if encoder.presets:
                    mid_index = len(encoder.presets) // 2
                    self.preset_combo.setCurrentIndex(mid_index)
                
                # Update rate controls
                self.rate_combo.clear()
                self.rate_combo.addItems([rc.upper() for rc in encoder.rate_controls])
                
                self.encoder_changed.emit(encoder)