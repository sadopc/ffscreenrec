from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGroupBox, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor
from typing import Optional, Tuple


class PreviewWidget(QWidget):
    # Signals
    region_selected = Signal(tuple)  # (x, y, width, height)
    
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.selected_region: Optional[Tuple[int, int, int, int]] = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Preview group
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Preview display
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(640, 360)
        self.preview_label.setMaximumSize(1280, 720)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #2a2a2a;
                border: 2px solid #444;
                border-radius: 4px;
            }
        """)
        self.preview_label.setScaledContents(True)
        
        # Set placeholder text
        self.preview_label.setText("Preview will appear here")
        self.preview_label.setStyleSheet(self.preview_label.styleSheet() + """
            color: #888;
            font-size: 14px;
        """)
        
        preview_layout.addWidget(self.preview_label)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #333;
                color: #ccc;
                padding: 8px;
                border-radius: 4px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        preview_layout.addWidget(self.status_label)
        
        layout.addWidget(preview_group)
        
        # Apply dark theme
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
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
        """)
    
    def update_preview(self, pixmap: QPixmap):
        # Clear text if it was showing
        if self.preview_label.text():
            self.preview_label.clear()
            self.preview_label.setStyleSheet(self.preview_label.styleSheet().replace("color: #888;", "").replace("font-size: 14px;", ""))
        
        # Draw recording indicator if recording
        if self.is_recording:
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.drawRect(0, 0, pixmap.width() - 1, pixmap.height() - 1)
            
            # Draw REC indicator
            painter.setPen(QColor(255, 0, 0))
            painter.setBrush(QColor(255, 0, 0))
            painter.drawEllipse(10, 10, 10, 10)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(25, 20, "REC")
            painter.end()
        
        self.preview_label.setPixmap(pixmap)
    
    def set_recording(self, is_recording: bool):
        self.is_recording = is_recording
    
    def update_status(self, status: str):
        self.status_label.setText(status)
    
    def set_region(self, region: Tuple[int, int, int, int]):
        self.selected_region = region
    
    def clear_preview(self):
        self.preview_label.clear()
        self.preview_label.setText("Preview will appear here")
        self.preview_label.setStyleSheet(self.preview_label.styleSheet() + """
            color: #888;
            font-size: 14px;
        """)