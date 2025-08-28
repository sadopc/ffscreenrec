#!/usr/bin/env python3
"""
Script to test if recording works in the UI
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from ui.main_window import MainWindow

def test_ui_recording():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    # Get the main window
    windows = app.topLevelWidgets()
    main_window = None
    for window in windows:
        if isinstance(window, MainWindow):
            main_window = window
            break
    
    if not main_window:
        print("Could not find main window")
        return
    
    print("Found main window, attempting to start recording...")
    
    # Simulate clicking the start button
    if hasattr(main_window, 'start_btn'):
        print("Clicking start button...")
        main_window.start_btn.click()
        
        # Wait 5 seconds then stop
        QTimer.singleShot(5000, lambda: stop_recording(main_window))
    else:
        print("Could not find start button")

def stop_recording(main_window):
    print("Stopping recording...")
    if hasattr(main_window, 'stop_btn'):
        main_window.stop_btn.click()
    QTimer.singleShot(1000, lambda: QApplication.quit())

if __name__ == "__main__":
    test_ui_recording()