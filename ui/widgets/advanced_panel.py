from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QSpinBox, QComboBox, QLineEdit,
                             QGroupBox, QPushButton, QSlider, QCheckBox)
from PySide6.QtCore import Signal, Qt
from typing import Optional


class BitrateControl(QWidget):
    # Signals
    bitrate_changed = Signal(int)
    max_bitrate_changed = Signal(int)
    buffer_size_changed = Signal(int)
    crf_changed = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Bitrate
        layout.addWidget(QLabel("Bitrate:"), 0, 0)
        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(100, 100000)
        self.bitrate_spin.setValue(8000)
        self.bitrate_spin.setSuffix(" kbps")
        self.bitrate_spin.setSingleStep(500)
        self.bitrate_spin.valueChanged.connect(self._on_bitrate_changed)
        layout.addWidget(self.bitrate_spin, 0, 1)
        
        # Bitrate slider
        self.bitrate_slider = QSlider(Qt.Horizontal)
        self.bitrate_slider.setRange(100, 50000)
        self.bitrate_slider.setValue(8000)
        self.bitrate_slider.valueChanged.connect(self.bitrate_spin.setValue)
        self.bitrate_spin.valueChanged.connect(self.bitrate_slider.setValue)
        layout.addWidget(self.bitrate_slider, 0, 2)
        
        # Max bitrate
        layout.addWidget(QLabel("Max Rate:"), 1, 0)
        self.max_bitrate_spin = QSpinBox()
        self.max_bitrate_spin.setRange(100, 100000)
        self.max_bitrate_spin.setValue(8000)
        self.max_bitrate_spin.setSuffix(" kbps")
        self.max_bitrate_spin.setSingleStep(500)
        self.max_bitrate_spin.valueChanged.connect(self.max_bitrate_changed.emit)
        layout.addWidget(self.max_bitrate_spin, 1, 1)
        
        # Buffer size
        layout.addWidget(QLabel("Buffer:"), 2, 0)
        self.buffer_spin = QSpinBox()
        self.buffer_spin.setRange(100, 200000)
        self.buffer_spin.setValue(16000)
        self.buffer_spin.setSuffix(" kbps")
        self.buffer_spin.setSingleStep(1000)
        self.buffer_spin.valueChanged.connect(self.buffer_size_changed.emit)
        layout.addWidget(self.buffer_spin, 2, 1)
        
        # CRF
        layout.addWidget(QLabel("CRF:"), 3, 0)
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(23)
        self.crf_spin.valueChanged.connect(self.crf_changed.emit)
        layout.addWidget(self.crf_spin, 3, 1)
        
        self.crf_slider = QSlider(Qt.Horizontal)
        self.crf_slider.setRange(0, 51)
        self.crf_slider.setValue(23)
        self.crf_slider.valueChanged.connect(self.crf_spin.setValue)
        self.crf_spin.valueChanged.connect(self.crf_slider.setValue)
        layout.addWidget(self.crf_slider, 3, 2)
        
        # Apply styling
        self.setStyleSheet("""
            QSpinBox {
                background-color: #333;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 3px;
                min-width: 100px;
            }
            QSpinBox:hover {
                border-color: #777;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 6px;
                background: #333;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0d7377;
                border: 1px solid #0d7377;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #0e8a8f;
            }
        """)
    
    def _on_bitrate_changed(self, value: int):
        # Auto-adjust max bitrate and buffer
        self.max_bitrate_spin.setValue(value)
        self.buffer_spin.setValue(value * 2)
        self.bitrate_changed.emit(value)
    
    def set_rate_control(self, rate_control: str):
        is_crf = rate_control.upper() == "CRF"
        self.bitrate_spin.setEnabled(not is_crf)
        self.bitrate_slider.setEnabled(not is_crf)
        self.max_bitrate_spin.setEnabled(not is_crf)
        self.buffer_spin.setEnabled(not is_crf)
        self.crf_spin.setEnabled(is_crf)
        self.crf_slider.setEnabled(is_crf)


class AdvancedPanel(QWidget):
    # Signals
    settings_changed = Signal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Advanced Settings Group
        group = QGroupBox("Advanced Settings")
        group_layout = QVBoxLayout(group)
        
        # Bitrate controls
        self.bitrate_control = BitrateControl()
        self.bitrate_control.bitrate_changed.connect(lambda: self.settings_changed.emit())
        group_layout.addWidget(self.bitrate_control)
        
        # GOP/Keyframe interval
        gop_layout = QHBoxLayout()
        gop_layout.addWidget(QLabel("Keyframe Interval:"))
        self.gop_spin = QSpinBox()
        self.gop_spin.setRange(1, 600)
        self.gop_spin.setValue(120)
        self.gop_spin.setSuffix(" frames")
        self.gop_spin.valueChanged.connect(lambda: self.settings_changed.emit())
        gop_layout.addWidget(self.gop_spin)
        gop_layout.addStretch()
        group_layout.addLayout(gop_layout)
        
        # Profile selector
        profile_layout = QHBoxLayout()
        profile_layout.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["baseline", "main", "high"])
        self.profile_combo.setCurrentText("high")
        self.profile_combo.currentTextChanged.connect(lambda: self.settings_changed.emit())
        profile_layout.addWidget(self.profile_combo)
        profile_layout.addStretch()
        group_layout.addLayout(profile_layout)
        
        # Scale selector
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Output Scale:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems([
            "Original",
            "4K (3840×2160)",
            "1440p (2560×1440)",
            "1080p (1920×1080)",
            "720p (1280×720)",
            "Custom"
        ])
        self.scale_combo.currentTextChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self.scale_combo)
        
        self.custom_width = QSpinBox()
        self.custom_width.setRange(128, 7680)
        self.custom_width.setValue(1920)
        self.custom_width.setVisible(False)
        scale_layout.addWidget(self.custom_width)
        
        scale_layout.addWidget(QLabel("×"))
        
        self.custom_height = QSpinBox()
        self.custom_height.setRange(128, 4320)
        self.custom_height.setValue(1080)
        self.custom_height.setVisible(False)
        scale_layout.addWidget(self.custom_height)
        
        scale_layout.addStretch()
        group_layout.addLayout(scale_layout)
        
        # Audio settings
        audio_layout = QGridLayout()
        audio_layout.addWidget(QLabel("Audio Bitrate:"), 0, 0)
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems(["96", "128", "160", "192", "256", "320"])
        self.audio_bitrate_combo.setCurrentText("160")
        self.audio_bitrate_combo.currentTextChanged.connect(lambda: self.settings_changed.emit())
        audio_layout.addWidget(self.audio_bitrate_combo, 0, 1)
        audio_layout.addWidget(QLabel("kbps"), 0, 2)
        
        audio_layout.addWidget(QLabel("Sample Rate:"), 1, 0)
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000"])
        self.sample_rate_combo.setCurrentText("48000")
        self.sample_rate_combo.currentTextChanged.connect(lambda: self.settings_changed.emit())
        audio_layout.addWidget(self.sample_rate_combo, 1, 1)
        audio_layout.addWidget(QLabel("Hz"), 1, 2)
        
        self.normalize_check = QCheckBox("Normalize audio")
        self.normalize_check.setChecked(True)
        self.normalize_check.toggled.connect(lambda: self.settings_changed.emit())
        audio_layout.addWidget(self.normalize_check, 2, 0, 1, 3)
        
        group_layout.addLayout(audio_layout)
        
        layout.addWidget(group)
        layout.addStretch()
        
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
            }
            QComboBox:hover, QSpinBox:hover {
                border-color: #777;
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
    
    def _on_scale_changed(self, text: str):
        is_custom = text == "Custom"
        self.custom_width.setVisible(is_custom)
        self.custom_height.setVisible(is_custom)
        self.settings_changed.emit()
    
    def get_scale(self) -> Optional[tuple]:
        text = self.scale_combo.currentText()
        if text == "Original":
            return None
        elif text == "Custom":
            return (self.custom_width.value(), self.custom_height.value())
        elif "3840" in text:
            return (3840, 2160)
        elif "2560" in text:
            return (2560, 1440)
        elif "1920" in text:
            return (1920, 1080)
        elif "1280" in text:
            return (1280, 720)
        return None
    
    def get_bitrate(self) -> int:
        return self.bitrate_control.bitrate_spin.value()
    
    def get_max_bitrate(self) -> int:
        return self.bitrate_control.max_bitrate_spin.value()
    
    def get_buffer_size(self) -> int:
        return self.bitrate_control.buffer_spin.value()
    
    def get_crf(self) -> int:
        return self.bitrate_control.crf_spin.value()
    
    def get_gop(self) -> int:
        return self.gop_spin.value()
    
    def get_profile(self) -> str:
        return self.profile_combo.currentText()
    
    def get_audio_bitrate(self) -> int:
        return int(self.audio_bitrate_combo.currentText())
    
    def get_sample_rate(self) -> int:
        return int(self.sample_rate_combo.currentText())
    
    def get_normalize(self) -> bool:
        return self.normalize_check.isChecked()
    
    def set_rate_control(self, rate_control: str):
        self.bitrate_control.set_rate_control(rate_control)