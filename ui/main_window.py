from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QSplitter, QScrollArea, QMessageBox,
                             QFileDialog, QTextEdit, QTabWidget, QLabel,
                             QComboBox, QLineEdit, QGroupBox, QStatusBar)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QAction, QKeySequence
from pathlib import Path
import subprocess
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ffmpeg_locator import FFmpegLocator
from core.device_probe import DeviceProbe
from core.encoder_detect import EncoderDetector
from core.recorder import Recorder, RecorderState, RecorderStats
from core.preview import ScreenPreview
from core.settings import SettingsManager
from core.command_builder import RecordingConfig, RateControl, Container
from core.logger import logger

from ui.widgets.preview_widget import PreviewWidget
from ui.widgets.device_selectors import VideoSourceSelector, AudioSourceSelector, EncoderSelector
from ui.widgets.advanced_panel import AdvancedPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ffmpeg = FFmpegLocator()
        self.device_probe = DeviceProbe(self.ffmpeg)
        self.encoder_detector = EncoderDetector(self.ffmpeg)
        self.settings_manager = SettingsManager()
        self.recorder = None
        self.preview = ScreenPreview()
        
        self.init_ui()
        self.setup_connections()
        self.initialize_devices()
        self.restore_settings()
        
        # Check FFmpeg on startup
        if not self.ffmpeg.is_available():
            self.prompt_for_ffmpeg()
    
    def init_ui(self):
        self.setWindowTitle("FFScreenRec - Screen Recorder")
        self.setGeometry(100, 100, 1200, 700)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QSplitter::handle {
                background-color: #333;
                border: 1px solid #444;
            }
            QSplitter::handle:hover {
                background-color: #444;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #2a2a2a;
            }
            QTabBar::tab {
                background-color: #333;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #444;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #2a2a2a;
                border-bottom: 1px solid #2a2a2a;
            }
            QTabBar::tab:hover {
                background-color: #3a3a3a;
            }
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #444;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for left/right panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel (settings)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Profile selector
        profile_group = QGroupBox("Recording Profile")
        profile_layout = QHBoxLayout(profile_group)
        self.profile_combo = QComboBox()
        self.profile_combo.currentTextChanged.connect(self.apply_profile)
        profile_layout.addWidget(self.profile_combo)
        self.save_profile_btn = QPushButton("Save")
        self.save_profile_btn.setMaximumWidth(60)
        profile_layout.addWidget(self.save_profile_btn)
        left_layout.addWidget(profile_group)
        
        # Settings tabs
        self.settings_tabs = QTabWidget()
        
        # Source tab
        source_tab = QWidget()
        source_layout = QVBoxLayout(source_tab)
        
        self.video_selector = VideoSourceSelector()
        source_layout.addWidget(self.video_selector)
        
        self.audio_selector = AudioSourceSelector()
        source_layout.addWidget(self.audio_selector)
        source_layout.addStretch()
        
        self.settings_tabs.addTab(source_tab, "Source")
        
        # Encoding tab
        encoding_tab = QWidget()
        encoding_layout = QVBoxLayout(encoding_tab)
        
        self.encoder_selector = EncoderSelector()
        encoding_layout.addWidget(self.encoder_selector)
        
        self.advanced_panel = AdvancedPanel()
        encoding_layout.addWidget(self.advanced_panel)
        encoding_layout.addStretch()
        
        self.settings_tabs.addTab(encoding_tab, "Encoding")
        
        # Output tab
        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)
        
        output_group = QGroupBox("Output Settings")
        output_group_layout = QVBoxLayout(output_group)
        
        # Container format
        container_layout = QHBoxLayout()
        container_layout.addWidget(QLabel("Format:"))
        self.container_combo = QComboBox()
        self.container_combo.addItems(["mp4", "mkv", "mov"])
        container_layout.addWidget(self.container_combo)
        container_layout.addStretch()
        output_group_layout.addLayout(container_layout)
        
        # Output path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Path:"))
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setText(str(self.settings_manager.settings.output_path))
        path_layout.addWidget(self.output_path_edit)
        self.browse_btn = QPushButton("...")
        self.browse_btn.setMaximumWidth(30)
        self.browse_btn.clicked.connect(self.browse_output_path)
        path_layout.addWidget(self.browse_btn)
        output_group_layout.addLayout(path_layout)
        
        # File pattern
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("Pattern:"))
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setText("{date}_{time}_{codec}_{res}_{fps}fps")
        pattern_layout.addWidget(self.pattern_edit)
        output_group_layout.addLayout(pattern_layout)
        
        output_layout.addWidget(output_group)
        output_layout.addStretch()
        
        self.settings_tabs.addTab(output_tab, "Output")
        
        left_layout.addWidget(self.settings_tabs)
        
        # Scroll area for left panel
        scroll_area = QScrollArea()
        scroll_area.setWidget(left_panel)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(450)
        splitter.addWidget(scroll_area)
        
        # Right panel (preview + controls)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Preview widget
        self.preview_widget = PreviewWidget()
        right_layout.addWidget(self.preview_widget, 1)
        
        # Log output (collapsible)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setVisible(False)
        right_layout.addWidget(self.log_output)
        
        # Control buttons
        control_layout = QHBoxLayout()
        control_layout.addStretch()
        
        self.start_btn = QPushButton("Start Recording")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d7377;
                border: none;
                padding: 10px 30px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0e8a8f;
            }
            QPushButton:pressed {
                background-color: #0b6166;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #666;
            }
        """)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Recording")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                border: none;
                padding: 10px 30px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #666;
            }
        """)
        control_layout.addWidget(self.stop_btn)
        
        self.folder_btn = QPushButton("Open Output Folder")
        self.folder_btn.setMinimumHeight(40)
        self.folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: 1px solid #555;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #666;
            }
        """)
        control_layout.addWidget(self.folder_btn)
        
        control_layout.addStretch()
        right_layout.addLayout(control_layout)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([450, 750])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #252525;
                border-top: 1px solid #444;
            }
        """)
        
        # Create menu bar
        self.create_menu_bar()
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #252525;
                border-bottom: 1px solid #444;
            }
            QMenuBar::item {
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #333;
            }
            QMenu {
                background-color: #2a2a2a;
                border: 1px solid #444;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #333;
            }
        """)
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        start_action = QAction("Start Recording", self)
        start_action.setShortcut(QKeySequence("Ctrl+R"))
        start_action.triggered.connect(self.start_recording)
        file_menu.addAction(start_action)
        
        stop_action = QAction("Stop Recording", self)
        stop_action.setShortcut(QKeySequence("Ctrl+S"))
        stop_action.triggered.connect(self.stop_recording)
        file_menu.addAction(stop_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        log_action = QAction("Toggle Log Output", self)
        log_action.triggered.connect(self.toggle_log_output)
        view_menu.addAction(log_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        refresh_action = QAction("Refresh Devices", self)
        refresh_action.triggered.connect(self.refresh_devices)
        tools_menu.addAction(refresh_action)
        
        reset_action = QAction("Reset to Defaults", self)
        reset_action.triggered.connect(self.reset_to_defaults)
        tools_menu.addAction(reset_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_connections(self):
        # Connect signals
        self.start_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.folder_btn.clicked.connect(self.open_output_folder)
        
        # Connect preview
        self.preview.frame_ready.connect(self.preview_widget.update_preview)
        
        # Connect encoder selector to advanced panel
        self.encoder_selector.rate_control_changed.connect(self.advanced_panel.set_rate_control)
        
        # Connect refresh
        self.audio_selector.refresh_requested.connect(self.refresh_devices)
    
    def initialize_devices(self):
        # Initialize recorder
        if self.ffmpeg.is_available():
            self.recorder = Recorder(self.ffmpeg.ffmpeg_path)
            self.recorder.state_changed.connect(self.on_recorder_state_changed)
            self.recorder.stats_updated.connect(self.on_stats_updated)
            self.recorder.log_output.connect(self.on_log_output)
            self.recorder.error_occurred.connect(self.on_error)
        
        # Detect encoders
        encoders = self.encoder_detector.detect_encoders()
        self.encoder_selector.set_encoders(list(encoders.values()))
        
        # Probe devices
        self.refresh_devices()
        
        # Load profiles
        self.load_profiles()
        
        # Start preview
        self.preview.start_preview()
    
    def refresh_devices(self):
        # Probe devices
        self.device_probe.refresh()
        
        # Update video devices
        video_devices = self.device_probe.get_video_devices()
        self.video_selector.set_devices(video_devices)
        
        # Update audio devices
        system_devices = self.device_probe.get_audio_devices(output_only=True)
        mic_devices = self.device_probe.get_audio_devices(input_only=True)
        
        self.audio_selector.set_system_devices(system_devices)
        self.audio_selector.set_mic_devices(mic_devices)
        
        self.status_bar.showMessage("Devices refreshed", 2000)
    
    def load_profiles(self):
        profiles = self.settings_manager.get_all_profiles()
        self.profile_combo.clear()
        self.profile_combo.addItem("Custom")
        self.profile_combo.addItems(list(profiles.keys()))
    
    def apply_profile(self, profile_name: str):
        if profile_name == "Custom":
            return
        
        config = self.get_recording_config()
        if self.settings_manager.apply_profile(profile_name, config):
            self.apply_config_to_ui(config)
    
    def get_recording_config(self) -> RecordingConfig:
        config = RecordingConfig()
        
        # Video source
        video_device = self.video_selector.get_selected_device()
        if video_device:
            config.monitor_index = video_device.index
        config.fps = self.video_selector.get_fps()
        config.show_cursor = self.video_selector.get_show_cursor()
        
        # Video encoding
        encoder = self.encoder_selector.get_selected_encoder()
        if encoder:
            config.encoder = encoder
            config.encoder_name = encoder.name
        config.preset = self.encoder_selector.get_preset()
        
        rate_control = self.encoder_selector.get_rate_control()
        if rate_control:
            config.rate_control = RateControl[rate_control]
        
        config.bitrate = self.advanced_panel.get_bitrate()
        config.max_bitrate = self.advanced_panel.get_max_bitrate()
        config.buffer_size = self.advanced_panel.get_buffer_size()
        config.crf = self.advanced_panel.get_crf()
        config.keyframe_interval = self.advanced_panel.get_gop()
        config.profile = self.advanced_panel.get_profile()
        config.scale = self.advanced_panel.get_scale()
        
        # Audio
        system_device = self.audio_selector.get_system_device()
        if system_device:
            config.system_audio_enabled = True
            config.system_audio_device = system_device.device_id
        else:
            config.system_audio_enabled = False
        
        mic_device = self.audio_selector.get_mic_device()
        if mic_device:
            config.mic_enabled = True
            config.mic_device = mic_device.device_id
        else:
            config.mic_enabled = False
        
        config.audio_bitrate = self.advanced_panel.get_audio_bitrate()
        config.audio_sample_rate = self.advanced_panel.get_sample_rate()
        config.normalize_audio = self.advanced_panel.get_normalize()
        
        # Output
        config.container = Container[self.container_combo.currentText().upper()]
        config.output_path = Path(self.output_path_edit.text())
        config.file_pattern = self.pattern_edit.text()
        
        return config
    
    def apply_config_to_ui(self, config: RecordingConfig):
        # This would update UI from config - implementation needed
        pass
    
    @Slot()
    def start_recording(self):
        if not self.recorder:
            QMessageBox.warning(self, "Error", "FFmpeg not available")
            return
        
        config = self.get_recording_config()
        
        # Update settings
        self.settings_manager.update_recording_config(config)
        self.settings_manager.save()
        
        # Start recording
        if self.recorder.start_recording(config):
            self.preview_widget.set_recording(True)
            logger.info("Recording started")
        else:
            QMessageBox.critical(self, "Error", "Failed to start recording")
    
    @Slot()
    def stop_recording(self):
        if self.recorder:
            self.recorder.stop_recording()
            self.preview_widget.set_recording(False)
    
    @Slot()
    def open_output_folder(self):
        path = Path(self.output_path_edit.text())
        if path.exists():
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
    
    @Slot()
    def browse_output_path(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory",
            self.output_path_edit.text()
        )
        if path:
            self.output_path_edit.setText(path)
    
    @Slot(RecorderState)
    def on_recorder_state_changed(self, state: RecorderState):
        if state == RecorderState.IDLE:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.settings_tabs.setEnabled(True)
            self.preview_widget.update_status("Ready")
            
            # Add to recent files
            output_file = self.recorder.get_output_file()
            if output_file and output_file.exists():
                self.settings_manager.add_recent_file(output_file)
                
        elif state == RecorderState.RECORDING:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.settings_tabs.setEnabled(False)
            self.preview_widget.update_status("Recording...")
            
        elif state == RecorderState.STOPPING:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.preview_widget.update_status("Stopping...")
            
        elif state == RecorderState.ERROR:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.settings_tabs.setEnabled(True)
            self.preview_widget.update_status("Error")
    
    @Slot(RecorderStats)
    def on_stats_updated(self, stats: RecorderStats):
        # Format duration
        duration = int(stats.duration)
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Format file size
        size_mb = stats.file_size / (1024 * 1024)
        size_str = f"{size_mb:.1f} MB"
        
        # Update status
        status = f"Recording: {time_str} | {size_str} | {stats.fps:.0f} FPS"
        if stats.dropped_frames > 0:
            status += f" | Dropped: {stats.dropped_frames}"
        
        self.preview_widget.update_status(status)
        self.status_bar.showMessage(status)
    
    @Slot(str)
    def on_log_output(self, text: str):
        self.log_output.append(text)
    
    @Slot(str)
    def on_error(self, message: str):
        QMessageBox.critical(self, "Recording Error", message)
    
    def toggle_log_output(self):
        self.log_output.setVisible(not self.log_output.isVisible())
    
    def reset_to_defaults(self):
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_to_defaults()
            self.restore_settings()
    
    def show_about(self):
        QMessageBox.about(
            self, "About FFScreenRec",
            "FFScreenRec v1.0\n\n"
            "A powerful screen recording application for Windows\n"
            "Built with Python, PySide6, and FFmpeg\n\n"
            "© 2024"
        )
    
    def prompt_for_ffmpeg(self):
        QMessageBox.warning(
            self, "FFmpeg Not Found",
            "FFmpeg was not found on your system.\n\n"
            "Please download FFmpeg from https://ffmpeg.org/download.html\n"
            "and either:\n"
            "1. Place ffmpeg.exe in the 'assets' folder, or\n"
            "2. Add FFmpeg to your system PATH"
        )
    
    def restore_settings(self):
        # Restore window geometry
        geom = self.settings_manager.settings.window_geometry
        self.setGeometry(geom["x"], geom["y"], geom["width"], geom["height"])
        
        # Restore output path
        self.output_path_edit.setText(self.settings_manager.settings.output_path)
    
    def save_settings(self):
        # Save window geometry
        self.settings_manager.settings.window_geometry = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height()
        }
        
        # Save current config
        config = self.get_recording_config()
        self.settings_manager.update_recording_config(config)
        self.settings_manager.save()
    
    def closeEvent(self, event):
        # Stop recording if active
        if self.recorder and self.recorder.get_state() == RecorderState.RECORDING:
            reply = QMessageBox.question(
                self, "Recording in Progress",
                "Recording is still in progress. Stop and exit?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            self.recorder.stop_recording()
        
        # Stop preview
        self.preview.stop_preview()
        
        # Save settings
        self.save_settings()
        
        event.accept()